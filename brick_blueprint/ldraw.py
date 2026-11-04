"""Read LDraw data from an explicit library directory or ZIP; never execute it."""
from pathlib import Path, PurePosixPath
from functools import lru_cache
import hashlib
import math
import re
import zipfile

I = (1, 0, 0, 0, 1, 0, 0, 0, 1)

def decode_library_text(data):
    """Read standard UTF-8 library data or an older single-byte text file."""
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            return data.decode("cp1252")
        except UnicodeDecodeError:
            return data.decode("latin-1")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def mv(m, p):
    return tuple(sum(m[3*r+c]*p[c] for c in range(3)) for r in range(3))

def add(a, b):
    return tuple(x+y for x, y in zip(a, b))

def det(m):
    return m[0]*(m[4]*m[8]-m[5]*m[7])-m[1]*(m[3]*m[8]-m[5]*m[6])+m[2]*(m[3]*m[7]-m[4]*m[6])

def validate_transform(t, m):
    if len(t)!=3 or len(m)!=9 or not all(math.isfinite(v) for v in (*t,*m)) or abs(det(m))<1e-12:
        raise ValueError('Invalid or singular LDraw transform')

def color_code(text):
    return int(text, 16) if text.lower().startswith('0x') else int(text)

def safe_ref(ref):
    ref=ref.replace('\\','/').lower()
    if not ref or PurePosixPath(ref).is_absolute() or '..' in ref.split('/') or ':' in ref:
        raise ValueError('Unsafe part reference: '+ref)
    return ref

class Library:
    """Compatible byte reader for directories and ZIPs with or without ldraw/ prefix."""
    def __init__(self, path):
        self.path=Path(path).resolve(); self.visited=set(); self.archive=None
        if self.path.is_dir():
            names=[p.relative_to(self.path).as_posix() for p in self.path.rglob('*') if p.is_file()]
        else:
            self.archive=zipfile.ZipFile(self.path)
            names=[n for n in self.archive.namelist() if not n.endswith('/')]
        self.names={}
        for name in names:
            key=name.lower()
            if key in self.names:
                if self.archive:self.archive.close()
                raise ValueError('Ambiguous case-insensitive library entry: '+name)
            self.names[key]=name
        self.prefix='ldraw/' if 'ldraw/ldconfig.ldr' in self.names else ''
        self.z=self  # inherited feature walker uses a byte-reader protocol
        self.colors={}
        config_name=self.prefix+'LDConfig.ldr'
        config_data=self.read(config_name)
        config=decode_library_text(config_data)
        # Preserve the bytes actually parsed for material colors. DAT geometry
        # hashes alone cannot identify a library's palette revision.
        headers=config.splitlines()
        self.config_receipt={'file':self.names[config_name.lower()],
                             'sha256':hashlib.sha256(config_data).hexdigest(),
                             'authors':[s[2:] for s in headers if s.startswith('0 Author:')],
                             'licenses':[s[11:] for s in headers if s.startswith('0 !LICENSE ')]}
        for line in config.splitlines():
            m=re.match(r'0 !COLOUR (.+?)\s+CODE\s+(\d+)\s+VALUE\s+#([0-9a-fA-F]{6})\s+EDGE\s+#([0-9a-fA-F]{6})',line)
            if m:
                alpha=re.search(r'\bALPHA\s+(\d+)',line)
                self.colors[int(m[2])]={'name':m[1],'value':m[3],'edge':m[4],'alpha':int(alpha[1])/255 if alpha else 1.}
    def read(self, name):
        name=safe_ref(name)
        actual=self.names.get(name)
        if actual is None: raise ValueError('Missing library data: '+name)
        if self.archive:
            if self.archive.getinfo(actual).file_size>16*1024*1024:raise ValueError('Library entry exceeds 16 MiB limit')
            return self.archive.read(actual)
        path=(self.path/actual).resolve()
        if self.path not in path.parents:raise ValueError('Library symlink leaves library root')
        if path.stat().st_size>16*1024*1024:raise ValueError('Library entry exceeds 16 MiB limit')
        return path.read_bytes()
    def resolve(self, ref):
        ref=safe_ref(ref)
        for name in [self.prefix+'parts/'+ref,self.prefix+'p/'+ref]:
            if name.lower() in self.names:return self.names[name.lower()]
        raise ValueError('Missing DAT dependency: '+ref)
    @lru_cache(None)
    def records(self, path):
        records=[]
        for number,line in enumerate(decode_library_text(self.read(path)).splitlines(),1):
            fields=line.split()
            if not fields or fields[0]=='0':continue
            kind=int(fields[0]);expected={1:15,2:8,3:11,4:14,5:14}.get(kind)
            if expected is None or len(fields)!=expected:raise ValueError(f'Malformed DAT {path}:{number}')
            records.append(fields)
        return records
    def close(self):
        self.records.cache_clear()
        if self.archive:self.archive.close()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()

MAX_MODEL_BYTES=16*1024*1024
MAX_SUBMODELS=1024
MAX_MODEL_DEPTH=64
MAX_MODEL_EXPANSIONS=100000

