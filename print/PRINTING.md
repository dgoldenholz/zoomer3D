# Integrated articulation update

This is an earlier prototype. Use [the revised modular XTI-30](modular/PRINTING.md) for the current print and assembly instructions.

The full passive articulation CAD is now in [articulated/PRINTING.md](articulated/PRINTING.md). The files described below remain the original static display and clearance coupons.

# Printing Zoomer on the Prusa XL

The robot's neutral dimensions are 180 mm tall by 100 mm wide, with a depth of about 72 mm. The print files use millimetres. Import them at 100% scale.

The first print should be a joint coupon. Clearances depend on material, nozzle, cooling, extrusion calibration, and orientation. The values below are starting designs, not tested settings for your machine.

## Files

| File | What it is | Status |
| --- | --- | --- |
| `zoomer_static_body_180mm.3mf` or `.stl` | Fused display body with fixed limbs and tracks | Closed mesh; supports required |
| `dome_080mm_wall.stl` | Separate open-bottom dome, about 0.8 mm wall | Closed shell mesh; test fit required |
| `clearance_coupon_plate.3mf` | Five captive hinges arranged in rows | No intersecting rotor/socket solids |
| `hinge_35_assembled.3mf` | One 0.35 mm clearance captive hinge | Suggested first coupon |
| `ball_joint_support_required.3mf` | Captive ball, stem, and socket | Internal dissolvable support required |

The display body has no moving joints. Its small decorative details are simplified during the mesh union. The dome has a plain locating rim rather than a snap fit; check the fit before applying adhesive. Do not glue the dome on if you want to keep access to the face.

## Captive hinge coupons

The five rows have radial clearances of 0.25, 0.30, 0.35, 0.40, and 0.45 mm. The row at the smallest Y coordinate is 0.25 mm; each next row is 18 mm farther along Y. Filenames encode the gap in hundredths of a millimetre. A radial gap is the separation on one side, not the total diameter difference.

Keep the rotor and socket together when importing a 3MF. They are two separate volumes in one aligned assembly. Do not auto-arrange those volumes as independent objects. The individual STL files are supplied for inspection or deliberate material assignment, not for separate placement on the bed.

Print with the hinge axis vertical. Both lower bodies start on the bed. The outer rotor arm needs accessible support underneath its overhang. Keep support out of the bearing clearance. The pin has a lower retaining flange and an upper shoulder, so it stays captive after the support under the arm is removed. Check free rotation and vertical play, then record which gap works best.

The supplied coupon rotor is 4.4 mm across the shaft, with a 7.2 mm lower flange. The socket is 12.4 mm across. These test bearings are larger than the final finger pivots would be. A successful coupon does not validate a scaled-down finger joint.

## Ball-joint coupon

The ball is 8.4 mm across, with 0.35 mm radial clearance. Its socket opening retains the ball. The ball starts above the bed inside the socket, so it needs an internal support strategy. Use a compatible dissolvable support material and confirm that fluid can reach and leave the cavity. Do not fill that trapped cavity with ordinary support material that cannot be removed through the opening.

Inspect the sliced layers before printing. Check that the ball and socket remain separate, the stem clears the opening, and support does not permanently fuse the bearing. This coupon tests retention and motion; it does not define the final two-axis waist or all the arm bearings.

## Five-tool material plan

For initial coupons, use one structural material. This separates dimensional issues from material adhesion. A second tool can carry the chosen support material.

For a later colored body, a practical five-tool assignment is ivory, red, blue, dark gray, and support. Purple and green accents can be painted or printed separately. The Blender model has more than five material roles, and the static print export does not encode a production-ready five-tool color partition.

Print the dome separately. Clear FDM filament will usually remain visibly layered; the transparent Blender material does not predict the printed optical result. A formed clear cover is another fabrication option if seeing the eyes clearly matters.

Prusa documents separate meshes for multi-material work and explains the XL's material combinations. Use those guides when choosing the final filament/support pair: [modeling for printing](https://help.prusa3d.com/article/modeling-with-3d-printing-in-mind_164135), [combining materials on the XL](https://help.prusa3d.com/article/combining-materials-xl_498103), and [tool mapping](https://help.prusa3d.com/article/tools-mapping-and-filament-mapping-xl-mmu3_732461).

## What remains before a moving full-body print

The full robot needs integrated bearing geometry, accessible support removal, structural wall thicknesses, collision clearances throughout each movement, and a print orientation for every captive component. Finger joints at this size are the hardest part. The rotating dome also needs a retaining bearing; the current separate dome is a display cover.

If physical motor actuation becomes a goal, motor choice and packaging should precede that redesign. The supplied simulated torques do not establish that 35 actuators, gearing, and wiring can fit inside a 180 mm robot.
