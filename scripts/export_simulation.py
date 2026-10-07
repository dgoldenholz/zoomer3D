"""Export the Blender mesh manifest and shared joint tree to MJCF and URDF."""
import json, math, sys
import xml.etree.ElementTree as E
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from robot_design import build
D=build();scale=np.array(D['scale_xyz']);links={l['name']:l for l in D['links']};orig={n:np.array(l['origin'])*scale for n,l in links.items()}
manifest=json.loads((ROOT/'simulation/mesh_manifest.json').read_text())
def f(v):return ' '.join(f'{float(x):.8g}' for x in v)
def el(parent,tag,**kw):return E.SubElement(parent,tag,{k:str(v) for k,v in kw.items()})
def save(tree,path):E.indent(tree,space='  ');E.ElementTree(tree).write(path,encoding='unicode',xml_declaration=True)
def collision(c):
 pos=np.array(c['pos'])*scale-orig[c['body']];kind=c['kind'];axis=c['axis'];v=c['size']
 quat={'X':(.70710678,0,.70710678,0),'Y':(.70710678,.70710678,0,0),'Z':(1,0,0,0)}[axis]
 if kind=='box':size=np.array(v)*scale/2
 elif kind=='sphere':size=[v[0]*min(scale)]
 else:
  idx={'X':0,'Y':1,'Z':2}[axis];size=[v[0]*min(scale[j] for j in range(3) if j!=idx),v[1]*scale[idx]/2]
 return pos,size,quat

def mjcf(name,fixed=False,board=False):
 root=E.Element('mujoco',model=name)
 el(root,'compiler',angle='radian',meshdir='meshes',autolimits='true',balanceinertia='true')
 el(root,'option',timestep='.001',integrator='implicitfast',cone='elliptic',iterations=80)
 default=el(root,'default');el(default,'joint',damping='.002',armature='.000001')
 el(default,'geom',solref='.008 1',solimp='.95 .99 .001',friction='1 .005 .0001')
 asset=el(root,'asset')
 for n,col in D['colors'].items():el(asset,'material',name=n,rgba=f(col),specular='.4',shininess='.4')
 for i,m in enumerate(manifest):el(asset,'mesh',name=f'm{i}',file=m['file'])
 world=el(root,'worldbody');el(world,'light',pos='0 -.5 1',dir='0 .4 -1',diffuse='.9 .9 .9')
 # Align the floor with the belt's bottom. Fixed-base bench scenes leave
 # 2 mm clearance so the grounded proxies do not lock the drive motors.
 floor_z=-.0085*scale[2]-(.002 if fixed else 0)
 el(world,'geom',name='floor',type='plane',pos=f((0,0,floor_z)),size='1 1 .01',rgba='.12 .16 .21 1',contype=1,conaffinity=3)
 el(world,'camera',name='overview',pos='.32 -.50 .28',xyaxes='1 .5 0 -.17 .34 .94')
 el(world,'camera',name='front',pos='0 -.5 .12',xyaxes='1 0 0 0 0 1')
 bodies={}
 for n,l in links.items():
  parent=bodies[l['parent']] if l['parent'] else world
  b=el(parent,'body',name=n,pos=f(orig[n]-(orig[l['parent']] if l['parent'] else 0)));bodies[n]=b
  cols=[c for c in D['collisions'] if c['body']==n]
  com=np.mean([np.array(c['pos'])*scale-orig[n] for c in cols],axis=0) if cols else np.zeros(3)
  mass=l['mass']*.015;inertia=l['inertia']*.015*.12**2
  el(b,'inertial',pos=f(com),mass=mass,diaginertia=f([inertia]*3))
  if n=='base' and not fixed:el(b,'freejoint',name='floating_base')
  if l['axis']:
   kw=dict(name=n,axis=f(l['axis']),type='hinge')
   if l['limits']:kw['range']=f(np.deg2rad(l['limits']))
   else:kw['limited']='false'
   el(b,'joint',**kw)
  for i,m in enumerate(manifest):
   if m['body']==n:el(b,'geom',name=f'v{i}',type='mesh',mesh=f'm{i}',material=m['material'],contype=0,conaffinity=0,group=2,density=0)
  for ci,c in enumerate(cols):
   pos,size,quat=collision(c)
   el(b,'geom',name=f'{n}_collision_{ci}',type=c['kind'],pos=f(pos),size=f(size),quat=f(quat),contype=2,conaffinity=1,group=3,rgba='.9 .3 .1 .3',density=0)
  for site in D['sites']:
   if site['body']==n:el(b,'site',name=site['name'],pos=f(np.array(site['pos'])*scale-orig[n]),size='.001',rgba='1 .2 .1 1',group=4)
 if board:
  # Vertical 140 x 110 mm board, face at Y=-57.6 mm.
  el(world,'geom',name='whiteboard',type='box',pos='0 -.0596 .123',size='.07 .002 .055',rgba='.93 .96 .98 1',contype=1,conaffinity=3)
  el(world,'site',name='goal',pos='-.029 -.0571 .12',size='.0015',rgba='.1 .8 .25 1')
  b=bodies['right_wrist_roll'];p1=np.array((-.444,0,.59))*scale-orig['right_wrist_roll'];p2=np.array((-.444,0,.465))*scale-orig['right_wrist_roll']
  el(b,'geom',name='marker',type='capsule',fromto=f([*p1,*p2]),size='.0007',rgba='.03 .04 .06 1',contype=0,conaffinity=0,mass=0,group=2)
 act=el(root,'actuator');sens=el(root,'sensor')
 for n,l in links.items():
  if l['torque']:
   el(act,'motor',name=n,joint=n,gear=l['torque']*.0018,ctrlrange='-1 1')
   el(sens,'jointpos',name=n+'_position',joint=n);el(sens,'jointvel',name=n+'_velocity',joint=n)
 for side in ['left','right']:el(sens,'framepos',name=side+'_tool_position',objtype='site',objname=side+'_tool')
 save(root,ROOT/f'simulation/{name}.xml')

