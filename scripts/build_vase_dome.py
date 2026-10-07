"""Three-piece optical experiment for the existing modular Zoomer head.

The vase input is a solid envelope. The thin assembly mesh is for inspection only.
All dimensions are millimetres. Neither the original head nor its dome is changed.
"""
from pathlib import Path
import json, math, hashlib, subprocess
import numpy as np
import trimesh as tm
from manifold3d import Manifold, CrossSection, Mesh64
import build_modular_print as b
from package_modular_print import config, embed_config, SLICER

ROOT=b.ROOT
OUT=ROOT/'print/vase_dome'
R=29.5
A=33.4
LAYER=.25
WIDTH=.60
BASE_Z=.75
TOP_Z=28.25
CAP_BOTTOM=27.25
CAP_TOP=33.5
SLOPE=.8
CLEARANCE=.25
HEAD_LEDGE_Z=146.6
TRANSITION=A*SLOPE/math.sqrt(SLOPE*SLOPE+(R/A)**2)
TRANSITION_R=R*math.sqrt(1-(TRANSITION/A)**2)

def radius(z):
    return R*math.sqrt(1-(z/A)**2) if z<=TRANSITION else TRANSITION_R-SLOPE*(z-TRANSITION)

def revolve(points):
    return CrossSection([points]).revolve(256)

def outer_solid(zs,rs):
    return revolve([(0,float(zs[0]))]+[(float(r),float(z)) for z,r in zip(zs,rs)]+[(0,float(zs[-1]))])

def solid_mesh(v):
    m=v.to_mesh64()
    return tm.Trimesh(np.asarray(m.vert_properties)[:,:3],np.asarray(m.tri_verts),process=True)

def solid(t):
    return Manifold(Mesh64(np.asarray(t.vertices,dtype=float),np.asarray(t.faces,dtype=np.uint64)))

def export(name,v):
    t=solid_mesh(v)
    assert t.is_volume and len(t.split())==1,name
    t.export(OUT/'parts'/f'{name}.stl')
    reloaded=tm.load(OUT/'parts'/f'{name}.stl')
    assert reloaded.is_volume and len(reloaded.split())==1,name
    return t

