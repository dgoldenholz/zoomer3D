"""Drawing-led modular XTI-30. Millimetres, +X left, -Y front, +Z up.

Build with Python + numpy, trimesh, manifold3d, scipy, Pillow and shapely.
These meshes replace the print prototype only; the trained simulator is separate.
"""
from pathlib import Path
import json, math, zipfile
import xml.etree.ElementTree as E
import numpy as np
import trimesh as tm
from manifold3d import Manifold as M, CrossSection as CS

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'print/modular'
PALETTE={'ivory':'#E1E4DCFF','red':'#C33441FF','blue':'#334FA4FF','green':'#70A644FF','dark':'#30333CFF','clear':'#BFDDEB77'}
PARTS={}; META={}; DECOS={}

def box(size,c=(0,0,0)): return M.cube(size,True).translate(c)
def cyl(r,h,c=(0,0,0),axis='Z',r2=None,n=64):
    v=M.cylinder(h,r,r if r2 is None else r2,n,True)
    if axis=='X':v=v.rotate((0,90,0))
    if axis=='Y':v=v.rotate((90,0,0))
    return v.translate(c)
def sphere(r,c):return M.sphere(r,48).translate(c)
def section(outline):
    if sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(outline,outline[1:]+outline[:1]))<0:outline=outline[::-1]
    return CS([outline])
def panel(outline,depth,y=0):
    # Polygon is X,Z; extrude towards -Y.
    return section(outline).extrude(depth).rotate((90,0,0)).translate((0,y+depth/2,0))
def sidepanel(outline,depth,x=0):
    return section(outline).extrude(depth).transform(np.array([[0,0,1,x-depth/2],[1,0,0,0],[0,1,0,0]]))
def stroke(a,b,width=.65,depth=.7,y=-11.75):
    a,b=np.array(a),np.array(b);u=b-a;u=u/np.linalg.norm(u);n=np.array([-u[1],u[0]])*width/2
    return panel([(a+n).tolist(),(a-n).tolist(),(b-n).tolist(),(b+n).tolist()],depth,y)
def shape_mesh(v):
    a=v.simplify(.02).to_mesh64()
    # Quantize once to STL precision before welding. Remove zero-area facets
    # caused by float32 rounding; no hole filling or shape repair is applied.
    t=tm.Trimesh(np.array(a.vert_properties,dtype=np.float32)[:,:3],np.array(a.tri_verts),process=True)
    t.update_faces(t.nondegenerate_faces(height=1e-7));t.update_faces(t.unique_faces());t.remove_unreferenced_vertices()
    return t

def add(name,body,color,orientation,note):
    PARTS[name]=body;DECOS[name]=[];META[name]={'color':color,'rotation_deg':orientation,'print_note':note}
def deco(name,body,color):
    PARTS[name]+=body;DECOS[name].append((body,color))
def clip_back(v,y):return v^box((400,200,400),(0,y-100,100))
def tdhole(r,length,c,axis='X'):
    # Roof apex points towards -Y, the upward direction on back-down prints.
    circle=[(r*math.cos(a),r*math.sin(a)) for a in np.linspace(0,2*math.pi,64,endpoint=False)]
    sec=CS([circle])+CS([[(-r*.707,-r*.707),(0,-r*1.414),(r*.707,-r*.707)]])
    v=sec.extrude(length)
    # cross-section coordinates are Z,Y; extrusion along X.
    if axis=='X':return v.transform(np.array([[0,0,1,c[0]-length/2],[0,1,0,c[1]],[1,0,0,c[2]]]))
    return v.transform(np.array([[1,0,0,c[0]],[0,1,0,c[1]],[0,0,1,c[2]-length/2]]))
def text_solid(txt,size,depth,c):
    # Mesh generated once by Blender's built-in font, never a raster decal.
    f=ROOT/'assets/modular_text'/f'{txt.replace(":","_")}.stl'
    t=tm.load(f); t.apply_scale([size,depth,size]); t.apply_translation(c)
    from manifold3d import Mesh64
    return M(Mesh64(np.array(t.vertices),np.array(t.faces,dtype=np.uint64)))

