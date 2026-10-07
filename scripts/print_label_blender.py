"""Create printable raised text for the mechanical chest, in millimetres."""
import bpy,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
curve=bpy.data.curves.new('XTI-30 raised lettering','FONT');curve.body='XTI-30';curve.size=4.2;curve.extrude=.5;curve.align_x='CENTER';curve.align_y='CENTER';curve.resolution_u=6
obj=bpy.data.objects.new('XTI-30 label',curve);bpy.context.collection.objects.link(obj);obj.location=(0,-14.0,136);obj.rotation_euler.x=math.pi/2
obj.select_set(True);bpy.context.view_layer.objects.active=obj;bpy.ops.object.convert(target='MESH');bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
bpy.ops.wm.stl_export(filepath=str(ROOT/'assets/print_chest_label.stl'),export_selected_objects=True)
print('PRINT_LABEL_COMPLETE')
