"""Integrated passive print-in-place robot, in millimetres.

Every moving component is a separate watertight volume. Captured shafts use
0.35 mm radial and axial clearance. Open yokes expose internal support to water.
This is a printable articulation model, not a motor/gearbox packaging design.
"""
from pathlib import Path
import json,math,sys
import numpy as np
import trimesh as tm
from manifold3d import Manifold
from build_print import solid,mesh,box,cyl,mf3
from track_profile import track_path,track_wheels

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'print/articulated'
GAP=.35
PARTS={};JOINTS=[];COLORS={};ANCHORS={}
def sphere(radius,center):return solid(tm.creation.icosphere(subdivisions=2,radius=radius)).translate(center)
def cylinder(radius,length,center,axis=(0,0,1)):
    t=tm.creation.cylinder(radius,length,sections=40)
    t.apply_transform(tm.geometry.align_vectors([0,0,1],axis));t.apply_translation(center)
    return solid(t)
def beam(a,b,r=1.8):
    a,b=np.asarray(a),np.asarray(b);delta=b-a
    return cylinder(r,np.linalg.norm(delta),((a+b)/2).tolist(),delta/np.linalg.norm(delta))+sphere(r,a)+sphere(r,b)
def add(name,value,color=0):
    PARTS[name]=(PARTS[name]+value) if name in PARTS else value;COLORS[name]=color
def transform(value,rotation,origin):return value.transform(np.column_stack([rotation,np.asarray(origin)]))

def hinge(name,parent,origin,axis=(1,0,0),size=1,limits=(-125,25),up=False):
    """Open yoke with a retained, integral axle and external end flanges."""
    o=np.array(origin,dtype=float);x=np.array(axis,dtype=float);x/=np.linalg.norm(x)
    z=np.array([0.,0.,1.]);z-=x*np.dot(x,z);z/=np.linalg.norm(z)
    if up:z=-z
    y=np.cross(z,x);rotation=np.column_stack([x,y,z]);s=size;gap=GAP if s>=.65 else .30
    shaft=1.25*s;cap=shaft+max(.65*s,.55);ear_r=4.3*s
    halfhub=1.9*s;ear_inner=halfhub+gap;ear_width=2*s
    ear_center=ear_inner+ear_width/2;ear_end=ear_inner+ear_width
    cap_inner=ear_end+gap;cap_width=max(.8*s,.65);cap_center=cap_inner+cap_width/2
    rotor=cylinder(2.8*s,2*halfhub,[0,0,0],(1,0,0))+cylinder(shaft,2*cap_inner,[0,0,0],(1,0,0))
    socket=Manifold()
    for sign in [-1,1]:
        rotor+=cylinder(cap,cap_width,[sign*cap_center,0,0],(1,0,0))
        ear=cylinder(ear_r,ear_width,[sign*ear_center,0,0],(1,0,0))-cylinder(shaft+gap,ear_width+2,[sign*ear_center,0,0],(1,0,0))
        socket+=ear
    back=max(5.5*s,3.2*s+.9+.3)
    socket+=box([2*ear_end,1.8*s,2.8*s],[0,back,0])
    for sign in [-1,1]:socket+=beam([sign*ear_center,3*s,0],[sign*ear_center,back,0],max(.65,1*s))
    # Rotor exit and parent attachment are on opposite sides of the bearing.
    anchor=o+rotation@np.array([0,0,-3.2*s]);parent_point=o+rotation@np.array([0,back,0])
    rotor+=beam([0,0,0],[0,0,-3.2*s],max(.9,1.7*s))
    # Carve a running clearance through any connector that approaches the pin.
    cutter=cylinder(shaft+gap,2*cap_inner,[0,0,0],(1,0,0))
    for sign in [-1,1]:cutter+=cylinder(cap+gap,cap_width+2*gap,[sign*cap_center,0,0],(1,0,0))
    local_rotor,local_socket=rotor,socket
    add(parent,transform(socket,rotation,o));add(name,transform(rotor,rotation,o),1)
    if parent in ANCHORS:add(parent,beam(ANCHORS[parent],parent_point,max(1.0,1.8*s)))
    ANCHORS[name]=anchor
    JOINTS.append(dict(name=name,parent=parent,type='hinge',origin_mm=o.tolist(),axis=x.tolist(),limits_deg=list(limits),
                       radial_gap_mm=gap,axial_gap_mm=gap,pin_diameter_mm=2*shaft,retention_overlap_mm=cap-shaft-gap,
                       local_rotor=local_rotor,local_socket=local_socket,rotation=rotation))
    JOINTS[-1]['cutter']=transform(cutter,rotation,o)
    return name

