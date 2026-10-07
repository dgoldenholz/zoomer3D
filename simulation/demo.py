"""Run `python simulation/demo.py` or `mjpython simulation/demo.py --viewer`."""
import argparse, json, time
from pathlib import Path
import numpy as np
import mujoco
from control import ZoomerEnv, solve_ik

def run(viewer=False):
    env=ZoomerEnv();m,d=env.model,env.data
    base=np.array([-.029,-.0571,.122]);radius=.005
    goal=base+np.array([radius,0,0])
    seed=np.zeros(m.nu)
    for n,v in [('right_shoulder_pitch',-65),('right_elbow',-85),('right_shoulder_roll',-12)]:seed[env.names.index(n)]=np.deg2rad(v)
    target,error=solve_ik(env,goal,seed)
    # Set initial state once; subsequent motion uses motor torques through mj_step.
    d.qpos[env.qadr]=target;mujoco.mj_forward(m,d)
    handle=None
    if viewer:
        from mujoco import viewer as mjviewer
        handle=mjviewer.launch_passive(m,d)
        handle.cam.lookat[:]=[0,0,.09];handle.cam.distance=.35;handle.cam.azimuth=110;handle.cam.elevation=-15
        handle.opt.geomgroup[3]=0
    samples=[]
    for i in range(800):
        start=time.time();angle=2*np.pi*i/799
        goal=base+radius*np.array([np.cos(angle),0,np.sin(angle)])
        env.goal=goal
        target,ikerr=solve_ik(env,goal,target,iterations=15)
        for sub in range(10):
            d.ctrl[:]=env.pd(target);mujoco.mj_step(m,d)
        mujoco.mj_forward(m,d)
        samples.append(dict(t=float(d.time),target=goal.tolist(),actual=d.site_xpos[env.site].copy().tolist(),ik_error=ikerr))
        if handle:
            handle.sync()
            if not handle.is_running():break
            time.sleep(max(0,.01-(time.time()-start)))
    if handle:handle.close()
    errors=np.array([np.linalg.norm(np.array(s['actual'])-s['target']) for s in samples])
    stats=dict(duration_s=float(d.time),samples=len(samples),rms_error_mm=float(np.sqrt(np.mean(errors**2))*1000),max_error_mm=float(errors.max()*1000),initial_ik_error_mm=error*1000,finite=bool(np.isfinite(d.qpos).all()))
    output=Path(__file__).resolve().parent.parent/'renders';(output/'whiteboard_trace.json').write_text(json.dumps(dict(stats=stats,samples=samples),indent=2))
    # SVG is an inspectable task trace, not a claim of physical ink deposition.
    def xy(v):return (320+float(v[0]-base[0])*35000,280-float(v[2]-base[2])*35000)
    actual=' '.join('%.2f,%.2f'%xy(s['actual']) for s in samples)
    targetline=' '.join('%.2f,%.2f'%xy(s['target']) for s in samples)
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="640" height="620" viewBox="0 0 640 620"><rect width="640" height="620" fill="#101c2b"/><text x="30" y="42" font-family="sans-serif" font-size="24" fill="#edf4ff">Zoomer motor-controlled tool trace</text><polyline points="{targetline}" fill="none" stroke="#60748c" stroke-width="8"/><polyline points="{actual}" fill="none" stroke="#49d5d1" stroke-width="3"/><text x="30" y="560" font-family="sans-serif" font-size="17" fill="#c8d6e7">10 mm circle · RMS error {stats['rms_error_mm']:.3f} mm</text><text x="30" y="590" font-family="sans-serif" font-size="14" fill="#8fabc4">Fixed base · IK + torque PD · position tracking, no ink/contact model</text></svg>'''
    (output/'whiteboard_trace.svg').write_text(svg)
    print(json.dumps(stats,indent=2));return stats
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--viewer',action='store_true');run(p.parse_args().viewer)
