"""Render the actual alternative cover meshes without changing the old model."""
from pathlib import Path
import json,bpy,bmesh
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'print/flat_window_domes'
SOURCE=ROOT/'assets/zoomer_modular.blend'
COLORS={'faceted_shell':(.15,.45,.67),'sheet_hood':(.15,.45,.67),'shared_cap':(.81,.57,.24),'shared_adapter':(.24,.52,.34),'sheet_retainer':(.81,.57,.24),'clear_sheet_NOT_FOR_PRINTING':(.55,.86,.95)}
def camera(scene,loc,target,scale):
    cam=scene.camera;cam.location=loc;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
def render(scene,name):
    scene.render.filepath=str(OUT/'qa'/f'{name}.png');bpy.ops.render.render(write_still=True)
report={}
for variant,names in [('faceted',['faceted_shell','shared_cap','shared_adapter']),('sheet_window',['sheet_hood','shared_cap','shared_adapter','sheet_retainer','clear_sheet_NOT_FOR_PRINTING'])]:
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24
    scene.render.resolution_x=900;scene.render.resolution_y=950;scene.render.resolution_percentage=100
    scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG'
    for ob in list(bpy.data.objects):
        if ob.name.startswith('dome |'):bpy.data.objects.remove(ob,do_unlink=True)
    parts={};control=bpy.data.objects['Head yaw'];control['angle_deg']=0
    for name in names:
        bpy.ops.wm.stl_import(filepath=str(OUT/'inspection_only'/f'{name}.stl'))
        ob=bpy.context.object;ob.name=name
        m=bpy.data.materials.new('Cover | '+name);m.use_nodes=True;m.diffuse_color=(*COLORS[name],1)
        node=m.node_tree.nodes.get('Principled BSDF');node.inputs['Base Color'].default_value=(*COLORS[name],1);node.inputs['Roughness'].default_value=.34
        if name=='clear_sheet_NOT_FOR_PRINTING':
            # Transparent shader marks the sheet's position without making an
            # optical simulation of a particular commercial sheet or print.
            tree=m.node_tree;trans=tree.nodes.new('ShaderNodeBsdfTransparent');mix=tree.nodes.new('ShaderNodeMixShader');mix.inputs[0].default_value=.035
            tree.links.new(trans.outputs[0],mix.inputs[1]);tree.links.new(node.outputs[0],mix.inputs[2]);tree.links.new(mix.outputs[0],tree.nodes.get('Material Output').inputs['Surface'])
        ob.data.materials.append(m);world=ob.matrix_world.copy();ob.parent=control;ob.matrix_world=world;parts[name]=ob
    assert all(ob.parent==control for ob in parts.values())
    report[variant]={'parts':names,'parent':'Head yaw','saved_scene':f'assets/zoomer_{variant}_dome.blend'}
    scene['README']='Flat viewing cover. See print/flat_window_domes/PRINTING.md. Construction colors and faint sheet are explanatory; optical performance is not simulated.'
    camera(scene,(200,-550,250),(0,0,90),214)
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'assets'/f'zoomer_{variant}_dome.blend'))
    render(scene,variant+'_robot')
    for ob in scene.objects:
        if ob.type=='MESH' and ob not in parts.values() and not ob.name.startswith('head |'):ob.hide_render=True
    camera(scene,(25,-270,161),(0,0,161),79)
    render(scene,variant+'_head')
    if variant=='faceted':
        ob=parts['faceted_shell'];dup=ob.copy();dup.data=ob.data.copy();scene.collection.objects.link(dup)
        bm=bmesh.new();bm.from_mesh(dup.data)
        bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-6,plane_co=(0,0,0),plane_no=(0,1,0),clear_inner=True,clear_outer=False)
        edges=[e for e in bm.edges if e.is_boundary]
        if edges:bmesh.ops.holes_fill(bm,edges=edges,sides=0)
        bm.to_mesh(dup.data);bm.free();ob.hide_render=True
        render(scene,'faceted_cutaway');ob.hide_render=False;bpy.data.objects.remove(dup,do_unlink=True)
    shifts={'shared_adapter':(0,0,4),'shared_cap':(0,0,28),'faceted_shell':(0,0,13),'sheet_hood':(0,0,13),'sheet_retainer':(0,-30,13),'clear_sheet_NOT_FOR_PRINTING':(0,-16,13)}
    for name,ob in parts.items():ob.location+=Vector(shifts[name])
    camera(scene,(50,-250,236),(0,-5,176),112)
    render(scene,variant+'_exploded')
(OUT/'qa/blender.json').write_text(json.dumps(report,indent=2)+'\n')
print('Both new inspection scenes saved; original model unchanged.')
