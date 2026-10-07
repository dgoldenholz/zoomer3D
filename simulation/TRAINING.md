# Drawing workshop

The workshop uses the 180 mm robot, a 480 × 200 mm whiteboard and a side table with black, red, blue and green markers. The editor maps drawings to a reachable 300 × 60 mm strip on the board. Each marker is a separate physical body.

## Open the drawing studio

From the repository root:

```sh
.venv/bin/python app/server.py
```

Open <http://127.0.0.1:8765>. Draw with a mouse, pen or touch. The editor has four colors, one 1.5 mm marker size, undo, stroke replay and JSON import/export. It saves stroke order, point order and relative timestamps. It never groups strokes by color. Black, red, black means three collection visits in that order.

Save the target, choose a training budget and select **Train this drawing**. One job runs at a time. **Stop and save checkpoint** requests a clean stop. Files stay on this computer in `targets/` and `training/<run-id>/`.

## Error and speed

The default distance tolerance is 3 cm RMS. For ordered 3D target positions `p` and measured nib positions `q`, the calculation is:

```text
MSE = mean(sum((p - q)², over x, y, z))
RMS distance = sqrt(MSE)
3 cm RMS = 0.03 m RMS = 0.0009 m² MSE
```

The UI accepts 0.05 to 10 cm. It shows both distance and MSE. The selected value is an overall error ceiling. Lettering also needs a local tracing tolerance, capped at 0.75 mm. The controller samples the path at intervals no larger than 0.6 mm and advances only after a visible, physical nib contact reaches the next point. This prevents the 3 cm default from skipping whole letters.

The reward subtracts elapsed time and control effort, and penalizes tracking errors beyond the local tolerance. Terminal evaluation also requires at least 98% of target samples to have ink within 1 mm and at least 95% of ink samples to lie within 1 mm of their assigned stroke. Missing strokes cannot earn a good score just because the completed contacts had low RMS error.

## Run or train from the terminal

```sh
# Controller baseline, with a task trace.
.venv/bin/python simulation/run_workshop.py --drawing targets/four_colors.json

# Interactive MuJoCo view on macOS.
.venv/bin/mjpython simulation/run_workshop.py --viewer

# Train the curriculum, then evaluate each stage on a separate reset seed.
.venv/bin/python simulation/train.py --drawing targets/four_colors.json --steps 100000 --output training/my_run

# Continue from a checkpoint.
.venv/bin/python simulation/train.py --drawing targets/four_colors.json --resume training/my_run/checkpoint.zip --steps 100000 --output training/continued

# Evaluate the saved policy.
.venv/bin/python simulation/run_workshop.py --policy training/my_run/policy.zip --output training/policy_trace.json
```

Stages are driving, pickup, drawing and the complete sequence. Skill resets sample different strokes and colors. A stage must pass evaluation before the next stage begins. The status file records the stage, number of training steps, measured results and whether the full sequence passed. A saved policy file alone does not mean training succeeded.

PPO learns seven residual commands around a task controller: two wheel-speed corrections, three Cartesian hand corrections, a grip correction and a head-yaw correction. Inverse kinematics and torque feedback turn those commands into the robot's 35 motor commands. This assistance shortens training. It is not learning all 35 joint torques from scratch. The zero-residual baseline is available for comparison.

The task controller preserves the drawing sequence. It carries one marker at a time, returns it to its original holder before a color change and returns the last marker when the drawing is finished. The base centers under each letter and plans an 85 mm gap to the board. Standing closer forced the wrist toward its limit and caused contact loss. For long strokes, the controller lifts the nib before repositioning along the board, then resumes the same point. Wheel residuals apply only during travel. At a station, wheel-angle feedback holds the base in place. After lifting the nib, the robot backs away with the arm held still before folding it for travel. Pickup and return can try alternate inverse-kinematics poses; writing keeps the arm configuration continuous. The ink trace records contact breaks rather than drawing a line through a pen-up move.

## Sight, contact and measurements

Both eyes have a 120° vertical field of view, with fixed optics angled 25° down. The head supplies yaw. MuJoCo rays test the field of view and occlusion by the scene and robot collision shapes. The transparent dome does not block those rays. Marker poses in the policy observation are zeroed when no sampled part of the marker is visible.

Grasping, lifting and placement require marker visibility. Drawing requires a visible patch within 3 mm of the target because the nib can cover its own contact point. An occluding wall still blocks that patch. The visibility test uses geometric object detection, not a trained RGB vision model. The task controller knows the fixed station layout. Eye cameras are present in the MJCF for future camera-based perception work.

