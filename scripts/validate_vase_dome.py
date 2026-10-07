"""Inspect sliced spiral continuity, fit envelopes and cap bridge paths."""
from pathlib import Path
import json, re, math, hashlib, zipfile
from collections import Counter
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import build_vase_dome as b

OUT=b.OUT

def paths(path):
    text=path.read_text(); state={'X':0.,'Y':0.,'Z':0.,'F':0.}; feature='Custom'; layer=-1; moves=[]
    relative=True; eprev=0
    for raw in text.splitlines():
        if raw.startswith(';TYPE:'):feature=raw[6:]
        if raw==';LAYER_CHANGE':layer+=1
        line=raw.split(';',1)[0].strip()
        if line=='M83':relative=True
        if line=='M82':relative=False
        if line.startswith('G92 E'):eprev=float(line[5:]);continue
        if not re.match(r'^G[01] ',line):continue
        values={k:float(v) for k,v in re.findall(r'([XYZEF])(-?(?:\d*\.)?\d+)',line)}
        start=state.copy();state.update({k:v for k,v in values.items() if k in state})
        e=values.get('E',0) if relative else values.get('E',eprev)-eprev
        if 'E' in values:eprev=values['E']
        dist=math.hypot(state['X']-start['X'],state['Y']-start['Y'])
        if dist>1e-5:moves.append({'a':[start[k] for k in 'XYZ'],'b':[state[k] for k in 'XYZ'],'extruding':e>0,'feature':feature,'layer':layer,'speed':state['F']/60,'e':e})
    stats={k:v for k,v in re.findall(r'^; (.*?) = (.*?)$',text,re.M) if k.startswith(('estimated printing time','total filament used','filament used [','total toolchanges'))}
    return text,moves,stats

