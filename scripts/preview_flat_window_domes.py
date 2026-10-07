"""Create comparison and assembly cards from the checked construction renders."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
OUT=Path(__file__).resolve().parents[1]/'print/flat_window_domes'
BG='#f3f4f2';INK='#193747';MUTED='#526770'
def font(n):return ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',n)
def card(title,subtitle):
    im=Image.new('RGB',(1500,1030),BG);d=ImageDraw.Draw(im)
    d.text((40,27),title,font=font(34),fill=INK)
    d.text((40,78),subtitle,font=font(21),fill=MUTED)
    return im,d
def paste(im,file,x):
    p=Image.open(OUT/'qa'/file).convert('RGBA');p.thumbnail((705,745))
    im.paste(p,(x+(705-p.width)//2,134),p)
im,d=card('Two flat viewing covers','Both fit the existing head. Construction colors and faint sheet do not predict optical clarity.')
paste(im,'faceted_head.png',20);paste(im,'sheet_window_head.png',775)
d.text((170,860),'Fully printed faceted cover',font=font(28),fill=INK)
d.text((855,860),'Hood with a clear-sheet window',font=font(28),fill=INK)
d.text((117,912),'Single 0.60 mm vase wall; flat front panel.',font=font(23),fill=MUTED)
d.text((846,912),'Flat 0.50 mm PETG sheet; normal-printed frame.',font=font(22),fill=MUTED)
d.text((40,980),'0.25 mm layers throughout. New cap and mounting adapter fit either version.',font=font(23),fill=INK)
im.save(OUT/'designs.png')
im,d=card('How the covers assemble','Blue: printed body   |   Amber: cap and retainer   |   Green: adapter   |   Faint blue: clear sheet')
paste(im,'faceted_cutaway.png',20);paste(im,'sheet_window_exploded.png',775)
d.text((170,860),'Faceted shell, front half removed',font=font(26),fill=INK)
d.text((905,860),'Sheet version, exploded',font=font(26),fill=INK)
d.text((91,912),'Bond the body to the adapter after checking its fit.',font=font(21),fill=MUTED)
d.text((848,912),'Load the sheet from the front, then add the retainer.',font=font(21),fill=MUTED)
d.text((40,980),'The sheet is a cut part. The test tube and faceted shell are the only vase-mode prints.',font=font(22),fill=INK)
im.save(OUT/'assembly.png')
