"""Run an expert baseline or trained policy and save its complete task trace."""
import argparse,json,time
from pathlib import Path
import numpy as np
from workshop import WorkshopEnv

def run(args):
    env=WorkshopEnv(args.drawing,stage=args.stage,max_steps=args.steps)
    policy=None
    if args.policy:
        from stable_baselines3 import PPO
        policy=PPO.load(args.policy,device='cpu')
    obs,_=env.reset(seed=args.seed);handle=None;previous=None;trajectory=[]
    if args.viewer:
        import mujoco.viewer
        handle=mujoco.viewer.launch_passive(env.model,env.data)
        handle.cam.lookat[:]=[-.13,-.20,.10];handle.cam.distance=.9;handle.cam.azimuth=100;handle.cam.elevation=-35
        handle.opt.geomgroup[3]=0;handle.opt.sitegroup[:]=0
    for step in range(args.steps):
        started=time.time();action=np.zeros(7) if policy is None else policy.predict(obs,deterministic=True)[0]
        obs,reward,done,truncated,info=env.step(action)
        if previous!=info['phase']:
            print(f"{info['time_s']:.2f}s {info['phase']} {info['color']} stroke {info['stroke']}",flush=True);previous=info['phase']
        if step%10==0:trajectory.append(dict(time_s=info['time_s'],base=env.data.qpos[:7].tolist(),phase=info['phase'],visible=info['visible']))
        if handle:
            handle.user_scn.ngeom=0;env.draw_ink(handle.user_scn)
            handle.sync()
            if not handle.is_running():break
            time.sleep(max(0,env.dt-(time.time()-started)))
        if done or truncated:break
    if handle:handle.close()
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    np.savez(output.with_suffix('.npz'),qpos=env.data.qpos,qvel=env.data.qvel,ctrl=env.data.ctrl,eq_data=env.model.eq_data,eq_active=env.data.eq_active,command=env.command)
    output.write_text(json.dumps(dict(controller='trained residual PPO' if policy else 'task controller baseline',result=info,events=env.events,ink=env.ink,trajectory=trajectory),indent=2))
    print(json.dumps(info,indent=2));env.close();return info
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--drawing',default='targets/four_colors.json');p.add_argument('--output',default='training/baseline.json')
    p.add_argument('--policy');p.add_argument('--viewer',action='store_true');p.add_argument('--steps',type=int,default=26000);p.add_argument('--seed',type=int,default=7)
    p.add_argument('--stage',choices=['navigation','pickup','drawing','sequence'],default='sequence');run(p.parse_args())