def main():
    report={'physical_print_test':'Not performed','slicer':'PrusaSlicer 2.9.6','jobs':{}}
    allmoves={}
    for label,filename,jobname in [('window','zoomer_vase_window.gcode','01_XL_viewing_shell_VASE'),('fittings','zoomer_vase_fittings.gcode','02_XL_cap_and_ring_NORMAL')]:
        path=Path('/private/tmp')/filename;text,moves,stats=paths(path);allmoves[label]=moves
        log=(OUT/'qa'/f'{label}_slice.log').read_text()
        assert 'Slicing result exported to' in log
        assert not re.search(r'warning|error',log,re.I),log
        with zipfile.ZipFile(OUT/f'{jobname}.3mf') as z:
            settings=dict(re.findall(r'^; (\w+) = (.*)$',z.read('Metadata/Slic3r_PE.config').decode(),re.M))
        assert settings['layer_height']=='0.25' and settings['first_layer_height']=='0.25'
        assert settings['printer_model']=='XL5IS' and settings['nozzle_diameter']=='0.4,0.4,0.4,0.4,0.4'
        assert settings['filament_type']=='PETG;PETG;PETG;PETG;PETG'
        assert settings['spiral_vase']==('1' if label=='window' else '0')
        assert settings['support_material']=='0'
        assert not any(m['feature'].startswith('Support material') for m in moves)
        physical=[m for m in moves if m['extruding'] and m['feature'] not in ['Custom','Skirt/Brim']]
        coords=np.asarray([m['b'] for m in physical])
        assert np.all(coords[:,:2]>5) and np.all(coords[:,:2]<355)
        heights=[float(v) for v in re.findall(r'^;HEIGHT:([.\d]+)$',text,re.M)]
        assert heights and all(abs(h-.25)<1e-6 for h in heights)
        report['jobs'][label]={'layer_count':len(heights),'stats':stats,'warnings':[],
            'extrusion_features':dict(Counter(m['feature'] for m in physical)),
            'path_z_min_max_mm':[float(coords[:,2].min()),float(coords[:,2].max())],
            'gcode_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'project_sha256':hashlib.sha256((OUT/f'{jobname}.3mf').read_bytes()).hexdigest()}
    body=[m for m in allmoves['window'] if m['feature']=='External perimeter' and m['layer']>=0]
    extruded=[m for m in body if m['extruding']]
    assert set(m['feature'] for m in allmoves['window'] if m['extruding'] and m['feature']!='Custom')<= {'Skirt/Brim','External perimeter'}
    spiral=[m for m in extruded if m['layer']>=1]
    assert len(spiral)>1000
    assert all(m['b'][2]>=m['a'][2]-1e-6 for m in spiral)
    assert all(m['extruding'] for m in body if 1<=m['layer']<max(v['layer'] for v in body)), 'Travel within vase wall'
    assert max(m['speed'] for m in extruded)<=15.01
    endpoints=np.asarray([m['b'] for m in extruded]);angles=np.unwrap(np.arctan2(endpoints[:,1]-180,endpoints[:,0]-180))
    turns=abs((angles[-1]-angles[0])/(2*np.pi))
    assert 110<turns<112,turns
    points=np.asarray([m['b'] for m in spiral])
    rad=np.linalg.norm(points[:,:2]-180,axis=1)
    z=points[:,2]+b.BASE_Z
    outer=rad+b.WIDTH/2;inner=rad-b.WIDTH/2
    nominal=np.asarray([b.radius(float(v)) for v in z])
    cap_mask=z>=b.CAP_BOTTOM
    gap_outer=b.CLEARANCE+nominal[cap_mask]-outer[cap_mask]
    gap_inner=inner[cap_mask]-(nominal[cap_mask]-b.WIDTH-b.CLEARANCE)
    # The rising nozzle samples contours at layer midplanes. Account for this
    # using measured paths, rather than trusting ideal CAD mating dimensions.
    assert gap_outer.min()>.05 and gap_inner.min()>.05,(gap_outer.min(),gap_inner.min())
    ring_mask=z<=1.75
    ring_gap=inner[ring_mask]-28.64
    assert ring_gap.min()>.10,ring_gap.min()
    report['spiral']={'turns':turns,'continuous_extrusion_after_first_layer':True,'monotonic_z':True,
        'max_wall_speed_mm_s':max(m['speed'] for m in extruded),
        'max_outer_radius_error_vs_cad_mm':float(abs(outer-nominal).max()),
        'cap_outer_groove_min_radial_clearance_from_paths_mm':float(gap_outer.min()),
        'cap_inner_groove_min_radial_clearance_from_paths_mm':float(gap_inner.min()),
        'mounting_ring_min_radial_clearance_from_paths_mm':float(ring_gap.min())}
    assert not any('Bridge' in m['feature'] for m in allmoves['fittings'] if m['extruding']), 'Cap groove requires bridging'
    report['cap_roof']={'bridge_infill_paths':0,'support_paths':0,'construction':'Tapered annular groove roof'}
    report['passed']=True
    (OUT/'qa/validation.json').write_text(json.dumps(report,indent=2)+'\n')
    draw_preview(allmoves)
    print(json.dumps(report,indent=2))

def draw_preview(allmoves):
    image=Image.new('RGB',(1500,760),'#f3f4f2');d=ImageDraw.Draw(image)
    font=lambda n:ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',n)
    d.text((35,24),'Sliced paths | 0.25 mm layers',font=font(30),fill='#152c3b')
    d.text((35,67),'Actual PrusaSlicer output. One spiral shell; separate cap and ring printed normally.',font=font(20),fill='#52636c')
    for label,cx,cy,scale,title,xoffset in [('window',180,180,7.3,'Viewing shell, continuous spiral',385),('fittings',180,180,5.4,'Cap and ring, 25 layers',1120)]:
        for m in allmoves[label]:
            if not m['extruding'] or m['feature']=='Custom':continue
            a,bb=m['a'],m['b']
            col='#cbd3d4' if m['feature']=='Skirt/Brim' else ('#d96c36' if 'Bridge' in m['feature'] else '#236b88')
            d.line((xoffset+(a[0]-cx)*scale,400+(a[1]-cy)*scale,xoffset+(bb[0]-cx)*scale,400+(bb[1]-cy)*scale),fill=col,width=1)
        d.text((xoffset-240,680),title,font=font(23),fill='#152c3b')
    image.save(OUT/'qa/toolpaths.png')

if __name__=='__main__':main()
