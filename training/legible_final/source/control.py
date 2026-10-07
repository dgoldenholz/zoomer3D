"""Named torque commands and a small outcome-based environment for Zoomer."""
from pathlib import Path
import numpy as np
import mujoco
HERE=Path(__file__).resolve().parent

class ZoomerEnv:
    """NumPy interface: 35 normalized torque commands, joint state and tool goal.

    This is a starter environment, not a trained policy or a Gymnasium adapter.
    step() advances 10 ms. A goal is a world-space right-tool position in metres.
    """
    def __init__(self, scene='whiteboard', horizon=1000):
        self.model=mujoco.MjModel.from_xml_path(str(HERE/f'{scene}.xml'))
        self.data=mujoco.MjData(self.model)
        self.names=[self.model.actuator(i).name for i in range(self.model.nu)]
        self.jids=self.model.actuator_trnid[:,0]
        self.qadr=self.model.jnt_qposadr[self.jids]
        self.dadr=self.model.jnt_dofadr[self.jids]
        self.gear=self.model.actuator_gear[:,0]
        self.site=mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_SITE,'right_tool')
        self.horizon=horizon;self.goal=np.array([-.029,-.0571,.12]);self.steps=0
        self.reset()
    def reset(self, goal=None):
        mujoco.mj_resetData(self.model,self.data);self.steps=0
        if goal is not None:self.goal=np.array(goal,dtype=float)
        mujoco.mj_forward(self.model,self.data)
        return self.observe()
    def observe(self):
        return dict(joint_position=self.data.qpos[self.qadr].copy(),
                    joint_velocity=self.data.qvel[self.dadr].copy(),
                    achieved_goal=self.data.site_xpos[self.site].copy(),
                    desired_goal=self.goal.copy())
    def step(self, action):
        action=np.asarray(action,dtype=float)
        if action.shape!=(self.model.nu,) or not np.all(np.isfinite(action)):
            raise ValueError(f'Expected {self.model.nu} finite motor commands')
        self.data.ctrl[:]=np.clip(action,-1,1)
        mujoco.mj_step(self.model,self.data,nstep=10);self.steps+=1
        mujoco.mj_forward(self.model,self.data)
        obs=self.observe();error=np.linalg.norm(obs['achieved_goal']-self.goal)
        reward=-float(error)-1e-5*float(np.square(action).sum())
        success=bool(error<.001)
        return obs,reward,success,self.steps>=self.horizon,dict(distance_m=float(error))
    def command(self, **named_torques):
        action=np.zeros(self.model.nu)
        for name,value in named_torques.items():action[self.names.index(name)]=value
        return self.step(action)
    def pd(self, target):
        """Gravity-compensated PD converted to the normalized torque action."""
        q=self.data.qpos[self.qadr];v=self.data.qvel[self.dadr]
        # Mass-scaled PD avoids an oversized gain on the gram-scale finger links.
        M=np.zeros((self.model.nv,self.model.nv))
        mujoco.mj_fullM(self.model,self.data,M)
        acc=np.zeros(self.model.nv)
        acc[self.dadr]=400*(np.asarray(target)-q)-40*v
        tau=(M@acc+self.data.qfrc_bias-self.data.qfrc_passive)[self.dadr]
        return np.clip(tau/self.gear,-1,1)


def solve_ik(env, goal, initial=None, iterations=250):
    """Damped least-squares IK for the seven right-arm joints, position and marker direction."""
    m=env.model;d=mujoco.MjData(m)
    d.qpos[:]=env.data.qpos
    if initial is not None:d.qpos[env.qadr]=initial
    names=['right_shoulder_pitch','right_shoulder_roll','right_shoulder_yaw','right_elbow','right_forearm_roll','right_wrist_pitch','right_wrist_roll']
    js=np.array([m.joint(n).id for n in names]);qs=m.jnt_qposadr[js];ds=m.jnt_dofadr[js]
    jac=np.zeros((3,m.nv));jacr=np.zeros((3,m.nv))
    for _ in range(iterations):
        mujoco.mj_forward(m,d);err=np.asarray(goal)-d.site_xpos[env.site]
        z=d.site_xmat[env.site].reshape(3,3)[:,2];direction=np.array([0.,1.,0.])
        er=np.cross(z,direction)
        if np.linalg.norm(err)<.000025 and np.linalg.norm(er)<.001:break
        mujoco.mj_jacSite(m,d,jac,jacr,env.site)
        J=np.vstack([jac[:,ds],.03*(np.eye(3)-np.outer(z,z))@jacr[:,ds]])
        err=np.r_[err,.03*er]
        dq=J.T@np.linalg.solve(J@J.T+np.eye(6)*1e-7,err)
        d.qpos[qs]+=np.clip(dq,-.12,.12)
        d.qpos[qs]=np.clip(d.qpos[qs],m.jnt_range[js,0]+.001,m.jnt_range[js,1]-.001)
    mujoco.mj_forward(m,d)
    return d.qpos[env.qadr].copy(),float(np.linalg.norm(np.asarray(goal)-d.site_xpos[env.site]))
