"""Check model loading, motor response, finite dynamics and URDF consistency."""
from pathlib import Path
import sys,json,xml.etree.ElementTree as ET
import numpy as np
import mujoco
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'simulation'))
from control import ZoomerEnv
from demo import run
report={'mujoco_version':mujoco.__version__,'scenes':{},'motor_response':{}}
for name in ['zoomer','zoomer_fixed','whiteboard']:
    env=ZoomerEnv(name);m,d=env.model,env.data
    target=d.qpos[env.qadr].copy()
    for _ in range(2000):
        d.ctrl[:]=env.pd(target);mujoco.mj_step(m,d)
    assert np.isfinite(d.qpos).all() and np.isfinite(d.qvel).all()
    assert d.time>1.99 and not any(w.number for w in d.warning)
    assert m.nu==35
    report['scenes'][name]=dict(motors=m.nu,scalar_joints=m.njnt-(name=='zoomer'),mass_kg=float(m.body_mass.sum()),steps=2000,finite=True,warnings=0,base_z_m=float(d.body('base').xpos[2]))
env=ZoomerEnv('zoomer_fixed');m,d=env.model,env.data
# Each motor is tested independently with an in-range command while all other motors hold neutral.
for i,n in enumerate(env.names):
    env.reset();target=d.qpos[env.qadr].copy();delta=-.12 if n.endswith('elbow') else .12
    target[i]+=delta
    for _ in range(700):d.ctrl[:]=env.pd(target);mujoco.mj_step(m,d)
    actual=float(d.qpos[env.qadr[i]]);assert abs(actual-delta)<.03,(n,actual,delta)
    report['motor_response'][n]=dict(target_rad=delta,actual_rad=actual)
u=ET.parse(ROOT/'simulation/zoomer.urdf').getroot();uj={j.attrib['name']:j for j in u.findall('joint')}
for i,n in enumerate(env.names):
    j=uj[n];assert np.allclose(np.fromstring(j.find('axis').attrib['xyz'],sep=' '),m.jnt_axis[env.jids[i]])
    if m.jnt_limited[env.jids[i]]:
        lim=j.find('limit').attrib;assert np.allclose([float(lim['lower']),float(lim['upper'])],m.jnt_range[env.jids[i]])
imported=mujoco.MjModel.from_xml_path(str(ROOT/'simulation/zoomer.urdf'))
assert imported.njnt==49
report['urdf']=dict(links=len(u.findall('link')),joints=len(uj),motor_axes_and_limits_match=True,imported_by_mujoco=True)
for side in ['left','right']:
    expected=[f'{side}_drive']+[f'{side}_idler_{i}' for i in range(1,5)]+[f'{side}_return_{i}' for i in range(1,4)]
    assert all(mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_JOINT,n)>=0 for n in expected)
report['tread_layout']=dict(lower_wheels_per_side=5,upper_rollers_per_side=3,drive_motors=2,passive_wheel_joints=14)
report['tool_path']=run();assert report['tool_path']['rms_error_mm']<.5
(ROOT/'simulation/validation.json').write_text(json.dumps(report,indent=2));print('PASS: all 35 motors, three scenes, URDF axes/limits, and circular tool path')
