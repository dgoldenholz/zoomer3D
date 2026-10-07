"""Shared dimensions, geometry and joints. Metres; +X left, -Y forward, +Z up."""
from math import sin, cos, pi
import json
from pathlib import Path
from track_profile import track_path, track_samples, track_wheels
ROOT = Path(__file__).resolve().parents[1]
COLORS = {
 'ivory': (.79,.84,.85,1), 'red': (.62,.024,.043,1),
 'blue': (.035,.13,.55,1), 'purple': (.18,.065,.34,1),
 'green': (.12,.48,.075,1), 'dark': (.018,.027,.042,1),
 'rubber': (.012,.016,.022,1), 'metal': (.3,.39,.46,1),
 'glass': (.55,.86,.96,.16), 'cyan': (.015,.65,.92,1),
 'white': (.95,.97,1,1), 'amber': (1,.35,.018,1)}
LINKS=[]; PARTS=[]; COLLISIONS=[]; SITES=[]

def link(name, parent, origin, axis=None, limits=None, torque=0, mass=.1, inertia=.0002):
 d=dict(name=name,parent=parent,origin=list(origin),axis=axis,limits=limits,torque=torque,mass=mass,inertia=inertia)
 LINKS.append(d); return name

def part(name, kind, body, pos, mat, **kw):
 PARTS.append(dict(name=name,kind=kind,body=body,pos=list(pos),mat=mat,**kw))

def box(n,b,p,s,m,bevel=.009): part(n,'box',b,p,m,size=s,bevel=bevel)
def cyl(n,b,p,r,h,m,axis='Z'): part(n,'cylinder',b,p,m,radius=r,depth=h,axis=axis)
def sph(n,b,p,r,m,scale=(1,1,1)): part(n,'sphere',b,p,m,radius=r,scale=scale)
def ring(n,b,p,r,t,m,axis='Z'): part(n,'torus',b,p,m,radius=r,tube=t,axis=axis)
def beam(n,b,a,z,r,m): part(n,'beam',b,a,m,end=z,radius=r)
def collision(b,kind,pos,size,axis='Z'): COLLISIONS.append(dict(body=b,kind=kind,pos=pos,size=size,axis=axis))
def text(n,b,p,body,size,m): part(n,'text',b,p,m,text=body,size=size)

