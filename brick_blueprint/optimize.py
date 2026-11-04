from pathlib import Path
import re,xml.etree.ElementTree as E,collections,json,hashlib,gzip,zipfile,io,time,sys
B=Path(__file__).resolve().parent;SOURCE=B/'selected-union.svg';NS='http://www.w3.org/2000/svg';XL='http://www.w3.org/1999/xlink';E.register_namespace('',NS);E.register_namespace('xlink',XL)
SCALE=1000000

def integer(s):
 neg=s.startswith('-');s=s.lstrip('+-');a,_,b=s.partition('.');assert len(b)<=6;v=int(a or'0')*SCALE+int((b+'000000')[:6]);return-v if neg else v

def number(v):
 sign='-'if v<0 else'';v=abs(v);a,b=divmod(v,SCALE);return sign+str(a)+(('.'+str(b).zfill(6).rstrip('0'))if b else'')

def quant(v,q):return((v+q//2)//q)*q if v>=0 else-(((-v+q//2)//q)*q)

def parse(d,q=1):
 for sub in d.split('Z')[:-1]:yield[tuple(quant(integer(v),q)for v in p.split(','))for p in re.findall(r'[ML]([^MLZ]*)',sub)]

def area(p):return sum(a[0]*b[1]-b[0]*a[1]for a,b in zip(p,p[1:]+p[:1]))

def edges(ps):
 c=collections.Counter()
 for p in ps:
  for a,b in zip(p,p[1:]+p[:1]):
   if a==b:continue
   if a<b:c[(a,b)]+=1
   else:c[(b,a)]-=1
 return+c,-c

def simplify(p):
 # Only remove an exactly collinear between-point. Integral projected geometry is unchanged.
 def removable(a,b,c):return(b[0]-a[0])*(c[1]-b[1])==(b[1]-a[1])*(c[0]-b[0])and(b[0]-a[0])*(c[0]-b[0])+(b[1]-a[1])*(c[1]-b[1])>=0
 out=[]
 for v in p:
  while len(out)>1 and removable(out[-2],out[-1],v):out.pop()
  out.append(v)
 changed=True
 while changed and len(out)>2:
  changed=False
  if removable(out[-1],out[0],out[1]):out.pop(0);changed=True
  if len(out)>2 and removable(out[-2],out[-1],out[0]):out.pop();changed=True
 return out

def merge(ps):
 original_area=sum(area(p)for p in ps);pos,neg=edges(ps);adj=collections.defaultdict(list);degrees=collections.Counter();retained=0
 for (a,b),n in pos.items():adj[a].append([b,n]);degrees[a]+=n;degrees[b]-=n;retained+=n
 for (a,b),n in neg.items():adj[b].append([a,n]);degrees[b]+=n;degrees[a]-=n;retained+=n
 assert not any(degrees.values()),'unbalanced exact contour graph'
 loops=[]
 for start in list(adj):
  if not adj[start]:continue
  stack=[start];tour=[]
  while stack:
   v=stack[-1]
   if adj[v]:
    item=adj[v][-1];nxt=item[0];item[1]-=1
    if item[1]==0:adj[v].pop()
    stack.append(nxt)
   else:tour.append(stack.pop())
  tour=tour[::-1];assert tour[0]==tour[-1];loops.append(tour[:-1])
 # Winding is determined by the oriented boundary multiset: assert exact equality before simplification.
 assert edges(loops)==(pos,neg)
 loops=[simplify(p)for p in loops];loops=[p for p in loops if len(p)>2 and not all((v[0]-p[0][0])*(p[1][1]-p[0][1])==(v[1]-p[0][1])*(p[1][0]-p[0][0])for v in p[2:])]
 assert sum(area(p)for p in loops)==original_area
 return loops,retained

def encode(ps):return''.join('M'+number(p[0][0])+','+number(p[0][1])+''.join('L'+number(x)+','+number(y)for x,y in p[1:])+'Z'for p in ps)

def optimize(tag,q,source=None,output_dir=None):
 B=Path(output_dir) if output_dir is not None else Path(__file__).resolve().parent
 SOURCE=Path(source) if source is not None else B/"selected-union.svg"
 started=time.perf_counter();root=E.fromstring(SOURCE.read_bytes());stats=collections.Counter();source_geometry=[];out_geometry=[]
 for node in root.iter():
  if node.tag=='{'+NS+'}path':
   d=node.attrib['d']
   if d.endswith('Z'):
    ps=list(parse(d,q));stats['input_polygons']+=len(ps);stats['input_vertices']+=sum(map(len,ps));old=d
    clean=[]
    for p in ps:
     unique=[]
     for v in p:
      if not unique or unique[-1]!=v:unique.append(v)
     if len(unique)>1 and unique[0]==unique[-1]:unique.pop()
     # A zero-area polygon is dropped only when every point is exactly collinear.
     if len(unique)<3 or all((v[0]-unique[0][0])*(unique[1][1]-unique[0][1])==(v[1]-unique[0][1])*(unique[1][0]-unique[0][0])for v in unique[2:]):stats['collinear_empty_subpaths_removed']+=1;continue
     clean.append(unique)
    loops,retained=merge(clean);node.attrib['d']=encode(loops);stats['output_polygons']+=len(loops);stats['output_vertices']+=sum(map(len,loops));stats['exact_oriented_edges_retained']+=retained;stats['fill_paths_exact_boundary_checks']+=1
   else:
    # Preserve stroke structure/caps, only canonicalise decimal coordinate spelling (or quantise for explicit approximation).
    node.attrib['d']=re.sub(r'[-+]?\d+\.\d+',lambda m:number(quant(integer(m[0]),q)),d)
  elif node.tag=='{'+NS+'}circle':
   for k in ['cx','cy','r']:node.attrib[k]=number(quant(integer(node.attrib[k]),q))
  if node.text is not None and not node.text.strip():node.text=None
  node.tail=None
 out=B/(tag+'.svg');data=E.tostring(root,encoding='utf-8',short_empty_elements=True);out.write_bytes(data)
 z=B/(tag+'.zip')
 with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED,compresslevel=9)as f:f.writestr(out.name,data)
 gz=gzip.compress(data,compresslevel=9,mtime=0);(B/(tag+'.svg.gz')).write_bytes(gz)
 r={'tag':tag,'coordinate_quantum_px':q/SCALE,'maximum_coordinate_axis_change_px':0 if q==1 else q/SCALE/2,'classification':'lossless serialized coordinate geometry / exact winding preservation'if q==1 else'approximate coordinate quantisation, then exact winding-preserving compaction on quantised geometry','SVG_bytes':len(data),'ZIP_bytes':z.stat().st_size,'gzip_bytes':len(gz),'SVG_sha256':hashlib.sha256(data).hexdigest(),'optimization_seconds':time.perf_counter()-started,**stats};(B/(tag+'.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
if __name__=='__main__':
 for tag,q in [('post-q3',1000)]:optimize(tag,q)
