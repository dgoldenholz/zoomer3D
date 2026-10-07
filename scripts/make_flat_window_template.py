"""Create a 1:1 sheet cutting template using the checked CAD outline."""
from pathlib import Path
import json
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import letter

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'print/flat_window_domes'
g=json.loads((OUT/'qa/geometry.json').read_text())
points=g['sheet_outline_x_v_mm'];v0=min(p[1] for p in points)
wb,wt,h=g['sheet_dimensions_mm']
pdf=OUT/'templates/clear_sheet_cutting_template.pdf'
c=canvas.Canvas(str(pdf),pagesize=letter,pageCompression=1)
c.setTitle('Zoomer flat window - full-size cutting template')
c.setAuthor('Zoomer3D')
ink=HexColor('#193747');gray=HexColor('#526670');blue=HexColor('#267894')
def text(x,y,s,size=10,color=ink):
    c.setFillColor(color);c.setFont('Helvetica',size);c.drawString(x,y,s)
def line(x1,y1,x2,y2,color=gray,width=.55):
    c.setStrokeColor(color);c.setLineWidth(width);c.line(x1,y1,x2,y2)
text(42,746,'Zoomer clear-sheet window',23)
text(42,719,'Full-size cutting template | 0.50 mm clear PETG sheet',12,gray)
text(42,687,'Print at 100% or Actual size. Turn off Fit, Shrink and Scale to fit.',11)
text(42,669,'Measure the 50 mm box below before cutting the sheet.',11)

c.setFillColor(HexColor('#f2f5f4'));c.roundRect(42,406,528,230,10,fill=1,stroke=0)
text(62,609,'Cut on the black outline',13)
ox=193;oy=468
c.setStrokeColor(HexColor('#000000'));c.setLineWidth(.5)
p=c.beginPath()
for i,(x,v) in enumerate(points):
    if i==0:p.moveTo(ox+x*mm,oy+(v-v0)*mm)
    else:p.lineTo(ox+x*mm,oy+(v-v0)*mm)
p.close();c.drawPath(p,stroke=1,fill=0)
for x in [ox-wt*mm/2,ox+wt*mm/2]:line(x,oy+h*mm+3,x,oy+h*mm+22)
line(ox-wt*mm/2,oy+h*mm+17,ox+wt*mm/2,oy+h*mm+17)
text(ox-27,oy+h*mm+23,f'{wt:.2f} mm',9)
for x in [ox-wb*mm/2,ox+wb*mm/2]:line(x,oy-3,x,oy-22)
line(ox-wb*mm/2,oy-17,ox+wb*mm/2,oy-17)
text(ox-27,oy-32,f'{wb:.2f} mm',9)
xx=ox-wb*mm/2-22
line(xx,oy,xx,oy+h*mm)
line(xx-4,oy,ox-wb*mm/2-3,oy)
line(xx-4,oy+h*mm,ox-wt*mm/2-3,oy+h*mm)
c.saveState();c.translate(xx-7,oy+10);c.rotate(90);text(0,0,f'{h:.2f} mm',9);c.restoreState()
text(331,566,'Narrow edge at the top',12)
for y,s in zip([541,524,507,482,465,448],['Keep the sheet flat.','Do not print this panel in filament.','Leave protective film on while cutting.','Try the fit before applying adhesive.','The rebate allows 0.20 mm per edge.','Trim burrs rather than forcing the fit.']):text(331,y,s,9,gray)

text(42,367,'Scale check',13)
x=62;y=315
c.setStrokeColor(ink);c.setLineWidth(.5);c.rect(x,y,50*mm,10*mm,fill=0,stroke=1)
text(x+35,y+10,'50.00 x 10.00 mm',9)
text(240,335,'Measure between the line centers.',10,gray)
text(240,318,'If the size is wrong, correct printer scaling.',10,gray)

text(42,270,'Optional target for the flat-wall test',13)
text(42,248,'Place the target inside the test tube and view it through one wall only.',10,gray)
text(42,232,'Compare it with the uncovered target at the same distance.',10,gray)
c.setFillColor(HexColor('#ffffff'));c.setStrokeColor(ink);c.rect(63,137,116,71,fill=1,stroke=1)
c.setFillColor(HexColor('#000000'));c.circle(97,187,4.5,fill=1,stroke=0);c.circle(145,187,4.5,fill=1,stroke=0)
text(81,162,'XTI-30',17,HexColor('#000000'))
for i in range(18):
    if i%2==0:c.setFillColor(HexColor('#000000'));c.rect(76+i*5,145,5,5,fill=1,stroke=0)
text(240,185,'The tube is an optical test, not a mounting part.',10,gray)
text(240,167,'A flat printed wall can still show layer ripples.',10,gray)
text(240,149,'The sheet version removes those printed ridges.',10,gray)
line(42,95,570,95,color=HexColor('#c7d2d4'))
text(42,76,'Use with 04_XL_sheet_hood_and_retainer_NORMAL.3mf and the shared cap/adapter.',9,gray)
text(42,59,'Geometry checked; this revision has not been physically printed.  |  2026-10-02',9,gray)
c.showPage();c.save()

# A minimal metric SVG is also provided for vector workflows.
coords=' '.join(f'{x+wb/2+5:.8f},{h-(v-v0)+5:.8f}' for x,v in points)
(OUT/'templates/clear_sheet_outline.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{wb+10:.8f}mm" height="{h+10:.8f}mm" viewBox="0 0 {wb+10:.8f} {h+10:.8f}"><title>0.5 mm clear PETG sheet cut outline</title><polygon points="{coords}" fill="none" stroke="black" stroke-width="0.08"/></svg>\n')
print(pdf)
