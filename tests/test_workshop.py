from pathlib import Path
import sys
import copy
import json
import numpy as np
import mujoco
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'simulation'))
from drawing import validate_drawing,path_errors,resample,ink_quality
from workshop import WorkshopEnv,example

def test_stop_request_interrupts_evaluation(tmp_path):
    from train import evaluate
    stop_file=tmp_path/'stop_requested';stop_file.touch()
    assert evaluate(None,example(),'navigation',episodes=1,stop_file=stop_file) is None

def test_drawing_contract_keeps_order_and_units():
    drawing=example();drawing['strokes'].append(copy.deepcopy(drawing['strokes'][0]))
    clean=validate_drawing(drawing)
    assert [s['color'] for s in clean['strokes']]==['black','red','blue','green','black']
    assert clean['tolerance_m']**2==.0009
    result=path_errors([[0,0,0],[0,0,0]],[[.03,0,0],[0,.03,0]])
    assert result['mse_m2']==pytest.approx(.0009)
    assert result['rmse_m']==pytest.approx(.03)
    assert clean['strokes'][0]['points'][1]['t_ms']==700

@pytest.mark.parametrize('value',[float('nan'),-.01,True,.2])
def test_bad_tolerances_rejected(value):
    drawing=example();drawing['tolerance_m']=value
    with pytest.raises(ValueError):validate_drawing(drawing)

def test_resampling_keeps_a_reversal():
    points=[dict(x=.2,y=.5,t_ms=0),dict(x=.4,y=.5,t_ms=1),dict(x=.2,y=.5,t_ms=2)]
    path=resample(points,.01)
    assert np.max(path[:,0])==pytest.approx(.12)
    assert np.allclose(path[0],path[-1])

def test_resampling_removes_stationary_samples_without_skipping_corners():
    points=[dict(x=x,y=y,t_ms=i) for i,(x,y) in enumerate([(.2,.2)]*100+[(.25,.2),(.25,.3)])]
    path=resample(points)
    assert len(path)<100
    assert np.max(np.linalg.norm(np.diff(path,axis=0),axis=1))<=.00060001
    assert any(np.allclose(p,[.075,.048]) for p in path)

def test_quality_rejects_missing_strokes_and_stray_ink():
    targets=[np.array([[0,0,0],[.0005,0,0]]),np.array([[.01,0,0]])]
    strokes=[{'color':'black'},{'color':'red'}]
    ink=[dict(stroke=0,color='black',position=[0,0,0]),dict(stroke=-1,color='red',position=[.5,0,0])]
    metrics=ink_quality(targets,strokes,ink)
    assert metrics['target_coverage_1mm']==pytest.approx(2/3)
    assert metrics['ink_precision_1mm']==.5
    assert metrics['shape_rmse_m'] is None

def test_three_cm_tolerance_does_not_skip_letter_geometry():
    env=WorkshopEnv(stage='drawing')
    assert env.tracking_tolerance<=.00075
    assert len(env.targets[0])>20
    env.close()

def test_canvas_right_maps_to_the_readers_right_on_the_board():
    # The reader stands on +Y facing the board, so screen-right is world -X.
    env=WorkshopEnv()
    assert env.targets[0][-1,0]<env.targets[0][0,0]
    assert env.layout['drawing_x_direction']==-1
    env.close()

def test_eye_frustum_and_occlusion():
    env=WorkshopEnv();m,d=env.model,env.data
    assert env.marker_visible('black') # wide optics can see the side table
    point=np.array([0,-.20,.13]);assert env.visible(point)
    assert not env.visible([0,.20,.13])
    blocker=m.geom('board_frame').id;old_pos=m.geom_pos[blocker].copy();old_size=m.geom_size[blocker].copy()
    m.geom_pos[blocker]=[0,-.10,.15];m.geom_size[blocker]=[.04,.01,.07]
    mujoco.mj_forward(m,d);assert not env.visible(point)
    m.geom_pos[blocker]=old_pos;m.geom_size[blocker]=old_size;env.close()