mjcf('zoomer');mjcf('zoomer_fixed',fixed=True);mjcf('whiteboard',fixed=True,board=True)
# URDF preserves the joint axes, limits and individual visual meshes.
root=E.Element('robot',name='zoomer_xi30')
for n,l in links.items():
 body=el(root,'link',name=n);mass=l['mass']*.015;iv=l['inertia']*.015*.12**2
 cols=[c for c in D['collisions'] if c['body']==n]
 com=np.mean([np.array(c['pos'])*scale-orig[n] for c in cols],axis=0) if cols else np.zeros(3)
 inertial=el(body,'inertial');el(inertial,'origin',xyz=f(com));el(inertial,'mass',value=mass);el(inertial,'inertia',ixx=iv,iyy=iv,izz=iv,ixy=0,ixz=0,iyz=0)
 for m in manifest:
  if m['body']!=n:continue
  visual=el(body,'visual');geom=el(visual,'geometry');el(geom,'mesh',filename='meshes/'+m['file']);mat=el(visual,'material',name=m['material']);el(mat,'color',rgba=f(D['colors'][m['material']]))
 for c in cols:
  pos,size,quat=collision(c);col=el(body,'collision');rpy={'X':(0,math.pi/2,0),'Y':(math.pi/2,0,0),'Z':(0,0,0)}[c['axis']]
  el(col,'origin',xyz=f(pos),rpy=f(rpy));g=el(col,'geometry')
  if c['kind']=='box':el(g,'box',size=f(size*2))
  elif c['kind']=='sphere':el(g,'sphere',radius=size[0])
  else:el(g,'cylinder',radius=size[0],length=size[1]*2)  # capsule -> conservative cylinder in URDF
 if l['parent']:
  kind='revolute' if l['limits'] else 'continuous';j=el(root,'joint',name=n,type=kind)
  el(j,'parent',link=l['parent']);el(j,'child',link=n);el(j,'origin',xyz=f(orig[n]-orig[l['parent']]));el(j,'axis',xyz=f(l['axis']))
  limit=dict(effort=l['torque']*.0018,velocity=4)
  if l['limits']:limit.update(lower=math.radians(l['limits'][0]),upper=math.radians(l['limits'][1]))
  el(j,'limit',**limit);el(j,'dynamics',damping='.002',friction='0')
save(root,ROOT/'simulation/zoomer.urdf')
joints=[dict(name=n,axis=l['axis'],limits_deg=l['limits'],torque_Nm=l['torque']*.0018) for n,l in links.items() if l['torque']]
(ROOT/'simulation/motor_map.json').write_text(json.dumps(joints,indent=2))
print('Exported 3 MJCF scenes, URDF and',len(joints),'motor channels')
