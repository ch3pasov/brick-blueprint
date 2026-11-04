"""Optional signed-winding finite-grid audit of the original kiosk's actual DAT surfaces.

Bound to this example, not a general assembly validator. The embedded standalone
scanner derives from the existing project-owned independent winding audit; no
historical application launcher is imported or executed. Temporary meshes are
removed; only JSON evidence is delivered. Physical clutch/stability are untested.
"""
from collections import Counter
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from brick_blueprint import __version__
from brick_blueprint.ldraw import Library,load_model
from brick_blueprint.instruction_features import scene_with_features
from check_kiosk import check as check_nominal

CPP=r"""#include <array>
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iostream>
#include <vector>
using P=std::array<double,3>;
P minus(P a,P b){return {a[0]-b[0],a[1]-b[1],a[2]-b[2]};}
double dot(P a,P b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
P cross(P a,P b){return {a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]};}
struct Mesh {std::vector<std::array<P,3>> faces;P lo={1e100,1e100,1e100},hi={-1e100,-1e100,-1e100};
 double winding(P point)const {double angle=0;for(auto&f:faces){P a=minus(f[0],point),b=minus(f[1],point),c=minus(f[2],point);double aa=std::sqrt(dot(a,a)),bb=std::sqrt(dot(b,b)),cc=std::sqrt(dot(c,c));angle+=2*std::atan2(dot(a,cross(b,c)),aa*bb*cc+dot(a,b)*cc+dot(b,c)*aa+dot(c,a)*bb);}return angle/(4*std::acos(-1));}
};
int main(int argc,char**argv){if(argc!=4)return 2;std::ifstream in(argv[1]);int n;in>>n;std::vector<Mesh> meshes(n);for(auto&m:meshes){int count;in>>count;m.faces.resize(count);for(auto&f:m.faces)for(auto&p:f)for(int k=0;k<3;k++){in>>p[k];m.lo[k]=std::min(m.lo[k],p[k]);m.hi[k]=std::max(m.hi[k],p[k]);}}if(!in)return 3;double pitch=std::stod(argv[2]);int phase=std::stoi(argv[3]);P shift=phase==0?P{.217,.333,.481}:P{.491,.113,.691};long long total=0,overlap=0;int screened=0;bool first=true;std::cout<<"{\"pitch\":"<<pitch<<",\"phase\":"<<phase<<",\"offset\":["<<shift[0]<<","<<shift[1]<<","<<shift[2]<<"],\"AABB_depth_tolerance\":0.22,\"abs_winding_threshold\":0.55,\"pairs\":[";
 for(int i=0;i<n;i++)for(int j=i+1;j<n;j++){P lo,hi;bool candidate=true;for(int k=0;k<3;k++){lo[k]=std::max(meshes[i].lo[k],meshes[j].lo[k]);hi[k]=std::min(meshes[i].hi[k],meshes[j].hi[k]);candidate&=hi[k]-lo[k]>.22;}screened++;if(!candidate)continue;long long probes=0,bad=0;std::vector<P>witness;
  for(double x=lo[0]+shift[0];x<hi[0];x+=pitch)for(double y=lo[1]+shift[1];y<hi[1];y+=pitch)for(double z=lo[2]+shift[2];z<hi[2];z+=pitch){P p={x,y,z};probes++;if(std::abs(meshes[i].winding(p))>.55&&std::abs(meshes[j].winding(p))>.55){bad++;if(witness.size()<8)witness.push_back(p);}}
  total+=probes;overlap+=bad;if(!first)std::cout<<",";first=false;std::cout<<"{\"a\":"<<i<<",\"b\":"<<j<<",\"probes\":"<<probes<<",\"overlap\":"<<bad<<",\"first_witnesses\":[";for(size_t k=0;k<witness.size();k++){if(k)std::cout<<",";auto&p=witness[k];std::cout<<"["<<p[0]<<","<<p[1]<<","<<p[2]<<"]";}std::cout<<"]}";
 }std::cout<<"],\"screened_pairs\":"<<screened<<",\"total_probes\":"<<total<<",\"total_overlap\":"<<overlap<<"}\n";
}
"""


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compile_scanner(cache):
    compiler=os.environ.get('CXX') or shutil.which('clang++') or shutil.which('g++')
    if not compiler:raise RuntimeError('A C++17 compiler is required')
    version=subprocess.run([compiler,'--version'],check=True,capture_output=True,text=True,timeout=30).stdout
    key=hashlib.sha256((CPP+compiler+version).encode()).hexdigest()[:20]
    folder=Path(cache)/'kiosk-winding'/key;folder.mkdir(parents=True,exist_ok=True)
    target=folder/('scanner.exe' if os.name=='nt' else 'scanner')
    if not target.is_file():
        with tempfile.TemporaryDirectory(dir=folder) as temp:
            temp=Path(temp);source=temp/'scanner.cpp';source.write_text(CPP)
            try:
                subprocess.run([compiler,'-O2','-std=c++17',source,'-o',temp/target.name],
                               check=True,capture_output=True,text=True,timeout=300)
            except subprocess.CalledProcessError as error:
                raise RuntimeError('Mesh scanner C++17 build failed: '+error.stderr[-2000:]) from error
            os.replace(temp/target.name,target)
    return target.resolve(),dict(compiler=Path(compiler).name,
        compiler_version=(version.splitlines() or [Path(compiler).name])[0],scanner_binary_sha256=sha(target),
        scanner_source_sha256=hashlib.sha256(CPP.encode()).hexdigest(),cache_key=key)


