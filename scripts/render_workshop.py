"""Render the actual workshop and its saved contact trace."""
from pathlib import Path
import sys,json
import numpy as np
import mujoco
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'simulation'))
from workshop import WorkshopEnv

env=WorkshopEnv();env.reset(seed=7)
Image.fromarray(env.render()).save(ROOT/'renders/workshop.png')
trace=json.loads((ROOT/'training/learned_sequence.json').read_text())
state=np.load(ROOT/'training/learned_sequence.npz')
for field in ['qpos','qvel','ctrl','eq_active']:getattr(env.data,field)[:]=state[field]
env.model.eq_data[:]=state['eq_data'];env.ink=trace['ink'];mujoco.mj_forward(env.model,env.data)
Image.fromarray(env.render()).save(ROOT/'renders/workshop_completed.png')
env.close();print('WORKSHOP_RENDERS_COMPLETE')
