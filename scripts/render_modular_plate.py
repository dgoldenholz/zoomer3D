"""Render the saved orientation and arrangement of the main print plate."""
from pathlib import Path
import json,bpy,math
from mathutils import Matrix,Vector,Euler
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'print/modular'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/zoomer_modular.blend'));scene=bpy.context.scene
manifest=json.loads((OUT/'manifest.json').read_text())
for ob in list(bpy.data.objects):
    if ' | ' not in ob.name:continue
    name=ob.name.split(' | ')[0]
    if name=='dome':bpy.data.objects.remove(ob,do_unlink=True);continue
    if name not in manifest:continue
    spec=manifest[name];ob.parent=None
    rot=Euler(tuple(math.radians(x) for x in spec['rotation_deg'])).to_matrix().to_4x4()
    rot.translation=Vector(spec['print_translation_mm'])+Vector(spec['plate_translation_mm']);ob.matrix_world=rot
bpy.ops.mesh.primitive_cube_add(size=1,location=(180,180,-1.2));bed=bpy.context.object;bed.scale=(360,360,2)
m=bpy.data.materials.new('XL bed');m.diffuse_color=(.13,.16,.18,1);bed.data.materials.append(m)
for loc in [0,60,120,180,240,300,360]:
    for size,pos in [((.5,360,.12),(loc,180,-.15)),((360,.5,.12),(180,loc,-.15))]:
        bpy.ops.mesh.primitive_cube_add(size=1,location=pos);bpy.context.object.scale=size;bpy.context.object.data.materials.append(bpy.data.materials['ivory'])
for ob in bpy.data.objects:
    if ob.type=='LIGHT':ob.location+=Vector((180,150,150));ob.data.energy*=1.6
cam=scene.camera;cam.location=(180,-270,540);cam.rotation_euler=(Vector((180,175,0))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=420
scene.render.resolution_x=1300;scene.render.resolution_y=1100;scene.cycles.samples=24
scene.render.filepath=str(OUT/'qa/main_plate.png');bpy.ops.render.render(write_still=True)
