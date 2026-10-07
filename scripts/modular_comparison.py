"""Compose a height-aligned comparison from the reference and actual CAD render."""
from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'print/modular/qa'
font='/System/Library/Fonts/Supplemental/Arial.ttf'
f=lambda n:ImageFont.truetype(font,n)
canvas=Image.new('RGB',(1350,1060),'#f4f2ed');d=ImageDraw.Draw(canvas)
d.text((46,30),'XTI-30 | Drawing and revised print',font=f(35),fill='#1c2b3a')
d.text((46,79),'Robot heights aligned for comparison. Perspective and hand-drawn asymmetry remain.',font=f(19),fill='#495564')
# Manual extent landmarks on the supplied 1627 x 1829 drawing, not an image fit score.
source=Image.open(ROOT/'zoomer.png').convert('RGB').crop((80,91,1290,1628));source.thumbnail((610,780));canvas.paste(source,(46+(610-source.width)//2,160))
render=Image.open(OUT/'front.png').convert('RGBA');render=render.crop(render.getbbox());render.thumbnail((610,780));canvas.paste(render,(710+(610-render.width)//2,160),render)
d.text((46,121),'Original drawing',font=f(24),fill='#1c2b3a');d.text((710,121),'Revised printable geometry',font=f(24),fill='#1c2b3a')
d.line((46,964,1303,964),fill='#b9c0c5',width=2)
d.text((46,981),'180 mm tall  /  140.6 mm wide  /  12 printed parts  /  3 movable joints  /  no metal',font=f(22),fill='#1c2b3a')
d.text((46,1020),'The clear-shell rendering is illustrative. An FDM PETG dome will be translucent.',font=f(18),fill='#495564')
canvas.save(OUT/'drawing_comparison.png')
landmarks={'method':'Manual image landmarks, normalized to 180 mm from crown y=91 to tread bottom y=1628. Approximate; the drawing is not orthographic.','source_image_pixels':[1627,1829],'landmarks_pixels':{'crown_y':91,'tread_bottom_y':1628,'shoulder_left_x':90,'shoulder_right_x':1288,'torso_top_y':385,'torso_lower_wing_y':1075,'central_underside_y':865,'base_deck_y':1270,'dome_left_x':408,'dome_right_x':910},'nominal_model_mm':{'height':180,'overall_width':140.6,'torso_height':80,'torso_width':84,'dome_width':59,'exposed_waist_height':48},'interpretation':'The broad silhouette, chest cutout, gauge arrangement and hand height are close. Symmetry, inferred depth, fixed pincer shape, blue-for-purple palette and the stepped base are deliberate manufacturing simplifications.'}
(OUT/'reference_landmarks.json').write_text(json.dumps(landmarks,indent=2))
