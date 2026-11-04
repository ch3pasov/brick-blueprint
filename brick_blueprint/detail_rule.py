"""Conservative common paper-scale LOD for paired shallow concave annular creases.
No design/file/instance/colour IDs or screen regions select eligibility.
All uncertain incidence, transparency, material boundaries and silhouettes preserve ink.
"""
import math,collections
from .ldraw import mv

def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def norm(a):return math.sqrt(dot(a,a))
def unit(a):return tuple(x/norm(a)for x in a)
PARAMETERS={'minimum_segments':8,'minimum_arc_degrees':180,'max_relative_band_width':.15,'max_band_width_points':1.5,'minimum_crease_degrees':5,'maximum_crease_degrees':50,'coordinate_weld_LDU':.001,'circle_bucket_LDU':.1,'circle_residual_LDU':.0035,'incidence_tolerance_LDU':.002,'preserve_any_transparent_root':True,'preserve_every_conditional_line':True,'preserve_material_boundaries_and_explicit_lines':True,'preserve_silhouette_pairs':True}
def circle(a,p,b):
 u=sub(a,p);v=sub(b,p);n=cross(u,v);nn=dot(n,n)
 if nn<1e-12:return None
 q1=cross(v,n);q2=cross(n,u);c=tuple(p[k]+(dot(u,u)*q1[k]+dot(v,v)*q2[k])/(2*nn)for k in range(3));r=norm(sub(c,p));axis=unit(n)
 if r<1e-5:return None
 for x in axis:
  if abs(x)>1e-6:
   if x<0:axis=tuple(-v for v in axis)
   break
 return c,r,axis

def refit_circle(fit,edge_ids,edges):
 c,r,n=fit;first=edges[next(iter(edge_ids))][0];u=unit(sub(first,c));v=cross(n,u);points=sorted(set(p for li in edge_ids for p in edges[li][:2]));A=[[0.,0.,0.,0.]for _ in range(3)]
 for p in points:
  d=sub(p,c);x,y=dot(d,u),dot(d,v);row=(x,y,1);b=-(x*x+y*y)
  for i in range(3):
   for j in range(3):A[i][j]+=row[i]*row[j]
   A[i][3]+=row[i]*b
 for k in range(3):
  pivot=max(range(k,3),key=lambda j:abs(A[j][k]));A[k],A[pivot]=A[pivot],A[k]
  if abs(A[k][k])<1e-12:return None
  den=A[k][k];A[k]=[x/den for x in A[k]]
  for j in range(3):
   if j==k:continue
   q=A[j][k];A[j]=[x-q*y for x,y in zip(A[j],A[k])]
 a,b,z=[A[k][3]for k in range(3)];cc=tuple(c[k]-a/2*u[k]-b/2*v[k]for k in range(3));rr=a*a/4+b*b/4-z
 return(cc,math.sqrt(rr),n)if rr>0 else None

def incidence(p,t):
 a,b,c=t;u=sub(b,a);v=sub(c,a);n=cross(u,v);nn=dot(n,n)
 if nn<1e-18:return None
 d=dot(sub(p,a),n)
 if abs(d)/math.sqrt(nn)>.002:return None
 q=tuple(p[k]-n[k]*d/nn-a[k]for k in range(3));aa=dot(u,u);bb=dot(u,v);cc=dot(v,v);den=aa*cc-bb*bb
 if den<1e-18:return None
 s=(cc*dot(q,u)-bb*dot(q,v))/den;z=(aa*dot(q,v)-bb*dot(q,u))/den
 if min(s,z,1-s-z)<-.0005:return None
 return unit(n)

