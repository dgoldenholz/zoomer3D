# Articulated Zoomer

This is an earlier prototype. Use [the revised modular XTI-30](../modular/PRINTING.md) for the current print and assembly instructions.

This directory contains the integrated passive articulation design. The moving parts print in their assembled positions. It has a retained waist swivel and pitch axle, a head swivel, three shoulder axes per arm, elbows, forearm swivels, two wrist axes and four two-joint fingers per hand. Both treads contain captive wheels and linked belts.

Open `zoomer_prusa_XL_assembled.3mf` in PrusaSlicer. It contains one object with named volumes and preserves the captive parts' positions. Keep the component coordinates. Do not split or arrange the moving volumes separately. The generic `zoomer_articulated_180mm.3mf` is also supplied, but PrusaSlicer can split that format into separate objects and move them to the bed. Use the Prusa-specific package for slicing. The individual STL files are for inspection and replacement exports. The Blender inspection file is `assets/zoomer_print_in_place.blend` at the project root.

This mechanism uses exposed yokes and separated joint pivots to fit printable bearings into the small robot. It differs from the cosmetic shells in the original Blender model. It is a passive poseable model. It does not contain motors, gears, wiring or a hardware control system.

The assembled CAD measures 180.00 mm tall, 99.80 mm wide and 70.87 mm deep. It contains 123 print volumes. PrusaSlicer 2.9.6 imported and re-exported the native package with one object, all volumes, all tool assignments and the same dimensions, without reporting mesh repairs. The sampled tread test found no collisions and a maximum pin misalignment of 0.0065 mm within the 0.35 mm bearing gap.

## Prusa XL setup

The design assumes 0.4 mm nozzles and 0.15 mm layers. Start with the existing captive-joint coupons before printing the whole assembly. Nominal radial and axial bearing gaps are 0.35 mm. Finger bearings use 0.30 mm. The smallest finger axles are about 1 mm in diameter and will be fragile.

Use the Prusa XL five-tool profile for the actual printer. A practical tool allocation is light PETG for the main structure, red PETG for accents, blue PETG for the base and wheels, clear PETG for the dome, and a support material whose manufacturer explicitly supports contact with that PETG. Assign all structural colors to compatible grades of PETG so joined decorative regions bond.

The Prusa-specific 3MF assigns structural volumes to tools 1–4. It does not contain a tested filament profile or printer-specific G-code. Select the five-tool XL profile, check the actual loaded materials, and assign both support and support interfaces to tool 5. The generic 3MF carries preview colors only. Clear FDM parts will be translucent unless their printing and finishing process produces optical clarity.

## Captive supports and release

Print the robot upright, with the tread bottoms on the bed. The horizontal axles, enclosed bearing gaps and suspended chain links require support. Use a compatible dissolvable material for support trapped inside captive joints. The yokes, swivel windows and dome openings provide flushing access. Breakaway support alone is unsuitable where a pin or socket encloses it.

The clear dome meets the head deck and is intended to bond to it. Both rotate together. Its openings allow internal support removal. The dome is not a separate optical lens or a removable pressure enclosure.

After support removal, free each bearing with small movements. Start with the waist and head, then the arm joints, then the fingers and tread links. Do not force a seized pin. Check the coupon results and change the parametric gap if the printer fuses a bearing. All axles have integral retaining flanges, so no separate metal pins are required for the passive model.

## What the checks establish

`validation.json` records manifold geometry, exported STL topology, neutral-pose intersections and sampled parent-child motion checks. The audit flags neutral intersections above 0.01 mm³ and motion intersections above 0.02 mm³; smaller volumes can arise from export rounding. `joints.json` gives pivots, axes, limits, nominal gaps and retaining-flange overlap. `tread_motion.json` records the sampled belt circulation check. Each joint is checked against its parent through its own range. The check does not establish clearance for every combination of whole-arm poses. These are geometric checks. They do not establish printed strength, friction, wear, support removal or the printer's achieved clearance.

No physical print has been tested. The design therefore needs coupon and first-article printing before it can be treated as a proven print-in-place mechanism. The 1 mm finger pins and the tread retaining flanges are the first features to inspect.

## Rebuild

```sh
"$BLENDER" --background --python scripts/print_label_blender.py
.venv/bin/python scripts/build_articulated_print.py
.venv/bin/python scripts/finish_articulated_print.py
.venv/bin/python scripts/check_tread_motion.py
.venv/bin/python scripts/package_prusa.py
"$BLENDER" --background --python scripts/view_articulated_blender.py
```

The final export step removes tiny triangulation features, adds the raised XTI-30 lettering and clears the moving connectors through their tested ranges. STL simplification uses tolerances no greater than 0.03 mm. Connector clearance cuts are recorded separately.

For material and support setup, follow [Prusa's XL material-combination guidance](https://help.prusa3d.com/article/combining-materials-xl_498103) and the support-filament manufacturer's compatibility instructions.
