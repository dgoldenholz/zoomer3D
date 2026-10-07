"""Save the replacement dome in a new inspection scene and render its assembly."""
import bpy, bmesh, math
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'print/vase_dome'
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24
scene.render.resolution_x=900;scene.render.resolution_y=950;scene.render.resolution_percentage=100
scene.render.film_transparent=True
scene.render.image_settings.file_format='PNG'
scene.render.use_file_extension=True
for ob in list(bpy.data.objects):
    if ob.name.startswith('dome |'):
        bpy.data.objects.remove(ob,do_unlink=True)

def material(name,color):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1)
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=.38
    return m

colors={'viewing_shell':(.18,.48,.67),'crown_cap':(.84,.53,.17),'mounting_ring':(.22,.52,.32)}
parts={}
control=bpy.data.objects['Head yaw'];control['angle_deg']=0
for name,col in colors.items():
    bpy.ops.wm.stl_import(filepath=str(OUT/'inspection_only'/f'{name}.stl'))
    ob=bpy.context.object;ob.name=name;ob.data.materials.append(material('Dome | '+name,col))
    for poly in ob.data.polygons:poly.use_smooth=False
    world=ob.matrix_world.copy();ob.parent=control;ob.matrix_world=world
    parts[name]=ob

cam=scene.camera
def point_camera(loc,target,scale):
    cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale

point_camera((200,-560,240),(0,0,90),214)
scene['README']='Three-piece replacement dome. Opaque construction colors; PETG clarity is not simulated. Only parts/01_viewing_shell_VASE_SOLID.stl is the vase slicer input. See print/vase_dome/PRINTING.md.'
scene['dome_layer_height_mm']=.25
scene['dome_width_mm']=.6
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'assets/zoomer_vase_dome.blend'))
scene.render.filepath=str(OUT/'qa/assembled.png');bpy.ops.render.render(write_still=True)

# Head-only views retain the existing colored print geometry.
for ob in scene.objects:
    if ob.type=='MESH' and ob not in parts.values() and not ob.name.startswith('head |'):
        ob.hide_render=True
point_camera((70,-250,230),(0,0,161),83)
cuts=[]
for name,ob in parts.items():
    dup=ob.copy();dup.data=ob.data.copy();scene.collection.objects.link(dup)
    dup.name=name+' | front half removed for inspection'
    bm=bmesh.new();bm.from_mesh(dup.data)
    # Imported STL vertices remain in assembly coordinates.
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-6,
        plane_co=(0,0,0),plane_no=(0,1,0),clear_inner=True,clear_outer=False)
    boundary=[e for e in bm.edges if e.is_boundary]
    if boundary:bmesh.ops.holes_fill(bm,edges=boundary,sides=0)
    bm.to_mesh(dup.data);bm.free();cuts.append(dup);ob.hide_render=True
scene.render.filepath=str(OUT/'qa/cutaway.png');bpy.ops.render.render(write_still=True)
for ob in cuts:bpy.data.objects.remove(ob,do_unlink=True)
for name,ob in parts.items():
    ob.hide_render=False
    ob.location.z+={'mounting_ring':4,'viewing_shell':14,'crown_cap':30}[name]
point_camera((60,-270,250),(0,0,178),105)
scene.render.filepath=str(OUT/'qa/exploded.png');bpy.ops.render.render(write_still=True)
print('New inspection scene and three construction renders completed. Original scene preserved.')
