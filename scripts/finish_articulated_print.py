"""Make float32-safe STL exports from the indexed 3MF solids and audit joints."""
from pathlib import Path
import io,json,zipfile,sys,xml.etree.ElementTree as E
import numpy as np
import trimesh as tm
from manifold3d import Manifold,Mesh64
from build_print import mf3
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'print/articulated'
NS={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}

def main():
    report=json.loads((OUT/'validation.json').read_text())
    with zipfile.ZipFile(OUT/'zoomer_articulated_180mm.3mf') as archive:root=E.fromstring(archive.read('3D/3dmodel.model'))
    meshes={};solids={};colors={};repairs={}
    for ob in root.findall('m:resources/m:object',NS):
        if ob.find('m:mesh',NS) is None:continue
        name=ob.get('name');colors[name]=int(ob.get('pindex','0'))
        vertices=np.array([[float(p.get(a)) for a in ['x','y','z']] for p in ob.findall('m:mesh/m:vertices/m:vertex',NS)])
        faces=np.array([[int(p.get(a)) for a in ['v1','v2','v3']] for p in ob.findall('m:mesh/m:triangles/m:triangle',NS)],dtype=np.uint64)
        original=Manifold(Mesh64(vertices,faces));assert str(original.status())=='Error.NoError',name
        for tolerance in [.01,.02,.015,.025,.03]:
            simplified=original.set_tolerance(tolerance);data=simplified.to_mesh64()
            precise=tm.Trimesh(data.vert_properties,data.tri_verts,process=False)
            exported=tm.load(io.BytesIO(precise.export(file_type='stl')),file_type='stl')
            exported.process(validate=True)
            if exported.is_watertight and exported.is_volume and len(exported.split())==1:break
        else:raise RuntimeError('STL topology could not be preserved: '+name)
        exported.export(OUT/(name+'.stl'));assert tm.load(OUT/(name+'.stl')).is_watertight,name
        meshes[name]=exported;solids[name]=Manifold(Mesh64(np.asarray(exported.vertices),np.asarray(exported.faces,dtype=np.uint64)))
        repairs[name]=tolerance
        report['parts'][name].update(watertight=True,exported_stl_watertight=True,components=1,volume_mm3=float(exported.volume),bounds_mm=exported.bounds.tolist())
    report['export_simplification_tolerance_mm']=repairs
    joints=json.loads((OUT/'joints.json').read_text())
    # Relieve the parent connector through the child's actual motion envelope.
    # The original retained shaft and flange dimensions remain the bearing datum.
    relieved=[];originals=dict(solids)
    cache=Path('/private/tmp/zoomer-tools/clearance_pass');cache.mkdir(parents=True,exist_ok=True)
    if '--resume-clearance' not in sys.argv:
        for previous in cache.glob('*.npz'):previous.unlink()
        (cache/'progress.json').write_text('[]')
    if '--resume-clearance' in sys.argv:
        relieved=json.loads((cache/'progress.json').read_text())
        for path in cache.glob('*.npz'):
            value=np.load(path);solids[path.stem]=Manifold(Mesh64(value['vertices'],value['faces']))
    for joint in reversed(joints):
        if joint['type']!='hinge':continue
        if joint['name'] in relieved:continue
        moving=solids[joint['name']];parent=joint['parent'];pivot=np.array(joint['origin_mm']);axis=np.array(joint['axis'])
        angles=np.linspace(*joint['limits_deg'],19)
        rotations=[tm.transformations.rotation_matrix(np.deg2rad(a),axis,pivot)[:3] for a in angles]
        if max((moving.transform(r)^solids[parent]).volume() for r in rotations)<.015:continue
        # The original child is a superset of its relieved version. Using it
        # avoids feeding increasingly detailed cuts into Minkowski sums.
        print('Clearing '+joint['name'],flush=True)
        offset=originals[joint['name']].simplify(.02).translate(-pivot).minkowski_sum(Manifold.sphere(.37,8)).translate(pivot).simplify(.01)
        value=solids[parent]
        for r in rotations:value=(value-offset.transform(r)).simplify(.01)
        pieces=sorted(value.decompose(),key=lambda p:p.volume(),reverse=True)
        if len(pieces)>1:
            print('Fragments '+parent+' '+str([p.volume() for p in pieces]),flush=True)
            # Discard isolated slivers smaller than a printer extrusion bead.
            if all(p.volume()<.05 for p in pieces[1:]):value=pieces[0]
            else:raise RuntimeError('Swept clearance disconnected '+parent)
        if value.is_empty():raise RuntimeError('Swept clearance emptied '+parent)
        solids[parent]=value;relieved.append(joint['name'])
        checkpoint=value.to_mesh64();np.savez(cache/(parent+'.npz'),vertices=checkpoint.vert_properties,faces=checkpoint.tri_verts)
        (cache/'progress.json').write_text(json.dumps(relieved))
        print('Cleared '+joint['name'],flush=True)
    # Materialize the Boolean results before later unions and STL rounding.
    # This also makes a fresh pass match a pass resumed from indexed meshes.
    for name,value in solids.items():
        data=value.to_mesh64();solids[name]=Manifold(Mesh64(data.vert_properties,data.tri_verts))
    # Raised label is fused to the chest substrate, not a separate loose object.
    label_path=ROOT/'assets/print_chest_label.stl'
    if label_path.exists():
        label=tm.load(label_path);solids['waist_pitch']+=Manifold(Mesh64(np.asarray(label.vertices),np.asarray(label.faces,dtype=np.uint64)))
    for name,original in solids.items():
        for tolerance in [.01,.02,.015,.025,.03]:
            data=original.set_tolerance(tolerance).to_mesh64();precise=tm.Trimesh(data.vert_properties,data.tri_verts,process=False)
            t=tm.load(io.BytesIO(precise.export(file_type='stl')),file_type='stl');t.process(validate=True)
            if t.is_watertight and t.is_volume and len(t.split())==1:break
        else:
            print('Export topology '+name+' '+str((t.is_watertight,t.is_volume,len(t.split(only_watertight=False)))),flush=True)
            raise RuntimeError('Final export failed: '+name)
        meshes[name]=t;t.export(OUT/(name+'.stl'));solids[name]=Manifold(Mesh64(np.asarray(t.vertices),np.asarray(t.faces,dtype=np.uint64)))
        repairs[name]=tolerance
        report['parts'][name].update(volume_mm3=float(t.volume),bounds_mm=t.bounds.tolist())
    report['final_export_simplification_max_mm']=.03
    report['swept_connector_reliefs']=relieved
    # Recheck intersections on exactly the solids delivered to the slicer.
    report['intersections']=[];names=list(meshes)
    for i,a in enumerate(names):
        for b in names[i+1:]:
            x,y=meshes[a].bounds,meshes[b].bounds
            if np.any(x[1]<y[0]) or np.any(y[1]<x[0]):continue
            volume=float((solids[a]^solids[b]).volume())
            if volume>.01:report['intersections'].append(dict(a=a,b=b,volume_mm3=volume))
    sweeps=[]
    for joint in joints:
        if joint['type']=='chain_pin':continue
        moving=solids[joint['name']];stationary=solids[joint['parent']];pivot=np.array(joint['origin_mm']);axis=np.array(joint['axis'])
        # This checks the assembled parent and child, including their connectors.
        for angle in np.linspace(*joint['limits_deg'],13):
            matrix=tm.transformations.rotation_matrix(np.deg2rad(angle),axis,pivot)
            overlap=float((moving.transform(matrix[:3])^stationary).volume())
            if overlap>.02:sweeps.append(dict(joint=joint['name'],angle_deg=float(angle),overlap_mm3=overlap))
    report['assembled_joint_sweep_collisions']=sweeps
    report['cad_pass']=not report['intersections'] and not sweeps
    report['export_topology_pass']=True
    (OUT/'validation.json').write_text(json.dumps(report,indent=2))
    mf3('articulated/zoomer_articulated_180mm.3mf',[(name,t,colors[name]) for name,t in meshes.items()])
    print(json.dumps(dict(parts=len(meshes),intersections=report['intersections'],assembled_joint_sweep_collisions=sweeps,cad_pass=report['cad_pass']),indent=2),flush=True)
if __name__=='__main__':main()
