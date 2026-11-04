"""Generate original synthetic geometry for tests; no external part data."""
from pathlib import Path
import math
B=Path(__file__).parent/'library'
HEADER='0 Original synthetic rendering fixture\n0 Author: Brick Blueprint project\n0 !LICENSE Project license pending; see docs/LICENSING.md\n0 BFC CERTIFY CCW\n'

def write(name,body):
    path=B/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(HEADER+'\n'.join(body)+'\n')

def row(kind,points,color=16):return str(kind)+' '+str(color)+' '+' '.join(format(v,'.8g') for p in points for v in p)
p=[(-1,-1,-1),(1,-1,-1),(1,-1,1),(-1,-1,1),(-1,1,-1),(1,1,-1),(1,1,1),(-1,1,1)]
faces=[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]
edges=sorted({tuple(sorted((a,b))) for f in faces for a,b in zip(f,f[1:]+f[:1])})
write('parts/unit-box.dat',[row(4,[p[i] for i in f]) for f in faces]+[row(2,[p[a],p[b]],24) for a,b in edges])
body=[];n=24
for i in range(n):
    a,b=2*math.pi*i/n,2*math.pi*(i+1)/n
    p0=(math.cos(a),-1,math.sin(a));p1=(math.cos(b),-1,math.sin(b));p2=(p1[0],1,p1[2]);p3=(p0[0],1,p0[2])
    body += [row(4,[p0,p1,p2,p3]),row(3,[(0,-1,0),p1,p0]),row(3,[(0,1,0),p3,p2]),row(2,[p0,p1],24),row(2,[p2,p3],24)]
write('parts/unit-cylinder.dat',body)
(B/'LDConfig.ldr').write_text('0 Minimal original test palette\n'+ '\n'.join(f'0 !COLOUR {name} CODE {code} VALUE #{value} EDGE #333333'+(' ALPHA 128' if code==47 else '') for code,name,value in [(0,'Dark', '393A3B'),(4,'Red','D42625'),(14,'Yellow','FCE61E'),(15,'White','F4F4F4'),(1,'Blue','2A6DA8'),(2,'Green','2E8D59'),(47,'Glass','FCFCFC')])+'\n')
placements=[]
def part(c,x,y,z,sx,sy,sz,name='unit-box.dat'):
    placements.append(f'1 {c} {x} {y} {z} {sx} 0 0 0 {sy} 0 0 0 {sz} {name}')
part(1,0,0,0,58,4,38);part(15,-20,-16,0,15,12,17);part(4,-20,-36,0,15,8,17);part(15,-20,-56,0,15,12,17)
part(0,-20,-70,0,22,2,22,'unit-cylinder.dat');part(14,-20,-83,0,5,10,5,'unit-cylinder.dat')
part(47,-20,-85,0,17,13,17);part(0,-20,-100,0,23,2,23,'unit-cylinder.dat')
part(4,29,-16,0,19,12,25);part(15,29,-30,0,22,2,28);part(0,29,-34,0,24,2,30)
part(2,30,-16,-25.5,7,10,1);part(47,49,-17,6,1,7,8)
(Path(__file__).parent/'demo.ldr').write_text('0 Original abstract beacon scene; renderer demonstration, not an official set\n'+'\n'.join(placements)+'\n')
