"""Measure actual preset cameras against saved body/stud coordinates.

NumPy and a separately supplied LDraw library are required. Official pixels
are not needed. The two source images were used to choose these recipes; this
is implementation validation on known data, not an independent source test.
"""
import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from brick_blueprint import __version__
from brick_blueprint.project import project
from brick_blueprint.camera_presets import all_camera_presets
from check_camera_strength import project as project_points, centroid


def check(library):
    source=ROOT/'docs/research/VOLUME-CAMERA-RESULTS.json'
    data=json.loads(source.read_text())
    strength=json.loads((ROOT/'docs/research/CAMERA-STRENGTH.json').read_text())
    theta=np.linspace(0,2*np.pi,256,endpoint=False)
    ring=np.c_[6*np.cos(theta),np.zeros(256),6*np.sin(theta)]
    records=[]
    with tempfile.TemporaryDirectory() as temp:
        t=Path(temp)
        for specimen in data['replay']:
            key=specimen['id']
            frame=next(r['frame_points'] for r in strength['results'] if r['id']==key)
            model=t/(key+'.ldr')
            model.write_text(f"0 Camera validation specimen\n1 {specimen['color']} 0 0 0 1 0 0 0 1 0 0 0 1 {specimen['part']}\n")
            edges=sorted([r for r in data['rows'] if r['id']==key],key=lambda r:r['threshold'])
            caps=next(r for r in data['stud_validation']['results'] if r['id']==key)
            cap_trials=sorted(caps['measured'],key=lambda r:r['threshold'])
            for name in all_camera_presets():
                rec=project(model,library,t/'scene',width=frame[0],height=frame[1],camera_preset=name)
                camera=dict(rec['camera'])
                if name=='orthographic':
                    # Orthographic offset cancels in the scale/translation fit.
                    # Basis is given by the same LDraw camera convention.
                    az=np.radians(camera['azimuth']);el=np.radians(camera['elevation'])
                    camera.update(right=[-np.cos(az),0,np.sin(az)],
                        down=[np.sin(az)*np.sin(el),np.cos(el),np.cos(az)*np.sin(el)],
                        offset_points=[0,0],points_per_ldu=rec['points_per_ldu'])
                xyz=np.array(caps['world_stud_centers'])+[0,12,0]
                predicted=np.array([centroid(project_points(camera,p+ring)) for p in xyz])
                comparisons=[]
                for edge in edges:
                    body=project_points(camera,np.array(edge['world_xyz'])+[0,12,0])
                    uv=np.array(edge['points']);x=body-body.mean(0);y=uv-uv.mean(0)
                    scale=(x*y).sum()/(x*x).sum();shift=uv.mean(0)-scale*body.mean(0)
                    for cap in cap_trials:
                        measured=np.array(cap['centers'])*[1,edge['pixel_aspect_y_x']]
                        error=scale*predicted+shift-measured
                        comparisons.append(dict(edge_threshold=edge['threshold'],cap_threshold=cap['threshold'],
                            cap_rms_px=float(np.sqrt(np.mean(np.sum(error**2,axis=1)))),
                            alignment_scale=float(scale),alignment_shift=shift.tolist()))
                records.append(dict(id=key,preset=name,frame_points=frame,camera=rec['camera'],
                    model_sha256=rec['model_sha256'],comparisons=comparisons,
                    primary_rms_px=comparisons[len(comparisons)//2]['cap_rms_px']))
    pairs=[]
    for key in sorted(set(r['id'] for r in records)):
        weak=next(r for r in records if r['id']==key and r['preset']=='instruction')
        strong=next(r for r in records if r['id']==key and r['preset']=='presentation')
        pairs.extend(a['cap_rms_px']<b['cap_rms_px'] for a,b in zip(weak['comparisons'],strong['comparisons']))
    return dict(status='PASS' if all(pairs) else 'FAIL',renderer_version=__version__,
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        method='Actual preset camera, automatic geometry target/distance, documented frame. Only positive uniform scale and translation fitted to seven body corners. Stud tops reserved. All 3x3 threshold combinations.',
        scope='Two known source images used in recipe selection; not new independent validation or exact camera recovery.',
        instruction_beats_presentation=f'{sum(pairs)}/{len(pairs)}',records=records)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library',required=True,type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args();result=check(args.library)
    if args.output:
        with args.output.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='records'},indent=2))
    raise SystemExit(result['status']!='PASS')