def build():
    zs=np.unique(np.r_[np.linspace(BASE_Z,TOP_Z,300),TRANSITION])
    rs=np.array([radius(z) for z in zs])
    envelope=outer_solid(zs-BASE_Z,rs)
    inspection=revolve([(float(r),float(z)) for z,r in zip(zs,rs)]+[(float(r-WIDTH),float(z)) for z,r in zip(zs[::-1],rs[::-1])])
    # Slip over the already printed 55 mm head lip. A 0.75 mm tall ledge
    # supports the vase edge. The upper sleeve locates inside the thin wall.
    ring=(b.cyl(29.5,.75,(0,0,.375),n=256)+b.cyl(28.64,1.75,(0,0,.875),n=256))-b.cyl(27.9,3,(0,0,1),n=256)
    # Cap is a solid shallow crown. Its underside has an annular receiving
    # groove, so both the centre disk and outside skirt start on the bed.
    # Close the slot gradually: its outer roof advances only 0.25 mm per
    # layer. A flat annular roof produced long tangential bridges in slicing.
    cap_r0=radius(CAP_BOTTOM)+CLEARANCE+1.0
    # A cubic crown follows the original outline more closely than a shallow
    # ellipsoid whose equator starts at the cap split.
    t=np.linspace(0,1,240)
    p0=np.array([cap_r0,CAP_BOTTOM]);p1=np.array([cap_r0-2.5,CAP_BOTTOM+3.125])
    p2=np.array([8.0,CAP_TOP]);p3=np.array([0.,CAP_TOP])
    curve=(1-t[:,None])**3*p0+3*(1-t[:,None])**2*t[:,None]*p1+3*(1-t[:,None])*t[:,None]**2*p2+t[:,None]**3*p3
    rc=curve[:,0];zc=curve[:,1]
    cap=outer_solid(zc,rc)
    zg=np.linspace(CAP_BOTTOM-.05,TOP_Z,30)
    roof_height=.75
    zr=np.linspace(TOP_Z,TOP_Z+roof_height,60)
    outer=[(radius(z)+CLEARANCE,float(z)) for z in zg]
    inner=[(radius(z)-WIDTH-CLEARANCE,float(z)) for z in zg]
    for z in zr[1:]:
        dz=z-TOP_Z
        outer.append((radius(TOP_Z)+CLEARANCE-dz,float(z)))
        inner.append((radius(TOP_Z)-WIDTH-CLEARANCE+((WIDTH+2*CLEARANCE)/roof_height-1)*dz,float(z)))
    groove=revolve(outer+inner[::-1])
    cap-=groove
    meshes={
        '01_viewing_shell_VASE_SOLID':export('01_viewing_shell_VASE_SOLID',envelope),
        '02_crown_cap_NORMAL':export('02_crown_cap_NORMAL',cap.translate((0,0,-CAP_BOTTOM))),
        '03_mounting_ring_NORMAL':export('03_mounting_ring_NORMAL',ring),
    }
    assemblies={'viewing_shell':inspection,'crown_cap':cap,'mounting_ring':ring}
    for name,v in assemblies.items():
        solid_mesh(v.translate((0,0,HEAD_LEDGE_Z))).export(OUT/'inspection_only'/f'{name}.stl')
    head=solid(tm.load(ROOT/'print/modular/assembled/head.stl'))
    overlaps={}
    for name,v in assemblies.items():
        overlaps[f'{name}/existing_head']=float((v.translate((0,0,HEAD_LEDGE_Z))^head).volume())
    for i,(name,v) in enumerate(assemblies.items()):
        for name2,v2 in list(assemblies.items())[i+1:]:overlaps[f'{name}/{name2}']=float((v^v2).volume())
    assert all(v<.002 for v in overlaps.values()),overlaps
    head_mesh=tm.load(ROOT/'print/modular/assembled/head.stl')
    eye_top=float(head_mesh.bounds[1,2])-HEAD_LEDGE_Z
    assert CAP_BOTTOM-eye_top>.5
    dr=np.diff(rs);dz=np.diff(zs)
    assert np.max(-dr/dz)<SLOPE+1e-6
    stats={}
    for name,t in meshes.items():
        bottom=(t.face_normals[:,2]<-.999)&(t.triangles_center[:,2]<1e-4)
        stats[name]={'watertight':bool(t.is_watertight),'connected_components':len(t.split()),'dimensions_mm':t.extents.tolist(),'volume_mm3':float(t.volume),'bed_contact_area_mm2':float(t.area_faces[bottom].sum())}
    report={'layer_height_mm':LAYER,'nozzle_mm':.4,'vase_extrusion_width_mm':WIDTH,
        'shell_print_height_mm':TOP_Z-BASE_Z,'shell_bottom_outer_diameter_mm':2*radius(BASE_Z),
        'shell_top_outer_diameter_mm':2*radius(TOP_Z),'nominal_horizontal_wall_mm':WIDTH,
        'minimum_wall_normal_thickness_mm':WIDTH/math.sqrt(1+SLOPE**2),
        'transition_height_above_old_dome_base_mm':TRANSITION,
        'max_radial_step_per_layer_mm':SLOPE*LAYER,'nominal_minimum_path_overlap_fraction':1-SLOPE*LAYER/WIDTH,
        'cap_bottom_above_eye_top_mm':CAP_BOTTOM-eye_top,'cap_straight_groove_depth_mm':TOP_Z-CAP_BOTTOM,'cap_tapered_roof_height_mm':roof_height,
        'cap_maximum_nominal_seating_drop_mm':CLEARANCE,'cap_min_eye_clearance_after_seating_mm':CAP_BOTTOM-eye_top-CLEARANCE,
        'cap_groove_radial_width_mm':WIDTH+2*CLEARANCE,'cap_groove_clearance_each_side_mm':CLEARANCE,
        'ring_to_head_radial_clearance_mm':27.9-27.5,
        'ring_to_shell_min_radial_clearance_mm':radius(1.75)-WIDTH-28.64,
        'assembled_dome_height_mm':CAP_TOP,'original_dome_height_mm':A,
        'maximum_window_radial_change_from_original_mm':radius(TOP_Z)-R*math.sqrt(1-(TOP_Z/A)**2),
        'maximum_cap_radial_change_from_original_mm':float(np.max(rc[zc<=A]-R*np.sqrt(1-(zc[zc<=A]/A)**2))),
        'parts':stats,'intersection_volume_mm3':overlaps,'physical_test':'Not performed. Transparency and fits require printing.',
        'head_sha256':hashlib.sha256((ROOT/'print/modular/assembled/head.stl').read_bytes()).hexdigest()}
    (OUT/'qa/geometry.json').write_text(json.dumps(report,indent=2)+'\n')
    (OUT/'qa/profile.json').write_text(json.dumps({'window':[[float(r),float(z)] for r,z in zip(rs,zs)],'cap':[[float(r),float(z)] for r,z in zip(rc,zc)],'groove':outer+inner[::-1],'head_top':eye_top,'base_z':BASE_Z,'cap_bottom':CAP_BOTTOM,'shell_top':TOP_Z,'width':WIDTH},indent=2)+'\n')
    return meshes

