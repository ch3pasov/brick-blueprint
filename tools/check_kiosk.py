"""Bounded geometric audit of the upright Little Blue Kiosk sample.

This is an example-specific check, not a general collision/connection feature.
It reads actual DAT surfaces and stud frames, checks conservative body boxes,
nominal stud seats and each saved stage. Physical clutch/stability are untested.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from brick_blueprint.ldraw import Library, I, add, mm, mv, load_model
from brick_blueprint.instruction_features import scene_with_features

# Explicit reviewed support: X/Z stud dimensions, body depth, top studs present.
# Round 1x1 parts use conservative square body envelopes.
FORMS={'41539.dat':(8,8,8,True), '2431.dat':(4,1,8,False),
       '3009.dat':(6,1,24,True), '3004.dat':(2,1,24,True),
       '3020.dat':(4,2,8,True), '3010.dat':(4,1,24,True),
       '3005.dat':(1,1,24,True), '3035.dat':(8,4,8,True),
       '3623.dat':(3,1,8,True), '3062b.dat':(1,1,24,True),
       '98138.dat':(1,1,8,False)}
TOL=1e-6


def bounds(points):
    return [[min(p[k] for p in points),max(p[k] for p in points)] for k in range(3)]


def box_world(p, box):
    return bounds([add(p['xyz'],mv(p['matrix'],(x,y,z)))
                   for x in box[0] for y in box[1] for z in box[2]])


def equal(a,b):return all(abs(x-y)<TOL for x,y in zip(a,b))


def stud_frames(lib, ref, t=(0,0,0), m=I, trail=()):
    name=lib.resolve(ref)
    if name in trail:raise ValueError('DAT cycle')
    result=[]
    for f in lib.records(name):
        if f[0]!='1':continue
        ct=add(t,mv(m,tuple(map(float,f[2:5]))));cm=mm(m,tuple(map(float,f[5:14])))
        child=f[14].replace('\\','/').lower()
        if child in ('stud.dat','stud2.dat','stud2a.dat','stud15.dat'):
            if equal(mv(cm,(0,-1,0)),(0,-1,0)) and abs(ct[1])<TOL:
                result.append(ct)
        result.extend(stud_frames(lib,child,ct,cm,(*trail,name)))
    return sorted(set(result))


def inspect_forms(lib,parts):
    result={}
    for ref in sorted({p['part'] for p in parts}):
        if ref not in FORMS:raise ValueError('Unsupported sample form: '+ref)
        nx,nz,depth,studded=FORMS[ref]
        p=dict(part=ref,ldraw_color=15,xyz=(0,0,0),matrix=I,step=1)
        triangles,_,_,_=scene_with_features(lib,[p])
        actual=bounds([v for tri,*_ in triangles for v in tri])
        expected=[[-10*nx,10*nx],[-4 if studded else 0,depth],[-10*nz,10*nz]]
        if not all(equal(a,b) for a,b in zip(actual,expected)):
            raise ValueError('Actual DAT bounds differ from reviewed form: '+ref)
        seats=[(x,depth,z) for x in range(-10*(nx-1),10*nx,20)
               for z in range(-10*(nz-1),10*nz,20)]
        studs=stud_frames(lib,ref)
        expected_studs=sorted((x,0,z) for x,_,z in seats) if studded else []
        if studs!=expected_studs:raise ValueError('Actual DAT stud frames differ: '+ref)
        result[ref]=dict(actual_bounds=actual,
                         body_bounds=[actual[0],[0,depth],actual[2]],
                         studs=studs,nominal_receivers=seats,
                         receiver_scope='Standard upright grid underside; clutch tolerances and force not measured.')
    return result


def audit(parts,forms):
    bodies=[];full=[];hosts=[];receivers=[]
    for index,p in enumerate(parts):
        m=p['matrix']
        # Only upright right-angle rotations are admitted by this sample audit.
        if not equal(mv(m,(0,1,0)),(0,1,0)) or any(abs(v-round(v))>TOL for v in m):
            raise ValueError('Unsupported sample orientation')
        if sum(v*v for v in m)!=3:raise ValueError('Unsupported non-rigid sample transform')
        form=forms[p['part']]
        bodies.append(box_world(p,form['body_bounds']))
        full.append(box_world(p,form['actual_bounds']))
        hosts.extend((index,add(p['xyz'],mv(m,s))) for s in form['studs'])
        receivers.extend((index,add(p['xyz'],mv(m,s))) for s in form['nominal_receivers'])
    edges=[];seated=set()
    for i,a in hosts:
        for j,b in receivers:
            if i!=j and equal(a,b):
                edges.append(dict(host=parts[i]['id'],receiver=parts[j]['id'],point_ldu=a))
                seated.add(tuple(sorted((i,j))))
    body_overlaps=[];unclassified=[]
    for i in range(len(parts)):
        for j in range(i):
            def overlap(boxes):
                return [min(boxes[i][k][1],boxes[j][k][1])-max(boxes[i][k][0],boxes[j][k][0]) for k in range(3)]
            extent=overlap(bodies)
            if min(extent)>TOL:
                body_overlaps.append(dict(a=parts[j]['id'],b=parts[i]['id'],extent_ldu=extent))
            elif min(overlap(full))>TOL and (j,i) not in seated:
                unclassified.append([parts[j]['id'],parts[i]['id']])
    stages=[]
    for step in sorted({p['step'] for p in parts}):
        ids={p['id'] for p in parts if p['step']<=step}
        graph={i:set() for i in ids}
        for edge in edges:
            a,b=edge['host'],edge['receiver']
            if a in ids and b in ids:graph[a].add(b);graph[b].add(a)
        components=[];left=set(ids)
        while left:
            seen=set();todo=[min(left)]
            while todo:
                a=todo.pop()
                if a not in seen:seen.add(a);todo.extend(graph[a]-seen)
            components.append(sorted(seen));left-=seen
        stages.append(dict(step=step,parts=len(ids),components=components))
    return dict(passed=not body_overlaps and not unclassified and all(len(s['components'])==1 for s in stages),
                body_overlaps=body_overlaps,unclassified_full_bounds_overlaps=unclassified,
                nominal_seats=edges,stages=stages)


def check(model,library):
    parts,structure=load_model(model)
    with Library(library) as lib:
        forms=inspect_forms(lib,parts)
        result=audit(parts,forms)
        # Known wrong placement: push the front sill ten LDU into the side sills.
        wrong=deepcopy(parts)
        sill=next((p for p in wrong if p['part']=='3009.dat' and equal(p['xyz'],(0,-24,10))),None)
        if sill is None:raise ValueError('This example audit requires the full kiosk with its known front-sill control placement')
        sill['xyz']=(0,-24,0)
        control=audit(wrong,forms)
        # A cap raised by eight LDU must no longer have a nominal stud seat.
        floating=deepcopy(parts)
        cap=next((p for p in floating if p['part']=='98138.dat'),None)
        if cap is None:raise ValueError('This example audit requires the full kiosk with its round-cap control placement')
        cap['xyz']=tuple(v-8 if k==1 else v for k,v in enumerate(cap['xyz']))
        float_result=audit(floating,forms)
        controls=dict(body_intrusion_detected=bool(control['body_overlaps']),
                      intrusion_pairs=control['body_overlaps'],
                      floating_cap_detected=not float_result['passed'])
        result['passed']=result['passed'] and controls['body_intrusion_detected'] and controls['floating_cap_detected']
        dependencies=[]
        for name in sorted(lib.visited):
            data=lib.read(name);lines=data.decode('latin1').splitlines()
            dependencies.append(dict(file=name,sha256=hashlib.sha256(data).hexdigest(),
                                     authors=[s[2:] for s in lines if s.startswith('0 Author:')],
                                     licenses=[s[11:] for s in lines if s.startswith('0 !LICENSE ')]))
        return dict(checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    model_sha256=hashlib.sha256(Path(model).read_bytes()).hexdigest(),
                    model_structure=structure,parts=len(parts),forms=forms,audit=result,
                    controls=controls,dependencies=dependencies,library_config=lib.config_receipt,
                    limits=['Example-specific upright regular-part check; unsupported forms fail.',
                            'Conservative body envelopes exclude stud regions; matched nominal seats classify stud-envelope contact.',
                            'No finite-grid mesh certificate, clutch force, physical color availability or stability claim.',
                            'This original design has no official instruction source to certify.'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',type=Path,default=ROOT/'examples/kiosk/kiosk.ldr')
    parser.add_argument('--library',type=Path,required=True)
    args=parser.parse_args()
    try:result=check(args.model,args.library)
    except (ValueError,OSError,RuntimeError) as error:parser.exit(1,str(error)+'\n')
    print(json.dumps(result,indent=2))
    return 0 if result['audit']['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
