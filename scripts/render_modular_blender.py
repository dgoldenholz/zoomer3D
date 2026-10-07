"""Render actual exported print meshes. Color view represents five PLA colors."""
import bpy, math, json, sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'print/modular'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=32
scene.world.color=(.45,.45,.45);scene.view_settings.view_transform='AgX'
scene.render.resolution_x=1000;scene.render.resolution_y=1250;scene.render.resolution_percentage=100
palette={'ivory':(.81,.84,.79,1),'red':(.60,.03,.06,1),'blue':(.045,.09,.4,1),'green':(.24,.46,.085,1),'dark':(.025,.03,.045,1),'clear':(.68,.88,.96,1)}
for name,col in palette.items():
    m=bpy.data.materials.new(name);m.diffuse_color=col;m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=col;p.inputs['Roughness'].default_value=.33
    if name=='clear':p.inputs['Transmission Weight'].default_value=1;p.inputs['Roughness'].default_value=.10;p.inputs['IOR'].default_value=1.46
objs={}
for path in sorted((OUT/'colors').glob('*.stl')):
    name,color=path.stem.split('__');bpy.ops.wm.stl_import(filepath=str(path));ob=bpy.context.object;ob.name=name+' | '+color;ob.data.materials.append(bpy.data.materials[color]);objs.setdefault(name,[]).append(ob)
    for p in ob.data.polygons:p.use_smooth=False
# Three inspection controls correspond to the three physical joints.
for label,names,pivot,axis,limit in [('Head yaw',['head','dome'],(0,0,146.6),2,180),('Left shoulder',['left_arm'],(58,0,134),0,75),('Right shoulder',['right_arm'],(-58,0,134),0,75)]:
    control=bpy.data.objects.new(label,None);scene.collection.objects.link(control);control.location=pivot;control.empty_display_type='ARROWS';control.empty_display_size=8
    control['angle_deg']=0.0;control.id_properties_ui('angle_deg').update(min=-limit,max=limit)
    bpy.context.view_layer.update()
    for n in names:
        for ob in objs[n]:world=ob.matrix_world.copy();ob.parent=control;ob.matrix_world=world
    fc=control.driver_add('rotation_euler',axis);v=fc.driver.variables.new();v.name='a';v.type='SINGLE_PROP';v.targets[0].id=control;v.targets[0].data_path='["angle_deg"]';fc.driver.expression='a*pi/180'
# Exact geometry, no render-only bevels or hidden replacement shells.
for loc,power,size in [((100,-160,290),1500000,170),((-180,-80,170),1000000,150),((100,130,250),1600000,130)]:
    bpy.ops.object.light_add(type='AREA',location=loc);ob=bpy.context.object;ob.data.energy=power;ob.data.shape='DISK';ob.data.size=size;ob.rotation_euler=(Vector((0,0,90))-ob.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(0,-600,90));cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=212;scene.camera=cam
cam.rotation_euler=(Vector((0,0,90))-cam.location).to_track_quat('-Z','Y').to_euler()
scene.render.film_transparent=True
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.001
scene['README']='Revised modular print. Three passive joints. Actual print meshes; clear dome view is an optical illustration, not an FDM transparency claim. See print/modular/PRINTING.md.'
# Save an assembled inspection scene with original drawing packed as an image.
im=bpy.data.images.load(str(ROOT/'zoomer.png'));im.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'assets/zoomer_modular.blend'))
for view,loc,target in [('front',(0,-600,90),(0,0,90)),('hero',(240,-550,255),(0,0,88)),('rear',(-220,530,230),(0,0,88))]:
    cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/'qa'/f'{view}.png');bpy.ops.render.render(write_still=True)
# Explode only assembly groups; all part geometry stays unchanged.
for n,group in objs.items():
    shift=Vector((0,0,0))
    if n=='torso':shift=Vector((0,0,20))
    elif n=='head':shift=Vector((0,0,45))
    elif n=='dome':shift=Vector((0,0,65))
    elif n=='head_peg':shift=Vector((0,0,32))
    elif 'arm' in n:shift=Vector((28 if n.startswith('left') else -28,0,20))
    elif 'shoulder_pin' in n:shift=Vector((48 if n.startswith('left') else -48,0,20))
    elif 'track' in n:shift=Vector((18 if n.startswith('left') else -18,0,-8))
    for ob in group:ob.location+=shift
cam.location=(240,-570,270);cam.rotation_euler=(Vector((0,0,120))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=290
scene.render.filepath=str(OUT/'qa/exploded.png');bpy.ops.render.render(write_still=True)
