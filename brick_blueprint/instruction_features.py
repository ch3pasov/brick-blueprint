"""Actual recursive DAT features, identical logic for every root instance.

Stud wall = cylindrical surface primitive beneath a standard stud primitive.
No set number, root design-ID list, instance ID, screen ROI or edited DAT ZIP.
"""
from functools import lru_cache
import re,math
from pathlib import PurePosixPath
from .ldraw import add,mv,det,validate_transform,color_code,decode_library_text

def scene_with_features(lib,parts):
 @lru_cache(None)
 def walk(ref,colour,stack=(),stud=False,cylinder=False,explicit=False):
  path=lib.resolve(ref)
  if path in stack:raise ValueError('DAT cycle '+path)
  lib.visited.add(path);lib.records(path);base=PurePosixPath(path).name
  stud=stud or bool(re.fullmatch(r'stud\d*[a-z]?\.dat',base))
  cylinder=cylinder or bool(stud and re.search(r'cyli[^/]*\.dat$',base))
  triangles=[];lines=[];cw=False;invert=False
  for raw in decode_library_text(lib.z.read(path)).splitlines():
   f=raw.split()
   if not f:continue
   if f[0]=='0':
    if len(f)>1 and f[1]=='!TEXMAP':raise ValueError('Unsupported texture mapping')
    if 'BFC'in f:
     if 'INVERTNEXT'in f:invert=True
     elif 'CCW'in f:cw=False
     elif 'CW'in f:cw=True
    continue
   typ=int(f[0]);rawcol=color_code(f[1]);c=colour if rawcol==16 else rawcol;ex=explicit or rawcol not in(16,24)
   if typ==1:
    t=tuple(map(float,f[2:5]));m=tuple(map(float,f[5:14]));validate_transform(t,m);ts,ls=walk(f[14].replace('\\','/').lower(),c,stack+(path,),stud,cylinder,ex)
    for tri,mat,role in ts:
     q=tuple(add(t,mv(m,v))for v in tri)
     if(det(m)<0)^invert:q=(q[0],q[2],q[1])
     transformed=(role[0],mv(m,role[1]))if isinstance(role,tuple)else role
     triangles.append((q,mat,transformed))
    lines.extend((tuple(add(t,mv(m,v))for v in pts),mat,edge,role,isexplicit)for pts,mat,edge,role,isexplicit in ls);invert=False
   else:
    pts=tuple(tuple(map(float,f[j:j+3]))for j in range(2,len(f),3))
    if not all(math.isfinite(x)for v in pts for x in v):raise ValueError('Nonfinite DAT')
    if typ in(2,5):lines.append((pts,colour if c==24 else c,c==24,'stud'if stud else'body',rawcol!=24))
    elif typ in(3,4):
     role=('stud_cylinder_wall',(0,1,0))if cylinder else'explicit_colour_surface'if ex else'stud_cap_or_ring'if stud else'body'
     for ids in[(0,1,2)]+([(0,2,3)]if typ==4 else[]):triangles.append((tuple(pts[i]for i in(ids[::-1]if cw else ids)),c,role))
  return tuple(triangles),tuple(lines)
 triangles=[];lines=[];tf=[];lf=[]
 for ix,p in enumerate(parts):
  ts,ls=walk(p['part'],p['ldraw_color'])
  for tri,c,role in ts:
   q=tuple(add(p['xyz'],mv(p['matrix'],v))for v in tri)
   if det(p['matrix'])<0:q=(q[0],q[2],q[1])
   if isinstance(role,tuple):
    axis=mv(p['matrix'],role[1]);length=math.sqrt(sum(x*x for x in axis));role='stud_cylinder_wall'if length>0 and abs(axis[1])/length>.99 else'sideways_stud_cylinder_wall'
   triangles.append((q,c,ix,p['step']));tf.append(role)
  for pts,c,edge,role,explicit in ls:lines.append((tuple(add(p['xyz'],mv(p['matrix'],v))for v in pts),c,edge,ix,p['step']));lf.append({'role':role,'explicit':explicit})
 return triangles,lines,tf,lf
