"""Faceted vase cover, sheet-window cover, and a flat-wall optical test.

Dimensions are millimetres. Assembly coordinates use the existing head ledge.
Vase inputs are solid envelopes; inspection meshes approximate the printed wall.
"""
from pathlib import Path
import json, math, subprocess, hashlib
import numpy as np
import trimesh as tm
from manifold3d import Manifold as M, CrossSection as CS, JoinType
import build_modular_print as b
from build_vase_dome import solid_mesh, solid
from package_modular_print import config, embed_config, SLICER

ROOT=b.ROOT;OUT=ROOT/'print/flat_window_domes'
BASE=2.25;TOP=28.25;CAP_BOTTOM=27.25;CAP_TOP=33.5
H=TOP-BASE;SCALE_TOP=.68;WIDTH=.6;HEAD_Z=146.6
K=21*(1-SCALE_TOP)/H;N=math.sqrt(1+K*K);VL=H*N
RAW=[(-20,-21),(20,-21),(27.5,-10),(27.5,10),(20,21),(-20,21),(-27.5,10),(-27.5,-10)]
P0=CS([RAW]).offset(-1,JoinType.Miter).offset(1,JoinType.Round,circular_segments=48)

def scale(z):return 1-(1-SCALE_TOP)*(z-BASE)/H
def section(z,offset=0):
    return P0.scale((scale(z),scale(z))).offset(offset,JoinType.Miter)
def hull_sections(profiles):
    pts=[]
    for z,cs in profiles:
        for contour in cs.to_polygons():pts.extend([[float(x),float(y),float(z)] for x,y in contour])
    return M.hull_points(np.asarray(pts))
def frustum(z0,z1,offset=0):return hull_sections([(z0,section(z0,offset)),(z1,section(z1,offset))])
def flat_shape(points):return b.section(points)
def planar(v,w=0):
    # local x = horizontal, y = distance up the inclined front, z = outward.
    return v.transform(np.array([[1,0,0,0],[0,K/N,-1/N,-21-w/N],[0,1/N,K/N,BASE+w*K/N]]))
def front_halfwidth(v,margin):return 20*scale(BASE+v/N)-margin
def trap(v0,v1,margin):
    a=front_halfwidth(v0,margin);c=front_halfwidth(v1,margin)
    return flat_shape([(-a,v0),(a,v0),(c,v1),(-c,v1)])

def export(name,v):
    t=solid_mesh(v);assert t.is_volume and len(t.split())==1,name
    t.export(OUT/'parts'/f'{name}.stl')
    check=tm.load(OUT/'parts'/f'{name}.stl');assert check.is_volume and len(check.split())==1,name
    return t