def build():
    # Wide shoulders, long sculpted chest, short waist measured from zoomer.png.
    outline=[(-42,142),(-38,145),(38,145),(42,142),(40,65),(30,67),(30,76),(12,89),(-12,89),(-30,76),(-30,67),(-40,65)]
    torso=panel(outline,20)
    # Blind, externally accessible shoulder sockets. Teardrop roofs avoid support.
    for s in [-1,1]:torso-=tdhole(4.2,12,(s*39,0,134))
    # Column mortise opens underneath. Head peg socket opens above.
    torso-=box((8.6,6.6,9),(0,0,91.5))
    torso-=tdhole(4.2,12,(0,0,141.5),axis='Z')
    add('torso',torso,'ivory',(-90,0,0),'Back down; chest details face up. No supports.')
    # Crown, central red outline and trapezoidal display surround follow sketch.
    deco('torso',panel([(-42,142),(-38,145),(38,145),(42,142),(42,135),(-42,135)],1.2,-10.2),'red')
    for s in [-1,1]:
        deco('torso',panel([(s*18,133),(s*19.1,133),(s*21.5,103),(s*20.3,103)],.8,-10.3),'red')
    deco('torso',panel([(-20,103),(-13,116),(13,116),(20,103),(17,104),(12,114),(-12,114),(-17,104)],.9,-10.4),'red')
    deco('torso',box((19,1.5,7.4),(0,-10.6,104.5)),'dark')
    for i,col in enumerate(['green','blue','green','blue','red']):deco('torso',box((2.5,1.2,1.2),(-9+i*4.5,-10.6,110.4)),col)
    for s in [-1,1]:
        for z,r,col in [(120,6.1,'green' if s<0 else 'red'),(104.5,5.4,'blue')]:
            deco('torso',cyl(r,1.5,(s*28,-10.4,z),'Y'),'dark')
            deco('torso',cyl(r-.8,1.0,(s*28,-11.2,z),'Y'),'ivory')
            for a in np.linspace(0,2*math.pi,10,endpoint=False):
                deco('torso',stroke((s*28+(r-2)*math.cos(a),z+(r-2)*math.sin(a)),(s*28+(r-1.2)*math.cos(a),z+(r-1.2)*math.sin(a))),col)
            deco('torso',stroke((s*28,z),(s*28-1.7,z+3),.8),'dark')
        tri=[(s*35,79),(s*35,95),(s*16,95)]
        deco('torso',panel(tri,.9,-10.4),'dark')
        for z in [84,87,90,93]:
            w=(z-79)*19/16-2
            if w>1:deco('torso',box((w,.65,.65),(s*(35-w/2-1),-11,z)),'ivory')
        deco('torso',panel([(s*37,68),(s*37,75),(s*31,76),(s*31,70)],.9,-10.3),'green')
    deco('torso',text_solid('XTI-30',6.7,.7,(-14.8,-9.85,124)),'dark')
    deco('torso',text_solid('10:15',3.5,.6,(-6.8,-11.25,103)),'ivory')
    # Three-part base. All track wheels and tread pads fuse to a solid side plate.
    chassis=box((60,46,10),(0,0,25))+box((55,41,6),(0,0,33))+box((43,34,4),(0,0,38))
    chassis-=box((8.6,6.6,8),(0,0,39))
    for s in [-1,1]:
        for y in [-12,12]:chassis-=box((9.6,6.6,4),(s*22.5,y,21.5))
    add('base_deck',chassis,'blue',(0,0,0),'Flat underside down. No supports; key sockets bridge 6.6 mm.')
    deco('base_deck',box((55,41,5.5),(0,0,33.25)),'red')
    deco('base_deck',box((43,34,3.8),(0,0,38.1)),'ivory')
    deco('base_deck',cyl(11,2,(0,0,40)),'green')
    # Recut the socket through all decoration.
    PARTS['base_deck']-=box((8.6,6.6,10),(0,0,39))
    for s in [-1,1]:
        for y in [-10,-5,0,5,10]:deco('base_deck',box((8,2,1),(s*16,y,40.2)),'green')
        n='left_track' if s>0 else 'right_track'
        # Steep front and longer rear slope, flat contact footprint.
        path=[(-26,4),(-23,0),(19,0),(27,4),(28,10),(19,20),(-20,20),(-26,9)]
        track=sidepanel(path,12,s*24)
        for y in [-12,12]:track+=box((9,6,3.5),(s*22.5,y,21.25))
        add(n,track,'dark',(0,-s*90,0),'Inner broad face down; wheel faces up. No supports.')
        for y,z,r in [(-19,6,4.8),(-9,5.7,4.5),(1,5.7,4.5),(11,5.7,4.5),(21,7,4.5),(-13,15,3.5),(-3,15,3.5),(7,15,3.5)]:
            deco(n,cyl(r,1.2,(s*30.2,y,z),'X'),'blue')
            deco(n,cyl(r*.44,.9,(s*30.9,y,z),'X'),'dark')
        for a,b in zip(path,path[1:]+path[:1]):
            a,b=np.array(a,dtype=float),np.array(b,dtype=float);d=b-a;length=np.linalg.norm(d);u=d/length;normal=np.array([-u[1],u[0]])
            for distance in np.arange(1.8,length-1,3.3):
                center=a+distance*u
                corners=[(center+u*du+normal*dn).tolist() for du,dn in [(-.5,-.25),(.5,-.25),(.5,.65),(-.5,.65)]]
                PARTS[n]-=sidepanel(corners,12.1,s*24)
    # One solid, flat-backed column. Longitudinal layers carry the chest.
    col=cyl(5.2,48,(0,0,65))+box((8,6,7),(0,0,37.5))+box((8,6,7),(0,0,91.5))
    for z in [46,56,66,76,86]:col+=cyl(8,2.5,(0,0,z),r2=6.4)
    col=clip_back(col,3)
    add('waist_column',col,'blue',(-90,0,0),'Flat rear down. No supports. End keys glue into torso and deck.')
    for z in [46,56,66,76,86]:deco('waist_column',clip_back(cyl(8,2.5,(0,0,z),r2=6.4),3),'red')
    # Solid arms. Flat rear and planar claws remove all finger and wrist hinges.
    for s in [-1,1]:
        n='left_arm' if s>0 else 'right_arm';x=s*58
        arm=panel([(x-10,142),(x-8,145),(x+8,145),(x+10,142),(x+9,111),(x+7,106),(x+8,99),(x+8,77),(x+6,60),(x-6,60),(x-8,77),(x-8,99),(x-7,106),(x-9,111)],13)
        # Circular shoulder boss inside, with 0.6 mm axial gap to torso.
        arm+=clip_back(cyl(9,25.4,(s*55.3,0,134),'X'),6.5)
        for sign in [-1,1]:
            # Thick, fixed pincer outline. Both fingers remain supported from bed.
            a=(x+sign*3,0,61);b=(x+sign*9,0,53);c=(x+sign*3,0,40)
            arm+=panel([(a[0]-1.6,a[2]),(b[0]-1.6,b[2]),(c[0]-1.6,c[2]),(c[0]+1.6,c[2]),(b[0]+1.6,b[2]),(a[0]+1.6,a[2])],13)
        arm-=tdhole(4.35,32,(x,0,134))
        add(n,arm,'ivory',(-90,0,0),'Flat rear down; cosmetic front up. Shoulder hole has a teardrop roof.')
        deco(n,panel([(x-10,142),(x-8,145),(x+8,145),(x+10,142),(x+10,137),(x-10,137)],1,-6.7),'red')
        deco(n,box((13,1.0,8),(x,-6.7,112)),'green')
        deco(n,panel([(x-8,87),(x,80),(x+8,87),(x+8,76),(x-8,76)],1,-6.7),'blue')
        for z in [71,74]:deco(n,box((14,1.4,1.4),(x,-6.9,z)),'dark')
        for dx in [-4,4]:deco(n,box((.9,1.1,17),(x+dx,-6.9,93)),'ivory')
        for dx in [-6,-3,0,3,6]:deco(n,box((1,1.5,13),(x+dx,-9.1,134)),'dark')
        # Inset shoulder pin head stops at the outer arm face, separate from rotor.
        pin=cyl(4,33.3,(s*51.65,0,134),'X')+cyl(6,2,(s*69.3,0,134),'X')
        # Reduced leading tip; the full 8 mm shaft anchors inside the torso.
        pin+=cyl(3.7,1,(s*34.5,0,134),'X')
        add('left_shoulder_pin' if s>0 else 'right_shoulder_pin',pin,'red',(0,s*90,0),'Flange down. Glue only the inner 5 mm into the torso; leave the arm free.')
    # Head deck and face. Broad eye stalks and joined cheeks avoid thin islands.
    head_socket=cyl(4.3,8,(0,0,139.9))+cyl(4.3,4.3,(0,0,146.05),r2=0)
    head_deck=cyl(29.5,1.2,(0,0,141.6))+cyl(27.5,1.4,(0,0,142.7))
    head=head_deck
    head+=box((21,13,17),(0,0,151.5))
    head-=head_socket
    add('head',head,'green',(0,0,0),'Deck down. The peg socket has a 45-degree conical roof.')
    deco('head',head_deck,'ivory')
    for s in [-1,1]:
        deco('head',panel([(s*11,143),(s*11,160),(s*17,163),(s*21,159),(s*21,143)],13,0),'blue')
        deco('head',box((6,1.8,12),(s*7,-7.0,149)),'blue')
        deco('head',box((3.6,4.0,7),(s*5.5,-.2,162)),'ivory')
        deco('head',CS.square((3.6,4),True).extrude(1,scale_top=(5.5/3.6,4.5/4)).translate((s*5.5,-.2,163.6))+box((5.5,4.5,3.8),(s*5.5,-.2,166.5)),'ivory')
        deco('head',cyl(1.6,1.4,(s*5.5,-2.0,166),'Y'),'red')
    deco('head',box((5.5,.7,2.3),(0,-6.5,146)),'dark')
    PARTS['head']-=head_socket
    peg=cyl(4,11,(0,0,142))+cyl(3.7,1,(0,0,148))
    add('head_peg',peg,'ivory',(0,0,0),'Upright. Glue lower end into torso only; head lifts off.')
    # Independent dome: support is exposed and can be removed before installation.
    PARTS['head']=PARTS['head'].translate((0,0,4.4))
    DECOS['head']=[(b.translate((0,0,4.4)),c) for b,c in DECOS['head']]
    outer=M.sphere(1,128).scale((29.5,29.5,33.4)).translate((0,0,146.6))
    inner=M.sphere(1,128).scale((28.1,28.1,32.0)).translate((0,0,146.6))
    dome=(outer-inner)^box((70,70,42),(0,0,167.6))
    add('dome',dome,'clear',(0,0,0),'Rim down. Optional clear PETG; accessible interior supports required near crown.')
    # Trim decoration to final solids after all holes and slots have been cut.
    for n in PARTS:DECOS[n]=[(b^PARTS[n],c) for b,c in DECOS[n]]


