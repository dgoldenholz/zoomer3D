"""Create a Blender file for the manufactured joint geometry and render it."""
from pathlib import Path
import json,math
import bpy
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/zoomer.blend'))
# Reuse the verified studio, and replace only the robot in this separate file.
for collection in ['01 | Joint controls (degrees)','02 | Robot geometry','04 | Reference']:
    c=bpy.data.collections.get(collection)
    if c:
        for obj in list(c.objects):bpy.data.objects.remove(obj,do_unlink=True)
        bpy.data.collections.remove(c)
scene=bpy.context.scene;scene.frame_set(1)
rig=bpy.data.collections.new('01 | Captive joint controls');scene.collection.children.link(rig)
parts=bpy.data.collections.new('02 | Printable volumes');scene.collection.children.link(parts)
joints=json.loads((ROOT/'print/articulated/joints.json').read_text())
controls={};origin={'base':Vector((0,0,0))}
base=bpy.data.objects.new('base',None);rig.objects.link(base);controls['base']=base
for joint in joints:
    name=joint['name'];o=bpy.data.objects.new(name,None);rig.objects.link(o);controls[name]=o
    p=Vector(joint['origin_mm'])*.001;origin[name]=p
    parent=controls.get(joint['parent']) if joint['type']!='chain_pin' else base
    o.parent=parent;o.location=p-origin.get(joint['parent'],Vector()) if joint['type']!='chain_pin' else p
    o.empty_display_type='ARROWS';o.empty_display_size=.004
    if joint['type']!='chain_pin':
        o.rotation_mode='AXIS_ANGLE';o.rotation_axis_angle=(0,*joint['axis']);o['command_deg']=0.0
        limits=joint['limits_deg'];o.id_properties_ui('command_deg').update(min=limits[0],max=limits[1])
        fc=o.driver_add('rotation_axis_angle',0);v=fc.driver.variables.new();v.name='q';v.type='SINGLE_PROP';v.targets[0].id=o;v.targets[0].data_path='["command_deg"]';fc.driver.expression='q*pi/180'
    o['gap_mm']=joint['radial_gap_mm'];o['mechanism']=joint['type']
valid=json.loads((ROOT/'print/articulated/validation.json').read_text())['parts']
for path in sorted((ROOT/'print/articulated').glob('*.stl')):
    if path.stem not in valid:continue
    bpy.ops.wm.stl_import(filepath=str(path));obj=bpy.context.object;name=path.stem;obj.name=name+' | print solid'
    obj.scale=(.001,.001,.001)
    for c in list(obj.users_collection):c.objects.unlink(obj)
    parts.objects.link(obj)
    parent=controls.get(name,controls.get('head_yaw') if name=='dome_cover' else base)
    bpy.context.view_layer.update();world=obj.matrix_world.copy();obj.parent=parent;obj.matrix_world=world
    material='glass' if name=='dome_cover' else 'blue' if 'wheel' in name or name=='base' else 'dark' if 'tread' in name else 'red' if name.endswith(('yaw','roll')) else 'ivory'
    obj.data.materials.clear();obj.data.materials.append(bpy.data.materials[material])
    for face in obj.data.polygons:face.use_smooth=False
    obj['units']='source STL millimetres'
scene['README']='Integrated passive articulation CAD. See print/articulated/validation.json and PRINTING.md before slicing. Internal supports require removal. No physical print has been tested.'
scene.frame_end=1
scene.camera=bpy.data.objects['Hero camera'];scene.camera.location=Vector((.282,-.552,.258))
scene.camera.rotation_euler=(Vector((0,0,.09))-scene.camera.location).to_track_quat('-Z','Y').to_euler();scene.camera.data.ortho_scale=.2256
scene.render.resolution_x=1400;scene.render.resolution_y=1600;scene.cycles.samples=24
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'assets/zoomer_print_in_place.blend'))
scene.render.filepath=str(ROOT/'renders/zoomer_print_in_place.png');bpy.ops.render.render(write_still=True)
print('MECHANICAL_BLEND_COMPLETE')