def swivel(name,parent,origin,radius=5.5,up=False):
    o=np.asarray(origin,dtype=float);r=radius;shaft=r*.40;cap=r*.70;half=2.8 if r>4 else 1.8
    rotor=cylinder(shaft,2*(half+GAP),[0,0,0])
    for sign in [-1,1]:rotor+=cylinder(cap,.9,[0,0,sign*(half+GAP+.45)])
    socket=cylinder(r,2*half,[0,0,0])-cylinder(shaft+GAP,2*half+2,[0,0,0])
    # Radial windows allow flushing support from the captive shaft cavity.
    for a in [0,90,180,270]:
        slot=box([r*2,1.2,1.2],[0,0,0]).rotate([0,0,a]);socket-=slot
    add(parent,socket.translate(o));add(name,rotor.translate(o),3)
    side=o+np.array([0,r-1,0])
    if parent in ANCHORS:
        corner=np.array([o[0],o[1]+r+1,ANCHORS[parent][2]])
        add(parent,beam(ANCHORS[parent],corner,1.4)+beam(corner,side,1.4))
    direction=1 if up else -1
    ANCHORS[name]=o+np.array([0,0,direction*(half+GAP+.9)])
    JOINTS.append(dict(name=name,parent=parent,type='continuous',origin_mm=o.tolist(),axis=[0,0,1],limits_deg=[-180,180],
                       radial_gap_mm=GAP,axial_gap_mm=GAP,pin_diameter_mm=2*shaft,retention_overlap_mm=cap-shaft-GAP,
                       local_rotor=rotor,local_socket=socket,rotation=np.eye(3)))
    cutter=cylinder(shaft+GAP,2*(half+GAP),[0,0,0])
    for sign in [-1,1]:cutter+=cylinder(cap+GAP,.9+2*GAP,[0,0,sign*(half+GAP+.45)])
    JOINTS[-1]['cutter']=cutter.translate(o)
    return name

def make_robot():
    PARTS.clear();JOINTS.clear();COLORS.clear();ANCHORS.clear()
    add('base',box([43,60,8],[0,0,28]),2)
    column=cylinder(5.8,58,[0,0,59])-cylinder(4.6,9,[0,0,86])
    add('base',column,2)
    for z in [38,49,60,71,82]:add('base',cylinder(8,2,[0,0,z]),2)
    waist=swivel('waist_yaw','base',[0,0,90],radius=7,up=True)
    torso=hinge('waist_pitch',waist,[0,0,101],up=True,limits=(-25,25))
    # A hollow chest reduces mass and gives access to the head bearing.
    chest=box([60,25,32],[0,0,130])-box([55,20,30],[0,0,128])
    add(torso,chest);add(torso,beam(ANCHORS[torso],[0,0,110],1.7));add(torso,beam([0,0,110],[0,0,116],3));add(torso,beam([0,0,116],[0,-11.5,116],2))
    add(torso,box([24,2.2,20],[0,-13,132]))
    add(torso,box([58,25,3],[0,0,146]),0)
    # Head swivel has a hollow support pedestal, avoiding its lower flange.
    add(torso,cylinder(7,6,[0,0,148])-cylinder(4.7,8,[0,0,148]))
    ANCHORS.pop(torso,None)
    head=swivel('head_yaw',torso,[0,0,150],radius=6.8,up=True)
    add(head,cylinder(22.1,2,[0,0,157]))
    add(head,beam(ANCHORS[head],[0,0,157],3.5))
    add(head,box([17,9,12],[0,0,162]),4)
    for x in [-7,7]:add(head,beam([x,0,166],[x,-1,172],1.2));add(head,cylinder(2.4,3,[x,-2,172],(0,1,0)))
    # Thin hemispherical shell: its rim bonds to the head deck during printing.
    dome=sphere(22,[0,0,158])-sphere(21.1,[0,0,158]);dome-=box([60,60,50],[0,0,133])
    for y in [-21,21]:dome-=box([3,6,2],[0,y,159.2])
    add('dome_cover',dome,0)
    for side,sign in [('right',-1),('left',1)]:
        x=sign*43
        # Each shoulder retains three independent, physically separated axes.
        sh=hinge(side+'_shoulder_pitch',torso,[x,0,137],limits=(-125,25))
        add(torso,beam([sign*29,5.5,137],[x,5.5,137],2.0))
        roll=hinge(side+'_shoulder_roll',sh,[x,0,126],axis=(0,sign,0),size=.85,limits=(-55,55))
        yaw=swivel(side+'_shoulder_yaw',roll,[x,0,115],radius=4.6)
        elbow=hinge(side+'_elbow',yaw,[x,0,103],size=.85,limits=(-125,0))
        fore=swivel(side+'_forearm_roll',elbow,[x,0,92],radius=4.6)
        wrist=hinge(side+'_wrist_pitch',fore,[x,0,81],size=.70,limits=(-50,50))
        palm=hinge(side+'_wrist_roll',wrist,[x,0,72],axis=(0,sign,0),size=.60,limits=(-30,30))
        add(palm,cylinder(4.8,3,[x,0,65]));add(palm,beam(ANCHORS[palm],[x,0,65],1.5))
        for i in range(4):
            a=(i+.5)*np.pi/2;u=np.array([np.cos(a),np.sin(a),0]);axis=np.array([-u[1],u[0],0])
            p=np.array([x,0,62])+u*5.0
            proximal=hinge(f'{side}_finger_{i+1}_base',palm,p,axis=axis,size=.40,limits=(-15,50))
            add(palm,beam([x,0,65],p+np.cross([0,0,1],axis)*1.6,1.0))
            mid=np.array([x,0,55.5])+u*6.0
            distal=hinge(f'{side}_finger_{i+1}_tip',proximal,mid,axis=axis,size=.38,limits=(-10,60))
            tip=np.array([x,0,49])+u*2.5
            add(distal,beam(ANCHORS[distal],tip,.95));add(distal,sphere(1.1,tip))
    return PARTS

