"""Refresh presentation renders from the saved Blender robot."""
import bpy
from mathutils import Vector
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/zoomer.blend'))
scene=bpy.context.scene;cam=bpy.data.objects['Hero camera'];scene.camera=cam
scene.cycles.samples=32
views=[('zoomer_hero',1,(2.35,-4.6,2.15),(0,0,.75),1.88,1500,1700),
       ('zoomer_front',1,(0,-5,1.1),(0,0,.75),1.78,1400,1600),
       ('zoomer_articulated',105,(2.35,-4.6,2.15),(0,0,.85),2.0,1400,1600)]
for name,frame,location,target,scale,w,h in views:
 scene.frame_set(frame);cam.location=Vector(location)*.12
 cam.rotation_euler=(Vector(target)*.12-cam.location).to_track_quat('-Z','Y').to_euler()
 cam.data.ortho_scale=scale*.12;scene.render.resolution_x=w;scene.render.resolution_y=h
 scene.render.filepath=str(ROOT/f'renders/{name}.png');bpy.ops.render.render(write_still=True)
print('PRESENTATION_RENDERS_COMPLETE')
