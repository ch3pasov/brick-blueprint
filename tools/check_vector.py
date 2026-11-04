from pathlib import Path
import sys,subprocess,json,re,math,xml.etree.ElementTree as E,tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from brick_blueprint.native import build
exe=build(Path(__file__).resolve().parents[1]/'.brickblueprint-cache')['vector']
NS='{http://www.w3.org/2000/svg}';XL='{http://www.w3.org/1999/xlink}href'
with tempfile.TemporaryDirectory() as temp:
 T=Path(temp)
 def quad(owner,z,rgb,a=1,x0=2,y0=2,x1=14,y1=14):
  p=[(x0,y0,z(x0,y0)),(x1,y0,z(x1,y0)),(x1,y1,z(x1,y1)),(x0,y1,z(x0,y1))];return[(owner,rgb,a,[p[i]for i in ids])for ids in[(0,1,2),(0,2,3)]]
 def run(name,faces,lines=[]):
  rows=['32 32 212 237 252 '+str(len(faces))]
  for id,c,a,ps in faces:rows.append(' '.join(map(str,[id,*c,a,*(v for p in ps for v in(p[0]*2,p[1]*2,p[2]))])))
  rows.append(str(len(lines))+' 2.4')
  for id,c,a,b in lines:rows.append(' '.join(map(str,[id,*c,a[0]*2,a[1]*2,a[2],b[0]*2,b[1]*2,b[2]])))
  s=T/(name+'.scene');s.write_text('\n'.join(rows)+'\n');out=T/(name+'.svg');subprocess.run([str(exe),str(s),str(out)],check=True,capture_output=True);return E.parse(out).getroot()
 def rgb(v):return[int(v[i:i+2],16)for i in(1,3,5)]
 def point(d,x,y):
  polys=[];p=[]
  for m in re.finditer(r'([MLZ])([^MLZ]*)',d):
   c,v=m.groups()
   if c=='Z':polys.append(p);p=[]
   else:p.append(tuple(map(float,v.split(','))))
  for p in polys:
   if len(p)<3:continue
   if all((p[(i+1)%len(p)][0]-a[0])*(y-a[1])-(p[(i+1)%len(p)][1]-a[1])*(x-a[0])>=-1e-7 for i,a in enumerate(p)):return True
  return False
 
 def sample(root,x,y):
  col=[212.,237.,252.];defs={p.attrib['id']:p.attrib['d']for p in root.findall(NS+'defs/'+NS+'path')}
  def paint(c,a):
   nonlocal col
   col=[a*v+(1-a)*u for v,u in zip(c,col)]
  for g in root:
   if g.tag!=NS+'g':continue
   id=g.attrib.get('id')
   if id in ['opaque-visible-faces','depth-composited-ink']:
    for p in g:
     if point(p.attrib['d'],x,y):paint(rgb(p.attrib['fill']),1)
   elif id=='ordered-glass-cells':
    for group in g:
     for p in group:
      if point(defs[p.attrib[XL][1:]],x,y):paint(rgb(p.attrib['fill']),float(p.attrib['fill-opacity']))
   elif id in ['depth-clipped-ink','original-endpoint-round-ink']:
    radius=float(g.attrib['stroke-width'])/2;roundcap=g.attrib['stroke-linecap']=='round'
    for p in g:
     for m in re.finditer(r'M([^MLZ]+)L([^MLZ]+)',p.attrib['d']):
      a,b=[tuple(map(float,v.split(',')))for v in m.groups()];dx,dy=b[0]-a[0],b[1]-a[1];ll=dx*dx+dy*dy;t=((x-a[0])*dx+(y-a[1])*dy)/ll if ll else 0
      if not roundcap and not 0<=t<=1:continue
      t=max(0,min(1,t));dist=math.hypot(x-a[0]-t*dx,y-a[1]-t*dy)
      if dist<=radius:paint(rgb(p.attrib['stroke']),1);break
   elif id=='original-endpoint-caps':
    for p in g:
     if math.hypot(x-float(p.attrib['cx']),y-float(p.attrib['cy']))<=float(p.attrib['r']):paint(rgb(p.attrib['fill']),1)
  return col
 rows=[]
 def check(name,r,pts):
  for p,expected in pts:
   actual=sample(r,*p);assert max(abs(a-b)for a,b in zip(actual,expected))<=.51,(name,p,actual,expected)
  rows.append({'case':name,'samples':len(pts),'passed':True})
 red=[220,0,0];blue=[0,20,230];green=[20,190,20]
 r=run('opaque-depth-crossing',quad(0,lambda x,y:x,red)+quad(1,lambda x,y:16-x,blue));check('crossing opaque planes',r,[((5.3,7.2),blue),((11.2,7.2),red)])
 faces=quad(0,lambda x,y:x,red)+quad(1,lambda x,y:y,blue)+quad(2,lambda x,y:20-x-y,green);r=run('three-opaque-planes',faces);pts=[]
 for x,y in[(3.2,4.3),(8.7,3.4),(4.1,10.2),(10.1,8.3),(6.2,6.7)]:pts.append(((x,y),[red,blue,green][max(range(3),key=lambda i:[x,y,20-x-y][i])]))
 check('three-way opaque depth',r,pts)
 r=run('hidden-same-owner',quad(0,lambda x,y:12,[180]*3),[(0,[0]*3,(3,8,10),(13,8,10))]);check('same-owner rear edge hidden',r,[((7.2,8),[180]*3)])
 r=run('partial-line',quad(1,lambda x,y:20,red,x0=8),[(0,[0]*3,(3,8,10),(13,8,10))]);check('partial edge clipped',r,[((6.8,8),[0]*3),((8.1,8),red),((10.2,8),red)]);caps=r.find(NS+'g[@id="original-endpoint-caps"]');assert all(abs(float(p.attrib['cx'])-8)>.1 for p in caps);rows.append({'case':'no round cap at generated occlusion cut','passed':True})
 r=run('self-slope',quad(0,lambda x,y:2*y,[200]*3),[(0,[0]*3,(3,8.1,16.2),(13,8.1,16.2))]);check('sloped own surface edge visible',r,[((7.2,8.1),[0]*3)])
 r=run('wall005',quad(1,lambda x,y:16.25,[180]*3),[(0,[0]*3,(3,8.1,16.2),(13,8.1,16.2))]);check('wall+.05 occludes edge',r,[((7.2,8.1),[180]*3)])
 base=[150]*3;clear=[252]*3;yellow=[245,205,47];a=.45
 def blend(c,v,alpha):return[q*alpha+p*(1-alpha)for p,q in zip(c,v)]
 faces=quad(0,lambda x,y:0,base)+quad(1,lambda x,y:3,clear,a)+quad(2,lambda x,y:4,yellow,a)
 r=run('glass-stack',faces);expected=blend(blend(base,clear,a),yellow,a);check('two real glass layers',r,[((7.2,8.3),expected)])
 rr=run('glass-stack-reversed',list(reversed(faces)));check('record order invariant',rr,[((7.2,8.3),expected)])
 faces=quad(0,lambda x,y:0,base)+quad(1,lambda x,y:x,clear,a)+quad(2,lambda x,y:16-x,yellow,a);r=run('glass-crossing',faces);check('crossing glass order changes at x8',r,[((5.2,7.3),expected),((11.2,7.3),blend(blend(base,yellow,a),clear,a))])
 r=run('glass-ink',quad(0,lambda x,y:0,base)+quad(1,lambda x,y:3,clear,a)+quad(2,lambda x,y:4,yellow,a),[(3,[0]*3,(3,8.1,1),(13,8.1,1))]);ink=blend(blend([0]*3,clear,a),yellow,a);check('ink transported through real foreground glass',r,[((7.2,8.1),ink)])
 r=run('joint-round',[],[(0,[0]*3,(3,8,10),(8,8,10)),(0,[0]*3,(8,8,10),(11,4,10))]);check('round original join fills wedge',r,[((8.2,8.2),[0]*3)])
 # Regression: a physical transparent owner is one alpha layer, not front+back layers.
 faces=quad(0,lambda x,y:0,base)+quad(1,lambda x,y:3,clear,a)+quad(1,lambda x,y:4,clear,a)
 r=run('same-owner-two-surfaces',faces);once=blend(base,clear,a);check('same transparent owner alpha applied once',r,[((7.2,8.3),once)])
 rr=run('same-owner-reordered',list(reversed(faces)));check('object shell independent of face record order',rr,[((7.2,8.3),once)])
 r=run('own-rear-line',faces,[(1,[0]*3,(3,8.1,3.5),(13,8.1,3.5))]);check('transparent owner rear/internal edge hidden by front shell',r,[((7.2,8.1),once)])
 r=run('behind-other-owner-line',faces,[(2,[0]*3,(3,8.1,1),(13,8.1,1))]);check('unrelated content behind glass preserved with same alpha',r,[((7.2,8.1),blend([0]*3,clear,a))])
 r=run('ink-crossing-depth',[],[(1,[0,0,0],(8,3,12),(8,13,12)),(2,[0,20,230],(3,8,10),(13,8,10))]);check('crossing ink sorted by depth rather than RGB',r,[((8,8),[0,0,0])])
 assert not any(el.tag in [NS+"image",NS+"foreignObject"] for el in r.iter())
 print(json.dumps({"all_passed":True,"cases":len(rows),"rows":rows}))
