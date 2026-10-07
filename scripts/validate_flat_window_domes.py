"""Validate the saved projects and their actual toolpaths."""
import json,re,zipfile,hashlib
from pathlib import Path
from collections import Counter
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import Polygon,Point
import build_flat_window_domes as b
from validate_vase_dome import paths

OUT=b.OUT
def main():
    geometry=json.loads((OUT/'qa/geometry.json').read_text())
    assert all(p['watertight'] and p['connected_components']==1 for p in geometry['parts'].values())
    assert all(v['visible'] for v in geometry['face_visibility_checks'])
    results={'physical_print_test':'Not performed','slicer':'PrusaSlicer 2.9.6','jobs':[]}
    moves_by_job={}
    for job in json.loads((OUT/'qa/jobs.json').read_text()):
        name=job['name'];project=b.ROOT/job['project']
        log=(OUT/'qa'/f'{name}_slice.log').read_text()
        assert 'Slicing result exported to' in log
        assert not re.search(r'warning|error',log,re.I),log
        txt,moves,stats=paths(Path(job['gcode']));moves_by_job[name]=moves
        with zipfile.ZipFile(project) as z:
            cfg=dict(re.findall(r'^; (\w+) = (.*)$',z.read('Metadata/Slic3r_PE.config').decode(),re.M))
        assert cfg['layer_height']==cfg['first_layer_height']=='0.25'
        assert cfg['printer_model']=='XL5IS' and cfg['nozzle_diameter']=='0.4,0.4,0.4,0.4,0.4'
        assert cfg['spiral_vase']==str(int(job['vase']))
        assert cfg['support_material']=='0' and cfg['fill_density']==('0%' if job['vase'] else '100%')
        physical=[m for m in moves if m['extruding'] and m['feature'] not in ['Custom','Skirt/Brim']]
        coords=np.asarray([m['b'] for m in physical]);assert np.all(coords[:,:2]>5) and np.all(coords[:,:2]<355)
        features=Counter(m['feature'] for m in physical)
        assert not any('Support' in f for f in features)
        heights=[float(h) for h in re.findall(r'^;HEIGHT:([.\d]+)',txt,re.M)]
        assert heights and all(abs(h-.25)<1e-6 for h in heights)
        record={'name':name,'parts':job['parts'],'layer_comments':len(heights),'stats':stats,'features':dict(features),'warnings':[],
            'project_sha256':hashlib.sha256(project.read_bytes()).hexdigest()}
        if job['vase']:
            assert set(features)=={'External perimeter'}
            walls=[m for m in moves if m['feature']=='External perimeter' and m['layer']>=0]
            last=max(m['layer'] for m in walls)
            # A sub-millimetre reposition may join the flat first loop to the
            # spiral. Require uninterrupted extrusion once Z starts rising.
            assert all(m['extruding'] for m in walls if m['a'][2]>.25001 and m['layer']<last)
            assert all(m['b'][2]>=m['a'][2]-1e-6 for m in physical)
            assert max(m['speed'] for m in physical)<=15.01
            record['continuous_spiral']=True
            if 'faceted' in name:
                midpoints=[(np.asarray(m['a'])+np.asarray(m['b']))/2 for m in physical]
                front=[p for p in midpoints if abs(p[0]-180)<8 and p[1]<180-10 and 1<p[2]<25]
                errors=[abs((p[1]-180)-(-21*b.scale(p[2]+b.BASE)+.3)) for p in front]
                assert max(errors)<.08,max(errors)
                record['front_path_max_deviation_from_plane_mm']=max(errors)
                gaps=[]
                for p in coords:
                    z=p[2]+b.BASE
                    if z<b.CAP_BOTTOM:continue
                    outer=Polygon(b.section(z,.25).to_polygons()[0]);inner=Polygon(b.section(z,-.85).to_polygons()[0]);pt=Point(p[0]-180,p[1]-180)
                    gaps.append(min(outer.boundary.distance(pt),inner.boundary.distance(pt))-.3)
                assert min(gaps)>.05,min(gaps)
                record['minimum_cap_clearance_from_shell_paths_mm']=min(gaps)
        bridges=[m for m in physical if 'Bridge' in m['feature']]
        record['bridge_segment_count']=len(bridges)
        record['longest_bridge_segment_mm']=max([np.linalg.norm(np.asarray(m['a'])[:2]-np.asarray(m['b'])[:2]) for m in bridges],default=0)
        results['jobs'].append(record)
    results['passed']=True
    (OUT/'qa/validation.json').write_text(json.dumps(results,indent=2)+'\n')
    preview(moves_by_job)
    print(json.dumps(results,indent=2))

def preview(jobs):
    im=Image.new('RGB',(1600,1350),'#f3f4f2');d=ImageDraw.Draw(im)
    f=lambda s:ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',s)
    d.text((35,25),'Four print jobs | actual sliced paths',font=f(32),fill='#193747')
    labels=['Flat-wall test: vase mode','Faceted shell: vase mode','Shared cap and adapter: normal','Sheet hood and retainer: normal']
    for i,((name,moves),title) in enumerate(zip(jobs.items(),labels)):
        x=400+(i%2)*800;y=350+(i//2)*600;s=5
        for m in moves:
            if not m['extruding'] or m['feature']=='Custom':continue
            col='#becacb' if m['feature']=='Skirt/Brim' else ('#d97636' if 'Bridge' in m['feature'] else '#287798')
            a,mend=np.asarray(m['a'])[:2],np.asarray(m['b'])[:2]
            d.line((x+(a[0]-180)*s,y+(a[1]-175)*s,x+(mend[0]-180)*s,y+(mend[1]-175)*s),fill=col,width=1)
        d.text((x-330,y+240),title,font=f(26),fill='#193747')
    d.text((35,1280),'0.25 mm layers throughout. Blue: extrusion. Gray: brim. Orange: bridge paths, if any.',font=f(22),fill='#536770')
    im.save(OUT/'qa/toolpaths.png')

if __name__=='__main__':main()