def filter_lines(parts,triangles,lines,line_features,direction,points_per_ldu,alpha,*,camera_position=None):
 removed=set();receipts=[];group_receipts=[];stats=collections.Counter();ts=collections.defaultdict(list);ls=collections.defaultdict(list)
 for tri,c,ix,st in triangles:ts[ix].append((tri,c))
 for li,line in enumerate(lines):ls[line[3]].append((li,line))
 for ix,p in enumerate(parts):
  if any(alpha(c)<.999999 for tri,c in ts[ix]):stats['transparent_roots_preserved']+=1;continue
  M=p['matrix'];T=tuple(M[k]for k in[0,3,6,1,4,7,2,5,8]);I=[sum(T[3*r+k]*M[3*k+c]for k in range(3))for r in range(3)for c in range(3)]
  if max(abs(v-(1 if k in[0,4,8]else 0))for k,v in enumerate(I))>1e-8:stats['nonrigid_roots_preserved']+=1;continue
  native=lambda v:mv(T,sub(v,p['xyz']));D=mv(T,direction);detM=M[0]*(M[4]*M[8]-M[5]*M[7])-M[1]*(M[3]*M[8]-M[5]*M[6])+M[2]*(M[3]*M[7]-M[4]*M[6]);nt=[]
  for tri,c in ts[ix]:
   q=tuple(native(v)for v in tri);nt.append(((q[0],q[2],q[1])if detM<0 else q,c))
  edges={};graph=collections.defaultdict(list)
  for li,(pts,c,e,owner,st)in ls[ix]:
   if len(pts)!=2 or not e or line_features[li]['explicit']:continue
   a,b=map(native,pts);ka,kb=[tuple(round(x,3)for x in v)for v in[a,b]]
   if ka==kb:continue
   edges[li]=(a,b,c);graph[ka].append((li,a,b));graph[kb].append((li,b,a))
  buckets=collections.defaultdict(lambda:{'edges':set(),'fits':[]})
  for links in graph.values():
   for i,(a,p0,p1)in enumerate(links):
    for b,q0,q1 in links[i+1:]:
     if edges[a][2]!=edges[b][2]:continue
     fit=circle(p1,p0,q1)
     if fit is None:continue
     c,r,n=fit;key=(*[round(x/.1)for x in c],round(r/.1),*[round(x/.001)for x in n],edges[a][2]);g=buckets[key];g['edges'].update([a,b]);g['fits'].append(fit)
  groups=[]
  for g in buckets.values():
   if len(g['edges'])<8:continue
   fit=refit_circle(g['fits'][0],g['edges'],edges)
   if fit is None:continue
   c,r,n=fit;arc=0;valid=True
   for li in g['edges']:
    a,b,col=edges[li]
    if any(abs(norm(sub(v,c))-r)>.0035 or abs(dot(sub(v,c),n))>.0035 for v in[a,b]):valid=False;break
    arc+=math.acos(max(-1,min(1,dot(unit(sub(a,c)),unit(sub(b,c))))))
   if valid and math.pi-1e-5<=arc<=2*math.pi+1e-4:groups.append({'c':c,'r':r,'n':n,'edges':g['edges'],'colour':edges[next(iter(g['edges']))][2],'arc':math.degrees(arc)})
  group_receipts.append({'root_index':ix,'circles':[{'centre':g['c'],'radius':g['r'],'axis':g['n'],'edges':len(g['edges']),'arc':g['arc']}for g in groups]})
  def profile(g):
   result=[]
   for li in sorted(g['edges']):
    a,b,col=edges[li];mid=tuple((a[k]+b[k])/2 for k in range(3));ns=[]
    for tri,c in nt:
     N=incidence(mid,tri)
     if N is not None:
      if c!=col:return None,'material_boundary'
      ns.append(N)
    if len(ns)<2:return None,'uncertain_incidence'
    flat=[n for n in ns if abs(dot(n,g['n']))>.9999];other=[n for n in ns if abs(dot(n,g['n']))<=.9999]
    if not flat or not other:return None,'not_flat_plus_slope'
    f=flat[0];angles=[math.degrees(math.acos(max(-1,min(1,dot(f,n)))))for n in other]
    if not all(5<=a<=50 for a in angles):return None,'crease_outside_detail_band'
    view=sub(native(camera_position),mid) if camera_position is not None else D
    if min(dot(n,view)for n in ns)<=1e-8 and max(dot(n,view)for n in ns)>=-1e-8:return None,'silhouette'
    radial=unit(sub(mid,g['c']));slope=sum(dot(n,radial)for n in other)/len(other)
    result.append({'line_index':li,'radial_normal':slope,'flat_normal':f,'max_angle':max(angles)})
   return result,None
  cache={}
  for i,g1 in enumerate(groups):
   for j,g2 in enumerate(groups[i+1:],i+1):
    small,big=(g1,g2)if g1['r']<g2['r']else(g2,g1);w=big['r']-small['r']
    if w<=1e-5 or w/((small['r']+big['r'])/2)>.15 or w*points_per_ldu>1.5:continue
    if small['colour']!=big['colour']or norm(sub(small['c'],big['c']))>.015 or dot(small['n'],big['n'])<.999999:continue
    if small['edges']&big['edges']:continue
    for k,g in[(i,g1),(j,g2)]:
     if k not in cache:cache[k]=profile(g)
    A,whyA=cache[i];C,whyC=cache[j]
    if A is None or C is None:stats['paired_reject_'+str(whyA or whyC)]+=1;continue
    inner,outer=(A,C)if g1 is small else(C,A)
    if not all(a['radial_normal']>.05 for a in inner)or not all(a['radial_normal']<-.05 for a in outer):stats['raised_or_ambiguous_band_preserved']+=1;continue
    if dot(inner[0]['flat_normal'],outer[0]['flat_normal'])<.999999:continue
    remove=small['edges']|big['edges'];removed.update(remove);receipts.append({'root_index':ix,'radii_LDU':[small['r'],big['r']],'centre_native':small['c'],'axis_native':small['n'],'arc_degrees':[small['arc'],big['arc']],'band_width_points':w*points_per_ldu,'removed_hard_segments':len(remove),'lines':sorted(remove),'maximum_crease_degrees':max(a['max_angle']for a in inner+outer),'classification':'paired shallow concave annular crease, opaque equal material, non-silhouette, below paper detail width'})
 keep=[i for i in range(len(lines))if i not in removed];r={'rule':'paired_shallow_concave_annular_detail_v1','parameters':PARAMETERS,'points_per_ldu':points_per_ldu,'scale_kind':'perspective Jacobian upper bound' if camera_position is not None else 'uniform orthographic','view_direction':'per edge midpoint' if camera_position is not None else 'parallel','input_lines':len(lines),'removed_hard_segments':len(removed),'output_lines':len(keep),'pairs':receipts,'circular_groups':group_receipts,'preservation_counts':dict(stats),'surface_triangles_unchanged':True,'conditional_lines_never_removed':True,'no_design_instance_colour_id_or_ROI_selectors':True}
 return[lines[i]for i in keep],[line_features[i]for i in keep],r