def make_tracks():
    # Each belt is a closed chain of 36 retained-pin links. Wheel axles are
    # captured separately in the chassis. The sprocket is friction driven.
    path=np.array(track_path(36))*1000*(.18/1.5085);offset=1.55-float(path[:,1].min());path[:,1]+=offset
    count=len(path);width=9.8
    for side,sign in [('right',-1),('left',1)]:
        x=sign*29
        for i,w in enumerate(track_wheels()):
            y=w['y']*1000*(.18/1.5085);z=w['z']*1000*(.18/1.5085)+offset
            r=w['radius']*1000*(.18/1.5085)-.9
            o=np.array([x,y,z]);pin_radius=1.1;shaft=cylinder(pin_radius,12,o,(1,0,0))
            for dx in [-6.45,6.45]:shaft+=cylinder(1.9,.9,o+[dx,0,0],(1,0,0))
            add('base',shaft);inner=o+[-sign*6,0,0]
            add('base',beam([sign*20,y,27],inner,1.4))
            wheel=cylinder(r,6.8,o,(1,0,0))-cylinder(pin_radius+GAP,8,o,(1,0,0))
            name=f'{side}_wheel_{i}';add(name,wheel,2)
            JOINTS.append(dict(name=name,parent='base',type='continuous',origin_mm=o.tolist(),axis=[1,0,0],limits_deg=[-180,180],radial_gap_mm=GAP,axial_gap_mm=2.25,pin_diameter_mm=2.2,retention_overlap_mm=.45))
        for i in range(count):
            a=np.r_[x,path[i]];b=np.r_[x,path[(i+1)%count]];v=b-a;length=np.linalg.norm(v);t=v/length
            normal=np.cross([1,0,0],t);frame=np.column_stack([[1,0,0],t,normal]);mid=(a+b)/2
            link=transform(box([width,length-3.6,1.3],[0,0,0]),frame,mid)
            # Fork at a, shaft and central knuckle at b. Adjacent components
            # remain separate; flange retention prevents pins sliding out.
            for dx in [-3.35,3.35]:
                ear=cylinder(1.55,1.7,a+[dx,0,0],(1,0,0))+beam(a+[dx,0,0],mid+[dx,0,0],.65)
                ear-=cylinder(.95,2.1,a+[dx,0,0],(1,0,0))
                link+=ear
            link+=cylinder(1.4,4.2,b,(1,0,0))+cylinder(.6,9.2,b,(1,0,0))
            for dx in [-4.85,4.85]:link+=cylinder(1.15,.6,b+[dx,0,0],(1,0,0))
            link+=beam(mid,b,.75)
            name=f'{side}_tread_{i:02d}';add(name,link,3)
            JOINTS.append(dict(name=name,parent=f'{side}_tread_{(i-1)%count:02d}',type='chain_pin',origin_mm=a.tolist(),axis=[1,0,0],limits_deg=[-35,35],radial_gap_mm=.35,axial_gap_mm=.35,pin_diameter_mm=1.2,retention_overlap_mm=.20))