def build():
 LINKS.clear(); PARTS.clear(); COLLISIONS.clear(); SITES.clear()
 base=link('base',None,(0,0,.16),mass=24,inertia=.7)
 box('lower chassis',base,(0,0,.17),(.53,.46,.13),'blue',.026)
 box('red upper skirt',base,(0,0,.247),(.53,.43,.064),'red',.024)
 box('ivory deck',base,(0,0,.283),(.42,.36,.034),'ivory',.017)
 box('front bumper',base,(0,-.252,.17),(.43,.04,.048),'metal')
 for s in [-1,1]:
  box('running light',base,(s*.185,-.275,.195),(.065,.011,.014),'cyan',.004)
  box('deck vent',base,(s*.158,0,.305),(.086,.22,.012),'dark',.008)
  for y in [-.08,-.04,0,.04,.08]: box('deck louver',base,(s*.158,y,.315),(.071,.008,.007),'green',.002)
 collision(base,'box',(0,0,.19),(.50,.43,.15))
 # Eight wheels per side follow the supplied side elevation.
 # Contact cylinders include the belt thickness; the belt is a visual loop.
 for side,s in [('right',-1),('left',1)]:
  x=s*.282
  for w in track_wheels():
   name=f"{side}_{w['name']}";y=w['y'];z=w['z'];r=w['radius'];lower=w['row']=='lower'
   wheel=link(name,base,(x,y,z),(1,0,0),None,35 if w['name']=='drive' else 0,
              mass=.4 if lower else .2,inertia=.00045 if lower else .00016)
   cyl(f"{side} {w['row']} wheel {w['name']}",wheel,(x,y,z),r,.094,'rubber','X')
   cyl(f"{side} blue wheel rim {w['name']}",wheel,(x+s*.051,y,z),r*.92,.008,'blue','X')
   cyl(f"{side} dark wheel hub {w['name']}",wheel,(x+s*.057,y,z),r*.48,.008,'dark','X')
   # The first four road contacts share the flat lower belt plane. The rear
   # wheel and return rollers are elevated, as in the side-view drawing.
   contact_r=(z+.0085) if lower and w['name']!='idler_4' else r+.008
   collision(wheel,'cylinder',(x,y,z),(contact_r,.094),'X')
  part(f'{side} continuous tread belt','track_belt',base,(x,0,0),'rubber',
       path=track_path(),depth=.104,half_wall=.0085)
  part(f'{side} ivory belt outline','track_belt',base,(x+s*.058,0,0),'ivory',
       path=track_path(),depth=.006,half_wall=.006)
  for i,(y,z,angle) in enumerate(track_samples()):
   part(f'{side} tread pad {i:02}','box',base,(x,y,z),'rubber',size=(.116,.018,.022),bevel=.002,rx=angle)
   part(f'{side} tread ridge {i:02}','box',base,(x,y-.014*sin(angle),z+.014*cos(angle)),
        'metal',size=(.105,.006,.006),bevel=.001,rx=angle)
 # Lower cylinder and nonmoving collars.
 cyl('pedestal bearing',base,(0,0,.33),.13,.06,'metal')
 cyl('lower body cylinder',base,(0,0,.56),.058,.45,'blue')
 for i,z in enumerate([.365,.455,.545,.635,.725]):
  cyl('red cylinder collar',base,(0,0,z),.085,.025,'red')
  ring('collar lip',base,(0,0,z+.014),.078,.007,'metal')
 for a in range(12):
  t=2*pi*a/12
  beam('cylinder flute',base,(.06*cos(t),.06*sin(t),.35),(.06*cos(t),.06*sin(t),.77),.003,'metal')
 collision(base,'cylinder',(0,0,.55),(.06,.45))
 yaw=link('waist_yaw',base,(0,0,.79),(0,0,1),None,130,mass=1.5,inertia=.025)
 cyl('waist turntable',yaw,(0,0,.79),.103,.045,'dark')
 ring('turntable red ring',yaw,(0,0,.804),.1,.009,'red')
 pitch=link('waist_pitch',yaw,(0,0,.835),(1,0,0),[-25,25],160,mass=9,inertia=.35)
 cyl('waist pitch axle',pitch,(0,0,.835),.062,.21,'metal','X')
 box('waist mounting saddle',pitch,(0,0,.913),(.19,.16,.092),'metal',.012)
 # Chest silhouette with a lifted centre undercut, like the sketch.
 outline=[(-.345,1.20),(-.27,1.23),(.27,1.23),(.345,1.20),(.325,.82),(.255,.84),(.155,.925),(-.155,.925),(-.255,.84),(-.325,.82)]
 part('chest main shell','panel',pitch,(0,0,0),'ivory',outline=outline,depth=.29,y=0,bevel=.014)
 box('red chest crown',pitch,(0,0,1.208),(.65,.292,.055),'red',.018)
 box('chest central face',pitch,(0,-.155,1.075),(.31,.026,.247),'red',.018)
 box('chest inset',pitch,(0,-.172,1.077),(.275,.018,.208),'ivory',.012)
 text('robot designation',pitch,(0,-.185,1.128),'XTI-30',.060,'dark')
 text('robot name',pitch,(0,-.185,1.187),'Z O O M E R',.018,'ivory')
 box('status display bezel',pitch,(0,-.184,.995),(.19,.025,.055),'dark',.006)
 text('clock display',pitch,(0,-.201,.998),'10:15',.035,'cyan')
 for i,m in enumerate(['green','blue','green','blue','red']):
  box('status indicator',pitch,(-.075+i*.038,-.187,1.038),(.022,.012,.009),m,.002)
 for s in [-1,1]:
  for z,r,m in [(1.108,.046,'green'),(.989,.036,'purple')]:
   cyl('instrument rim',pitch,(s*.235,-.159,z),r,.018,'metal','Y')
   cyl('instrument dial',pitch,(s*.235,-.172,z),r*.86,.01,'dark','Y')
   for i in range(10):
    a=2*pi*i/10
    sph('dial tick',pitch,(s*.235+r*.69*cos(a),-.18,z+r*.69*sin(a)),.0026,m)
   beam('dial needle',pitch,(s*.235,-.184,z),(s*.235-.015,-.184,z+.025),.0025,'ivory')
  box('lower chest vent',pitch,(s*.255,-.148,.9),(.10,.025,.07),'dark',.008)
  for i in range(5):box('chest vent rib',pitch,(s*.255,-.165,.875+i*.011),(.084,.008,.004),'metal',.001)
  for z in [.855,1.177]:cyl('shell screw',pitch,(s*.307,-.155,z),.008,.006,'metal','Y')
 collision(pitch,'box',(0,0,1.065),(.65,.275,.3))
 # Head assembly spins together within the dome footprint.
 head=link('head_yaw',pitch,(0,0,1.237),(0,0,1),None,8,mass=1.3,inertia=.025)
 cyl('head bearing',head,(0,0,1.239),.221,.035,'dark')
 ring('dome seal',head,(0,0,1.258),.222,.011,'metal')
 part('transparent pressure dome','dome',head,(0,0,1.258),'glass',radius=.235,height=.242,thickness=.003)
 cyl('head turntable deck',head,(0,0,1.266),.199,.024,'purple')
 box('head core',head,(0,.012,1.333),(.18,.115,.125),'green',.02)
 for s in [-1,1]:
  box('violet cheek shield',head,(s*.133,.007,1.332),(.071,.123,.14),'purple',.02)
  box('blue face plate',head,(s*.067,-.069,1.323),(.058,.022,.083),'blue',.012)
  for i in range(4):box('head circuit fin',head,(s*(.021+i*.026),-.068,1.382),(.009,.013,.032),'green',.003)
  beam('eye stalk',head,(s*.071,-.008,1.377),(s*.071,-.019,1.417),.008,'metal')
  box('square eye housing',head,(s*.071,-.025,1.427),(.049,.034,.047),'ivory',.007)
  cyl('red eye ring',head,(s*.071,-.045,1.427),.017,.012,'red','Y')
  cyl('optical eye lens',head,(s*.071,-.053,1.427),.011,.008,'cyan','Y')
  sph('eye glint',head,(s*.071-.003,-.059,1.431),.003,'white')
 box('mouth grille',head,(0,-.081,1.306),(.035,.013,.02),'metal',.003)
 for x in [-.01,0,.01]:box('mouth slot',head,(x,-.089,1.306),(.003,.004,.014),'dark',.001)
 collision(head,'sphere',(0,0,1.345),(.15,))
 # Three shoulder axes, hinge elbow, forearm rotation, two wrist axes.
 for side,s in [('right',-1),('left',1)]:
  x=s*.444; sh=(x,0,1.139)
  cyl('shoulder mounting spindle',pitch,(s*.356,0,1.139),.047,.11,'metal','X')
  j1=link(f'{side}_shoulder_pitch',pitch,sh,(1,0,0),[-165,60],65,mass=.3,inertia=.002)
  cyl('shoulder pitch bearing',j1,sh,.084,.139,'dark','X')
  for dx in [-.038,0,.038]:ring('shoulder bellows',j1,(x+dx,0,1.139),.078,.007,'metal','X')
  j2=link(f'{side}_shoulder_roll',j1,sh,(0,1,0),[-95,95],65,mass=.25,inertia=.002)
  sph('shoulder ball',j2,sh,.072,'metal')
  j3=link(f'{side}_shoulder_yaw',j2,sh,(0,0,1),[-110,110],32,mass=1.8,inertia=.014)
  box('red shoulder cap',j3,(x,0,1.174),(.149,.16,.082),'red',.025)
  box('upper arm shell',j3,(x,0,1.036),(.116,.14,.168),'ivory',.029)
  box('upper arm stripe',j3,(x,-.073,1.049),(.057,.009,.106),'green',.01)
  collision(j3,'capsule',(x,0,1.03),(.052,.15))
  elbow=link(f'{side}_elbow',j3,(x,0,.889),(1,0,0),[-145,0],45,mass=1.2,inertia=.009)
  cyl('elbow pivot',elbow,(x,0,.889),.057,.138,'green','X')
  cyl('elbow pin',elbow,(x+s*.074,0,.889),.03,.012,'metal','X')
  fore=link(f'{side}_forearm_roll',elbow,(x,0,.863),(0,0,1),[-180,180],14,mass=.8,inertia=.007)
  box('forearm shell',fore,(x,0,.776),(.109,.13,.162),'ivory',.024)
  box('forearm face accent',fore,(x,-.068,.75),(.08,.009,.093),'purple',.009)
  for dx in [-.021,.021]:beam('forearm rail',fore,(x+dx,-.071,.72),(x+dx,-.071,.825),.004,'metal')
  collision(fore,'capsule',(x,0,.777),(.047,.14))
  w1=link(f'{side}_wrist_pitch',fore,(x,0,.67),(1,0,0),[-70,70],9,mass=.2,inertia=.001)
  cyl('wrist pitch pin',w1,(x,0,.67),.038,.10,'metal','X')
  w2=link(f'{side}_wrist_roll',w1,(x,0,.657),(0,1,0),[-40,40],7,mass=.35,inertia=.001)
  for z in [.665,.648]:ring('wrist collar',w2,(x,0,z),.049,.008,'dark')
  cyl('palm',w2,(x,0,.622),.047,.05,'ivory')
  cyl('palm underside',w2,(x,0,.594),.042,.011,'purple')
  collision(w2,'cylinder',(x,0,.622),(.047,.05))
  SITES.append(dict(name=f'{side}_tool',body=w2,pos=(x,0,.465)))
  # Four radial fingers, each with proximal and distal hinges.
  for f in range(4):
   t=f*pi/2+pi/4; u=(cos(t),sin(t)); axis=(-u[1],u[0],0)
   p=(x+.041*u[0],.041*u[1],.6)
   mid=(x+.068*u[0],.068*u[1],.55)
   tip=(x+.025*u[0],.025*u[1],.496)
   knuckle=link(f'{side}_finger_{f+1}_base',w2,p,axis,[-25,55],2,mass=.045,inertia=.00003)
   sph('finger knuckle',knuckle,p,.015,'metal')
   beam('proximal claw',knuckle,p,mid,.013,'ivory')
   collision(knuckle,'capsule',tuple((a+b)/2 for a,b in zip(p,mid)),(.010,.044))
   distal=link(f'{side}_finger_{f+1}_tip',knuckle,mid,axis,[-10,70],1,mass=.025,inertia=.00002)
   sph('finger hinge',distal,mid,.014,'purple')
   beam('distal claw',distal,mid,tip,.011,'metal')
   sph('grip pad',distal,tip,.013,'rubber',(.9,.9,1.5))
   collision(distal,'sphere',tip,(.013,))
 return dict(name='Zoomer XTI-30',height_m=.18,width_m=.10,scale_xyz=(.1/1.048,.18/1.5085,.18/1.5085),coordinates='Design coordinates; multiply by scale_xyz for SI metres. +X left; -Y forward; +Z up',colors=COLORS,links=LINKS,parts=PARTS,collisions=COLLISIONS,sites=SITES)

if __name__=='__main__':
 design=build(); (ROOT/'assets/robot_spec.json').write_text(json.dumps(design,indent=2))
 print(f'{len(LINKS)} links, {sum(bool(x["torque"]) for x in LINKS)} motors, {len(PARTS)} visual parts')
