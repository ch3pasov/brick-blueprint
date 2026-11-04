"""Draw original FAQ diagrams from public measurements. No official artwork.
Python standard library; optional Pillow preview with --preview-dir.
"""
from pathlib import Path
import json,math,html,argparse
R=Path(__file__).resolve().parents[1];O=R/'docs/images';ops=[]
def text(x,y,s,n=18,c='#173342'):ops.append(('text',(x,y),s,n,c))
def line(p,c='#173342',w=2):ops.append(('line',p,c,w))
def rect(x,y,w,h,c,stroke='none',sw=1):ops.append(('rect',(x,y,w,h),c,stroke,sw))
def dot(x,y,r,c):ops.append(('dot',(x,y,r),c))
def poly(p,c):ops.append(('poly',p,c))
def start(title,subtitle,h=500):
 global ops,H;H=h;ops=[];rect(0,0,1080,H,'#f5f9fc');text(28,40,title,27);text(28,70,subtitle,16,'#526b78')
def save(name):
 a=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="{H}" viewBox="0 0 1080 {H}">',f'<title>{html.escape(name)}</title>']
 for op in ops:
  k=op[0]
  if k=='text':
   _,(x,y),s,n,c=op;a.append(f'<text x="{x}" y="{y}" font-family="Arial, Helvetica, sans-serif" font-size="{n}" fill="{c}">{html.escape(s)}</text>')
  elif k=='rect':
   _,(x,y,w,h),c,st,sw=op;a.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{c}" stroke="{st}" stroke-width="{sw}"/>')
  elif k=='dot':
   _,(x,y,r),c=op;a.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{c}"/>')
  else:
   pts=' '.join(f'{x:.3f},{y:.3f}' for x,y in op[1]);a.append(f'<polyline points="{pts}" fill="none" stroke="{op[2]}" stroke-width="{op[3]}"/>' if k=='line' else f'<polygon points="{pts}" fill="{op[2]}"/>')
 (O/(name+'.svg')).write_text('\n'.join(a+['</svg>'])+'\n')
 if args.preview_dir:
  from PIL import Image,ImageDraw,ImageFont
  im=Image.new('RGB',(1080,H));d=ImageDraw.Draw(im)
  for op in ops:
   k=op[0]
   if k=='text':
    _,(x,y),s,n,c=op;d.text((x,y-n*.85),s,font=ImageFont.truetype(args.font,n),fill=c)
   elif k=='rect':
    _,(x,y,w,h),c,st,sw=op;d.rectangle((x,y,x+w,y+h),fill=c,outline=None if st=='none' else st,width=max(1,round(sw)))
   elif k=='dot':
    _,(x,y,r),c=op;d.ellipse((x-r,y-r,x+r,y+r),fill=c)
   elif k=='line':d.line(op[1],fill=op[2],width=round(op[3]))
   else:d.polygon(op[1],fill=op[2])
  p=Path(args.preview_dir);p.mkdir(parents=True,exist_ok=True);im.save(p/(name+'.png'))
ap=argparse.ArgumentParser();ap.add_argument('--preview-dir');ap.add_argument('--font',default='/System/Library/Fonts/Helvetica.ttc');args=ap.parse_args()
start('Isometric is one special camera, not a synonym for 3D','Original cube diagrams. The perspective example is exaggerated for explanation.')
for i,(az,el,dist,title) in enumerate([(45,math.degrees(math.asin(1/math.sqrt(3))),None,'Isometric'),(35,35,None,'Other orthographic'),(35,35,5,'Perspective')]):
 cx=190+i*350;cy=275;a,e=map(math.radians,(az,el))
 def p(x,y,z):
  sx=-math.sin(a)*x+math.cos(a)*y;sy=-math.sin(e)*(math.cos(a)*x+math.sin(a)*y)+math.cos(e)*z;depth=math.cos(e)*(math.cos(a)*x+math.sin(a)*y)+math.sin(e)*z
  f=1 if dist is None else dist/(dist-depth)
  return (cx+sx*66*f,cy-sy*66*f)
 for face,col in [([(1,-1,-1),(1,1,-1),(1,1,1),(1,-1,1)],'#8bb9d8'),([(-1,1,-1),(1,1,-1),(1,1,1),(-1,1,1)],'#b7d7f3'),([(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)],'#d4edfc')]:
  q=[p(*v) for v in face];poly(q,col);line(q+[q[0]])
 for t in [-.5,0,.5]:line([p(t,-1,1),p(t,1,1)],'#507a91',1);line([p(-1,t,1),p(1,t,1)],'#507a91',1)
 text(cx-130,115,title,23);text(cx-130,410,f'Azimuth {az} / elevation {el:.3f} deg',17);text(cx-130,443,'Parallel axes; equal foreshortening' if i==0 else ('Parallel axes; unequal foreshortening' if i==1 else 'Depth changes scale; lines converge'),15)
