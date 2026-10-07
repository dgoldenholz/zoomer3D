"""Sample rigid tread links around the closed belt path, including pin play."""
from pathlib import Path
import json
import numpy as np
import trimesh as tm
from manifold3d import Manifold,Mesh64
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'print/articulated'
def load(path):
    mesh=tm.load(path);return Manifold(Mesh64(np.asarray(mesh.vertices),np.asarray(mesh.faces,dtype=np.uint64))),mesh.bounds

def main():
    joints=json.loads((OUT/'joints.json').read_text());report=dict(phases=12,max_pin_misalignment_mm=0,collisions=[])
    base,basebounds=load(OUT/'base.stl')
    for side in ['left','right']:
        nodes=sorted([j for j in joints if j['type']=='chain_pin' and j['name'].startswith(side)],key=lambda j:j['name'])
        points=np.array([j['origin_mm'] for j in nodes]);ends=np.roll(points,-1,axis=0)
        lens=np.linalg.norm(ends-points,axis=1);distance=np.r_[0,np.cumsum(lens)];period=distance[-1]
        solids=[load(OUT/(j['name']+'.stl'))[0] for j in nodes]
        wheels=[load(OUT/f'{side}_wheel_{i}.stl')[0] for i in range(8)]
        def sample(s):
            s%=period;i=min(len(nodes)-1,np.searchsorted(distance,s,side='right')-1)
            return points[i]+(ends[i]-points[i])*(s-distance[i])/lens[i]
        def advance(s,length):
            start=sample(s);cycle=np.floor(s/period);u=s-cycle*period
            index=min(len(nodes)-1,np.searchsorted(distance,u,side='right')-1)
            for _ in range(len(nodes)+1):
                direction=(ends[index]-points[index])/lens[index];offset=points[index]-start
                projection=float(offset@direction);disc=projection*projection-float(offset@offset)+length*length
                if disc>=0:
                    root=-projection+np.sqrt(disc)
                    absolute=cycle*period+distance[index]+root
                    if root<=lens[index]+1e-8 and root>=-1e-8 and absolute>s+1e-6:return absolute
                index+=1
                if index==len(nodes):index=0;cycle+=1
            raise RuntimeError('Cannot close tread path')
        def closed_positions(start):
            # Distribute the small necessary bearing play over the whole loop,
            # rather than stretching individual rigid links at a sharp corner.
            lower,upper=-.20,.20
            for _ in range(24):
                play=(lower+upper)/2;s=start;locations=[]
                for length in lens:locations.append(s);s=advance(s,length+play)
                if s-start>period:upper=play
                else:lower=play
            return np.array([sample(s) for s in locations])
        for phase in range(12):
            shift=phase/12*period;new=closed_positions(shift)
            moving=[];startpins=[];endpins=[]
            for i,solid in enumerate(solids):
                j=(i+1)%len(nodes);a,b=points[i],points[j];aa,bb=new[i],new[j]
                delta=np.arctan2((bb-aa)[2],(bb-aa)[1])-np.arctan2((b-a)[2],(b-a)[1])
                mat=tm.transformations.rotation_matrix(delta,[1,0,0]);mat[:3,3]=(aa+bb)/2-mat[:3,:3]@((a+b)/2)
                moving.append(solid.transform(mat[:3]));startpins.append((mat@np.r_[a,1])[:3]);endpins.append((mat@np.r_[b,1])[:3])
            pinerrors=np.linalg.norm(np.array(endpins)-np.roll(startpins,-1,axis=0),axis=1)
            report['max_pin_misalignment_mm']=max(report['max_pin_misalignment_mm'],float(pinerrors.max()))
            for i,a in enumerate(moving):
                for name,b in [(nodes[(i+1)%len(nodes)]['name'],moving[(i+1)%len(nodes)])]+[(f'{side}_wheel_{k}',w) for k,w in enumerate(wheels)]+[('base',base)]:
                    ba=np.array(a.bounding_box()).reshape(2,3);bb=np.array(b.bounding_box()).reshape(2,3)
                    if np.any(ba[1]<bb[0]) or np.any(bb[1]<ba[0]):continue
                    overlap=float((a^b).volume())
                    if overlap>.02:report['collisions'].append(dict(side=side,phase=phase,a=nodes[i]['name'],b=name,volume_mm3=overlap))
    report['pin_clearance_mm']=.35
    report['pass']=report['max_pin_misalignment_mm']<.35 and not report['collisions']
    (OUT/'tread_motion.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
