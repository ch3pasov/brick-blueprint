"""Audit recorded conditional camera tests without rerunning all bootstraps."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

import analyze_volume_camera as camera
from analyze_camera_pvalues import PRIMARY, statistics, fit_pair
import check_fixed_camera_direction as fixed
import camera_pvalue_fit as stable

ROOT = Path(__file__).resolve().parents[1]


def check(path):
    saved = json.loads(path.read_text())
    source = json.loads((ROOT/'docs/research/VOLUME-CAMERA-RESULTS.json').read_text())
    checks = []

    def ok(name, condition):
        checks.append(dict(name=name, pass_check=bool(condition)))

    for name, expected in saved['source_hashes'].items():
        ok(name+' hash', hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected)
    ok('two distinct source identities', len({r['id'] for r in saved['rows']})==2)
    ok('three thresholds per source', all(sum(r['id']==key for r in saved['rows'])==3 for key in PRIMARY))
    diagnostics = []
    for row in saved['rows']:
        tag = row['id']+'/'+str(row['threshold'])
        data = next(r for r in source['rows'] if r['id']==row['id'] and r['threshold']==row['threshold'])
        xyz, uv = np.array(data['world_xyz']), np.array(data['points'])
        p0, p1 = np.array(row['fixed_parameters']), np.array(row['free_parameters'])
        rss0 = np.sum((camera.predict(p0, xyz)-uv)**2)
        rss1 = np.sum((camera.predict(p1, xyz)-uv)**2)
        ok(tag+' RSS0', abs(rss0-row['rss_fixed'])<1e-9)
        ok(tag+' RSS1', abs(rss1-row['rss_free'])<1e-9)
        angles = camera.local_view(dict(parameters=p0))
        ok(tag+' null local direction', max(abs(angles[k]-35) for k in ['azimuth','elevation'])<1e-10)
        ok(tag+' fourteen coordinates', uv.shape==(7,2))
        stat = statistics(rss0, rss1)
        ok(tag+' F replay', abs(stat['F']-row['statistics']['F'])<1e-9)
        ok(tag+' approximate p replay', abs(stat['approximate_F_p']-row['statistics']['approximate_F_p'])<1e-12)
        columns = []
        for k in range(9):
            hi, lo = p1.copy(), p1.copy()
            step = 1e-5*max(1,abs(p1[k]))
            hi[k] += step
            lo[k] -= step
            columns.append(((camera.predict(hi,xyz)-camera.predict(lo,xyz))/(2*step)).ravel())
        jac = np.array(columns).T
        jac /= np.linalg.norm(jac,axis=0)
        s = np.linalg.svd(jac,compute_uv=False)
        rank = int(sum(s>1e-9*s[0]))
        ok(tag+' local free camera rank9', rank==9)
        diagnostics.append(dict(id=row['id'],threshold=row['threshold'],scaled_J_condition=float(s[0]/s[-1]),rank=rank))
        if row['primary']:
            ok(tag+' primary threshold', PRIMARY[row['id']]==row['threshold'])
            boot = row['bootstrap']
            trials = boot['trials']
            ok(tag+' all1999 retained', len(trials)==boot['draws']==1999)
            ok(tag+' finite statistics', all(np.isfinite(t['F']) for t in trials))
            ok(tag+' nested fits', all(0<=t['rss_free']<=t['rss_fixed']+1e-8 for t in trials))
            ok(tag+' every camera RSS stabilized',all(t[which].get('restart_RSS_change',1)<1e-10 for t in trials for which in ['fixed_fit','free_fit']))
            ok(tag+' all simulation F values',all(abs(t['F']-max(0,(t['rss_fixed']/t['rss_free']-1)*2.5))<1e-8 for t in trials))
            k = sum(t['F']>=stat['F'] for t in trials)
            ok(tag+' exceedance count', k==boot['exceedances'])
            ok(tag+' plus-one bootstrap p', abs((k+1)/2000-boot['p'])<1e-15)
            ok(tag+' all null noise scale', abs(boot['coordinate_sigma_px']**2-rss0/7)<1e-12)
            diagnostics[-1].update(draws_at_iteration_limit=sum(t['iterations']>=1000 for t in trials),
                                   orthographic_limit_fits=sum(t['inverse_distance']==0 for t in trials))
            # Fixed indices: restart eight saved simulations, then refine both fits.
            rng=np.random.default_rng(boot['seed'])
            prediction=np.array(row['fixed_fit']['prediction'])
            audits=[]
            for index in range(boot['draws']):
                simulated=prediction+rng.normal(0,boot['coordinate_sigma_px'],prediction.shape)
                if index not in [0,99,999,1998]:
                    continue
                h0,h1,s0,s1=fit_pair(simulated,xyz,p0)
                h0b=stable.fit(simulated,xyz,h0,restricted=True,maxiter=1000)
                h1b=stable.fit(simulated,xyz,h1,maxiter=1000)
                new0,new1=h0b['rss'],h1b['rss']
                replay_F=statistics(s0,s1)['F']
                refined_F=statistics(new0,new1)['F']
                ok(tag+' simulation replay '+str(index),abs(replay_F-trials[index]['F'])<1e-7)
                ok(tag+' simulation refinement '+str(index),abs(refined_F-replay_F)<1e-5)
                audits.append(dict(index=index,refinement_F_change=float(refined_F-replay_F)))
            diagnostics[-1]['refit_audits']=audits
    # Independent numerical integration of the F(2,5) density after t=u/(1-u).
    for value in [.0620548604198,.4770791909128,5.78613504335]:
        u0 = value/(1+value)
        u = np.linspace(u0,1-1e-9,100001)
        t = u/(1-u)
        integral = np.trapezoid((1+2*t/5)**(-3.5)/(1-u)**2,u)
        exact = (5/(5+2*value))**2.5
        ok('F tail integral '+str(value), abs(integral-exact)<1e-7)
    # A separate known-camera positive/negative control; not a false-positive-rate estimate.
    datum=source['rows'][1]
    xyz=np.array(datum['world_xyz'])
    base=np.array(datum['camera']['parameters'])
    distance=np.linalg.norm(camera.local_view(datum['camera'])['eye_relative_to_brick_center_ldu'])
    rng=np.random.default_rng(2026110301)
    controls=[]
    for azimuth,elevation in [(35,35),(30,40)]:
        a,e=np.radians([azimuth,elevation])
        eye=distance*np.array([np.sin(a)*np.cos(e),-np.sin(e),np.cos(a)*np.cos(e)])
        t=-camera.basis(*base[:3])@eye
        parameters=np.r_[base[:3],np.log(t[2]),base[4],t[:2],base[7:9]]
        uv=camera.predict(parameters,xyz)+rng.normal(0,.3,(7,2))
        h0,h1,s0,s1=fit_pair(uv,xyz,parameters)
        stat=statistics(s0,s1)
        ok('synthetic '+str((azimuth,elevation)),stat['approximate_F_p']>.05 if azimuth==35 else stat['approximate_F_p']<.001)
        controls.append(dict(known_angles=[azimuth,elevation],statistics=stat))
    return dict(status='PASS' if all(r['pass_check'] for r in checks) else 'FAIL',
                checks=len(checks), failed=[r['name'] for r in checks if not r['pass_check']],
                diagnostics=diagnostics,synthetic_controls=controls,
                limits='Numerical consistency only. Gaussian independent-corner errors, a shared-edge covariance model and population representativeness are not validated.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,default=ROOT/'docs/research/CAMERA-PVALUES.json')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    result=check(args.data)
    if args.output:
        args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    raise SystemExit(result['status']!='PASS')
