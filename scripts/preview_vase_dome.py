"""Produce an assembly card and dimensioned section from the generated profile."""
import json,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import build_vase_dome as b

OUT=b.OUT
BG='#f3f4f2';INK='#173342';MUTED='#546873'
COL={'viewing_shell':'#3988ae','crown_cap':'#dba14a','mounting_ring':'#4d9564'}
def font(size):return ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',size)
def title(d,heading,sub):
    d.text((40,28),heading,font=font(34),fill=INK)
    d.text((40,79),sub,font=font(21),fill=MUTED)

def section():
    p=json.loads((OUT/'qa/profile.json').read_text())
    im=Image.new('RGB',(1500,950),BG);d=ImageDraw.Draw(im)
    title(d,'Dome section and original profile','Blue: vase shell   |   Amber: cap   |   Green: mounting ring   |   Dashed gray: previous dome')
    scale=14;cx=535;baseline=724
    xy=lambda pt:(cx+pt[0]*scale,baseline-pt[1]*scale)
    # Draw the true solid cap cross section and subtract its two annular slots.
    cap=p['cap']
    d.polygon([xy((-r,z)) for r,z in cap]+[xy((r,z)) for r,z in cap[::-1]],fill=COL['crown_cap'])
    for sign in [-1,1]:
        d.polygon([xy((sign*r,z)) for r,z in p['groove']],fill=BG)
        wall=[xy((sign*r,z)) for r,z in p['window']]+[xy((sign*(r-b.WIDTH),z)) for r,z in p['window'][::-1]]
        d.polygon(wall,fill=COL['viewing_shell'])
        ring=[(27.9,0),(29.5,0),(29.5,.75),(28.64,.75),(28.64,1.75),(27.9,1.75)]
        d.polygon([xy((sign*r,z)) for r,z in ring],fill=COL['mounting_ring'])
    for sign in [-1,1]:
        old=[xy((sign*b.R*math.sqrt(1-(z/b.A)**2),z)) for z in [i*b.A/240 for i in range(241)]]
        for i in range(0,len(old)-2,4):d.line(old[i:i+3],fill='#66767c',width=2)
    eye_y=xy((0,p['head_top']))[1]
    for xx in range(130,940,14):d.line((xx,eye_y,xx+7,eye_y),fill='#85756d',width=2)
    d.text((272,eye_y+13),'Highest eye detail: 26.20 mm',font=font(21),fill=MUTED)
    d.line((120,baseline,950,baseline),fill='#c4cece',width=2)
    d.text((298,baseline+14),'Existing head ledge / original dome base',font=font(21),fill=MUTED)
    d.text((1040,183),'0.25 mm layers',font=font(28),fill=INK)
    entries=[('Viewing shell','0.60 mm extrusion width','27.50 mm print height'),('Crown cap','Groove faces the bed','1.05 mm above the eyes*'),('Mounting ring','59.0 mm outer diameter','55.8 mm hole; 1.75 mm tall')]
    for y,(h,a,c) in zip([260,395,530],entries):
        d.text((1040,y),h,font=font(25),fill=INK)
        d.text((1040,y+40),a,font=font(20),fill=MUTED)
        d.text((1040,y+69),c,font=font(20),fill=MUTED)
    d.text((40,831),'Upper shell widens by up to 1.46 mm radially to limit each inward step to 0.20 mm.',font=font(22),fill=INK)
    d.text((40,873),'*Nominal cap position. Allowing 0.25 mm seating movement leaves 0.80 mm above the eyes.',font=font(21),fill=MUTED)
    im.save(OUT/'section.png')

def assembly():
    im=Image.new('RGB',(1500,1110),BG);d=ImageDraw.Draw(im)
    title(d,'Three-piece vase dome','Construction colors show the parts. PETG transparency is not simulated.')
    for x,key,name in [(45,'viewing_shell','Vase shell'),(530,'crown_cap','Crown cap'),(1000,'mounting_ring','Mounting ring')]:
        d.rounded_rectangle((x,129,x+25,154),radius=5,fill=COL[key]);d.text((x+37,127),name,font=font(22),fill=INK)
    for x,path in [(30,'cutaway.png'),(780,'exploded.png')]:
        pic=Image.open(OUT/'qa'/path).convert('RGBA');pic.thumbnail((690,795))
        im.paste(pic,(x+(690-pic.width)//2,190),pic)
    d.text((190,950),'Assembled, front half removed',font=font(26),fill=INK)
    d.text((920,950),'Exploded assembly',font=font(26),fill=INK)
    d.text((40,1025),'Cap and ring use normal printing. All three parts use 0.25 mm layers and need no supports.',font=font(23),fill=MUTED)
    im.save(OUT/'assembly.png')

if __name__=='__main__':section();assembly()
