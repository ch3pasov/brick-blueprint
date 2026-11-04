"""Original schematic legend; no official image, font program or CAD geometry.

Writes an SVG using Python's standard library. Optional --preview requires Pillow
and a locally supplied TrueType font; it is a visual QA aid, not a library dependency.
"""
from pathlib import Path
import argparse, math, html

ROOT=Path(__file__).resolve().parents[1]
W,H=1040,590
ops=[]
def rect(x,y,w,h,fill,stroke='none',width=1):ops.append(('rect',(x,y,w,h),fill,stroke,width))
def line(points,color='#182D36',width=2):ops.append(('line',points,color,width))
def poly(points,fill,stroke='none',width=1):ops.append(('poly',points,fill,stroke,width))
def circle(x,y,r,fill,stroke='#182D36',width=2):ops.append(('circle',(x,y,r),fill,stroke,width))
def text(x,y,s,size=16,color='#182D36',bold=False):ops.append(('text',(x,y),s,size,color,bold))
def arrow(points,color='#182D36',width=3,head=10):
    line(points,color,width);a,b=points[-2:];dx,dy=b[0]-a[0],b[1]-a[1];n=math.hypot(dx,dy);dx/=n;dy/=n
    poly([b,(b[0]-head*dx+head*.45*dy,b[1]-head*dy-head*.45*dx),(b[0]-head*dx-head*.45*dy,b[1]-head*dy+head*.45*dx)],color)
def arc(cx,cy,r,start,end,color):
    points=[(cx+r*math.cos(math.radians(t)),cy+r*math.sin(math.radians(t))) for t in [start+(end-start)*i/40 for i in range(41)]]
    arrow(points,color,5,12)

rect(0,0,W,H,'#D4EDFC');text(28,42,'Instruction marks have different jobs',28,bold=True)
text(28,69,'Original schematic specimens. These are a design study, not generated assembly steps.',15)
titles=['Insertion','Destination leader','View rotation','Mechanism motion','Part quantity','Build repetition','Length badge','Print-size reference']
notes=[['Move along a defined axis.','Color is source-specific.'],['Connect inset to location.','The route is not a trajectory.'],['Change the viewing direction.','Do not imply joint motion.'],['Move a hinged mechanism.','Requires a known joint.'],['Count one inventory item.','Preserve physical scale.'],['Repeat the whole sequence.','Scope must be explicit.'],['Identify nominal length.','This is not a quantity.'],['Compare at intended size.','Requires a print-scale check.']]
for i,title in enumerate(titles):
    x=28+(i%4)*252;y=92+(i//4)*230
    rect(x,y,228,212,'#FFFFFF','#B7D7F3',1);text(x+14,y+28,title,17,bold=True)
    cx=x+114;cy=y+98
    if i==0:
        rect(cx-19,cy-41,38,18,'#B7D7F3','#182D36',2);circle(cx,cy+39,17,'#E8F0F4');arrow([(cx,cy-15),(cx,cy+25)],'#D92529')
    elif i==1:
        rect(x+25,y+53,75,37,'#FFF5CB','#182D36',1);circle(x+175,y+137,5,'#B7D7F3');arrow([(x+62,y+90),(x+62,y+119),(x+175,y+119),(x+175,y+130)])
    elif i==2:
        rect(cx-21,cy-16,42,32,'#E8F0F4','#182D36',2);arc(cx,cy,47,-145,140,'#182D36')
    elif i==3:
        circle(cx-30,cy+28,6,'#182D36');line([(cx-30,cy+28),(cx+32,cy+28)],'#182D36',4);line([(cx-30,cy+28),(cx+6,cy-30)],'#A5B6BF',4);arc(cx-30,cy+28,58,-5,-58,'#DCA900')
    elif i==4:
        rect(cx-33,cy-28,66,24,'#B7D7F3','#182D36',2);text(cx-18,cy+35,'4x',32,bold=True)
    elif i==5:
        rect(x+24,y+52,180,92,'#FFF5CB','#182D36',1);text(x+38,y+83,'1',20);text(x+102,y+83,'2',20);arrow([(x+65,y+77),(x+87,y+77)],'#D92529',2,7);text(x+153,y+129,'2x',28,bold=True)
    elif i==6:
        line([(x+26,cy),(x+138,cy)],'#5D6F78',12);circle(x+175,cy,20,'#FFFFFF');text(x+169,cy+7,'4',23)
    else:
        rect(x+25,y+58,178,79,'#E8F0F4','#182D36',1);line([(x+42,cy+15),(x+112,cy+15)])
        for j in range(5):line([(x+42+j*17.5,cy+15),(x+42+j*17.5,cy+6)])
        text(x+133,cy+21,'1:1',26,bold=True)
    for j,s in enumerate(notes[i]):text(x+14,y+174+j*20,s,14)
text(28,572,'Meaning belongs in the scene data; color and line treatment belong in the presentation preset.',15)

def svg():
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', '<title>Eight distinct instruction annotation roles</title>']
    for op in ops:
        kind=op[0]
        if kind=='rect':
            _,(x,y,w,h),fill,stroke,width=op;out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')
        elif kind in ('line','poly'):
            points=' '.join(f'{x:.3f},{y:.3f}' for x,y in op[1])
            if kind=='line':out.append(f'<polyline points="{points}" fill="none" stroke="{op[2]}" stroke-width="{op[3]}" stroke-linejoin="round"/>')
            else:out.append(f'<polygon points="{points}" fill="{op[2]}" stroke="{op[3]}" stroke-width="{op[4]}"/>')
        elif kind=='circle':
            _,(x,y,r),fill,stroke,width=op;out.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')
        else:
            _,(x,y),s,size,color,bold=op;out.append(f'<text x="{x}" y="{y}" font-family="Arial, Helvetica, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}">{html.escape(s)}</text>')
    return '\n'.join(out+['</svg>'])+'\n'

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--preview');ap.add_argument('--font');args=ap.parse_args()
    (ROOT/'docs/images/annotation-roles.svg').write_text(svg())
    if args.preview:
        from PIL import Image,ImageDraw,ImageFont
        if not args.font:ap.error('--preview requires --font')
        im=Image.new('RGB',(W,H),'white');d=ImageDraw.Draw(im)
        for op in ops:
            k=op[0]
            if k=='rect':
                _,(x,y,w,h),fill,stroke,width=op;d.rectangle((x,y,x+w,y+h),fill=fill,outline=None if stroke=='none' else stroke,width=width)
            elif k=='line':d.line(op[1],fill=op[2],width=op[3],joint='curve')
            elif k=='poly':d.polygon(op[1],fill=op[2])
            elif k=='circle':
                _,(x,y,r),fill,stroke,width=op;d.ellipse((x-r,y-r,x+r,y+r),fill=fill,outline=stroke,width=width)
            else:
                _,(x,y),s,size,color,bold=op;f=ImageFont.truetype(args.font,size);d.text((x,y),s,font=f,fill=color,anchor='ls',stroke_width=0)
        Path(args.preview).parent.mkdir(parents=True,exist_ok=True);im.save(args.preview)
