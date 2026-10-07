"""Create a fused static display body from the detailed Blender geometry."""
import bpy,bmesh,sys,math,json
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from robot_design import build
from track_profile import track_path, track_wheels
D=build();S=Matrix.Diagonal((*D['scale_xyz'],1))
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/zoomer.blend'));scene=bpy.context.scene;scene.frame_set(1)
objs=[]
for o in list(bpy.data.collections['02 | Robot geometry'].objects):
 if o.get('material_role')=='glass':o.hide_render=True;o.hide_set(True);continue
 M=o.matrix_world.copy();o.parent=None;o.matrix_world=M;objs.append(o)
def cylinder(a,b,r):
 a=Vector(a);b=Vector(b);delta=b-a
 bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=r,depth=delta.length,location=(a+b)/2);o=bpy.context.object;o.rotation_euler=delta.to_track_quat('Z','Y').to_euler();bpy.context.view_layer.update();o.matrix_world=S@o.matrix_world;objs.append(o)
def cube(loc,dims):
 bpy.ops.mesh.primitive_cube_add(location=loc);o=bpy.context.object;o.dimensions=dims;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);bpy.context.view_layer.update();o.matrix_world=S@o.matrix_world;objs.append(o)
for s in [-1,1]:
 cylinder((s*.444,0,.89),(s*.444,0,.98),.026)
 for w in track_wheels():cylinder((s*.19,w['y'],w['z']),(s*.30,w['y'],w['z']),.016)
 # The static print core uses the same asymmetric outline as the visual belt.
 # It connects all tread pads and wheels without restoring the old capsule shape.
 path=track_path(128);N=len(path)
 verts=[(s*.282+dx,y,z) for dx in [-.04,.04] for y,z in path]
 faces=[tuple(range(N-1,-1,-1)),tuple(range(N,2*N))]+[(i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N)]
 me=bpy.data.meshes.new('Static tread core');me.from_pydata(verts,[],faces);me.update()
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 core=bpy.data.objects.new('Static tread core',me);bpy.context.collection.objects.link(core);core.matrix_world=S;objs.append(core)
bpy.ops.object.select_all(action='DESELECT')
for o in objs:o.select_set(True)
bpy.context.view_layer.objects.active=objs[0];bpy.ops.object.convert(target='MESH');bpy.ops.object.join();o=bpy.context.object;o.name='Fused static display body'
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
mod=o.modifiers.new('0.18 mm print union','REMESH');mod.mode='VOXEL';mod.voxel_size=.00018;mod.use_smooth_shade=False
bpy.ops.object.modifier_apply(modifier=mod.name)
# Slight surface smoothing removes stair steps from the union without changing the silhouette.
mod=o.modifiers.new('Surface cleanup','SMOOTH');mod.factor=.25;mod.iterations=2;bpy.ops.object.modifier_apply(modifier=mod.name)
o.data.materials.clear();o.data.materials.append(bpy.data.materials['ivory'])
scene.render.resolution_x=800;scene.render.resolution_y=960;scene.cycles.samples=12
scene.render.filepath=str(ROOT/'renders/zoomer_static_print.png');bpy.ops.render.render(write_still=True)
# STL has no unit metadata, so export coordinates in millimetres.
bpy.ops.wm.stl_export(filepath=str(ROOT/'print/zoomer_static_body_raw.stl'),export_selected_objects=True,global_scale=1000)
print('STATIC_PRINT_EXPORT',len(o.data.vertices),len(o.data.polygons))
