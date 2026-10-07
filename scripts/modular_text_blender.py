import bpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'assets/modular_text';out.mkdir(exist_ok=True)
for txt in ['XTI-30','10:15']:
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    cu=bpy.data.curves.new(txt,'FONT');cu.body=txt;cu.size=1;cu.extrude=.5;cu.resolution_u=8
    ob=bpy.data.objects.new(txt,cu);bpy.context.collection.objects.link(ob);bpy.context.view_layer.objects.active=ob;ob.select_set(True)
    # Text lies in X,Z facing -Y. Unit text height follows Blender font em.
    ob.rotation_euler=(1.57079632679,0,0)
    bpy.ops.object.convert(target='MESH');bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    # Normalize depth to one; builder chooses the physical extrusion.
    ys=[v.co.y for v in ob.data.vertices];lo=min(ys);hi=max(ys)
    for v in ob.data.vertices:v.co.y=(v.co.y-hi)/(hi-lo)
    bpy.ops.wm.stl_export(filepath=str(out/(txt.replace(':','_')+'.stl')),export_selected_objects=True)
