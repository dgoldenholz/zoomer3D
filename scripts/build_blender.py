"""Run with Blender: blender --background --python scripts/build_blender.py -- --render"""
import bpy, bmesh, sys, math, json
from pathlib import Path
from mathutils import Vector, Matrix
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from robot_design import build
D=build(); SCALE=Vector(D['scale_xyz']); S=Matrix.Diagonal((*SCALE,1));
(ROOT/'assets/robot_spec.json').write_text(json.dumps(D,indent=2))
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for c in list(bpy.data.collections):
 if c.name!='Collection' and c.users==0: bpy.data.collections.remove(c)
scene=bpy.context.scene
scene.unit_settings.system='METRIC';scene.unit_settings.length_unit='METERS'
scene.render.engine='CYCLES';scene.cycles.samples=48
scene.cycles.use_denoising=True
scene.render.resolution_x=1500;scene.render.resolution_y=1700;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.view_settings.view_transform='AgX'
scene.world.color=(.2,.2,.2)
world=scene.world;world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.10,.14,.19,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.4

def collection(n):
 c=bpy.data.collections.new(n);scene.collection.children.link(c);return c
rigcol=collection('01 | Joint controls (degrees)');viscol=collection('02 | Robot geometry');studiocol=collection('03 | Studio');refcol=collection('04 | Reference')

def move(obj,col):
 for c in list(obj.users_collection):c.objects.unlink(obj)
 col.objects.link(obj)

mats={}
for n,rgba in D['colors'].items():
 m=bpy.data.materials.new(n);m.diffuse_color=rgba;m.use_nodes=True
 p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=rgba
 p.inputs['Metallic'].default_value=.72 if n in ['metal','blue','purple','red'] else .2
 p.inputs['Roughness'].default_value=.29 if n!='rubber' else .7
 if n in ['cyan','green','amber']:
  p.inputs['Emission Color'].default_value=rgba;p.inputs['Emission Strength'].default_value=.45 if n=='green' else 2.2
 if n=='glass':
  p.inputs['Base Color'].default_value=(.84,.96,1,1)
  p.inputs['Metallic'].default_value=0;p.inputs['Roughness'].default_value=.085
  p.inputs['Transmission Weight'].default_value=1;p.inputs['IOR'].default_value=1.15
  # Optical shell with some straight-through light to keep the small face legible.
  nt=m.node_tree;out=nt.nodes.get('Material Output');tr=nt.nodes.new('ShaderNodeBsdfTransparent');mix=nt.nodes.new('ShaderNodeMixShader');mix.inputs[0].default_value=.30
  nt.links.new(p.outputs[0],mix.inputs[1]);nt.links.new(tr.outputs[0],mix.inputs[2]);nt.links.new(mix.outputs[0],out.inputs['Surface'])
 mats[n]=m

origins={d['name']:S.to_3x3()@Vector(d['origin']) for d in D['links']};controls={}
for d in D['links']:
 o=bpy.data.objects.new(d['name'],None);rigcol.objects.link(o);controls[d['name']]=o
 o.empty_display_type='ARROWS';o.empty_display_size=.006
 o.location=origins[d['name']]-(origins[d['parent']] if d['parent'] else Vector((0,0,0)))
 if d['parent']:o.parent=controls[d['parent']]
 o['mass_kg']=d['mass']*.015;o['motor_torque_Nm']=d['torque']*.0018
 if d['axis']:
  o.rotation_mode='AXIS_ANGLE';o.rotation_axis_angle=(0,*d['axis']);o['command_deg']=0.0
  limits=d['limits'] or [-3600,3600]
  o['joint_axis']=list(d['axis']);o['limits_deg']=limits;o['continuous']=d['limits'] is None
  o.id_properties_ui('command_deg').update(min=limits[0],max=limits[1],soft_min=max(limits[0],-180),soft_max=min(limits[1],180),description='Joint rotation in degrees. Shared pivot and axis with simulation.')
  fc=o.driver_add('rotation_axis_angle',0);v=fc.driver.variables.new();v.name='q';v.type='SINGLE_PROP';v.targets[0].id=o;v.targets[0].data_path='["command_deg"]'
  fc.driver.expression=f'min(max(q,{limits[0]}),{limits[1]})*pi/180'
  o.show_in_front=True

meshes_by_link={n:[] for n in controls}
def bevel(o,w):
 mod=o.modifiers.new('Machined edge radius','BEVEL');mod.width=w;mod.segments=3
 mod=o.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL')
