"""Replay preprint 0.2 angles from published numeric landmarks (NumPy only).

This does not re-extract landmarks or validate the camera assumptions.
No official illustrations, fonts, or CAD library are required.
"""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np

def angles(grid, xy):
    design = np.column_stack([np.ones(len(grid)), grid])
    coefficients = np.linalg.lstsq(design, xy, rcond=None)[0]
    _, singular, vectors = np.linalg.svd(coefficients[1:].T)
    result = [float(np.degrees(np.arctan2(abs(vectors[0, 1]), abs(vectors[0, 0])))),
              float(np.degrees(np.arcsin(singular[1] / singular[0])))]
    residual = xy - design @ coefficients
    return result, float(np.sqrt(np.mean(np.sum(residual**2, axis=1))))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path(__file__).resolve().parents[1] / 'docs/research/CAMERA-CATALOGUE-DATA.json')
    parser.add_argument('--output', type=Path, required=True, help='New directory; never overwrite a prior replay.')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output directory already exists; select a new directory.')
    source = json.loads(args.input.read_text())
    results = []
    largest_difference = 0.0
    for record in source['records']:
        for trial in record['trials']:
            points = np.array(trial['centers'], float)
            grid = points[:, :2]
            xy = points[:, 2:4].copy()
            xy[:, 1] *= record['aspect']
            estimate, rms = angles(grid, xy)
            difference = float(np.max(np.abs(np.array(estimate) - trial['reference_angles_deg'])))
            largest_difference = max(largest_difference, difference)
            assert difference < 1e-10, (record['id'], trial['threshold'], difference)
            assert abs(rms - trial['reference_rms']) < 1e-10
            results.append(dict(id=record['id'], threshold=trial['threshold'], primary_cap_set=record['primary_cap_set'], n=len(points), angles_deg=estimate, rms=rms))
    # An independently specified orthogonal projection with 30-degree elevation:
    # lengths of two singular axes are 2 and 1; azimuth comes from V's first row.
    grid = np.array([(u, v) for u in range(4) for v in range(4)], float)
    theta = np.radians(20)
    rotation = np.array([[np.cos(theta), np.sin(theta)], [-np.sin(theta), np.cos(theta)]])
    matrix = np.diag([2., 1.]) @ rotation
    test, _ = angles(grid, grid @ matrix.T + [5, 9])
    assert np.max(np.abs(np.array(test) - [20, 30])) < 1e-10
    args.output.mkdir(parents=True)
    report = dict(input_sha256=hashlib.sha256(args.input.read_bytes()).hexdigest(), replayed_trials=len(results), max_angle_difference_deg=largest_difference, numerical_control='20-degree azimuth / 30-degree elevation recovered', scope='Numeric replay only; does not establish independent samples, calibrated uncertainty, source segmentation, or actual LEGO camera.', results=results)
    (args.output / 'REPLAY.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ['replayed_trials', 'max_angle_difference_deg', 'numerical_control']}, indent=2))

if __name__ == '__main__':
    main()