def write_mesh(path,groups):
    if not 1<=len(groups)<=1000:raise ValueError('Invalid diagnostic mesh count')
    count=sum(map(len,groups))
    if count>1000000:raise ValueError('Diagnostic triangle budget exceeded')
    with Path(path).open('x') as stream:
        stream.write(str(len(groups))+'\n')
        for group in groups:
            stream.write(str(len(group))+'\n')
            for triangle in group:
                values=[v for p in triangle for v in p]
                if len(values)!=9 or not all(math.isfinite(v) for v in values):raise ValueError('Invalid diagnostic triangle')
                stream.write(' '.join(format(v,'.12g') for v in values)+'\n')


def scan_meshes(groups,binary,*,pitch=.75,phase=0,timeout=600):
    if pitch not in (.75,1.5) or phase not in (0,1):raise ValueError('Unsupported diagnostic sampling plan')
    with tempfile.TemporaryDirectory(prefix='brick-kiosk-winding-') as temp:
        mesh=Path(temp)/'geometry.mesh';write_mesh(mesh,groups);mesh_hash=sha(mesh)
        start=time.perf_counter()
        run=subprocess.run([binary,mesh,str(pitch),str(phase)],check=True,
                           capture_output=True,text=True,timeout=timeout)
        result=json.loads(run.stdout)
        result.update(mesh_sha256=mesh_hash,elapsed_seconds=round(time.perf_counter()-start,3))
        return result


def model_meshes(model,library):
    parts,structure=load_model(model)
    with Library(library) as lib:
        triangles,_,_,_=scene_with_features(lib,parts)
        groups=[[] for _ in parts];seen=[set() for _ in parts]
        for triangle,color,owner,step in triangles:
            # Cyclic duplicates have the same orientation; opposing triangles
            # must remain so their winding can cancel on internal boundaries.
            key=min(tuple(triangle[i:]+triangle[:i]) for i in range(3))
            if key not in seen[owner]:seen[owner].add(key);groups[owner].append(triangle)
    return parts,structure,groups


def physical_signature(p):
    return p['part'],p['ldraw_color'],tuple(p['xyz']),tuple(p['matrix']),p['step']