def axisrot(o,a):
 if a=='X':o.rotation_euler[1]=math.pi/2
 if a=='Y':o.rotation_euler[0]=math.pi/2

def dome(p):
 verts=[];faces=[];N=80;K=28
 # Two closed nested domes joined at the equator, no open mesh boundaries.
 for inset in [0,p['thickness']]:
  r=p['radius']-inset;h=p['height']-inset
  for j in range(K):
   t=(math.pi/2)*(j/K)
   for i in range(N):
    a=2*math.pi*i/N;verts.append((r*math.cos(t)*math.cos(a),r*math.cos(t)*math.sin(a),h*math.sin(t)))
  verts.append((0,0,h))
 stride=K*N+1
 for layer in range(2):
  off=layer*stride
  for j in range(K-1):
   for i in range(N):
    q=(off+j*N+i,off+j*N+(i+1)%N,off+(j+1)*N+(i+1)%N,off+(j+1)*N+i)
    faces.append(q if layer==0 else q[::-1])
  for i in range(N):
   q=(off+(K-1)*N+i,off+(K-1)*N+(i+1)%N,off+K*N);faces.append(q if layer==0 else q[::-1])
 for i in range(N):faces.append((i,stride+i,stride+(i+1)%N,(i+1)%N))
 m=bpy.data.meshes.new('dome shell');m.from_pydata(verts,[],faces);m.update();o=bpy.data.objects.new(p['name'],m);viscol.objects.link(o);return o

def track_belt(p):
 pts=p['path'];N=len(pts);vertices=[];faces=[]
 normals=[]
 for i in range(N):
  a=Vector(pts[i-1]);b=Vector(pts[(i+1)%N]);t=(b-a).normalized();normals.append(Vector((-t.y,t.x)))
 for x in [-p['depth']/2,p['depth']/2]:
  for sign in [1,-1]:
   for yz,n in zip(pts,normals):
    q=Vector(yz)+sign*p['half_wall']*n;vertices.append((x,q.x,q.y))
 for i in range(N):
  j=(i+1)%N
  faces.extend([(i,j,2*N+j,2*N+i),(N+j,N+i,3*N+i,3*N+j),
                (j,i,N+i,N+j),(2*N+i,2*N+j,3*N+j,3*N+i)])
 me=bpy.data.meshes.new(p['name']);me.from_pydata(vertices,[],faces);me.update()
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 o=bpy.data.objects.new(p['name'],me);viscol.objects.link(o);return o

for p in D['parts']:
 k=p['kind'];loc=Vector(p['pos'])
 if k=='box':
  bpy.ops.mesh.primitive_cube_add();o=bpy.context.object;o.dimensions=p['size'];bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);bevel(o,p.get('bevel',.005));o.rotation_euler.x=p.get('rx',0)
 elif k=='cylinder':
  bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=p['radius'],depth=p['depth']);o=bpy.context.object;axisrot(o,p.get('axis','Z'));bevel(o,min(.004,p['depth']*.2))
 elif k=='sphere':
  bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=p['radius']);o=bpy.context.object;o.scale=p.get('scale',(1,1,1))
 elif k=='torus':
  bpy.ops.mesh.primitive_torus_add(major_segments=48,minor_segments=10,major_radius=p['radius'],minor_radius=p['tube']);o=bpy.context.object;axisrot(o,p.get('axis','Z'))
 elif k=='beam':
  end=Vector(p['end']);delta=end-loc
  bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=p['radius'],depth=delta.length);o=bpy.context.object;o.rotation_euler=delta.to_track_quat('Z','Y').to_euler();loc=(loc+end)/2;bevel(o,.002)
 elif k=='panel':
  outline=p['outline'];N=len(outline);verts=[(x,y,z) for y in [-p['depth']/2,p['depth']/2] for x,z in outline]
  faces=[tuple(range(N-1,-1,-1)),tuple(range(N,2*N))]+[(i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N)]
  m=bpy.data.meshes.new(p['name']);m.from_pydata(verts,[],faces);m.update();o=bpy.data.objects.new(p['name'],m);viscol.objects.link(o);bevel(o,p['bevel'])
 elif k=='dome':o=dome(p)
 elif k=='track_belt':o=track_belt(p)
 elif k=='text':
  cu=bpy.data.curves.new(p['name'],'FONT');cu.body=p['text'];cu.align_x='CENTER';cu.align_y='CENTER';cu.size=p['size'];cu.extrude=.0003
  o=bpy.data.objects.new(p['name'],cu);viscol.objects.link(o);o.rotation_euler.x=math.pi/2
 else:raise ValueError(k)
 o.name=p['name'];move(o,viscol);o.data.materials.append(mats[p['mat']]);o.location=loc;bpy.context.view_layer.update();M=S@o.matrix_world.copy();o.parent=controls[p['body']];o.matrix_basis=Matrix.Translation(-origins[p['body']])@M
 o['link']=p['body'];o['material_role']=p['mat']
 if o.type=='MESH':
  for face in o.data.polygons:face.use_smooth=k not in ['box','panel']
 meshes_by_link[p['body']].append(o)