def test_cannot_grasp_from_a_distance():
    env=WorkshopEnv();assert not env.grasp_allowed('black');assert env.held is None
    assert not any(env.data.eq_active[env.model.equality('grasp_'+c).id] for c in ['black','red','blue','green'])
    env.close()

def test_contact_qualified_pickup_and_lift():
    env=WorkshopEnv(stage='pickup')
    for _ in range(200):
        _,_,done,_,info=env.step(np.zeros(7))
        if done:break
    assert info['success'] and env.held=='black'
    assert env.marker_pos('black')[2]>.115
    assert not env.data.eq_active[env.model.equality('dock_black').id]
    env.close()

def test_drawing_requires_board_contact():
    env=WorkshopEnv(stage='drawing');env.data.eq_active[env.model.equality('grasp_black').id]=0
    # A released marker cannot be credited as held by the task controller.
    env.held=None
    for _ in range(3):env.step(np.zeros(7))
    assert env.ink==[] and env.errors==[]
    env.close()

def test_drawing_stage_records_ordered_contact_ink():
    env=WorkshopEnv(stage='drawing')
    for _ in range(200):
        _,_,done,_,info=env.step(np.zeros(7))
        if done:break
    assert info['success'] and info['rmse_m']<=env.drawing['tolerance_m']
    assert info['rmse_m']<.00075
    assert info['target_coverage_1mm']>=.98 and info['ink_precision_1mm']>=.95
    assert env.coverage==[(0,i) for i in range(len(env.targets[0]))]
    assert all(p['color']=='black' and p['stroke']==0 for p in env.ink)
    env.close()

def test_drive_residuals_cannot_move_base_during_pickup():
    baseline=WorkshopEnv(stage='pickup');perturbed=WorkshopEnv(stage='pickup')
    for _ in range(4):
        baseline.step(np.zeros(7));perturbed.step(np.array([1,-1,0,0,0,0,0]))
    assert np.allclose(baseline.data.qpos,perturbed.data.qpos,atol=1e-12)
    baseline.close();perturbed.close()

def test_marker_return_recovers_from_previous_stalled_pose():
    env=WorkshopEnv();m,d=env.model,env.data
    d.qpos[:]=json.loads((ROOT/'tests/fixtures/red_return_qpos.json').read_text())
    mujoco.mj_forward(m,d);env.stroke=2;env.command=d.qpos[env.qadr].copy()
    env._weld('red');env.station_wheels=d.qpos[env.qadr[env.wheels]].copy();env._set_phase('place')
    for _ in range(100):
        env.step(np.zeros(7))
        if env.phase=='release':break
    assert env.phase=='release'
    assert np.linalg.norm(env.marker_pos('red')-env.layout['marker_homes']['red'])<.003
    env.close()

def test_adaptive_pressure_recovers_a_nib_hovering_off_the_board():
    env=WorkshopEnv(stage='drawing');m,d=env.model,env.data
    d.qpos[:]=json.loads((ROOT/'tests/fixtures/nib_contact_loss_qpos.json').read_text())
    mujoco.mj_forward(m,d);env._weld('black');env._set_phase('draw')
    env.command=d.qpos[env.qadr].copy();env.pen_down=True
    env.station_wheels=d.qpos[env.qadr[env.wheels]].copy()
    env.targets[0]=np.array([[-.11463696,-.4353,.15050064]])
    for _ in range(20):
        _,_,done,_,info=env.step(np.zeros(7))
        if done:break
    assert info['success'] and env.ink and env.coverage==[(0,0)]
    env.close()

def test_invalid_action_does_not_advance_physics():
    env=WorkshopEnv();time=env.data.time
    with pytest.raises(ValueError):env.step(np.ones(6))
    with pytest.raises(ValueError):env.step(np.full(7,np.nan))
    assert env.data.time==time
    env.close()
