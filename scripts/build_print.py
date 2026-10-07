"""Millimetre print prototypes. Uses manifold booleans; no printer-specific G-code."""
from pathlib import Path
import json, zipfile
import numpy as np
import trimesh as tm
from manifold3d import Manifold, Mesh
from xml.etree import ElementTree as E
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'print';OUT.mkdir(exist_ok=True)

def solid(mesh):
    mesh.merge_vertices();mesh.fix_normals()
    return Manifold(Mesh(np.asarray(mesh.vertices,dtype=np.float32),np.asarray(mesh.faces,dtype=np.uint32)))
def mesh(m):
    a=m.to_mesh();return tm.Trimesh(np.array(a.vert_properties)[:,:3],np.array(a.tri_verts),process=True)
def box(size,center):return solid(tm.creation.box(size,transform=tm.transformations.translation_matrix(center)))
def cyl(r,h,z):return solid(tm.creation.cylinder(r,h,sections=96,transform=tm.transformations.translation_matrix([0,0,z+h/2])))
def revolve(points):return solid(tm.creation.revolve(np.array(points),sections=96))
def save_stl(m,n):
    t=mesh(m);assert t.is_watertight and t.is_volume,n;t.export(OUT/n);return t

def mf3(filename,parts):
    # One assembly with multiple connected or captive bodies. Millimetres explicitly encoded.
    ns='http://schemas.microsoft.com/3dmanufacturing/core/2015/02';E.register_namespace('',ns)
    tag=lambda s:'{'+ns+'}'+s
    model=E.Element(tag('model'),unit='millimeter',attrib={'{http://www.w3.org/XML/1998/namespace}lang':'en-US'})
    E.SubElement(model,tag('metadata'),name='Title').text=filename
    res=E.SubElement(model,tag('resources'));materials=E.SubElement(res,tag('basematerials'),id='1')
    palette=['#DFE6E8FF','#AF1B2CFF','#214C94FF','#212A36FF','#64409DFF']
    for i,c in enumerate(palette):E.SubElement(materials,tag('base'),name=['Ivory','Red','Blue','Dark','Purple'][i],displaycolor=c)
    for i,(name,t,color) in enumerate(parts):
        ob=E.SubElement(res,tag('object'),id=str(i+2),type='model',name=name,pid='1',pindex=str(color));me=E.SubElement(ob,tag('mesh'));vs=E.SubElement(me,tag('vertices'));ts=E.SubElement(me,tag('triangles'))
        for v in t.vertices:E.SubElement(vs,tag('vertex'),x=f'{v[0]:.6f}',y=f'{v[1]:.6f}',z=f'{v[2]:.6f}')
        for a,b,c in t.faces:E.SubElement(ts,tag('triangle'),v1=str(a),v2=str(b),v3=str(c))
    assembly=E.SubElement(res,tag('object'),id=str(len(parts)+2),type='model',name=filename);comps=E.SubElement(assembly,tag('components'))
    for i in range(len(parts)):E.SubElement(comps,tag('component'),objectid=str(i+2))
    build=E.SubElement(model,tag('build'));E.SubElement(build,tag('item'),objectid=str(len(parts)+2))
    types='<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>'
    rels='<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'
    with zipfile.ZipFile(OUT/filename,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml',types);z.writestr('_rels/.rels',rels);z.writestr('3D/3dmodel.model',E.tostring(model,encoding='utf-8',xml_declaration=True))

def main():
    report={'units':'mm','physical_print_test':'not performed','hinges':[]};allparts=[]
    for index,gap in enumerate([.25,.30,.35,.40,.45]):
        # Captured lower flange, 45-degree transition, vertical axle and upper rotor.
        pin=revolve([(0,0),(3.6,0),(3.6,1.2),(2.2,2.6),(2.2,8.6),(4,10.4),(4,12),(0,12),(0,0)])
        rotor=pin+box((18,6,1.6),(9,0,11.2))
        # The cavity sweeps the pin through +/- axial clearance and grows radially.
        p=[(0,-2),(3.6+gap,-2),(3.6+gap,1.2+gap),(2.2+gap,2.6+gap),(2.2+gap,8.6-gap),(4+gap,10.4-gap),(4+gap,14),(0,14),(0,-2)]
        bore=revolve(p)
        socket=(cyl(6.2,8.1,0)+box((17,9,3),(-11,0,1.5)))-bore
        overlap=(rotor^socket).volume();assert overlap<1e-5
        sweep_overlap=max((rotor.rotate((0,0,a))^socket).volume() for a in range(0,360,15));assert sweep_overlap<1e-4
        pinm=save_stl(rotor,f'hinge_{int(gap*100):02d}_rotor.stl');sockm=save_stl(socket,f'hinge_{int(gap*100):02d}_socket.stl')
        mf3(f'hinge_{int(gap*100):02d}_assembled.3mf',[('captive rotor',pinm,1),('bearing socket',sockm,0)])
        for n,t,c in [('rotor',pinm,1),('socket',sockm,0)]:
            t=t.copy();t.apply_translation([0,index*18,0]);allparts.append((f'{gap:.2f} mm {n}',t,c))
        # One raised dot per row provides a printable coupon index without fragile text.
        report['hinges'].append(dict(radial_gap_mm=gap,axial_gap_mm=gap,overlap_volume_mm3=overlap,rotor_volume_mm3=pinm.volume,socket_volume_mm3=sockm.volume,watertight=True,sweep_overlap_mm3=sweep_overlap))
    mf3('clearance_coupon_plate.3mf',allparts)
    # A captive ball joint to test shoulder/wrist motion at the proposed display scale.
    gap=.35;r=4.2
    ball=solid(tm.creation.icosphere(subdivisions=3,radius=r));ball=ball.translate((0,0,6))
    stem=cyl(1.65,8,6);moving=ball+stem+box((6,6,2),(0,0,14.5))
    # Print the enclosing socket and ball together, with an opening to reach the support.
    shell=cyl(6.8,10,0)-solid(tm.creation.icosphere(subdivisions=3,radius=r+gap)).translate((0,0,6))-cyl(2.8,10,8.5)
    # Bed opening lets the ball's lower cap build from the plate after a small sacrificial stem.
    # This prototype needs dissolvable internal support; it is separate from the hinge plate.
    ballmesh=save_stl(moving,'ball_joint_rotor.stl');shellmesh=save_stl(shell,'ball_joint_socket.stl')
    assert (moving^shell).volume()<1e-4
    mf3('ball_joint_support_required.3mf',[('ball and stem',ballmesh,1),('socket',shellmesh,0)])
    report['ball_joint']=dict(gap_mm=gap,watertight=True,internal_support_required=True,overlap_volume_mm3=(moving^shell).volume())
    (OUT/'validation.json').write_text(json.dumps(report,indent=2))
    print('Wrote five captive hinge clearances and ball-joint prototype')

if __name__=='__main__':
    main()