# Export visual meshes per material and link in local link coordinates.
# Meshes remain visual only in physics; simple collision shapes carry contact.
meshdir=ROOT/'simulation/meshes';meshdir.mkdir(exist_ok=True)
manifest=[];bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
for ln,objects in meshes_by_link.items():
 groups={}
 for o in objects:groups.setdefault(o['material_role'],[]).append(o)
 for mat,objs in groups.items():
  vs=[];faces=[];T=controls[ln].matrix_world.inverted()
  for ob in objs:
   e=ob.evaluated_get(deps);me=e.to_mesh();me.calc_loop_triangles();off=len(vs);trans=T@ob.matrix_world
   vs.extend([trans@v.co for v in me.vertices]);faces.extend([tuple(off+i for i in tri.vertices) for tri in me.loop_triangles]);e.to_mesh_clear()
  filename=f'{ln}__{mat}.obj';f=meshdir/filename
  with f.open('w') as out:
   out.write('# Zoomer visual mesh, local link coordinates in metres\n')
   for v in vs:out.write('v %.7f %.7f %.7f\n'%tuple(v))
   for tri in faces:out.write('f %d %d %d\n'%tuple(i+1 for i in tri))
  manifest.append(dict(body=ln,material=mat,file=filename))
(ROOT/'simulation/mesh_manifest.json').write_text(json.dumps(manifest,indent=2))
keep={m['file'] for m in manifest}
for old in meshdir.glob('*.obj'):
 if old.name not in keep:old.unlink()

# Tool target empties for inspection and pose development.
for s in D['sites']:
 o=bpy.data.objects.new(s['name'],None);rigcol.objects.link(o);o.parent=controls[s['body']];o.location=S.to_3x3()@Vector(s['pos'])-origins[s['body']];o.empty_display_type='SPHERE';o.empty_display_size=.0015
 o['purpose']='End-effector reference point; marker task uses this site.'
# Store the reference in the blend without cluttering the showroom.
ref=bpy.data.images.load(str(ROOT/'zoomer.png'));ref.pack()
o=bpy.data.objects.new('Original design drawing',None);refcol.objects.link(o);o.empty_display_type='IMAGE';o.data=ref;o.empty_display_size=1.5;o.location=(1.5,.6,.75);o.rotation_euler.x=math.pi/2;o.hide_viewport=True;o.hide_render=True

# A reversible articulation demonstration. Frame 1 is the simulation rest pose.
poses={1:{},55:{'right_shoulder_pitch':-50,'right_shoulder_roll':-20,'right_elbow':-70,'right_wrist_pitch':25,'head_yaw':-30},105:{'right_shoulder_pitch':-70,'right_shoulder_roll':-35,'right_elbow':-85,'right_wrist_pitch':-15,'left_elbow':-30,'waist_yaw':25,'waist_pitch':-8,'head_yaw':55},160:{'left_shoulder_pitch':-35,'left_shoulder_roll':30,'left_elbow':-95,'left_wrist_roll':20,'waist_yaw':-25,'head_yaw':180},220:{'head_yaw':360},250:{'head_yaw':360}}
for frame,pose in poses.items():
 for n,o in controls.items():
  if 'command_deg' not in o:continue
  val=pose.get(n,0)
  if '_finger_' in n and frame in [105,160]:val=32 if n.endswith('base') else 28
  o['command_deg']=float(val);o.keyframe_insert(data_path='["command_deg"]',frame=frame)
scene.frame_start=1;scene.frame_end=250;scene.render.fps=30;scene.frame_set(1)
for frame,label in [(1,'REST / export pose'),(55,'Reach'),(105,'Close grippers'),(160,'Waist + wrist'),(220,'360 degree head'),(250,'Loop')]:scene.timeline_markers.new(label,frame=frame)