def build():
    # The front and seven surrounding faces are planes. Only their corners
    # are rounded, away from the viewing region.
    envelope=frustum(BASE,TOP)
    thin=envelope-frustum(BASE-.05,TOP+.05,-WIDTH)
    test=CS.square((50,32),True).offset(-1,JoinType.Miter).offset(1,JoinType.Round,circular_segments=48)
    test_envelope=test.extrude(20)
    test_wall=test_envelope-test.offset(-WIDTH,JoinType.Miter).extrude(20.1).translate((0,0,-.05))

    # Adapter prints top face down. Its underside fits the known 55 mm lip.
    # The 0.75 mm plate starts 0.30 mm above that lip, keeping it off the face.
    adapter=b.cyl(30,BASE,(0,0,BASE/2),n=192)
    adapter-=b.cyl(27.9,1.7,(0,0,.65),n=192)
    aperture=CS.square((45,19),True).offset(-1,JoinType.Miter).offset(1,JoinType.Round,circular_segments=32)
    adapter-=aperture.extrude(BASE+1).translate((0,0,-.1))

    # Common cap with a socket around the 0.6 mm edge. Both printed variants
    # and the 0.5 mm sheet meet this socket. Its roof closes gradually.
    cap_outline=section(CAP_BOTTOM,1.25)
    profiles=[]
    for t in np.linspace(0,1,90):
        s=(1-t)**3+3*(1-t)**2*t*.96+3*(1-t)*t*t*.55
        z=(1-t)**3*CAP_BOTTOM+3*(1-t)**2*t*(CAP_BOTTOM+3.125)+3*(1-t)*t*t*CAP_TOP+t**3*CAP_TOP
        profiles.append((z,cap_outline.scale((max(s,.00001),max(s,.00001)))))
    cap=hull_sections(profiles)
    # Check the blind groove roof stays inside the crown, including corners.
    from shapely.geometry import Polygon,Point
    cap_ligaments=[]
    for z in np.linspace(CAP_BOTTOM+.001,TOP+.749,60):
        cp=Polygon(cap.slice(z).to_polygons()[0])
        off=.25 if z<=TOP else .25-(z-TOP)*(.55/.75)
        gp=Polygon(section(min(z,TOP),off).to_polygons()[0])
        assert cp.covers(gp),'Socket breaks through crown'
        cap_ligaments.append(cp.boundary.distance(gp.boundary))
    assert min(cap_ligaments)>.55
    zmid=TOP+.75
    gos=[(CAP_BOTTOM-.1,section(CAP_BOTTOM-.1,.25)),(TOP,section(TOP,.25)),(zmid,section(TOP,-.3))]
    gis=[(CAP_BOTTOM-.1,section(CAP_BOTTOM-.1,-.85)),(TOP,section(TOP,-.85)),(zmid,section(TOP,-.3))]
    groove=M()
    for i in range(2):groove+=hull_sections(gos[i:i+2])-hull_sections(gis[i:i+2])
    cap-=groove

    # Normal-printed C-shaped hood, open across the front up to its top.
    # The upper edge reduces to the same thickness as the vase shell.
    body=envelope-frustum(BASE-.05,27.0,-1.2)-frustum(27.0,TOP+.05,-WIDTH)
    opening=trap(.25,VL+3,2.5)
    body-=planar(opening.extrude(6),-3)
    sheet_profile=trap(.25,VL,1.0)
    rebate=sheet_profile.offset(.2,JoinType.Miter)
    body-=planar(rebate.extrude(3),-.60)
    sheet=planar(sheet_profile.extrude(.5),-.5)
    # A flat retaining frame is bonded along the solid outer side ledges.
    # Its top stays below the cap so it never crowds the cap's socket.
    vb=(CAP_BOTTOM-.30-BASE)*N
    bezel_outer=trap(0,vb,.15)
    # Omit the bottom crossbar to keep the low mouth detail in view.
    bezel_hole=trap(-1,vb-.65,2.5)
    bezel_local=(bezel_outer-bezel_hole).extrude(1.0)
    bezel=planar(bezel_local,.1)

    meshes={
        '01_flat_wall_test_VASE_SOLID':export('01_flat_wall_test_VASE_SOLID',test_envelope),
        '02_faceted_shell_VASE_SOLID':export('02_faceted_shell_VASE_SOLID',envelope.translate((0,0,-BASE))),
        '03_shared_cap_NORMAL':export('03_shared_cap_NORMAL',cap.translate((0,0,-CAP_BOTTOM))),
        '04_shared_adapter_NORMAL':export('04_shared_adapter_NORMAL',adapter.rotate((180,0,0)).translate((0,0,BASE))),
        '05_sheet_window_hood_NORMAL':export('05_sheet_window_hood_NORMAL',body.translate((0,0,-BASE))),
        '06_sheet_retainer_NORMAL':export('06_sheet_retainer_NORMAL',bezel_local),
    }
    assemblies={'faceted_shell':thin,'shared_cap':cap,'shared_adapter':adapter,'sheet_hood':body,'clear_sheet_NOT_FOR_PRINTING':sheet,'sheet_retainer':bezel}
    for name,v in assemblies.items():solid_mesh(v.translate((0,0,HEAD_Z))).export(OUT/'inspection_only'/f'{name}.stl')
    solid_mesh(test_wall).export(OUT/'inspection_only/flat_wall_test.stl')
    head=solid(tm.load(ROOT/'print/modular/assembled/head.stl'))
    overlaps={name:float((v.translate((0,0,HEAD_Z))^head).volume()) for name,v in assemblies.items()}
    for names in [('faceted_shell','shared_adapter','shared_cap'),('sheet_hood','clear_sheet_NOT_FOR_PRINTING','sheet_retainer','shared_adapter','shared_cap')]:
        for i,name in enumerate(names):
            for other in names[i+1:]:overlaps[f'{name}/{other}']=float((assemblies[name]^assemblies[other]).volume())
    assert max(overlaps.values())<.003,overlaps
    # Frontward rays from face landmarks must pass through both frame holes.
    op=Polygon(opening.to_polygons()[0]);bp=Polygon(bezel_hole.to_polygons()[0])
    visibility=[]
    for x,z,label in [(-8.25,26.2,'left eye outer top'),(8.25,26.2,'right eye outer top'),(-2.75,2.65,'mouth lower left'),(2.75,2.65,'mouth lower right')]:
        # A horizontal line at height z intersects the two inclined faces at
        # different v because the frame stands 1.1 mm forward of the hood.
        for w,poly in [(-.5,op),(1.1,bp)]:
            vv=(z-BASE)*N-w*K
            visibility.append({'feature':label,'plane_offset_mm':w,'visible':bool(poly.contains(Point(x,vv)))})
    assert all(item['visible'] for item in visibility),visibility
    stats={}
    for name,t in meshes.items():
        bottom=(t.face_normals[:,2]<-.999)&(t.triangles_center[:,2]<1e-4)
        stats[name]={'dimensions_mm':t.extents.tolist(),'volume_mm3':float(t.volume),'watertight':bool(t.is_watertight),'connected_components':len(t.split()),'bed_contact_area_mm2':float(t.area_faces[bottom].sum())}
    report={'layer_mm':.25,'nozzle_mm':.4,'vase_width_mm':WIDTH,'parts':stats,'intersection_volumes_mm3':overlaps,
        'front_panel_base_width_mm':40,'front_panel_top_width_mm':27.2,'front_panel_tilt_deg':math.degrees(math.atan(K)),
        'faceted_shell_print_height_mm':H,'overall_cover_height_mm':CAP_TOP,'adapter_bore_diameter_mm':55.8,
        'adapter_lip_vertical_clearance_mm':.3,'cap_eye_vertical_clearance_mm':1.05,
        'minimum_cap_material_outside_groove_mm':min(cap_ligaments),
        'max_face_inward_step_per_layer_mm':27.5*(1-SCALE_TOP)/H*.25,
        'sheet_thickness_mm':.5,'sheet_rebate_depth_mm':.6,'sheet_edge_clearance_mm':.2,
        'sheet_outline_x_v_mm':np.asarray(sheet_profile.to_polygons()[0]).tolist(),
        'sheet_dimensions_mm':[2*front_halfwidth(.25,1),2*front_halfwidth(VL,1),VL-.25],
        'face_visibility_checks':visibility,'physical_test':'Not performed. The previous curved vase dome improved clarity but distorted the image, per user feedback.',
        'head_sha256':hashlib.sha256((ROOT/'print/modular/assembled/head.stl').read_bytes()).hexdigest()}
    (OUT/'qa/geometry.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'overlaps':overlaps,'visibility':visibility},indent=2))
    return meshes

def package(meshes):
    vase=ROOT/'print/vase_dome/profiles/01_XL_viewing_shell_VASE.ini'
    normal=ROOT/'print/vase_dome/profiles/02_XL_cap_and_ring_NORMAL.ini'
    specs=[('01_XL_flat_wall_test_VASE',vase,['01_flat_wall_test_VASE_SOLID'],[(180,180,0)]),
        ('02_XL_faceted_shell_VASE',vase,['02_faceted_shell_VASE_SOLID'],[(180,180,0)]),
        ('03_XL_shared_cap_and_adapter_NORMAL',normal,['03_shared_cap_NORMAL','04_shared_adapter_NORMAL'],[(140,175,0),(215,175,0)]),
        ('04_XL_sheet_hood_and_retainer_NORMAL',normal,['05_sheet_window_hood_NORMAL','06_sheet_retainer_NORMAL'],[(145,180,0),(220,163,0)])]
    jobs=[]
    for name,src,names,locations in specs:
        cfg=OUT/'profiles'/f'{name}.ini';config(src,{'print_settings_id':f'"Zoomer flat viewing cover - {name}"'},cfg)
        objects=[]
        for part,loc in zip(names,locations):
            m=meshes[part].copy();m.apply_translation(loc);objects.append((part,[('ivory',m)]))
        geometry=OUT/'qa'/f'{name}_geometry.3mf';b.write3mf(geometry,objects)
        project=OUT/f'{name}.3mf'
        with (OUT/'qa'/f'{name}_import.log').open('w') as log:
            subprocess.run([str(SLICER),'--load',str(cfg),'--dont-arrange','--export-3mf','--output',str(project),str(geometry)],stdout=log,stderr=subprocess.STDOUT,check=True)
        embed_config(project,cfg)
        gc=Path('/private/tmp')/f'zoomer_{name}.gcode'
        with (OUT/'qa'/f'{name}_slice.log').open('w') as log:
            subprocess.run([str(SLICER),'--dont-arrange','--export-gcode','--output',str(gc),str(project)],stdout=log,stderr=subprocess.STDOUT,check=True)
        jobs.append({'name':name,'project':str(project.relative_to(ROOT)),'gcode':str(gc),'vase':src==vase,'parts':names})
    (OUT/'qa/jobs.json').write_text(json.dumps(jobs,indent=2)+'\n')

if __name__=='__main__':
    for sub in ['parts','profiles','inspection_only','qa','templates']:(OUT/sub).mkdir(parents=True,exist_ok=True)
    package(build())
