"""Train a residual PPO policy through a measured skill curriculum."""
import argparse
import json
import signal
import time
from pathlib import Path
import numpy as np
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.monitor import Monitor
from workshop import WorkshopEnv
from drawing import load_drawing

STOP=False
def stop(signum,frame):
    global STOP
    STOP=True

def atomic_json(path,value):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2,allow_nan=False));temp.replace(path)

def evaluate(policy,drawing,stage,episodes=2,seed=300,stop_file=None):
    results=[]
    horizon=max(26000,2500*len(load_drawing(drawing)['strokes'])) if isinstance(drawing,(str,Path)) else max(26000,2500*len(drawing['strokes']))
    env=WorkshopEnv(drawing,stage=stage,randomize=True,max_steps=horizon)
    for episode in range(episodes):
        obs,_=env.reset(seed=seed+episode)
        for _ in range(env.max_steps):
            if STOP or (stop_file and stop_file.exists()):
                env.close();return None
            action=np.zeros(7) if policy is None else policy.predict(obs,deterministic=True)[0]
            obs,_,done,truncated,info=env.step(action)
            if done or truncated:break
        results.append(info)
    env.close()
    return dict(success_rate=float(np.mean([r['success'] for r in results])),episodes=results)

def train(args):
    torch.set_num_threads(2);np.random.seed(args.seed);torch.manual_seed(args.seed)
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    stages=['navigation','pickup','drawing','sequence'] if args.curriculum else ['sequence']
    start=time.time();history=[];used=0
    horizon=max(26000,2500*len(load_drawing(args.drawing)['strokes']))
    env=Monitor(WorkshopEnv(args.drawing,stage=stages[0],randomize=True,max_steps=8000))
    if args.resume:policy=PPO.load(args.resume,env=env,device='cpu')
    else:
        policy=PPO('MlpPolicy',env,n_steps=256,batch_size=64,n_epochs=4,gamma=.995,
                   learning_rate=1e-4,ent_coef=.001,policy_kwargs=dict(net_arch=[64,64],log_std_init=-2),
                   seed=args.seed,device='cpu',verbose=0)
        # Start with the task controller and learn corrections, rather than spend
        # thousands of episodes discovering how to keep the robot upright.
        torch.nn.init.zeros_(policy.policy.action_net.weight);torch.nn.init.zeros_(policy.policy.action_net.bias)
    initial_steps=policy.num_timesteps
    state=dict(status='running',algorithm='PPO residual control',controller_version=3,target=str(Path(args.drawing).resolve()),seed=args.seed,requested_steps=args.steps,
               warm_start_steps=initial_steps,
               stages=stages,stage=stages[0],trained_steps=0,elapsed_s=0,evaluations=[],policy_ready=False)
    class Progress(BaseCallback):
        def _on_step(self):
            state.update(trained_steps=int(self.num_timesteps-initial_steps),elapsed_s=round(time.time()-start,1))
            if self.n_calls%100==0:atomic_json(out/'status.json',state)
            if self.n_calls%2000==0:self.model.save(out/'checkpoint')
            return not STOP and not (out/'stop_requested').exists()
    try:
        for index,stage in enumerate(stages):
            env=Monitor(WorkshopEnv(args.drawing,stage=stage,randomize=True,max_steps=8000 if stage!='sequence' else horizon))
            policy.set_env(env);state['stage']=stage;atomic_json(out/'status.json',state)
            remaining=args.steps-used
            allocation=max(256,remaining//(len(stages)-index))
            before=policy.num_timesteps
            policy.learn(total_timesteps=allocation,reset_num_timesteps=False,callback=Progress())
            used+=policy.num_timesteps-before;policy.save(out/'checkpoint')
            if STOP or (out/'stop_requested').exists():break
            result=evaluate(policy,args.drawing,stage,episodes=args.eval_episodes,stop_file=out/'stop_requested')
            if result is None:break
            history.append(dict(stage=stage,trained_steps=used,**result));state['evaluations']=history
            atomic_json(out/'status.json',state)
            env.close()
            if result['success_rate']<.8:
                # Do not call an unsuccessful skill mastered or silently skip it.
                state['needs_more_training']=stage
                break
        state.update(status='stopped' if STOP or (out/'stop_requested').exists() else 'completed',trained_steps=used,elapsed_s=round(time.time()-start,1),
                     policy_ready=bool(history and history[-1]['stage']=='sequence' and history[-1]['success_rate']>=.8))
        policy.save(out/'policy')
        atomic_json(out/'status.json',state)
        print(json.dumps(state,indent=2),flush=True)
    except Exception as error:
        state.update(status='failed',error=str(error));atomic_json(out/'status.json',state);raise
    finally:env.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--drawing',default='targets/four_colors.json');p.add_argument('--output',default='training/latest')
    p.add_argument('--steps',type=int,default=100000);p.add_argument('--seed',type=int,default=7)
    p.add_argument('--eval-episodes',type=int,default=2);p.add_argument('--resume');p.add_argument('--no-curriculum',dest='curriculum',action='store_false')
    args=p.parse_args()
    if args.steps<256:p.error('Use at least 256 steps.')
    train(args)
