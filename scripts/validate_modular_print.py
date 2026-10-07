"""Verify delivered meshes, assembly fit, motion, 3MF settings and sliced G-code."""
from pathlib import Path
import json,zipfile,hashlib,re
import numpy as np
import trimesh as tm
from manifold3d import Manifold,Mesh
import build_modular_print as b
OUT=b.OUT

def solid(t):
    return Manifold(Mesh(np.asarray(t.vertices,dtype=np.float32),np.asarray(t.faces,dtype=np.uint32)))
def main():
    b.build();r=json.loads((OUT/'qa/geometry.json').read_text())
    assert r['mesh_pass'] and not r['intersections'],r
    colors={};issues=[]
    for path in (OUT/'colors').glob('*.stl'):
        t=tm.load(path);colors[path.stem]={'watertight':bool(t.is_watertight),'volume_mm3':float(t.volume)}
        if not t.is_watertight or t.volume<=0:issues.append(str(path))
    for n in b.PARTS:
        part=tm.load(OUT/'parts'/f'{n}.stl')
        assert part.is_watertight and part.is_volume and len(part.split())==1,n
        assert abs(part.bounds[0,2])<1e-4,n
        assert r['parts'][n]['bed_contact_area_mm2']>45,n
    assert not issues,issues
    sweeps=[]
    for name,axis,pivot,angles in [('left_arm',0,(0,0,134),range(-75,76,5)),('right_arm',0,(0,0,134),range(-75,76,5)),('head',2,(0,0,146.6),range(-180,181,10))]:
        moving=b.PARTS[name]
        if name=='head':moving+=b.PARTS['dome']
        fixed=Manifold()
        for n,v in b.PARTS.items():
            if n!=name and not (name=='head' and n=='dome'):fixed+=v
        max_overlap=0
        for angle in angles:
            rot=[0,0,0];rot[axis]=angle
            posed=moving.translate(-np.array(pivot)).rotate(rot).translate(pivot)
            max_overlap=max(max_overlap,(posed^fixed).volume())
        sweeps.append({'part':name,'axis':'XYZ'[axis],'sample_angles_deg':list(angles),'max_overlap_mm3':max_overlap})
        assert max_overlap<.01,(name,max_overlap)
    profiles={};slices={}
    for j in json.loads((OUT/'qa/slice_jobs.json').read_text()):
        path=Path(j['file'])
        with zipfile.ZipFile(path) as z:
            cfg=z.read('Metadata/Slic3r_PE.config').decode()
            assert 'printer_model = XL5IS' in cfg
            assert 'layer_height = 0.15' in cfg
            assert 'nozzle_diameter = 0.4,0.4,0.4,0.4,0.4' in cfg
            settings=dict(re.findall(r'^; (\w+) = (.*)$',cfg,re.M))
        profiles[j['name']]={k:settings[k] for k in ['printer_model','nozzle_diameter','layer_height','perimeters','fill_density','support_material','brim_width','filament_type']}
        gcode=Path('/tmp')/f"zoomer_{j['name']}.gcode"
        log=(OUT/'qa'/f"{j['name']}_slice.log").read_text()
        assert 'Slicing result exported to' in log,j
        g=gcode.read_text()
        assert '; printer_model = XL5IS' in g
        assert '; layer_height = 0.15' in g
        stats={k:v for k,v in re.findall(r'^; (.*?) = (.*?)$',g,re.M) if k.startswith(('estimated printing time','total filament used','total toolchanges'))}
        warnings=log[log.index('print warning:'):log.index('88 =>',log.index('print warning:'))] if 'print warning:' in log else ''
        slices[j['name']]={'stats':stats,'warnings':warnings,'gcode_sha256':hashlib.sha256(g.encode()).hexdigest(),'project_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'support_toolpaths':len(re.findall(r'^;TYPE:Support material',g,re.M)),'layers':len(re.findall(r'^;LAYER_CHANGE',g,re.M))}
    report={'physical_print_test':'not performed','geometry_pass':True,'color_volume_checks':colors,'motion_sweeps':sweeps,'profiles':profiles,'slices':slices}
    (OUT/'qa/validation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'geometry_pass':True,'motion':sweeps,'slices':slices},indent=2))
if __name__=='__main__':main()
