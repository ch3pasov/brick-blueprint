"""Refit the measured-left face law on all 17 known colors.

Retrospective summary only. Existing frozen ten-color tests and runtime palette
are not refitted. The objective is clipped squared error; reporting uses MAE.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def analyze(path):
    import numpy as np
    from analyze_color_law import gain_fit, metrics

    data = json.loads(path.read_text())
    rows = data['protocol']['rows']
    assert len(rows) == len({r['code'] for r in rows}) == 17
    x = np.array([r['faces']['left'] for r in rows], float)
    results = {}
    for face, display_gain in [('top', 1.08), ('right', 1.1144)]:
        y = np.array([r['faces'][face] for r in rows], float)
        gain = float(gain_fit(x / 255, y / 255))
        full = np.clip(gain * x, 0, 255)
        displayed = np.clip(display_gain * x, 0, 255)
        folds, channel_folds = [], []
        for i, row in enumerate(rows):
            keep = np.arange(len(rows)) != i
            fold_gain = float(gain_fit(x[keep] / 255, y[keep] / 255))
            pred = np.clip(fold_gain * x[i], 0, 255)
            channel_gain = [float(gain_fit(x[keep, j] / 255, y[keep, j] / 255)) for j in range(3)]
            channel_folds.append(np.clip(channel_gain * x[i], 0, 255))
            folds.append(dict(excluded_code=row['code'], training_codes=[r['code'] for j, r in enumerate(rows) if j != i],
                              gain=fold_gain, observed=y[i].tolist(), prediction=pred.tolist()))
        # Independent stationary condition for the unsaturated channels.
        active = gain * x < 255
        independent_gain = float(np.sum(x[active] * y[active]) / np.sum(x[active] ** 2))
        assert abs(independent_gain - gain) < 1e-12
        results[face] = dict(gain=gain, display_gain=display_gain,
                             fitted=metrics(full, y), displayed=metrics(displayed, y),
                             leave_one_color_out=metrics([r['prediction'] for r in folds], y),
                             per_channel_leave_one_color_out=metrics(channel_folds, y),
                             independent_stationary_gain=independent_gain, folds=folds,
                             predictions=[dict(code=r['code'], input_left=x[i].tolist(), observed=y[i].tolist(),
                                               fitted=full[i].tolist(), displayed=displayed[i].tolist()) for i, r in enumerate(rows)])
    return dict(scope='Retrospective 17-color summary; measured left input, not LDraw RGB. No new materials or measurements.',
                source='docs/research/COLOR-SPACE-TRANSFER.json', source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                row_count=17, values_per_output=51,
                fit='Minimize sum((clip(k*x,0,255)-y)^2), one shared nonnegative gain per target, 0<=k<=4.',
                metric='Mean absolute encoded-RGB channel error after clipping, before integer rounding.',
                validation='Leave one complete color out; refit on the other 16; average the 17 predictions. Model family is fixed.',
                rows=rows, results=results)


# Other face-color replays use this absolute tolerance in 8-bit RGB units.
# Raw measurements, model IDs, fold membership and source hashes stay exact.
COMPUTED_FIELDS = {'gain', 'fitted', 'displayed', 'prediction', 'leave_one_color_out',
                   'per_channel_leave_one_color_out', 'independent_stationary_gain'}


def check_replay(saved, current, path=(), computed=False):
    """Report the first substantive difference, including its location in the record."""
    if isinstance(saved, dict) and isinstance(current, dict) and saved.keys() == current.keys():
        for key in saved:
            derived = computed or (path[:1] == ('results',) and key in COMPUTED_FIELDS)
            check_replay(saved[key], current[key], (*path, key), derived)
        return
    if isinstance(saved, list) and isinstance(current, list) and len(saved) == len(current):
        for i, (before, after) in enumerate(zip(saved, current)):
            check_replay(before, after, (*path, str(i)), computed)
        return
    if computed and type(saved) is float and type(current) is float:
        if math.isfinite(saved) and math.isfinite(current) and math.isclose(saved, current, rel_tol=0, abs_tol=1e-10):
            return
    elif type(saved) is type(current) and saved == current:
        return
    raise ValueError('Saved results differ from numerical replay at ' + '.'.join(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=ROOT/'docs/research/COLOR-SPACE-TRANSFER.json')
    parser.add_argument('--output', type=Path, default=ROOT/'docs/research/FACE-LAW-17.json')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = analyze(args.data)
    if args.check:
        try:
            check_replay(json.loads(args.output.read_text()), result)
        except ValueError as error:
            parser.exit(1, str(error) + '\n')
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({face: {k: result['results'][face][k] for k in ['gain', 'fitted', 'leave_one_color_out', 'per_channel_leave_one_color_out']} for face in ['top', 'right']}, indent=2))


if __name__ == '__main__':
    main()