def package(meshes):
    source=ROOT/'print/modular/qa/prusa_factory_petg_profile.ini'
    def five(v):return ','.join([str(v)]*5)
    common={'layer_height':str(LAYER),'first_layer_height':str(LAYER),'variable_layer_height':'0',
        'first_layer_temperature':five(250),'temperature':five(250),'bed_temperature':five(85),'first_layer_bed_temperature':five(85),
        'filament_settings_id':';'.join(['"Overture transparent PETG - Zoomer trial"']*5),'print_settings_id':'"Zoomer dome 0.25 mm"',
        'filament_colour':'#BFDDEB;#BFDDEB;#BFDDEB;#BFDDEB;#BFDDEB','filament_type':'PETG;PETG;PETG;PETG;PETG',
        'extrusion_multiplier':five(1),'wipe_tower':'0','support_material':'0','support_material_auto':'0',
        'complete_objects':'0','binary_gcode':'0','arc_fitting':'disabled','gcode_resolution':'0.01','resolution':'0',
        'elefant_foot_compensation':'0','brim_width':'4','brim_type':'outer_only','brim_separation':'0.1',
        'perimeter_speed':'15','external_perimeter_speed':'15','small_perimeter_speed':'15','infill_speed':'20',
        'solid_infill_speed':'20','top_solid_infill_speed':'15','gap_fill_speed':'15','bridge_speed':'15','first_layer_speed':'15',
        'infill_extruder':'1','perimeter_extruder':'1','solid_infill_extruder':'1',
        'support_material_extruder':'1','support_material_interface_extruder':'1','skirts':'0','min_skirt_length':'0',
        'enable_dynamic_overhang_speeds':'0','overhangs':'0','extra_perimeters':'0','extra_perimeters_on_overhangs':'0',
        'seam_position':'rear','ironing':'0','only_retract_when_crossing_perimeters':'1',
        'min_print_speed':five(10),'slowdown_below_layer_time':five(10)}
    window={'spiral_vase':'1','perimeters':'1','fill_density':'0%','top_solid_layers':'0','bottom_solid_layers':'0',
        'top_solid_min_thickness':'0','bottom_solid_min_thickness':'0','ensure_vertical_shell_thickness':'disabled',
        'extrusion_width':str(WIDTH),'perimeter_extrusion_width':str(WIDTH),'external_perimeter_extrusion_width':str(WIDTH),
        'first_layer_extrusion_width':str(WIDTH),'perimeter_generator':'classic',
        'fan_always_on':five(0),'cooling':five(1),'min_fan_speed':five(0),'max_fan_speed':five(15),
        'bridge_fan_speed':five(15),'enable_dynamic_fan_speeds':five(0),'fan_below_layer_time':five(10),'disable_fan_first_layers':five(3)}
    fittings={'spiral_vase':'0','perimeters':'3','fill_density':'100%','fill_pattern':'rectilinear','top_solid_layers':'4','bottom_solid_layers':'3',
        'top_solid_min_thickness':'0','bottom_solid_min_thickness':'0','ensure_vertical_shell_thickness':'enabled',
        'extrusion_width':'.45','external_perimeter_extrusion_width':'.45','perimeter_extrusion_width':'.45','first_layer_extrusion_width':'.45',
        'perimeter_generator':'arachne','fan_always_on':five(1),'min_fan_speed':five(30),'max_fan_speed':five(50),'bridge_fan_speed':five(50),'overhangs':'1'}
    jobs=[]
    for name,spec,names,locations in [
        ('01_XL_viewing_shell_VASE',window,['01_viewing_shell_VASE_SOLID'],[(180,180,0)]),
        ('02_XL_cap_and_ring_NORMAL',fittings,['02_crown_cap_NORMAL','03_mounting_ring_NORMAL'],[(145,180,0),(215,180,0)])]:
        cfg=OUT/'profiles'/f'{name}.ini';config(source,{**common,**spec},cfg)
        objects=[]
        for part,loc in zip(names,locations):
            mesh=meshes[part].copy();mesh.apply_translation(loc);objects.append((part,[('ivory',mesh)]))
        geometry=OUT/'qa'/f'{name}_geometry.3mf';b.write3mf(geometry,objects)
        project=OUT/f'{name}.3mf'
        with (OUT/'qa'/f'{name}_import.log').open('w') as log:
            subprocess.run([str(SLICER),'--load',str(cfg),'--dont-arrange','--export-3mf','--output',str(project),str(geometry)],stdout=log,stderr=subprocess.STDOUT,check=True)
        embed_config(project,cfg)
        jobs.append({'name':name,'project':str(project.relative_to(ROOT)),'profile':str(cfg.relative_to(ROOT))})
    (OUT/'qa/jobs.json').write_text(json.dumps(jobs,indent=2)+'\n')

def main():
    for sub in ['parts','inspection_only','profiles','qa']:(OUT/sub).mkdir(parents=True,exist_ok=True)
    meshes=build();package(meshes)
    print((OUT/'qa/geometry.json').read_text())
if __name__=='__main__':main()
