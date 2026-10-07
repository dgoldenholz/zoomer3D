"""Finish Blender's voxel-fused display STL and create a separate dome in millimetres."""
import json,sys
from pathlib import Path
import numpy as np
import trimesh as tm
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from robot_design import build
from build_print import mf3
D=build();sc=np.array(D['scale_xyz'])
t=tm.load(ROOT/'print/zoomer_static_body_raw.stl',force='mesh',process=True)
print('Loaded mesh:',len(t.faces),'faces',flush=True)
t=t.simplify_quadric_decimation(face_count=450000)
print('Simplified:',len(t.faces),'faces',flush=True)
t.update_faces(t.nondegenerate_faces());t.update_faces(t.unique_faces());t.remove_unreferenced_vertices()
components=t.split(only_watertight=False);main=max(components,key=lambda c:c.volume);main.fix_normals()
assert main.is_watertight and main.is_volume
main.apply_translation((0,0,-main.bounds[0,2]));main.export(ROOT/'print/zoomer_static_body_180mm.stl')
mf3('zoomer_static_body_180mm.3mf',[('supported static body',main,0)])
wall=.8;r=.233*sc[1]*1000+.3+wall;h=.242*sc[2]*1000;N=48
outer=[(r*np.cos(t),h*np.sin(t)) for t in np.linspace(0,np.pi/2,N)];inner=[((r-wall)*np.cos(t),(h-wall)*np.sin(t)) for t in np.linspace(np.pi/2,0,N)]
dome=tm.creation.revolve(np.array(outer+inner+[outer[0]]),sections=128);dome.apply_scale((sc[0]/sc[1],1,1));dome.fix_normals();assert dome.is_watertight;dome.export(ROOT/'print/dome_080mm_wall.stl')
# Include the dome's mounted location when checking the full robot's visual envelope.
origin={l['name']:np.array(l['origin'])*sc*1000 for l in D['links']};bounds=[]
for m in json.loads((ROOT/'simulation/mesh_manifest.json').read_text()):
    v=tm.load(ROOT/'simulation/meshes'/m['file'],force='mesh',process=False).vertices*1000+origin[m['body']];bounds.extend(v)
b=np.array(bounds)
report=dict(units='mm',visual_extent_xyz_mm=np.ptp(b,axis=0).tolist(),static_body_extent_xyz_mm=main.extents.tolist(),body_watertight=bool(main.is_watertight),body_components=1,omitted_decorative_components=len(components)-1,omitted_decorative_volume_mm3=float(sum(abs(c.volume) for c in components if c is not main)),dome_watertight=bool(dome.is_watertight),static_body_requires_supports=True,full_robot_print_in_place=False)
(ROOT/'print/display_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
