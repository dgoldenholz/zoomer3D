"""Capture a saved policy's real MuJoCo states and render an honest task video."""
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess, sys
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'simulation'))
from workshop import WorkshopEnv, PHASES
from drawing import COLORS


def paths(args):
    p = Path(args.output_prefix)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p, p.with_suffix('.npz'), p.with_suffix('.json')


def capture(args):
    import torch
    from stable_baselines3 import PPO
    torch.set_num_threads(2)
    prefix, states_path, trace_path = paths(args)
    drawing = json.loads(Path(args.drawing).read_text())
    limit = args.max_steps or max(26000, 5000 * len(drawing['strokes']))
    env = WorkshopEnv(args.drawing, max_steps=limit,randomize=args.randomize)
    policy = PPO.load(args.policy, device='cpu')
    obs, _ = env.reset(seed=args.seed)
    states, rows, completed = [], [], set()
    previous = None
    for _ in range(limit):
        action = policy.predict(obs, deterministic=True)[0]
        obs, _, done, truncated, info = env.step(action)
        if env.phase == 'retract':
            completed.add(env.stroke)
        states.append(env.data.qpos.copy())
        rows.append([env.data.time, PHASES.index(env.phase), list(COLORS).index(env.held or env.color),
                     env.stroke, len(env.ink), bool(env.visible_goal), len(completed), info['coverage']])
        if env.phase != previous:
            print(f'{env.data.time:.2f}s {env.phase} {env.held or env.color} stroke {env.stroke + 1}', flush=True)
            previous = env.phase
        if done or truncated:
            if truncated and not info['failure']:
                info['failure'] = 'episode_time_limit'
            break
    np.savez_compressed(states_path, qpos=np.array(states), rows=np.array(rows))
    record = dict(controller='Saved residual PPO with task controller', seed=args.seed,randomized_reset=args.randomize,
                  policy=str(Path(args.policy).resolve()), target=str(Path(args.drawing).resolve()),
                  policy_sha256=hashlib.sha256(Path(args.policy).read_bytes()).hexdigest(),
                  target_sha256=hashlib.sha256(Path(args.drawing).read_bytes()).hexdigest(),
                  phase_names=PHASES,
                  drawing_frame=dict(origin=env.layout['drawing_origin'],x_direction=env.layout.get('drawing_x_direction',1)),
                  result=info, events=env.events, ink=env.ink, drawing=env.drawing,
                  completed_strokes=sorted(completed), state_interval_s=env.dt,
                  poses='Measured MuJoCo states, without interpolation or animation edits')
    trace_path.write_text(json.dumps(record, indent=2))
    env.close()
    print(json.dumps(info, indent=2), flush=True)