def mm(a,b):
    return tuple(sum(a[3*r+k]*b[3*k+c] for k in range(3)) for r in range(3) for c in range(3))

def load_model(path):
    """Expand type-1 assembly blocks; external DAT resolution stays in Library.

    MPD is deliberately assembly-only: embedded custom DAT geometry, textures,
    INVERTNEXT and model-side edge color 24 are rejected, never silently lost.
    """
    path=Path(path)
    if path.stat().st_size>MAX_MODEL_BYTES:raise ValueError('Model exceeds 16 MiB limit')
    data=path.read_bytes()
    if len(data)>MAX_MODEL_BYTES:raise ValueError('Model exceeds 16 MiB limit')
    lines=data.decode('utf-8-sig').splitlines()
    multipart=any(line.split()[:2]==['0','FILE'] for line in lines)
    blocks={};root=None;active=None
    if not multipart:root=active='';blocks[root]=[]
    for number,line in enumerate(lines,1):
        f=line.split(maxsplit=2)
        if f[:2]==['0','FILE']:
            if len(f)!=3:raise ValueError(f'MPD FILE needs a name at line {number}')
            name=safe_ref(f[2].strip())
            if not name.endswith(('.ldr','.mpd')):raise ValueError('MPD supports assembly .ldr/.mpd blocks only; embedded DAT geometry is not supported')
            if name in blocks:raise ValueError('Duplicate MPD name: '+name)
            if len(blocks)>=MAX_SUBMODELS:raise ValueError('Too many MPD submodels')
            blocks[name]=[];active=name
            if root is None:root=name
            continue
        if f[:2]==['0','NOFILE']:
            if len(f)!=2 or not multipart:raise ValueError('Unexpected MPD NOFILE')
            active=None;continue
        if f[:2] in (['0','!DATA'],['0','!:'],['0','!TEXMAP']):
            raise ValueError('Embedded data/TEXMAP is not supported')
        if active is None:
            # The MPD envelope may contain prose; geometry before FILE is an error.
            if root is None and f and f[0] in ('1','2','3','4','5'):
                raise ValueError('LDraw geometry before first MPD FILE')
            continue
        blocks[active].append((number,line))
    parsed={};used=set();out=[];expansions=0

    def records(name):
        if name in parsed:return parsed[name]
        items=[];step=1
        for number,line in blocks[name]:
            f=line.split(maxsplit=14)
            if not f:continue
            if f[0]=='0':
                if 'INVERTNEXT' in line.split():raise ValueError('Model INVERTNEXT is not supported')
                if f[:2]==['0','STEP']:step+=1
                continue
            if f[0]!='1' or len(f)!=15:raise ValueError(f'Expected an assembly type-1 placement at line {number}')
            xyz=tuple(map(float,f[2:5]));matrix=tuple(map(float,f[5:14]));validate_transform(xyz,matrix)
            color=color_code(f[1])
            if color==24:raise ValueError('Model placement color 24 is not supported')
            items.append((safe_ref(f[14].strip()),color,xyz,matrix,step))
        parsed[name]=items;return items

    def expand(name,translation,matrix,color,root_step,trail):
        nonlocal expansions
        if name in trail:raise ValueError('MPD reference cycle: '+' -> '.join((*trail,name)))
        if len(trail)>=MAX_MODEL_DEPTH:raise ValueError('MPD nesting depth limit exceeded')
        expansions+=1
        if expansions>MAX_MODEL_EXPANSIONS:raise ValueError('MPD expansion limit exceeded')
        used.add(name)
        for ref,c,t,m,step in records(name):
            world_t=add(translation,mv(matrix,t));world_m=mm(matrix,m)
            validate_transform(world_t,world_m)
            world_color=color if c==16 else c
            placement_step=step if root_step is None else root_step
            if ref in blocks:
                expand(ref,world_t,world_m,world_color,placement_step,(*trail,name))
            else:
                if ref.endswith(('.ldr','.mpd')):raise ValueError('Missing model-local subfile: '+ref)
                if len(out)>=MAX_MODEL_EXPANSIONS:raise ValueError('Expanded part limit exceeded')
                out.append({'id':f'p{len(out)+1:03}','part':ref,'ldraw_color':world_color,
                            'xyz':world_t,'matrix':world_m,'step':placement_step})
    expand(root,(0,0,0),I,16,None,())
    if not out:raise ValueError('Empty MPD model' if multipart else 'Empty model')
    metadata={'format':'mpd' if multipart else 'ldr','root':root if multipart else None,
              'declared_submodels':len(blocks) if multipart else 0,
              'used_submodels':sorted(used) if multipart else [],
              'expanded_parts':len(out),'step_scope':'root placement step; submodel STEP does not advance the root timeline'}
    return out,metadata

def parse_model(path):
    return load_model(path)[0]

def material(lib, color, edge=False):
    if color in lib.colors:
        row=lib.colors[color];value=row['edge' if edge else 'value']
        return tuple(int(value[i:i+2],16) for i in (0,2,4)),1. if edge else row['alpha']
    if color>>24 in (2,3):return (color>>16&255,color>>8&255,color&255),.5 if color>>24==3 else 1.
    raise ValueError('Undefined render colour '+str(color))