def audit(model,library,output,*,cache_dir=ROOT/'.brickblueprint-cache',pitch=.75,phases=(0,1),timeout=600):
    output=Path(output)
    if output.exists():raise FileExistsError('Choose a new diagnostic output directory')
    if not phases or len(phases)!=len(set(phases)):raise ValueError('Choose phase 0 and/or 1 once each')
    design_path=ROOT/'examples/kiosk/design.json';design=json.loads(design_path.read_text())
    parts,structure,groups=model_meshes(model,library)
    expected=Counter((p['part'],p['color'],tuple(p['xyz']),tuple(p['matrix']),p['step']) for p in design['placements'])
    if Counter(map(physical_signature,parts))!=expected:
        raise ValueError('This diagnostic is bound to the original kiosk placements and eight root stages')
    nominal=check_nominal(model,library)
    if not nominal['audit']['passed']:raise ValueError('Resolve the example-specific nominal/body-envelope audit first')
    binary,compiler=compile_scanner(cache_dir)
    chosen=[]
    for ref,color,point in [('3004.dat',15,(-50,-24,-20)),('3004.dat',15,(50,-24,-20)),('3009.dat',1,(0,-24,10))]:
        chosen.append(next(p for p in parts if p['part']==ref and p['ldraw_color']==color and tuple(p['xyz'])==point))
    control_ids=[p['id'] for p in chosen]
    # Actual rejected front-sill body intrusion, transformed in its own owner mesh.
    control=[]
    for p in chosen:
        group=groups[parts.index(p)]
        control.append([tuple((v[0],v[1],v[2]-10) for v in triangle) for triangle in group] if p is chosen[-1] else group)
    scans=[];controls=[]
    for phase in phases:
        print('Mesh phase '+str(phase)+' / '+str(pitch)+' LDU',flush=True)
        scans.append(scan_meshes(groups,binary,pitch=pitch,phase=phase,timeout=timeout))
        controls.append(scan_meshes(control,binary,pitch=pitch,phase=phase,timeout=timeout))
    controls_work=all(r['total_overlap']>0 for r in controls)
    clean=all(r['total_overlap']==0 for r in scans)
    status='PASS_FINITE_GRID' if clean and controls_work else 'REVIEW_REQUIRED' if controls_work else 'CONTROL_FAILED'
    result=dict(status=status,package_version=__version__,model_sha256=sha(model),design_sha256=sha(design_path),
        model_structure=structure,part_ids=[p['id'] for p in parts],triangles=sum(map(len,groups)),
        tool_sha256=sha(__file__),python_version=platform.python_version(),compiler=compiler,
        geometry_reader_sha256=sha(ROOT/'brick_blueprint/ldraw.py'),
        BFC_walker_sha256=sha(ROOT/'brick_blueprint/instruction_features.py'),
        nominal_audit_sha256=hashlib.sha256(json.dumps(nominal,sort_keys=True).encode()).hexdigest(),
        dependencies=nominal['dependencies'],library_config=nominal['library_config'],scans=scans,
        positive_control=dict(part_ids=control_ids,change='Original front sill Z10 -> Z0; actual 10 LDU body intrusion',scans=controls),
        limits=['Finite sampling is not a continuous collision or physical clutch/stability certificate.',
                'Actual BFC-oriented recursive surfaces; absolute winding >0.55 and overlap-box depth >0.22 LDU.',
                'Offsets are applied inside each pair overlap box, not a universal scene grid.',
                'Any flagged pair requires separate review; no blanket nominal-contact allowance clears a flag.',
                'No swept-motion, source-instruction or physical color/stock acceptance. Raw meshes are not retained.'])
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.kiosk-mesh-report-',dir=output.parent) as temp:
        result_dir=Path(temp)/'result';result_dir.mkdir()
        (result_dir/'mesh-audit.json').write_text(json.dumps(result,indent=2)+'\n')
        if output.exists():raise FileExistsError('Output appeared during diagnostic; preserved it')
        os.replace(result_dir,output)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library',type=Path,required=True)
    parser.add_argument('--model',type=Path,default=ROOT/'examples/kiosk/kiosk.ldr')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--cache-dir',type=Path,default=ROOT/'.brickblueprint-cache')
    parser.add_argument('--pitch',type=float,choices=[.75,1.5],default=.75)
    parser.add_argument('--phase',type=int,choices=[0,1],action='append')
    parser.add_argument('--timeout',type=int,default=600)
    args=parser.parse_args()
    try:
        result=audit(args.model,args.library,args.output,cache_dir=args.cache_dir,
                     pitch=args.pitch,phases=tuple(args.phase or (0,1)),timeout=args.timeout)
    except (ValueError,OSError,RuntimeError,subprocess.SubprocessError) as error:
        parser.exit(1,'Mesh diagnostic failed: '+str(error)+'\n')
    print(json.dumps(dict(status=result['status'],phases=len(result['scans']),
                         probes=sum(r['total_probes'] for r in result['scans']),
                         overlap=sum(r['total_overlap'] for r in result['scans'])),indent=2))
    return 0 if result['status']=='PASS_FINITE_GRID' else 1


if __name__=='__main__':raise SystemExit(main())