A pickup must bring the gripper within 4 mm of the marker grip point and establish contact from at least two fingers. A weld then approximates a secure grasp. Finger-to-marker contacts are disabled while that weld holds the marker, avoiding two competing constraints. The marker can still contact the board and table. The holders use releasable docking constraints. No robot or marker pose is teleported during a task step. Curriculum resets can start near a station or with a marker already held.

Ink appears only when the nib contacts the board. Its position comes from the spherical nib's forward contact surface. A 1 kHz Cartesian feedback loop tracks the nib while torque control holds the arm pose. A slower pressure adjustment varies the normal preload between 4 and 60 mN. The nib-to-board friction coefficient is 0.2 and the grasp weld time constant is 2 ms; both are simulation assumptions. The trace retains the measured nib position, time, color, stroke index, contact flag and visibility flag. The RMS calculation includes contact samples while following the target, including samples outside the tolerance. Coverage records ordered target completion separately from error.

The drive model uses two effective traction contacts and low-friction support rollers. It is a differential-drive approximation to the treads. The decorative belt does not deform in MuJoCo. Robot self-collision remains disabled in the starter physics. Masses, inertias and torque limits are estimates. These choices support task development, but they are not a validated physical robot model.

## Validation and rebuilding

```sh
.venv/bin/python scripts/build_workshop.py
.venv/bin/python -m pytest -q tests/test_workshop.py
```

The tests cover drawing order and units, invalid inputs, eye occlusion, contact-qualified pickup, real board contact, stroke completion and invalid motor commands. `training/full_sequence.json` records the baseline's full sequence. Training results are stored separately from controller demonstrations.

The original checkpoint in `training/verified_policy/` belongs to the earlier four-mark controller. The longer target in `training/fbef1730519e4f848773550c1c03f80b/` failed during red-marker pickup and produced poorly matched lettering. Those checkpoints remain as historical artifacts. The revised controller changes the observation shape and requires a fresh policy relative to those original checkpoints. Use `--stages drawing sequence` to fine-tune these skills without repeating the pickup curriculum.

## Verified text drawing

`training/zoomer_readable/policy.zip` completes the saved 19-stroke target `targets/3201207f878b4707ab8753bffb68dbac.json`. The recorded evaluation uses seed 300 with randomized initial placement and traction. It completed all 19 strokes and returned black, red, blue and green markers in 814.74 simulated seconds.

The measured RMS tracking error was 0.361 mm, with a maximum sampled error of 0.589 mm. Every target sample had ink within 1 mm, and every ink sample was within 1 mm of its assigned stroke. The planar target-to-ink RMS distance was 0.248 mm. These figures describe this recorded run, not a benchmark on unseen drawings or hardware.

The policy accumulated 21,326 environment steps across controller revisions, including 1,024 after the canvas-to-board mapping correction. Controller changes supply most of the new capability: finer waypoint tracking, reachable drawing stances, marker-return pose recovery and contact feedback. This experiment does not isolate PPO's contribution to accuracy or speed.

The board faces +Y. Canvas-right therefore maps to world -X; canvas-up maps to +Z. Recordings retain this drawing frame alongside the target and policy hashes. The source snapshot is in `training/zoomer_readable/source/`.

Watch `renders/zoomer_ai_is_so_cool.mp4` or open `app/video.html`. Travel plays at 12x, drawing at 0.5x, and ordinary marker handling at real time. The ending compares the target with recorded contact ink. The video includes actual MuJoCo poses and does not animate the robot along the target curve.

To repeat the recorded reset with the saved policy:

```sh
.venv/bin/python scripts/record_workshop_video.py capture --drawing targets/3201207f878b4707ab8753bffb68dbac.json --policy training/zoomer_readable/policy.zip --randomize --seed 300 --output-prefix renders/repeated_text
.venv/bin/python scripts/record_workshop_video.py preview --output-prefix renders/repeated_text
.venv/bin/python scripts/record_workshop_video.py render --output-prefix renders/repeated_text
```

The implementation follows the [MuJoCo ray API](https://mujoco.readthedocs.io/en/stable/APIreference/APIfunctions.html#mj-ray), [MuJoCo weld constraints](https://mujoco.readthedocs.io/en/stable/XMLreference.html#equality-weld) and [Stable-Baselines3 PPO interface](https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html).
