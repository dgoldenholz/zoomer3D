# Print revision assessment

The former captive assembly was a poor first print. It needed support below most of the arms, inside bearings, between tread links and inside a dome bonded to the head. Removing that support would load the smallest pins before the model had moved. A single failed axle or fused link could spoil a much larger assembly.

The revised model addresses those problems through part orientation and fewer joints. The main eleven parts now slice without support; the twelfth part is the optional dome, printed separately with accessible support. Printed 8 mm pins replace the fine captive axles. The column lies along the bed, and the track keys reach the bed in their side-down orientation. Head cheek bases also meet the platform, and the head socket closes with a sloped roof.

## Match to the drawing

The supplied drawing is a hand-drawn perspective view. It establishes the silhouette and front details, but it does not determine an exact depth or an engineering tolerance. The comparison uses manually selected image landmarks and aligns the robot heights. It does not report a pixel-similarity score.

| Proportion | Drawing estimate at 180 mm height | Revised model |
| --- | ---: | ---: |
| Overall width | About 140 mm | 140.6 mm |
| Chest height to lower wings | About 81 mm | 80 mm |
| Dome width | About 59 mm | 59 mm |
| Exposed central column | About 47 mm | 48 mm |

The revision restores the broad shoulders, tall chest with its lower cutout, four gauges, red center outline, clock, bellows details and long arms. The base-to-body spacing and hand height now follow the sketch. See [the comparison](qa/drawing_comparison.png) and [the front render](qa/front.png).

The model uses symmetry where the drawing is uneven. Its depth is inferred. The hands are sturdy fixed pincers, the belt and wheels form solid units, and blue covers the purple regions in the five-tool print. The dome reads differently in the orthographic front render because the drawing shows its rim as a perspective ellipse. The single view cannot establish a unique 3D reconstruction. These differences leave the robot recognizable while removing fragile details and trapped support.

## Iterations and evidence

The first geometry pass restored the proportions but revealed detached lettering, a corner contact between two chest details, and small export facets. Those were corrected in the source geometry and checked again after STL export. The first sliced revision revealed unsupported track keys and head details. The final revision extends those features to supporting geometry. It also adds a dome seating ledge and clearance around the locating lip.

The final check records 12 connected watertight parts, watertight color volumes, no neutral assembly intersections above the audit threshold, and no intersections in 99 sampled joint poses. PrusaSlicer 2.9.6 sliced all four supplied projects using the embedded XL5IS profile, 0.4 mm nozzles and 0.15 mm layers. The two main plates and coupons contain no support toolpaths; the dome contains support. None of the final slicing logs contains a support or stability warning.

The saved Blender file and renders use the exported print geometry. There are no substitute cosmetic shells or render-only bevels. The transparent dome material helps inspect the face but does not predict FDM clarity.

Printed tolerances, glue retention, layer strength, support removal, joint friction and wear still require physical checks. Start with the coupons, then inspect the first article. The files are ready for that test; they are not a physically qualified product.