def render(args, preview=False):
    import mujoco
    from PIL import Image, ImageDraw, ImageFont
    prefix, states_path, trace_path = paths(args)
    record = json.loads(trace_path.read_text())
    state = np.load(states_path)
    rows, qpos = state['rows'], state['qpos']
    phases=record.get('phase_names',PHASES[:-2]+['done'])
    env = WorkshopEnv(record['drawing'])
    m, d = env.model, env.data
    m.vis.global_.offwidth = 1280
    m.vis.global_.offheight = 720
    renderer = mujoco.Renderer(m, 620, 1280, max_geom=20000)
    options = mujoco.MjvOption()
    options.geomgroup[3] = 0
    options.sitegroup[:] = 0
    fp = '/System/Library/Fonts/Supplemental/Arial.ttf'
    font, small, big = [ImageFont.truetype(fp, n) for n in [22, 17, 30]]
    colors, fps, ink = list(COLORS), 25, record['ink']
    total_strokes = len(record['drawing']['strokes'])
    success = record['result']['success']
    changes = np.flatnonzero(np.diff(rows[:, 1]) != 0) + 1
    starts = np.r_[0, changes]
    labels = {'navigate_pick': 'Drive to the marker table', 'reach_pick': 'Reach for the marker',
              'close': 'Close the gripper', 'lift': 'Lift the marker', 'navigate_board': 'Drive to the whiteboard',
              'draw': 'Draw the target stroke', 'retract': 'Lift the nib from the board',
              'reposition': 'Lift the nib before repositioning',
              'navigate_return': 'Return to the marker table', 'place': 'Put the marker in its holder',
              'release': 'Release the marker', 'done': 'Drawing complete and final marker returned'}

    def speed(index):
        phase = phases[int(rows[index, 1])]
        start = starts[np.searchsorted(starts, index, side='right') - 1]
        age = rows[index, 0] - rows[start, 0]
        if phase.startswith('navigate'):
            return args.travel_speed, f'{args.travel_speed:g}x travel'
        if phase == 'draw':
            return args.drawing_speed, f'{args.drawing_speed:g}x drawing'
        if age > 3.:
            return 8., '8x prolonged attempt'
        return 1., '1x real time'

    def camera(phase, row):
        if phase.startswith('navigate') or phase == 'done':
            return 'overview'
        cam = mujoco.MjvCamera()
        cam.type = mujoco.mjtCamera.mjCAMERA_FREE
        if phase in ['draw', 'retract', 'reposition']:
            hand = d.site_xpos[env.grasp_id]
            cam.lookat[:] = [hand[0], -.396, .132]
            cam.distance, cam.azimuth, cam.elevation = .245, 325, -23
        else:
            home = np.array(env.layout['marker_homes'][colors[int(row[2])]])
            cam.lookat[:] = home + [.016, .020, .006]
            cam.distance, cam.azimuth, cam.elevation = .225, 140, -23
        return cam

    def comparison(draw, im):
        im.paste('#14212c', (0, 50, 1280, 670))
        title = 'Drawing completed' if success else 'Attempt stopped before completing the drawing'
        draw.text((42, 68), title, font=big, fill='#eff4f7' if success else '#ffcf9e')
        coverage = record['result']['coverage'] * 100
        error = record['result']['rmse_m']
        rms = 'No contact samples' if error is None else f'{error * 1000:.2f} mm RMS on recorded contacts'
        draw.text((42, 114), f'{len(record["completed_strokes"])}/{total_strokes} strokes reached pen-up  |  {coverage:.1f}% target-point coverage  |  {rms}', font=small, fill='#c6d7e3')
        width, height = record['drawing']['width_m'], record['drawing']['height_m']
        drawing_frame=record.get('drawing_frame',dict(origin=[-.15,-.4353,.105],x_direction=1))
        origin = np.array(drawing_frame['origin']);x_direction=drawing_frame['x_direction']
        points = [[0, 0], [width, height]] + [[(p['position'][0] - origin[0])/x_direction, p['position'][2] - origin[2]] for p in ink]
        points = np.array(points)
        lower, upper = points.min(axis=0) - .003, points.max(axis=0) + .003
        scale = min(1120 / (upper[0] - lower[0]), 195 / (upper[1] - lower[1]))
        def board(top, actual):
            layer = Image.new('RGB', (1160, 210), 'white')
            painter = ImageDraw.Draw(layer)
            def xy(u, v):
                return (580 + (u - (upper[0] + lower[0]) / 2) * scale,
                        105 - (v - (upper[1] + lower[1]) / 2) * scale)
            pen = max(1, round(record['drawing']['marker_width_m'] * scale))
            if not actual:
                for stroke in record['drawing']['strokes']:
                    path = [xy(p['x'] * width, (1-p['y']) * height) for p in stroke['points']]
                    if len(path) > 1:
                        painter.line(path, fill=COLORS[stroke['color']], width=pen)
                    for x, y in [path[0], path[-1]]:
                        painter.ellipse((x-pen/2, y-pen/2, x+pen/2, y+pen/2), fill=COLORS[stroke['color']])
            else:
                previous = None
                for mark in ink:
                    p = np.array(mark['position']) - origin
                    p[0]/=x_direction
                    x, y = xy(p[0], p[2])
                    painter.ellipse((x-pen/2, y-pen/2, x+pen/2, y+pen/2), fill=COLORS[mark['color']])
                    if previous and previous['stroke'] == mark['stroke'] and previous['color'] == mark['color'] and mark['time_s']-previous['time_s'] < .032:
                        p0 = np.array(previous['position']) - origin
                        p0[0]/=x_direction
                        painter.line([xy(p0[0], p0[2]), (x, y)], fill=COLORS[mark['color']], width=pen)
                    previous = mark
            im.paste(layer, (60, top))
        draw.text((60, 145), 'TARGET', font=small, fill='#c6d7e3')
        board(171, False)
        draw.text((60, 393), 'ACTUAL INK', font=small, fill='#c6d7e3')
        board(419, True)
        failure = record['result']['failure']
        reason = f"Stopped during {labels[record['result']['phase']].lower()}." if failure else 'All markers returned.'
        draw.text((60, 644), reason + '  Ink comes only from measured nib contact.', font=small, fill='#c6d7e3')

    def frame(index, ending=False):
        row = rows[index].copy()
        phase, color = phases[int(row[1])], colors[int(row[2])]
        if phase=='release':
            releases=[e for e in record['events'] if e['phase']=='release' and e['time_s']<=row[0]]
            if releases:color=releases[-1]['color'];row[2]=colors.index(color)
        d.qpos[:] = qpos[index]
        mujoco.mj_forward(m, d)
        env.ink = ink[:int(row[4])]
        renderer.update_scene(d, camera=camera(phase, row), scene_option=options)
        env.draw_ink(renderer.scene)
        im = Image.new('RGB', (1280, 720), '#14212c')
        im.paste(Image.fromarray(renderer.render()), (0, 50))
        draw = ImageDraw.Draw(im)
        draw.text((24, 13), 'XTI-30  |  ' + record['drawing']['name'][:55], fill='#f2f5f7', font=font)
        draw.text((910, 17), 'MuJoCo  /  recorded policy motion', fill='#adbfce', font=small)
        draw.rounded_rectangle((20, 610, 825, 659), radius=7, fill='#14212c')
        draw.ellipse((37, 625, 55, 643), fill=COLORS[color], outline='white', width=1)
        progress=f'stroke {min(total_strokes,int(row[3])+1)}/{total_strokes}' if phase in ['draw','retract','reposition'] else f'{int(row[6])}/{total_strokes} strokes drawn'
        draw.text((68, 622), f'{labels[phase]}  |  {progress}', fill='white', font=font)
        playback = 'Recorded result' if ending else speed(index)[1]
        draw.text((24, 684), f'{row[0]:06.2f} s simulation time    |    {playback}    |    {color} marker', fill='#d5e1e8', font=small)
        draw.text((1060, 683), f'{int(row[6])}/{total_strokes} pen-ups', fill='#d5e1e8', font=small)
        if phase in ['draw', 'retract', 'reposition']:
            draw.rounded_rectangle((923, 73, 1261, 153), radius=8, fill='#14212c')
            draw.text((940, 86), 'Measured nib-contact ink', fill='white', font=small)
            draw.text((940, 116), 'Precision target: 0.75 mm', fill='#c1d2df', font=small)
        if ending:
            comparison(draw, im)
        return im

    if preview:
        for phase in ['navigate_pick', 'reach_pick', 'draw', 'place']:
            candidates = np.flatnonzero(rows[:, 1] == phases.index(phase))
            if len(candidates):
                index = int(candidates[min(len(candidates)-1, max(0, len(candidates)//8))])
                frame(index).save(prefix.parent / (prefix.name + '_preview_' + phase + '.png'))
        for color_index,color in enumerate(colors):
            candidates=np.flatnonzero((rows[:,1]==phases.index('draw')) & (rows[:,2]==color_index))
            if len(candidates):
                frame(int(candidates[len(candidates)//2])).save(prefix.parent / (prefix.name+'_preview_draw_'+color+'.png'))
        frame(len(rows)-1, True).save(prefix.parent / (prefix.name + '_poster.png'))
        renderer.close()
        env.close()
        return
    executable = shutil.which('ffmpeg')
    if not executable:
        raise RuntimeError('ffmpeg is required to encode the recording.')
    destination = prefix.with_suffix('.mp4')
    command = [executable, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '1280x720', '-r', str(fps), '-i', '-',
               '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(destination)]
    writer = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        t, count = rows[0, 0], 0
        first = frame(0)
        for _ in range(2*fps):
            writer.stdin.write(first.tobytes())
            count += 1
        while t <= rows[-1, 0]:
            index = min(len(rows)-1, int(np.searchsorted(rows[:, 0], t)))
            writer.stdin.write(frame(index).tobytes())
            count += 1
            following = changes[changes > index]
            boundary = rows[following[0], 0] if len(following) else float('inf')
            t = min(t + speed(index)[0] / fps, boundary)
            if count % 250 == 0:
                print(f'Rendered {count/fps:.1f}s video / {t:.1f}s simulation', flush=True)
        final = frame(len(rows)-1, True)
        final.save(prefix.parent / (prefix.name + '_poster.png'))
        for _ in range(10*fps):
            writer.stdin.write(final.tobytes())
            count += 1
    finally:
        writer.stdin.close()
        writer.wait()
        renderer.close()
        env.close()
    if writer.returncode:
        raise RuntimeError('Video encoding failed.')
    record['video'] = dict(path=str(destination.resolve()), duration_s=count/fps, fps=fps, resolution=[1280, 720],
                           travel_speed=args.travel_speed, drawing_speed=args.drawing_speed, prolonged_attempt_speed=8)
    trace_path.write_text(json.dumps(record, indent=2))
    print(f'VIDEO_COMPLETE {destination} {count/fps:.2f}s', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['capture', 'preview', 'render'])
    parser.add_argument('--drawing', default=str(ROOT / 'targets/four_colors.json'))
    parser.add_argument('--policy', default=str(ROOT / 'training/verified_policy/policy.zip'))
    parser.add_argument('--output-prefix', default=str(ROOT / 'renders/zoomer_drawing_test'))
    parser.add_argument('--seed', type=int, default=7)
    parser.add_argument('--max-steps', type=int)
    parser.add_argument('--randomize',action='store_true',help='Randomize the reset placement and traction, as in training evaluation.')
    parser.add_argument('--travel-speed',type=float,default=12.)
    parser.add_argument('--drawing-speed',type=float,default=.5)
    args = parser.parse_args()
    if args.travel_speed<=0 or args.drawing_speed<=0:parser.error('Playback speeds must be positive.')
    capture(args) if args.mode == 'capture' else render(args, preview=args.mode == 'preview')