# Studio composition.
bpy.ops.mesh.primitive_cylinder_add(vertices=128,radius=.0816,depth=.0042,location=(0,0,-.00444));plinth=bpy.context.object;plinth.name='Display plinth';plinth.data.materials.append(mats['dark']);bevel(plinth,.00108);move(plinth,studiocol)
bpy.ops.mesh.primitive_plane_add(size=20,location=(0,0,-.00684));o=bpy.context.object;o.name='Studio floor';move(o,studiocol)
floor=bpy.data.materials.new('Studio slate');floor.diffuse_color=(.055,.077,.10,1);floor.use_nodes=True;floor.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.055,.077,.10,1);floor.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.48;o.data.materials.append(floor)

def aim(o,point):o.rotation_euler=(Vector(point)*.12-o.location).to_track_quat('-Z','Y').to_euler()
def area(n,loc,power,color,size,target=(0,0,.8)):
 d=bpy.data.lights.new(n,'AREA');d.energy=power*.0144;d.color=color;d.shape='DISK';d.size=size*.12;o=bpy.data.objects.new(n,d);studiocol.objects.link(o);o.location=Vector(loc)*.12;aim(o,target)
area('Large softbox',(-2,-3,4),400,(.84,.92,1),3)
area('Warm key',(2,-1.5,2.8),280,(1,.82,.69),2)
area('Rim strip',(.5,2,2.9),600,(.35,.64,1),2)
area('Face fill',(-.1,-3,1.6),60,(1,1,1),1)
d=bpy.data.cameras.new('Hero camera');cam=bpy.data.objects.new('Hero camera',d);studiocol.objects.link(cam);cam.location=Vector((2.35,-4.6,2.15))*.12;aim(cam,(0,0,.75));d.clip_start=.001;d.type='ORTHO';d.ortho_scale=1.88*.12;scene.camera=cam
side_data=bpy.data.cameras.new('Tread side elevation');side_camera=bpy.data.objects.new('Tread side elevation',side_data);studiocol.objects.link(side_camera)
side_camera.location=(.5,0,.015);aim(side_camera,(0,0,.125));side_data.type='ORTHO';side_data.ortho_scale=.086;side_data.clip_start=.001
# Set an immediately usable starting view.
for screen in bpy.data.screens:
 for a in screen.areas:
  if a.type=='VIEW_3D':
   a.spaces.active.region_3d.view_perspective='CAMERA';a.spaces.active.shading.type='MATERIAL'
scene['README']='Pose through the command_deg custom property on joint empties in collection 01. Timeline 1-250 demonstrates articulation; frame 1 is rest. Units metres. See README.md for simulation and print limitations.'
scene['motor_count']=35
note=bpy.data.texts.new('START HERE');note.write('Zoomer XTI-30\n\nFrame 1 is the neutral pose. Play the timeline for a joint demonstration.\nSelect a joint empty in collection 01 and change its command_deg custom property.\nThe property is animated; clear keyframes to take manual control.\nAll visual parts are parented to the same joint tree used in MuJoCo and URDF.\nThe dark plinth and lighting are presentation objects.\nThe dome is a thin transmission shell. Hide it to inspect the eyes.\nPrint files are separate prototypes and require clearance tests.\n')
bpy.ops.object.select_all(action='DESELECT');controls['base'].select_set(True);bpy.context.view_layer.objects.active=controls['base']
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'assets/zoomer.blend'))
if '--render' in sys.argv:
 scene.cycles.samples=32
 scene.render.filepath=str(ROOT/'renders/zoomer_hero.png');bpy.ops.render.render(write_still=True)
 cam.location=Vector((0,-5,1.1))*.12;aim(cam,(0,0,.75));d.ortho_scale=1.78*.12;scene.render.resolution_x=1400;scene.render.resolution_y=1600;scene.render.filepath=str(ROOT/'renders/zoomer_front.png');bpy.ops.render.render(write_still=True)
 scene.frame_set(105);cam.location=Vector((2.35,-4.6,2.15))*.12;aim(cam,(0,0,.85));d.ortho_scale=2.0*.12;scene.render.filepath=str(ROOT/'renders/zoomer_articulated.png');bpy.ops.render.render(write_still=True)
if '--render' in sys.argv or '--side-only' in sys.argv:
 scene.frame_set(1);scene.camera=side_camera;scene.render.resolution_x=1600;scene.render.resolution_y=700;scene.cycles.samples=32
 scene.render.filepath=str(ROOT/'renders/zoomer_treads_side.png');bpy.ops.render.render(write_still=True)
print('BLENDER_BUILD_COMPLETE',len(D['parts']),len(manifest))
