"""Exact microunit SVG path normalization/compaction; no coordinate rounding."""
from pathlib import Path
import re,sys,json,hashlib,xml.etree.ElementTree as E,gzip,zipfile
SCALE=1000000
def integer(s):
 sign=-1 if s.startswith('-')else 1;s=s.lstrip('+-');a,_,b=s.partition('.');assert len(b)<=6
 return sign*(int(a or '0')*SCALE+int((b+'000000')[:6]))
def num(v):
 sign='-'if v<0 else '';a,b=divmod(abs(v),SCALE);s=str(a)+(('.'+str(b).zfill(6).rstrip('0'))if b else '')
 if s.startswith('0.'):s=s[1:]
 return sign+s
def expand(d):
 tokens=re.findall(r'[MLZmlHVhvz]|[-+]?(?:\d+(?:\.\d*)?|\.\d+)',d);out=[];i=0;x=y=sx=sy=0;cmd=None
 while i<len(tokens):
  if tokens[i].isalpha():cmd=tokens[i];i+=1
  assert cmd is not None
  if cmd in 'Zz':out.append(('Z',));x,y=sx,sy;cmd=None;continue
  if cmd in 'HhVv':
   v=integer(tokens[i]);i+=1
   if cmd=='H':x=v
   elif cmd=='h':x+=v
   elif cmd=='V':y=v
   else:y+=v
   out.append(('L',x,y));continue
  assert cmd in 'MLml';a,b=integer(tokens[i]),integer(tokens[i+1]);i+=2
  if cmd.islower():x+=a;y+=b
  else:x,y=a,b
  c=cmd.upper();out.append((c,x,y))
  if c=='M':sx,sy=x,y;cmd='l'if cmd=='m'else'L'
 return out
def encode(commands):
 out=[];x=y=sx=sy=0
 for row in commands:
  c=row[0]
  if c=='Z':out.append('Z');x,y=sx,sy;continue
  a,b=row[1:]
  if c=='M':out.append('M'+num(a)+','+num(b));sx,sy=a,b
  else:
   choices=['L'+num(a)+','+num(b),'l'+num(a-x)+','+num(b-y)]
   if b==y:choices+=['H'+num(a),'h'+num(a-x)]
   if a==x:choices+=['V'+num(b),'v'+num(b-y)]
   out.append(min(choices,key=len))
  x,y=a,b
 return ''.join(out)
def compact(src,dst):
 E.register_namespace('','http://www.w3.org/2000/svg');E.register_namespace('xlink','http://www.w3.org/1999/xlink');root=E.parse(src).getroot();n=0
 for p in root.iter():
  if p.tag.endswith('}path'):
   before=expand(p.attrib['d']);after=encode(before);assert expand(after)==before;p.attrib['d']=after;n+=1
 data=E.tostring(root,encoding='utf-8');dst.write_bytes(data)
 with zipfile.ZipFile(dst.with_suffix('.zip'),'w',zipfile.ZIP_DEFLATED,compresslevel=9)as z:z.writestr(dst.name,data)
 gz=gzip.compress(data,compresslevel=9,mtime=0);dst.with_suffix('.svg.gz').write_bytes(gz)
 r={'source':src.name,'output':dst.name,'classification':'exact coordinates and commands after expansion; shorter absolute/relative H/V/L syntax only','paths_exactly_checked':n,'SVG_bytes':len(data),'ZIP_bytes':dst.with_suffix('.zip').stat().st_size,'gzip_bytes':len(gz),'sha256':hashlib.sha256(data).hexdigest()};dst.with_suffix('.compact.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
if __name__=='__main__':compact(Path(sys.argv[1]),Path(sys.argv[2]))