save('faq-projections')
start('Perspective evidence: predict unseen stud centers','Held-out RMS in original image pixels. Lower is better; thresholds are a sensitivity check.',560)
for col,(file,title,main) in enumerate([('LARGE-GRID-MEASUREMENTS.json','21062 / PDF p20 / foundation',80),('INVENTORY-GRID-CONTROL.json','75375 / PDF p60 / parts tray',140)]):
 data=json.loads((R/'docs'/file).read_text());x=30+col*535;text(x,112,title,21)
 for j,r in enumerate(data['threshold_results']):
  fits=r['fits'].get('whole_grid',r['fits']);y=165+j*100;text(x,y-5,f'Threshold {r["threshold"]}',16)
  for k,(kind,color) in enumerate([('affine','#567a95'),('projective','#00897e')]):
   v=fits[kind]['held_out_rms_original_pixels'];rect(x+120,y-22+k*30,v*290,20,color);text(x+130+v*290,y-5+k*30,f'{v:.3f}',15)
 text(x,480,'Strong, stable projective advantage' if col==0 else 'Weak, threshold-sensitive advantage',18)
rect(30,514,18,16,'#567a95');text(58,528,'Affine / parallel projection',16);rect(340,514,18,16,'#00897e');text(368,528,'Projective / perspective-compatible',16)
save('faq-perspective-evidence')
start('Camera angles: a useful estimate, not a universal specification','31376 / PDF p16 parts tray: conditional orthographic estimate from the stud grid.',500)
# top view
text(40,120,'TOP VIEW / azimuth',21);cx,cy=190,290
line([(80,cy),(340,cy)],'#8ca7b5');line([(cx,380),(cx,165)],'#8ca7b5');a=math.radians(35);q=(cx+135*math.cos(a),cy-135*math.sin(a));line([(cx,cy),q],'#00897e',4);dot(*q,7,'#00897e');text(220,325,'~35 deg',22);text(45,420,'Acute grid-axis class; axis naming matters.',17)
text(570,120,'SIDE VIEW / elevation',21);cx,cy=650,310;line([(570,cy),(1015,cy)],'#8ca7b5');q=(cx+190*math.cos(a),cy-190*math.sin(a));line([(cx,cy),q],'#00897e',4);line([q,(q[0],cy)],'#8ca7b5',1);dot(*q,7,'#00897e');text(720,290,'~35 deg',22);text(575,420,'Elevation is above the horizontal plane.',17)
text(30,472,'Measured: 35.0 / 34.8 deg. Tool default: 35 / 30 deg. Do not confuse the two.',19)
save('faq-camera')
start('The same measured brown on three different backgrounds','Original color swatches, not official part illustrations. Interior face samples only.',420)
for i,(name,bg) in enumerate([('Classic 11038 / p21','#B2D7F3'),('Minecraft 21269 / p27','#D8E6D9'),('Star Wars 75375 / p20','#899093')]):
 x=30+i*350;rect(x,115,320,220,bg);rect(x+80,165,160,115,'#5b2b13');text(x,365,name,18)
text(30,402,'All three face medians: sRGB (91, 43, 19). Whole images differ; backgrounds differ.',18)
save('faq-color')
start('Physical units survive zoom; screenshots do not','Measured source values and renderer normalizations must remain separate.',430)
rect(30,110,480,240,'#B7D7F3','#202021',2);text(55,150,'SOURCE / 31051, 2016',22);text(55,195,'Frame: about 0.5 pt',21);text(55,235,'Inner corner: about 7.09 pt',21);text(55,275,'Quantity: Chalet Bold, 8 pt',21);text(55,320,'Step number: 38 pt',21)
rect(545,110,505,240,'#fff','#9eb6c4');text(570,150,'TOOL / normalized layout',22);text(570,195,'Corner: 7.087 pt / padding: 14.17 pt',21);text(570,235,'Page inset: 12 pt / quantity: 8 pt',21);text(570,275,'Model outline: 0.32 pt (separate)',21);text(570,320,'72 pt = 1 inch = 25.4 mm',21)
text(30,397,'Modern sampled frames: ~0.75 pt; Friends: ~2 pt. These are not model outline widths.',18)
save('faq-units')