def color_volumes(n):
    from manifold3d import OpType
    masks={}
    for b,c in DECOS[n]:masks.setdefault(c,[]).append(b)
    remainder=PARTS[n];vols=[]
    for c in ['dark','green','blue','red','ivory']:
        if c not in masks:continue
        mask=M.batch_boolean(masks[c],OpType.Add)
        b=mask^remainder
        if b.volume()>1e-6:vols.append((c,b));remainder-=b
    if remainder.volume()>1e-6:vols.append((META[n]['color'],remainder))
    grouped={}
    for c,b in vols:grouped[c]=grouped.get(c,M())+b
    return [(c,b) for c,b in grouped.items() if b.volume()>1e-6]

def write3mf(path,objects):
    ns='http://schemas.microsoft.com/3dmanufacturing/core/2015/02';tag=lambda x:'{'+ns+'}'+x
    E.register_namespace('',ns)
    model=E.Element(tag('model'),unit='millimeter',attrib={'xmlns:slic3rpe':'http://schemas.slic3r.org/3mf/2017/06'})
    E.SubElement(model,tag('metadata'),name='slic3rpe:Version3mf').text='1'
    res=E.SubElement(model,tag('resources'));build=E.SubElement(model,tag('build'));conf=E.Element('config')
    palette=list(PALETTE); mats=E.SubElement(res,tag('basematerials'),id='900')
    for c in palette:E.SubElement(mats,tag('base'),name=c,displaycolor=PALETTE[c])
    for idx,(name,volumes) in enumerate(objects,1):
        obj=E.SubElement(res,tag('object'),id=str(idx),type='model',name=name)
        mesh=E.SubElement(obj,tag('mesh'));vs=E.SubElement(mesh,tag('vertices'));ts=E.SubElement(mesh,tag('triangles'))
        co=E.SubElement(conf,'object',id=str(idx),instances_count='1');E.SubElement(co,'metadata',type='object',key='name',value=name)
        vo=fo=0
        for col,t in volumes:
            for v in t.vertices:E.SubElement(vs,tag('vertex'),**dict(zip('xyz',[f'{x:.7f}' for x in v])))
            for f in t.faces:E.SubElement(ts,tag('triangle'),v1=str(f[0]+vo),v2=str(f[1]+vo),v3=str(f[2]+vo),pid='900',p1=str(palette.index(col)))
            cv=E.SubElement(co,'volume',firstid=str(fo),lastid=str(fo+len(t.faces)-1))
            for k,v in [('name',col),('volume_type','ModelPart'),('extruder',str(min(palette.index(col)+1,5)))]:E.SubElement(cv,'metadata',type='volume',key=k,value=v)
            vo+=len(t.vertices);fo+=len(t.faces)
        E.SubElement(build,tag('item'),objectid=str(idx))
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml','<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/><Default Extension="config" ContentType="application/xml"/></Types>')
        z.writestr('_rels/.rels','<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr('3D/3dmodel.model',E.tostring(model));z.writestr('Metadata/Slic3r_PE_model.config',E.tostring(conf))

def main():
    for sub in ['parts','assembled','plates','qa','colors']:(OUT/sub).mkdir(parents=True,exist_ok=True)
    build();print('Built solids',flush=True);report={'units':'mm','physical_print_test':'not performed','parts':{},'intersections':[]}
    plate=[];assembly=[];colored=[];manifest={};px=35;py=40;rowheight=0
    for n,v in PARTS.items():
        print('Exporting',n,flush=True);t=shape_mesh(v);t.export(OUT/'assembled'/f'{n}.stl')
        rot=tm.transformations.euler_matrix(*np.radians(META[n]['rotation_deg']))
        p=t.copy();p.apply_transform(rot);offset=-p.bounds[0];p.apply_translation(offset)
        p.export(OUT/'parts'/f'{n}.stl')
        reread=tm.load(OUT/'parts'/f'{n}.stl')
        report['parts'][n]={'watertight':bool(reread.is_watertight),'components':len(reread.split(only_watertight=False)),'volume_mm3':float(t.volume),'print_dimensions_mm':p.extents.tolist(),'assembled_bounds_mm':t.bounds.tolist(),'bed_contact_area_mm2':float(p.area_faces[(p.face_normals[:,2]<-.999)&(p.triangles_center[:,2]<.001)].sum())}
        colors=[]
        for c,b in color_volumes(n):
            m=shape_mesh(b);m.export(OUT/'colors'/f'{n}__{c}.stl');colors.append((c,m))
        assembly.append((n,colors))
        # Main parts grouped into one short, broad plate. Dome has a separate plate.
        if n=='dome':place=np.array([145,145,0])
        else:
            if px+p.extents[0]>325:px=35;py+=rowheight+12;rowheight=0
            place=np.array([px,py,0]);px+=p.extents[0]+12;rowheight=max(rowheight,p.extents[1])
        pc=[]
        for c,m in colors:
            m=m.copy();m.apply_transform(rot);m.apply_translation(offset+place);pc.append((c,m))
        if n=='dome':write3mf(OUT/'plates/dome_geometry.3mf',[(n,[('ivory',pc[0][1])])])
        else:
            colored.append((n,pc));plain=p.copy();plain.apply_translation(place);plate.append((n,[('ivory',plain)]))
        manifest[n]={**META[n],'print_translation_mm':offset.tolist(),'plate_translation_mm':place.tolist()}
    write3mf(OUT/'plates/main_single_material.3mf',plate)
    write3mf(OUT/'plates/main_five_color.3mf',colored)
    write3mf(OUT/'assembly_view_only.3mf',assembly)
    names=list(PARTS)
    for i,a in enumerate(names):
        for b in names[i+1:]:
            overlap=(PARTS[a]^PARTS[b]).volume()
            if overlap>.005:report['intersections'].append({'a':a,'b':b,'volume_mm3':overlap})
    bounds=np.array([shape_mesh(v).bounds for v in PARTS.values()]);report['assembled_dimensions_mm']=(bounds[:,1].max(0)-bounds[:,0].min(0)).tolist()
    report['mesh_pass']=all(v['watertight'] and v['components']==1 for v in report['parts'].values())
    assert report['mesh_pass'], 'Resolve invalid or disconnected parts before packaging.'
    assert not report['intersections'], 'Resolve assembled intersections before packaging.'
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));(OUT/'qa/geometry.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
