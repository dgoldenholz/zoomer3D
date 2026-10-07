"""Add a marker table, free markers and eye cameras to the mobile robot."""
from pathlib import Path
import xml.etree.ElementTree as E
import json

ROOT=Path(__file__).resolve().parents[1]
PALETTE={'black':'.035 .045 .065 1','red':'.82 .06 .08 1','blue':'.06 .25 .85 1','green':'.04 .55 .27 1'}
def add(p,tag,**attrs):return E.SubElement(p,tag,{k:str(v) for k,v in attrs.items()})
def build():
    tree=E.parse(ROOT/'simulation/zoomer.xml');root=tree.getroot();root.set('model','zoomer_workshop')
    root.find('option').set('iterations','40')
    world=root.find('worldbody');floor=world.find("geom[@name='floor']");floor.set('size','1.2 1.2 .01')
    add(root,'visual');vis=root.find('visual');add(vis,'global',offwidth=1200,offheight=800)
    add(vis,'map',znear='.001',zfar='5')
    add(vis,'headlight',ambient='.35 .35 .35',diffuse='.7 .7 .7',specular='.2 .2 .2')
    add(world,'light',pos='-.4 .2 .8',dir='.1 -.5 -.5',diffuse='.8 .8 .8',castshadow='false')
    # Large physical board. The reachable drawing strip is 300 x 60 mm.
    add(world,'geom',name='board_frame',type='box',pos='0 -.445 .14',size='.255 .007 .11',rgba='.22 .31 .28 1',contype=1,conaffinity=3,group=0)
    add(world,'geom',name='board_face',type='box',pos='0 -.4365 .14',size='.24 .0015 .10',rgba='.97 .98 .96 1',contype=1,conaffinity=3,group=0)
    for x in [-.23,.23]:
        add(world,'geom',type='box',pos=f'{x} -.45 .023',size='.01 .02 .025',rgba='.22 .31 .28 1',contype=1,conaffinity=3)
    add(world,'geom',name='table_top',type='box',pos='-.36 -.26 .055',size='.080 .050 .004',rgba='.52 .36 .21 1',contype=1,conaffinity=3)
    for x in [-.425,-.295]:
        for y in [-.3]:add(world,'geom',name=f'table_back_leg_{x}',type='box',pos=f'{x} {y} .025',size='.006 .006 .029',rgba='.18 .24 .27 1',contype=1,conaffinity=3)
    add(world,'geom',name='table_rear_foot',type='box',pos='-.36 -.30 .003',size='.078 .023 .004',rgba='.18 .24 .27 1',contype=1,conaffinity=3)
    head=root.find(".//body[@name='head_yaw']")
    for side,x in [('left',.006775),('right',-.006775)]:
        add(head,'camera',name=f'{side}_eye',pos=f'{x} -.0073 .02267',xyaxes='-1 0 0 0 -.422618 .906308',fovy='120')
    hand=root.find(".//body[@name='right_wrist_roll']")
    add(hand,'site',name='right_grasp',pos='0 0 -.012',size='.001',group=4)
    add(hand,'site',name='grasp_axis',pos='0 0 -.014',size='.0005',group=4)
    eq=add(root,'equality')
    contact=root.find('contact')
    if contact is None:contact=add(root,'contact')
    homes={}
    for i,(color,rgba) in enumerate(PALETTE.items()):
        x=-.408+i*.032;y=-.225;z=.077
        homes[color]=[x,y,z+.012]
        # Three narrow rails form an open stand; a marker can leave vertically.
        for dx,dy in [(-.004,0),(.004,0),(0,-.004)]:
            add(world,'geom',name=f'{color}_stand_{dx}_{dy}',type='box',pos=f'{x+dx} {y+dy} .064',size='.001 .001 .005',rgba='.28 .34 .32 1',contype=1,conaffinity=3)
        b=add(world,'body',name='marker_'+color,pos=f'{x} {y} {z}')
        add(b,'freejoint',name='marker_'+color+'_free')
        add(b,'geom',name='marker_'+color+'_barrel',type='cylinder',size='.0022 .016',mass='.0018',rgba=rgba,contype=1,conaffinity=3,friction='1.2 .01 .0001')
        add(b,'geom',name='marker_'+color+'_nib',type='sphere',pos='0 0 -.017',size='.00075',mass='.0001',rgba=rgba,contype=1,conaffinity=3)
        add(b,'site',name='marker_'+color+'_tip',pos='0 0 -.01775',size='.0006',group=4)
        add(b,'site',name='marker_'+color+'_grip',pos='0 0 .012',size='.0005',group=4)
        add(eq,'weld',name='grasp_'+color,body1='right_wrist_roll',body2='marker_'+color,active='false',solref='.002 1')
        add(contact,'pair',geom1='marker_'+color+'_nib',geom2='board_face',condim=3,friction='.2 .2 .00001 .000001 .000001')
        add(eq,'weld',name='dock_'+color,body1='world',body2='marker_'+color,active='true',solref='.006 1')
    # Better lateral slip for the wheel-contact track approximation.
    for geom in root.findall('.//geom'):
        if '_collision_' in geom.get('name','') and any(k in geom.get('name','') for k in ('drive','idler')):
            geom.set('priority','1');geom.set('condim','3')
            if 'drive' in geom.get('name',''):
                geom.set('type','sphere');geom.set('size',geom.get('size').split()[0]);geom.set('friction','.7 .00001 .000001')
            else:geom.set('friction','.005 .000001 .000001')
    for joint in root.findall('.//joint'):
        if any(k in joint.get('name','') for k in ('drive','idler','return')):
            joint.set('damping','.000005')
    cam=world.find("camera[@name='overview']")
    cam.set('pos','.67 .48 .60');cam.set('xyaxes','-.649 .761 0 -.319 -.272 .907')
    E.indent(root,space='  ');tree.write(ROOT/'simulation/workshop.xml',encoding='unicode',xml_declaration=True)
    (ROOT/'simulation/workshop_layout.json').write_text(json.dumps(dict(board_y=-.435,drawing_origin=[.15,-.4353,.105],drawing_x_direction=-1,drawing_size=[.30,.06],marker_homes=homes,marker_length_m=.0355),indent=2))
    print('Workshop scene written')
if __name__=='__main__':build()