def main():
    OUT.mkdir(parents=True,exist_ok=True);make_robot();make_tracks()
    for joint in JOINTS:
        if 'cutter' in joint:PARTS[joint['parent']]-=joint['cutter']
    # Clearance around neighbouring link connectors, beyond the bearing itself.
    for joint in JOINTS:
        if 'local_rotor' not in joint:continue
        moving=PARTS[joint['name']];parent=joint['parent']
        if (moving^PARTS[parent]).volume()>.005:
            origin=np.array(joint['origin_mm'])
            cutter=moving.translate(-origin).minkowski_sum(Manifold.sphere(GAP,8)).translate(origin)
            result=PARTS[parent]-cutter
            if result.is_empty() or str(result.status())!='Error.NoError':
                raise RuntimeError('Clearance cut failed for '+parent)
            PARTS[parent]=result
    report=dict(units='mm',physical_print_test='not performed',nozzle_mm=.4,nominal_gap_mm=GAP,
                joint_count=len(JOINTS),parts={},joint_tests=[],intersections=[])
    # Check each bearing template before checking the complete assembly.
    for joint in JOINTS:
        if 'local_rotor' not in joint:continue
        rotor=joint['local_rotor'];socket=joint['local_socket'];axis=0 if joint['type']=='hinge' else 2
        values=np.linspace(*joint['limits_deg'],15);overlap=[]
        for angle in values:
            angles=[0.,0.,0.];angles[axis]=float(angle)
            overlap.append(float((rotor.rotate(angles)^socket).volume()))
        report['joint_tests'].append(dict(name=joint['name'],tested_angles_deg=values.tolist(),max_bearing_overlap_mm3=max(overlap)))
    meshes={}
    for name,value in PARTS.items():
        PARTS[name]=value.simplify(.005)
        data=PARTS[name].to_mesh64()
        meshes[name]=tm.Trimesh(np.array(data.vert_properties)[:,:3],np.array(data.tri_verts),process=False)
    for old in OUT.glob('*.stl'):
        if old.stem not in meshes:old.unlink()
    for name,t in meshes.items():
        t.export(OUT/(name+'.stl'))
        reread=tm.load(OUT/(name+'.stl'))
        report['parts'][name]=dict(watertight=bool(t.is_watertight),exported_stl_watertight=bool(reread.is_watertight),volume_mm3=float(t.volume),components=len(t.split(only_watertight=False)),bounds_mm=t.bounds.tolist())
    # Broad-phase bounds reject most part pairs before manifold intersection.
    names=list(meshes)
    for i,a in enumerate(names):
        for b in names[i+1:]:
            ba,bb=meshes[a].bounds,meshes[b].bounds
            if np.any(ba[1]<bb[0]) or np.any(bb[1]<ba[0]):continue
            overlap=float((PARTS[a]^PARTS[b]).volume())
            if overlap>.005:report['intersections'].append(dict(a=a,b=b,volume_mm3=overlap))
    bounds=np.array([t.bounds for t in meshes.values()]);report['extent_mm']=(bounds[:,1].max(axis=0)-bounds[:,0].min(axis=0)).tolist()
    report['cad_pass']=all(p['watertight'] and p['exported_stl_watertight'] and p['components']==1 for p in report['parts'].values()) and not report['intersections'] and all(j['max_bearing_overlap_mm3']<.005 for j in report['joint_tests'])
    cleaned=[{k:v for k,v in j.items() if k not in ['local_rotor','local_socket','rotation','cutter']} for j in JOINTS]
    (OUT/'joints.json').write_text(json.dumps(cleaned,indent=2));(OUT/'validation.json').write_text(json.dumps(report,indent=2))
    # Core 3MF retains the assembled coordinates and named moving volumes.
    mf3('articulated/zoomer_articulated_180mm.3mf',[(n,t,COLORS[n]) for n,t in meshes.items()])
    print(json.dumps({k:v for k,v in report.items() if k not in ['parts','joint_tests']},indent=2))
if __name__=='__main__':main()
