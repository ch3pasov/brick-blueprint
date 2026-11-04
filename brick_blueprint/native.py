"""Compile bundled C++ sources without downloads or application launches."""
from pathlib import Path
import hashlib
import json
import os
import platform
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).with_name('native')

def build(cache_dir, *, with_receipt=False):
    cache=Path(cache_dir);cache.mkdir(parents=True,exist_ok=True)
    compiler=os.environ.get('CXX') or shutil.which('clang++') or shutil.which('g++')
    if not compiler:raise RuntimeError('A C++17 compiler is required (clang++ or g++); set CXX to its executable')
    version=subprocess.run([compiler,'--version'],check=True,capture_output=True,text=True,timeout=30).stdout
    hasher=hashlib.sha256((compiler+version).encode())
    sources_hash=hashlib.sha256()
    for p in sorted(ROOT.rglob('*')):
        if p.is_file():
            payload=p.relative_to(ROOT).as_posix().encode()+p.read_bytes()
            hasher.update(payload);sources_hash.update(payload)
    key=hasher.hexdigest()[:20];folder=cache/key;folder.mkdir(exist_ok=True)
    vendor=ROOT/'vendor/Clipper2/Clipper2Lib'
    configs={'vector':[ROOT/'vector_render.cpp'],
             'union':[ROOT/'union_q3_tiled.cpp',ROOT/'opaque_underpaint.cpp',vendor/'src/clipper.engine.cpp',vendor/'src/clipper.offset.cpp',vendor/'src/clipper.rectclip.cpp']}
    result={}
    for name,sources in configs.items():
        target=folder/(name+('.exe' if os.name=='nt' else ''))
        if not target.is_file():
            with tempfile.TemporaryDirectory(dir=folder) as tmp:
                candidate=Path(tmp)/target.name
                command=[compiler,'-O2','-std=c++17','-I',str(vendor/'include'),*map(str,sources),'-o',str(candidate)]
                run=subprocess.run(command,text=True,capture_output=True,timeout=300)
                if run.returncode:raise RuntimeError('Native build failed:\n'+run.stderr)
                os.replace(candidate,target)
        result[name]=target.resolve()
    if not with_receipt:return result
    package=ROOT.parent
    source_rows=[(p.relative_to(package).as_posix(),hashlib.sha256(p.read_bytes()).hexdigest())
                 for p in sorted(package.rglob('*'),key=lambda p:p.relative_to(package).as_posix())
                 if p.is_file() and (p.suffix in {'.py','.json','.cpp','.h'} or p.name=='LICENSE')]
    return result,dict(python_version=platform.python_version(),
                       python_implementation=platform.python_implementation(),
                       system=platform.system(),machine=platform.machine(),
                       compiler=Path(compiler).name,
                       compiler_version=version.splitlines()[0] if version.splitlines() else '',
                       native_source_sha256=sources_hash.hexdigest(),
                       package_source_sha256=hashlib.sha256(json.dumps(source_rows,separators=(',',':')).encode()).hexdigest(),
                       package_source_files=len(source_rows),
                       native_cache_key=key,
                       native_binary_sha256={name:hashlib.sha256(path.read_bytes()).hexdigest()
                                             for name,path in result.items()})
