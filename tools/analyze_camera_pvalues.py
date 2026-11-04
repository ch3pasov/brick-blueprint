"""Conditional perspective-camera angle tests; no official artwork required.

Two selected source images, not population inference. Model: independent
isotropic Gaussian errors of the seven measured body-corner coordinates.
Parametric bootstrap refits both cameras on each simulation under H0=35/35.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np

import analyze_volume_camera as camera
import check_fixed_camera_direction as fixed
import camera_pvalue_fit as stable

ROOT = Path(__file__).resolve().parents[1]
PRIMARY = {'11038-p19-X1': 50, '11037-p8-X2': 145}


def statistics(rss0, rss1):
    f = max(0., (rss0-rss1)/2/(rss1/5))
    return dict(F=f, df=[2, 5], approximate_F_p=(5/(5+2*f))**2.5)


def fit_pair(uv, xyz, initial):
    restricted,free=stable.refine_pair(uv,xyz,initial)
    restricted['parameters']=stable.legacy_parameters(restricted)
    free['parameters']=stable.legacy_parameters(free)
    for value in [restricted,free]:value['rms_px']=math.sqrt(value['rss']/len(xyz))
    rss0,rss1=restricted['rss'],free['rss']
    if rss1 > rss0 + 1e-8:
        raise RuntimeError('Free camera fit is worse than its nested restricted start')
    return restricted, free, rss0, rss1


def wilson(k, n):
    z = 1.959963984540054
    center = (k/n+z*z/(2*n))/(1+z*z/n)
    half = z*math.sqrt(k/n*(1-k/n)/n+z*z/(4*n*n))/(1+z*z/n)
    return [max(0., center-half), min(1., center+half)]


def analyze(draws, seed, output):
    data_path = ROOT/'docs/research/VOLUME-CAMERA-RESULTS.json'
    fixed_path = ROOT/'docs/research/FIXED-DIRECTION-VALIDATION.json'
    data = json.loads(data_path.read_text())
    reference = json.loads(fixed_path.read_text())
    rows = []
    for source in data['rows']:
        uv, xyz = np.array(source['points']), np.array(source['world_xyz'])
        h0, h1, rss0, rss1 = fit_pair(uv, xyz, np.array(source['camera']['parameters']))
        saved = next(r['camera'] for r in reference['fixed_direction_fits'] if r['id']==source['id'] and r['threshold']==source['threshold'])
        assert abs(h0['rms_px']-saved['rms_px']) < 1e-6
        assert abs(h1['rms_px']-source['camera']['rms_px']) < 1e-6
        rows.append(dict(id=source['id'], threshold=source['threshold'], primary=source['threshold']==PRIMARY[source['id']],
                         n_corners=7, n_coordinates=14, rss_fixed=rss0, rss_free=rss1,
                         local_angles=dict(zip(['azimuth','elevation'],h1['local_angles'])), statistics=statistics(rss0, rss1),
                         fixed_parameters=h0['parameters'], free_parameters=h1['parameters'],
                         fixed_fit=h0,free_fit=h1))
    main = [r for r in rows if r['primary']]
    for i, row in enumerate(main):
        source = next(r for r in data['rows'] if r['id']==row['id'] and r['threshold']==row['threshold'])
        xyz = np.array(source['world_xyz'])
        initial = row['fixed_fit']
        null_prediction = np.array(row['fixed_fit']['prediction'])
        sigma = math.sqrt(row['rss_fixed']/7)
        rng = np.random.default_rng(seed+i)
        trials = []
        start = time.monotonic()
        for b in range(draws):
            uv = null_prediction+rng.normal(0, sigma, null_prediction.shape)
            h0, h1, rss0, rss1 = fit_pair(uv, xyz, initial)
            stat = statistics(rss0, rss1)
            trials.append(dict(F=stat['F'], rss_fixed=rss0, rss_free=rss1,
                               inverse_distance=h1['inverse_distance'],
                               local_angles=h1['local_angles'], iterations=h1['iterations'],
                               fixed_fit=h0,free_fit=h1))
            if (b+1) % 100 == 0:
                print(row['id'], b+1, '/', draws, 'seconds', round(time.monotonic()-start, 1), flush=True)
        k = sum(t['F'] >= row['statistics']['F'] for t in trials)
        row['bootstrap'] = dict(draws=draws, seed=seed+i, coordinate_sigma_px=sigma,
                                exceedances=k, p=(k+1)/(draws+1),
                                MC_probability_wilson95=wilson(k, draws),
                                normal_model_F05_rejection_fraction=sum(t['F']>5*(.05**(-.4)-1)/2 for t in trials)/draws,
                                trials=trials)
    rss0, rss1 = [sum(r[k] for r in main) for k in ['rss_fixed', 'rss_free']]
    f = (rss0-rss1)/4/(rss1/10)
    x = 10/(10+4*f)
    result = dict(schema_version=1, date='2026-11-03',
                  null='Both local eye angles of each selected brick are exactly35 degrees; camera roll, optical rotation, focus and framing remain free.',
                  error_model='Independent isotropic Gaussian errors of seven body corners (14 coordinates) per image; systematic/shared-edge error is not calibrated.',
                  method='Restricted7 versus free9 parameter perspective cameras; four framing parameters eliminated by linear least squares; inverse distance includes the orthographic limit. F statistic, approximate F(2,5) tail and refitted parametric null bootstrap.',
                  scope='Two Classic2024 images, not a population of LEGO cameras. Thresholds repeat the same images.',
                  rows=rows,
                  pooled_common_variance=dict(F=f, df=[4,10], approximate_p=x**5*(6-5*x),
                                              condition='Exploratory only: independent source errors and a common Gaussian coordinate variance.'),
                  source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [data_path, fixed_path]})
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({r['id']:dict(F=r['statistics']['F'], approximate_p=r['statistics']['approximate_F_p'], bootstrap_p=r['bootstrap']['p'], MC_interval=r['bootstrap']['MC_probability_wilson95']) for r in main}, indent=2), flush=True)
    print('pooled', result['pooled_common_variance'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--draws', type=int, default=1999)
    parser.add_argument('--seed', type=int, default=20261103)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    analyze(args.draws, args.seed, args.output)
