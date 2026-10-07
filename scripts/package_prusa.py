"""Package the checked solids as one PrusaSlicer object with named volumes."""
from pathlib import Path
import json, zipfile, xml.etree.ElementTree as E
import numpy as np
import trimesh as tm

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'print/articulated'
NS='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'

def main():
    report=json.loads((OUT/'validation.json').read_text())
    if not report['cad_pass']:raise RuntimeError('Resolve the CAD validation failures before packaging.')
    E.register_namespace('',NS);tag=lambda x:'{'+NS+'}'+x
    model=E.Element(tag('model'),unit='millimeter',attrib={'{http://www.w3.org/XML/1998/namespace}lang':'en-US','xmlns:slic3rpe':'http://schemas.slic3r.org/3mf/2017/06'})
    E.SubElement(model,tag('metadata'),name='slic3rpe:Version3mf').text='1'
    E.SubElement(model,tag('metadata'),name='Title').text='XTI-30 captive articulation'
    resources=E.SubElement(model,tag('resources'));obj=E.SubElement(resources,tag('object'),id='1',type='model')
    mesh=E.SubElement(obj,tag('mesh'));vertices=E.SubElement(mesh,tag('vertices'));triangles=E.SubElement(mesh,tag('triangles'))
    config=E.Element('config');co=E.SubElement(config,'object',id='1',instances_count='1')
    E.SubElement(co,'metadata',type='object',key='name',value='XTI-30 — keep assembled')
    assignments={};vo=0;fo=0;bounds=[]
    for name in report['parts']:
        t=tm.load(OUT/(name+'.stl'));bounds.append(t.bounds)
        for v in t.vertices:E.SubElement(vertices,tag('vertex'),**{a:format(float(x),'.9g') for a,x in zip('xyz',v)})
        for f in t.faces:E.SubElement(triangles,tag('triangle'),**{'v'+str(i+1):str(int(x)+vo) for i,x in enumerate(f)})
        volume=E.SubElement(co,'volume',firstid=str(fo),lastid=str(fo+len(t.faces)-1))
        tool=4 if name=='dome_cover' else 3 if name=='base' or 'wheel' in name or 'tread' in name else 2 if name.endswith(('yaw','roll')) else 1
        assignments[name]=tool
        for key,value in [('name',name),('volume_type','ModelPart'),('extruder',str(tool)),('matrix','1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1')]:
            E.SubElement(volume,'metadata',type='volume',key=key,value=value)
        E.SubElement(volume,'mesh',edges_fixed='0',degenerate_facets='0',facets_removed='0',facets_reversed='0',backwards_edges='0')
        vo+=len(t.vertices);fo+=len(t.faces)
    build=E.SubElement(model,tag('build'));E.SubElement(build,tag('item'),objectid='1',transform='1 0 0 0 1 0 0 0 1 180 180 0',printable='1')
    with zipfile.ZipFile(OUT/'zoomer_articulated_180mm.3mf') as source:
        types=source.read('[Content_Types].xml');rels=source.read('_rels/.rels')
    types=types.replace(b'</Types>',b'<Default Extension="config" ContentType="application/xml"/></Types>')
    dest=OUT/'zoomer_prusa_XL_assembled.3mf'
    with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml',types);z.writestr('_rels/.rels',rels)
        z.writestr('3D/3dmodel.model',E.tostring(model,encoding='utf-8',xml_declaration=True))
        z.writestr('Metadata/Slic3r_PE_model.config',E.tostring(config,encoding='utf-8',xml_declaration=True))
    b=np.array(bounds);dims=b[:,1].max(axis=0)-b[:,0].min(axis=0)
    manifest=dict(file=dest.name,units='mm',build_objects=1,volumes=len(assignments),dimensions_mm=dims.tolist(),
                  tools={'1':'light PETG','2':'red PETG','3':'blue PETG','4':'clear PETG dome','5':'PETG-compatible dissolvable support'},
                  volume_tools=assignments,printer_profile_included=False,physical_print_test='not performed')
    (OUT/'prusa_package.json').write_text(json.dumps(manifest,indent=2));print(json.dumps({k:v for k,v in manifest.items() if k!='volume_tools'},indent=2))
if __name__=='__main__':main()
