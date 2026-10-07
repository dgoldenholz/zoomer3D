"""Motor-driven drawing curriculum with visibility-gated task transitions.

The policy learns residual wheel speeds, Cartesian arm offsets, grip and head
commands around a task controller. Object poses are revealed only when visible.
A contact-qualified weld approximates a secure grasp; it is not a friction-only
grasp simulation. No robot or object pose is teleported during step().
"""
from pathlib import Path
import json
import math
import numpy as np
import mujoco
import gymnasium as gym
from gymnasium import spaces
from drawing import COLORS, load_drawing, validate_drawing, resample, path_errors
from control import ZoomerEnv

HERE=Path(__file__).resolve().parent
PHASES=['navigate_pick','reach_pick','close','lift','navigate_board','draw','retract','navigate_return','place','release','done']
def wrap(x):return (x+np.pi)%(2*np.pi)-np.pi

class WorkshopEnv(gym.Env):
    metadata={'render_modes':['rgb_array'],'render_fps':50}

    def __init__(self, drawing=None, stage='sequence', max_steps=26000, render_mode=None,
                 randomize=False, residual_scale=1.0):
        self.robot=ZoomerEnv('workshop');self.model=self.robot.model;self.data=self.robot.data
        self.layout=json.loads((HERE/'workshop_layout.json').read_text())
        self.drawing=load_drawing(drawing) if isinstance(drawing,(str,Path)) else validate_drawing(drawing or example())
        self.stage=stage;self.max_steps=max_steps;self.render_mode=render_mode;self.randomize=randomize
        self.residual_scale=residual_scale;self.renderer=None;self.dt=.02
        self.names=self.robot.names;self.qadr=self.robot.qadr;self.dadr=self.robot.dadr
        self.wheels=np.array([self.names.index(s+'_drive') for s in ['left','right']])
        self.arm_names=['right_shoulder_pitch','right_shoulder_roll','right_shoulder_yaw','right_elbow','right_forearm_roll','right_wrist_pitch','right_wrist_roll']
        self.arm_joints=np.array([self.model.joint(n).id for n in self.arm_names])
        self.arm_q=self.model.jnt_qposadr[self.arm_joints];self.arm_d=self.model.jnt_dofadr[self.arm_joints]
        self.arm_a=np.array([self.names.index(n) for n in self.arm_names])
        self.finger_a=[i for i,n in enumerate(self.names) if n.startswith('right_finger')]
        self.grasp_id=self.model.site('right_grasp').id
        self.head_a=self.names.index('head_yaw')
        self.action_space=spaces.Box(-1,1,(7,),dtype=np.float32)
        # 35 q + 35 qvel + phase + relative goal + 4 visible poses/masks + held + progress.
        self.observation_space=spaces.Box(-np.inf,np.inf,(35*2+len(PHASES)+3+4*4+5+3,),dtype=np.float32)
        self.reset()

    def reset(self,seed=None,options=None):
        super().reset(seed=seed);self.robot.reset();self.steps=0;self.phase_steps=0
        for color in COLORS:
            mask=self.model.geom_bodyid==self.model.body('marker_'+color).id
            self.model.geom_contype[mask]=1;self.model.geom_conaffinity[mask]=3
        self.stroke=0;self.point=0;self.held=None;self.phase='navigate_pick';self.events=[];self.ink=[];self.errors=[]
        self.coverage=[];self.fail_reason=None;self.returning_final=False;self.waypoints=[];self.last_grip=False
        self.targets=[]
        for stroke in self.drawing['strokes']:
            uv=resample(stroke['points']);origin=np.array(self.layout['drawing_origin'])
            self.targets.append(np.column_stack([origin[0]+uv[:,0],np.full(len(uv),origin[1]),origin[2]+uv[:,1]]))
        self.command=self.data.qpos[self.qadr].copy()
        # Initial placement may vary; subsequent motion comes only from motor torques.
        if self.randomize:
            self.data.qpos[0:2]+=self.np_random.uniform(-.015,.015,2)
            for side in ['left','right']:
                self.model.geom_friction[self.model.geom(side+'_drive_collision_0').id,0]=self.np_random.uniform(.60,.80)
        self.data.qpos[self.arm_q]=np.deg2rad([-25,-8,0,-65,0,0,0])
        self.command=self.data.qpos[self.qadr].copy();mujoco.mj_forward(self.model,self.data)
        self.goal=np.array(self.layout['marker_homes'][self.color]);self.visible_goal=False
        self._navigate('navigate_pick', self.pick_base())
        # Curriculum starts near a skill. These are reset states, never step-time shortcuts.
        if self.stage in ['pickup','drawing']:
            self.data.qpos[:2]=self.pick_base();mujoco.mj_forward(self.model,self.data)
            self._set_phase('reach_pick')
        if self.stage=='drawing':
            self.data.qpos[:2]=self.board_base(self.targets[0][0])
            self.command[self.arm_a]=np.deg2rad([-100,-12,0,-40,0,45,0])
            q=self.solve_arm(self.targets[0][0]+np.array([0,.02975,0]),np.array([0,1,0]),100)
            self.data.qpos[self.arm_q]=q;self.command[self.arm_a]=q;mujoco.mj_forward(self.model,self.data)
            self._seed_held(self.color);self._set_phase('draw')
        return self.observe(),self.info()

    @property
    def color(self):return self.drawing['strokes'][min(self.stroke,len(self.targets)-1)]['color']
    def marker_pos(self,color):return self.data.site('marker_'+color+'_grip').xpos.copy()
    def tip_pos(self):return self.data.site('marker_'+self.held+'_tip').xpos.copy() if self.held else self.data.site_xpos[self.grasp_id].copy()
    def yaw(self):
        r=self.data.body('base').xmat.reshape(3,3);return math.atan2(r[1,0],r[0,0])
    def pick_base(self,color=None):
        h=np.array(self.layout['marker_homes'][color or self.color]);return h[:2]+[.041,.034]
    def board_base(self,target):return np.array([target[0]+.031,-.372])
    def _set_phase(self,phase):
        self.events.append(dict(time_s=float(self.data.time),phase=phase,color=self.held or self.color,stroke=self.stroke))
        self.phase=phase;self.phase_steps=0
        if phase=='reach_pick':self.approach_ready=False
        if phase=='place':self.place_ready=False
        if phase=='draw':self.command[self.arm_a]=np.deg2rad([-100,-12,0,-40,0,45,0])
    def _navigate(self,phase,destination):
        # An open lane in front of both stations prevents driving through the table.
        here=self.data.qpos[:2].copy()
        self.waypoints=[np.array([here[0],-.12]),np.array([destination[0],-.12]),np.asarray(destination).copy()]
        self.reverse_waypoints=[bool(here[1]<-.14),False,False];self.aligning=False
        self._set_phase(phase)

    def visible(self,target,target_body=None):
        """At least one eye must pass the frustum and first-hit occlusion tests."""
        m,d=self.model,self.data;target=np.asarray(target)
        groups=np.array([1,1,0,1,0,0],dtype=np.uint8) # collision shapes occlude; glass does not
        for name in ['left_eye','right_eye']:
            c=m.camera(name).id;eye=d.cam_xpos[c];r=d.cam_xmat[c].reshape(3,3)
            vec=target-eye;distance=np.linalg.norm(vec)
            local=r.T@vec
            if distance<1e-6 or distance>.9 or local[2]>=0:continue
            half=np.deg2rad(m.cam_fovy[c]/2)
            if abs(local[1])>-local[2]*np.tan(half) or abs(local[0])>-local[2]*np.tan(half)*1.5:continue
            hit=np.array([-1],dtype=np.int32)
            length=mujoco.mj_ray(m,d,eye,vec/distance,groups,True,m.body('head_yaw').id,hit)
            if length<0 or length>=distance-.0015:return True
            if target_body is not None and hit[0]>=0 and m.geom_bodyid[hit[0]]==target_body:return True
        return False

    def solve_arm(self,goal,direction,iterations=10):
        m=self.model;d=mujoco.MjData(m);d.qpos[:]=self.data.qpos
        d.qpos[self.arm_q]=self.command[self.arm_a]
        jp=np.zeros((3,m.nv));jr=np.zeros_like(jp)
        for _ in range(iterations):
            mujoco.mj_forward(m,d);r=d.site_xmat[self.grasp_id].reshape(3,3)
            z=r@self.marker_axis_in_hand if self.held else r[:,2]
            err=np.r_[goal-d.site_xpos[self.grasp_id],.025*np.cross(z,direction)]
            if np.linalg.norm(err)<.00005:break
            mujoco.mj_jacSite(m,d,jp,jr,self.grasp_id)
            jac=np.vstack([jp[:,self.arm_d],.025*(np.eye(3)-np.outer(z,z))@jr[:,self.arm_d]])
            delta=jac.T@np.linalg.solve(jac@jac.T+np.eye(6)*1e-7,err)
            d.qpos[self.arm_q]=np.clip(d.qpos[self.arm_q]+np.clip(delta,-.18,.18),m.jnt_range[self.arm_joints,0]+.002,m.jnt_range[self.arm_joints,1]-.002)
        return d.qpos[self.arm_q].copy()

    def _weld(self,color):
        m,d=self.model,self.data;a=m.body('right_wrist_roll').id;b=m.body('marker_'+color).id
        r=d.xmat[a].reshape(3,3);relative=r.T@(d.xpos[b]-d.xpos[a])
        self.marker_axis_in_hand=r.T@d.xmat[b].reshape(3,3)[:,2]
        inv=np.empty(4);quat=np.empty(4);mujoco.mju_negQuat(inv,d.xquat[a]);mujoco.mju_mulQuat(quat,inv,d.xquat[b])
        i=m.equality('grasp_'+color).id;m.eq_data[i,3:6]=relative;m.eq_data[i,6:10]=quat;d.eq_active[i]=1
        d.eq_active[m.equality('dock_'+color).id]=0
        # Once the contact-qualified grasp is constrained, do not also solve
        # interpenetrating finger/barrel contacts against that same constraint.
        mask=m.geom_bodyid==b;m.geom_contype[mask]=4;m.geom_conaffinity[mask]=1
        self.held=color;mujoco.mj_forward(m,d)

    def _seed_held(self,color):
        # Used only for a drawing-stage reset to avoid relearning earlier skills.
        m,d=self.model,self.data;q=m.jnt_qposadr[m.joint('marker_'+color+'_free').id]
        d.qpos[q:q+3]=d.site_xpos[self.grasp_id]-d.body('right_wrist_roll').xmat.reshape(3,3)@np.array([0,0,.012]);d.qpos[q+3:q+7]=d.body('right_wrist_roll').xquat
        mujoco.mj_forward(m,d);self._weld(color)

    def contacts(self,color):
        m,d=self.model,self.data;marker=m.body('marker_'+color).id;fingers=set()
        for contact in d.contact:
            bodies=[m.geom_bodyid[g] for g in contact.geom]
            if marker not in bodies:continue
            other=bodies[1] if bodies[0]==marker else bodies[0];name=m.body(other).name or ''
            if name.startswith('right_finger'):fingers.add('_'.join(name.split('_')[:3]))
        return len(fingers)

    def marker_visible(self,color):
        b=self.data.body('marker_'+color);axis=b.xmat.reshape(3,3)[:,2]
        return any(self.visible(b.xpos+axis*offset,self.model.body('marker_'+color).id) for offset in [-.016,-.010,0,.010,.015])

    def drawing_visible(self,target):
        # A nib can cover its own contact point. Observe the surrounding 3 mm
        # patch; every ray must still pass the normal frustum/occlusion test.
        return any(self.visible(np.asarray(target)+offset) for offset in [[0,0,0],[.003,0,0],[-.003,0,0],[0,0,.003],[0,0,-.003]])

    def grasp_allowed(self,color):
        p=self.marker_pos(color)
        return (self.marker_visible(color) and
                np.linalg.norm(p-self.data.site_xpos[self.grasp_id])<.004 and self.contacts(color)>=2)

    def observe(self):
        base=self.data.body('base').xpos
        objects=[]
        for color in COLORS:
            p=self.marker_pos(color);seen=self.marker_visible(color)
            objects.extend([*(p-base if seen else np.zeros(3)),float(seen)])
        phase=np.eye(len(PHASES))[PHASES.index(self.phase)]
        held=np.eye(5)[list(COLORS).index(self.held)+1 if self.held else 0]
        # Navigation destinations are known map waypoints; live action targets need sight.
        visible_goal=self.visible(self.goal)
        goal=(self.goal-base) if visible_goal else np.zeros(3)
        obs=np.r_[np.sin(self.data.qpos[self.qadr]),np.clip(self.data.qvel[self.dadr],-20,20)/20,
                  phase,goal,objects,held,self.stroke/len(self.targets),self.point/len(self.targets[min(self.stroke,len(self.targets)-1)]),float(visible_goal)]
        return obs.astype(np.float32)

    def step(self,action):
        action=np.asarray(action,dtype=float)
        if action.shape!=(7,) or not np.isfinite(action).all():raise ValueError('Expected seven finite residual commands.')
        action=np.clip(action,-1,1)*self.residual_scale
        if self.phase=='done':return self.observe(),0.,True,False,self.info()
        m,d=self.model,self.data;self.steps+=1;self.phase_steps+=1;old_phase=self.phase
        wheel=np.zeros(2);close=False;direction=np.array([0.,0.,1.]);arm_goal=None
        home_color=self.held or (self.last_released if self.phase=='release' else self.color)
        home=np.array(self.layout['marker_homes'][home_color]);nav=self.phase.startswith('navigate')
        if nav:
            destination=self.waypoints[0]
            axle=(d.body('left_drive').xpos[:2]+d.body('right_drive').xpos[:2])/2
            desired_axle=destination+np.array([0.,-.02585])
            delta=desired_axle-axle;distance=np.linalg.norm(delta)
            angle=wrap(math.atan2(delta[0],-delta[1])-self.yaw())
            drive_sign=-1 if self.reverse_waypoints[0] else 1
            if drive_sign<0:angle=wrap(angle+np.pi)
            if self.aligning:distance=0
            if distance<.006:
                if len(self.waypoints)>1:self.waypoints.pop(0);self.reverse_waypoints.pop(0)
                else:
                    self.aligning=True
                    angle=wrap(-self.yaw())
                    if abs(angle)<.05:
                        if self.phase=='navigate_pick':self._set_phase('reach_pick')
                        elif self.phase=='navigate_return':self._set_phase('place')
                        else:self._set_phase('draw')
            speed=0 if distance<.006 else drive_sign*min(.085,distance*1.4)*max(0,math.cos(angle))**4
            turn=np.clip(angle*2.5-.5*d.qvel[5],-1.8,1.8);wheel=np.array([speed-turn*.027,speed+turn*.027])/.0085
            self.goal=np.r_[destination,.09]
            # Keep the hand above the table while driving, including after release.
            r=d.body('base').xmat.reshape(3,3);arm_goal=d.body('base').xpos+r@np.array([-.035,-.025,.112]);close=self.held is not None
        elif self.phase in ['reach_pick','close']:
            self.goal=self.marker_pos(self.color);arm_goal=self.goal.copy()
            close=self.phase=='close'
            if self.phase=='reach_pick' and not self.approach_ready:
                arm_goal[2]+=.028
                if np.linalg.norm(d.site_xpos[self.grasp_id]-arm_goal)<.003:self.approach_ready=True
            if self.phase=='reach_pick' and self.approach_ready and np.linalg.norm(d.site_xpos[self.grasp_id]-self.goal)<.003 and self.marker_visible(self.color):self._set_phase('close')
            if close and self.phase_steps>10 and self.grasp_allowed(self.color):
                self._weld(self.color);self._set_phase('lift')
        elif self.phase=='lift':
            arm_goal=home+[-.005,-.012,.034];self.goal=arm_goal;close=True
            if np.linalg.norm(d.site_xpos[self.grasp_id]-arm_goal)<.004 and self.marker_visible(self.held):
                if self.stage=='pickup':self._set_phase('done')
                else:self._navigate('navigate_board',self.board_base(self.targets[self.stroke][0]))
        elif self.phase=='draw':
            target=self.targets[self.stroke][self.point];self.goal=target;direction=np.array([0.,1.,0.]);close=True
            arm_goal=target+direction*.02975
            # Millimetre preload keeps the compliant nib in contact. Tangential
            # feedback compensates the small offset left by the contact grasp.
            arm_goal+=np.clip(target-self.tip_pos(),-.002,.002)*.7
            arm_goal[1]-=.0012
            # Travel horizontally across a large board; drawing height remains reachable.
            dx=self.board_base(target)[0]-d.qpos[0]
            if abs(dx)>.027:self._navigate('navigate_board',self.board_base(target))
        elif self.phase=='retract':
            direction=np.array([0.,1.,0.]);self.goal=self.targets[self.stroke][-1]+[0,.015,0];arm_goal=self.goal+direction*.02975;close=True
            if self.phase_steps>25:
                self.stroke+=1;self.point=0
                if self.stroke==len(self.targets):
                    self.stroke-=1;self.returning_final=True;self._navigate('navigate_return',self.pick_base(self.held))
                elif self.color!=self.held:self._navigate('navigate_return',self.pick_base(self.held))
                elif abs(self.board_base(self.targets[self.stroke][0])[0]-d.qpos[0])<.027:self._set_phase('draw')
                else:self._navigate('navigate_board',self.board_base(self.targets[self.stroke][0]))
        elif self.phase=='place':
            arm_goal=home;self.goal=home;close=True
            upright=d.body('marker_'+self.held).xmat.reshape(3,3)[2,2]>.98
            if not self.place_ready:
                arm_goal=home+[0,0,.028]
                if np.linalg.norm(self.marker_pos(self.held)-arm_goal)<.004 and upright:self.place_ready=True
            if self.place_ready and upright and np.linalg.norm(self.marker_pos(self.held)-home)<.003 and self.marker_visible(self.held):self._set_phase('release')
        elif self.phase=='release':
            arm_goal=home+[0,0,.035];self.goal=home
            if self.held:
                d.eq_active[m.equality('dock_'+self.held).id]=1
                d.eq_active[m.equality('grasp_'+self.held).id]=0;self.last_released=self.held;self.held=None
            if self.phase_steps>30 and d.site_xpos[self.grasp_id][2]>home[2]+.025:
                mask=m.geom_bodyid==m.body('marker_'+self.last_released).id;m.geom_contype[mask]=1;m.geom_conaffinity[mask]=3
                if np.linalg.norm(self.marker_pos(self.last_released)-home)>.008:
                    if self.phase_steps>150:self.fail_reason='marker_return_failed'
                elif self.returning_final:self._set_phase('done')
                else:self._navigate('navigate_pick',self.pick_base())
        if self.stage=='navigation' and self.phase=='reach_pick':self._set_phase('done')
        self.visible_goal=self.marker_visible(self.held or self.color) if self.phase in ['reach_pick','close','lift','place','release'] else self.drawing_visible(self.goal) if self.phase=='draw' else self.visible(self.goal)
        # Search by turning the head; a target action cannot complete without sight.
        delta=self.goal-d.body('head_yaw').xpos
        desired_head=wrap(math.atan2(delta[0],-delta[1])-self.yaw())
        self.command[self.head_a]=desired_head+action[6]*.15
        if arm_goal is not None:
            self.command[self.arm_a]=self.solve_arm(np.asarray(arm_goal)+action[2:5]*.002,direction)
        finger_angle=(.50 if close else -.20)+action[5]*.08
        for i in self.finger_a:self.command[i]=finger_angle if self.names[i].endswith('base') else (.6 if close else .05)
        wheel+=action[:2]*.35
        payload_torque=np.zeros(m.nu)
        if self.held:
            jac=np.zeros((3,m.nv));jr=np.zeros_like(jac)
            point=d.body('marker_'+self.held).xipos
            mujoco.mj_jac(m,d,jac,jr,point,m.body('right_wrist_roll').id)
            force=np.array([0.,-.012 if self.phase=='draw' else 0.,.0019*9.81])
            payload_torque=(jac.T@force)[self.dadr]/self.robot.gear
        for _ in range(20):
            d.ctrl[:]=np.clip(self.robot.pd(self.command)+payload_torque,-1,1)
            for i,v in zip(self.wheels,wheel):
                d.ctrl[i]=np.clip((.0003*(v-d.qvel[self.dadr[i]])-d.qfrc_passive[self.dadr[i]])/self.robot.gear[i],-1,1)
            mujoco.mj_step(m,d)
        mujoco.mj_forward(m,d)
        reward=-self.dt-.003*float(action@action)
        contact=False
        if self.held:
            board=m.geom('board_face').id;nib=m.geom('marker_'+self.held+'_nib').id
            contact=any(board in c.geom and nib in c.geom for c in d.contact)
            if contact:
                mark_stroke=self.stroke if old_phase in ['draw','retract'] else -1
                self.ink.append(dict(time_s=float(d.time),color=self.held,stroke=mark_stroke,point=self.point,
                                     position=self.tip_pos().tolist(),visible=bool(self.drawing_visible(self.tip_pos())),contact=True))
        if old_phase=='draw' and self.phase=='draw' and self.held==self.color:
            actual=self.tip_pos();target=self.targets[self.stroke][self.point]
            visible=self.drawing_visible(target);distance=float(np.linalg.norm(actual-target))
            # A line is deposited only when the nib physically touches the board face.
            if contact:self.errors.append((target.copy(),actual.copy()))
            if contact and visible:
                if distance<=self.drawing['tolerance_m']:
                    self.coverage.append((self.stroke,self.point));self.point+=1;reward+=1
                    if self.point==len(self.targets[self.stroke]):
                        if self.stage=='drawing':self._set_phase('done')
                        else:self._set_phase('retract')
            excess=max(0,distance**2-self.drawing['tolerance_m']**2)
            reward-=100*excess
        if self.phase!=old_phase:reward+=2
        if not self.visible_goal:reward-=.01
        if not np.isfinite(d.qpos).all() or abs(d.body('base').xmat.reshape(3,3)[2,2])<.8:self.fail_reason='unstable_robot'
        if self.phase_steps>3000:self.fail_reason='phase_timeout_'+self.phase
        if self.phase=='done' and self.stage in ['drawing','sequence'] and self.errors:
            if path_errors(*zip(*self.errors))['rmse_m']>self.drawing['tolerance_m']:self.fail_reason='drawing_error_exceeded'
        terminated=self.phase=='done' or self.fail_reason is not None
        truncated=self.steps>=self.max_steps and not terminated
        if self.phase=='done':reward+=20
        return self.observe(),float(reward),terminated,truncated,self.info()

    def info(self):
        metrics=path_errors(*zip(*self.errors)) if self.errors else dict(mse_m2=None,rmse_m=None,max_error_m=None)
        expected=sum(map(len,self.targets))
        return dict(phase=self.phase,held=self.held,color=self.color,stroke=self.stroke,point=self.point,
                    visible=bool(self.visible_goal),success=self.phase=='done' and self.fail_reason is None,
                    failure=self.fail_reason,time_s=float(self.data.time),coverage=len(set(self.coverage))/expected,
                    tolerance_m=self.drawing['tolerance_m'],mse_limit_m2=self.drawing['tolerance_m']**2,**metrics)
    def render(self):
        if self.renderer is None:self.renderer=mujoco.Renderer(self.model,800,1200)
        options=mujoco.MjvOption();options.geomgroup[3]=0;options.sitegroup[:]=0
        self.renderer.update_scene(self.data,camera='overview',scene_option=options)
        self.draw_ink(self.renderer.scene)
        return self.renderer.render()
    def draw_ink(self,scene):
        previous=None
        for mark in self.ink[-3000:]:
            if scene.ngeom>=scene.maxgeom:break
            p=np.asarray(mark['position']).copy();p[1]=self.layout['board_y']+.0003
            hexcolor=COLORS[mark['color']];rgba=np.array([int(hexcolor[i:i+2],16)/255 for i in [1,3,5]]+[1.],dtype=np.float32)
            geom=scene.geoms[scene.ngeom];mujoco.mjv_initGeom(geom,mujoco.mjtGeom.mjGEOM_SPHERE,np.array([.00075,0,0]),p,np.eye(3).reshape(-1),rgba)
            if previous is not None and previous['stroke']==mark['stroke'] and mark['time_s']-previous['time_s']<self.dt*1.6:
                a=np.asarray(previous['position']).copy();a[1]=p[1]
                if np.linalg.norm(a-p)>.00001:mujoco.mjv_connector(geom,mujoco.mjtGeom.mjGEOM_CAPSULE,.00075,a,p)
            scene.ngeom+=1;previous=mark
    def close(self):
        if self.renderer:self.renderer.close()

def example():
    return dict(version=1,name='Four-color line study',tolerance_m=.03,strokes=[
        dict(color=c,points=[dict(x=.43,y=.25+i*.16,t_ms=0),dict(x=.48,y=.25+i*.16,t_ms=700)])
        for i,c in enumerate(COLORS)])
