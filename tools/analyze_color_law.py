"""Compare view-specific color transfer laws using whole-color holdouts.

NumPy only; no source artwork or external LDraw library is required. The
measured runtime palette is not changed. RGB errors are not perceptual Delta E.
"""
from pathlib import Path
import argparse, hashlib, itertools, json
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ('identity', 'gain', 'affine', 'linear_gain', 'linear_affine',
              'channel_affine', 'matrix_affine')
PARAMETERS = dict(zip(CANDIDATES, (0, 1, 2, 1, 2, 6, 12)))

def decode(x):
    return np.where(x <= .04045, x / 12.92, ((x + .055) / 1.055) ** 2.4)

def encode(x):
    return np.where(x <= .0031308, x * 12.92, 1.055 * np.maximum(x, 0) ** (1 / 2.4) - .055)

def gain_fit(x, y):
    """Exact minimum of sum((clip(k*x)-y)^2), 0<=k<=4, x>=0."""
    x, y = x.ravel(), y.ravel()
    cuts = np.unique(np.r_[0., 4., 1 / x[x > .25]])
    candidates = list(cuts)
    for lo, hi in zip(cuts[:-1], cuts[1:]):
        active = x * ((lo + hi) / 2) < 1
        xx, yy = x[active], y[active]
        if xx @ xx > 0:
            candidates.append(float(np.clip((xx @ yy) / (xx @ xx), lo, hi)))
    return min(candidates, key=lambda k: np.sum((np.clip(k * x, 0, 1) - y) ** 2))

def polygon_clip(poly, normal, limit):
    out = []
    for a, b in zip(poly, poly[1:] + poly[:1]):
        da, db = normal @ a - limit, normal @ b - limit
        if da <= 1e-12:
            out.append(a)
        if (da < 0) != (db < 0):
            out.append(a + (b - a) * da / (da - db))
    return out

def affine_fit(x, y):
    """Global clipped-affine LS over 0<=a<=4, -1<=b<=1.

    Enumerate all lower-clipped / active / upper-clipped channel partitions.
    On each convex parameter polygon, test the quadratic stationary point,
    every vertex and each edge minimum. No iterative local optimizer.
    """
    x, y = x.ravel(), y.ravel()
    u = np.unique(x)
    best, cost = None, float('inf')
    for i in range(len(u) + 1):
        for j in range(i, len(u) + 1):
            poly = [np.array(p, dtype=float) for p in [(0, -1), (4, -1), (4, 1), (0, 1)]]
            constraints = []
            if i:
                constraints.append((np.array([u[i-1], 1]), 0))
            if j > i:
                constraints += [(np.array([-u[i], -1]), 0), (np.array([u[j-1], 1]), 1)]
            if j < len(u):
                constraints.append((np.array([-u[j], -1]), -1))
            for normal, limit in constraints:
                poly = polygon_clip(poly, normal, limit)
                if not poly:
                    break
            if not poly:
                continue
            active = np.zeros(x.shape, dtype=bool) if i == j else (x >= u[i]) & (x <= u[j-1])
            m = np.c_[x[active], np.ones(active.sum())]
            yy = y[active]
            candidates = list(poly)
            if len(m):
                q = np.linalg.lstsq(m, yy, rcond=None)[0]
                if 0 <= q[0] <= 4 and -1 <= q[1] <= 1 and all(n @ q <= b + 1e-10 for n, b in constraints):
                    candidates.append(q)
                for a, b in zip(poly, poly[1:] + poly[:1]):
                    v = m @ (b - a)
                    if v @ v > 1e-24:
                        t = np.clip((v @ (yy - m @ a)) / (v @ v), 0, 1)
                        candidates.append(a + t * (b - a))
            q = np.asarray(candidates)
            errors = np.sum((np.clip(q[:, :1] * x + q[:, 1:] , 0, 1) - y) ** 2, axis=1)
            k = int(np.argmin(errors))
            if errors[k] < cost:
                cost, best = float(errors[k]), q[k]
    return best.tolist()

def fit(name, x, y):
    linear = name.startswith('linear_')
    xx, yy = (decode(x / 255), decode(y / 255)) if linear else (x / 255, y / 255)
    kind = name.removeprefix('linear_')
    if kind == 'identity':
        coeff = []
    elif kind == 'gain':
        coeff = [gain_fit(xx, yy)]
    elif kind == 'affine':
        coeff = affine_fit(xx, yy)
    elif kind == 'channel_affine':
        coeff = [np.linalg.lstsq(np.c_[xx[:, c], np.ones(len(xx))], yy[:, c], rcond=None)[0].tolist() for c in range(3)]
    elif kind == 'matrix_affine':
        coeff = np.linalg.lstsq(np.c_[xx, np.ones(len(xx))], yy, rcond=None)[0].tolist()
    else:
        raise ValueError(name)
    return {'model': name, 'coefficients': coeff, 'parameter_count': PARAMETERS[name], 'unit': 'input/output normalized0..1 before encoding'}

def predict(model, x):
    name, c = model['model'], np.array(model['coefficients'])
    linear = name.startswith('linear_')
    xx = decode(x / 255) if linear else x / 255
    kind = name.removeprefix('linear_')
    if kind == 'identity': y = xx
    elif kind == 'gain': y = c[0] * xx
    elif kind == 'affine': y = c[0] * xx + c[1]
    elif kind == 'channel_affine': y = xx * c[:, 0] + c[:, 1]
    elif kind == 'matrix_affine': y = np.c_[np.atleast_2d(xx), np.ones(len(np.atleast_2d(xx)))] @ c
    else: raise ValueError(name)
    y = np.clip(y, 0, 1)
    return 255 * (encode(y) if linear else y)

def metrics(a, b):
    d = np.abs(np.asarray(a) - np.asarray(b))
    return {'MAE': float(d.mean()), 'max_channel_error': float(d.max()), 'RMSE': float(np.sqrt(np.mean(d*d)))}

def study(data):
    colors = data['colors']
    x = {f: np.array([r['source']['faces'][f] for r in colors]) for f in ('left', 'top', 'right')}
    x['ldraw'] = np.array([r['nominal_RGB'] for r in colors])
    relations = [(a, b) for a in ('left', 'top', 'right', 'ldraw') for b in ('left', 'top', 'right') if a != b]
    results = []
    for source, target in relations:
        for name in CANDIDATES:
            model = fit(name, x[source], x[target]); folds = []
            for i, row in enumerate(colors):
                keep = np.arange(len(colors)) != i
                fold = fit(name, x[source][keep], x[target][keep])
                pred = predict(fold, x[source][i:i+1])[0]
                folds.append(dict(color=row['label'], model=fold, observed_RGB=x[target][i].tolist(),
                                  predicted_RGB=pred.tolist(), error_RGB=(pred-x[target][i]).tolist()))
            transfer = []
            for row in data['transfer']:
                match = next(r for r in colors if r['ldraw_code'] == row['ldraw_code'])
                inp = np.array(match['nominal_RGB'] if source == 'ldraw' else row['faces'][source]['observed'])
                pred = predict(model, inp[None, :])[0]
                obs = np.array(row['faces'][target]['observed'])
                transfer.append(dict(set=row['set'], page=row['page'], image=row['image'], ldraw_code=row['ldraw_code'], predicted_RGB=pred.tolist(), observed_RGB=obs.tolist()))
            results.append(dict(source=source, target=target, model=model,
                training=metrics(predict(model,x[source]),x[target]),
                leave_one_color_out=metrics([r['predicted_RGB']for r in folds],x[target]), folds=folds,
                transfer=metrics([r['predicted_RGB']for r in transfer],[r['observed_RGB']for r in transfer]), transfer_rows=transfer))
        print(source, '->', target, 'complete', flush=True)
    sensitivity = []
    for target in ('top','right'):
        for si, ti in itertools.product(range(9),repeat=2):
            xx = np.array([r['source']['sensitivity']['left']['shifted_medians'][si]['rgb']for r in colors])
            yy = np.array([r['source']['sensitivity'][target]['shifted_medians'][ti]['rgb']for r in colors])
            predictions=[]
            for i in range(len(colors)):
                keep=np.arange(len(colors))!=i
                predictions.append(predict(fit('gain',xx[keep],yy[keep]),xx[i:i+1])[0])
            sensitivity.append(dict(target=target, input_shift_index=si, output_shift_index=ti,
                                    fitted_gain=fit('gain',xx,yy)['coefficients'][0], **metrics(predictions,yy)))
    return dict(protocol_sha256=data['protocol_sha256'], data_source_hashes=data['sources'],
                library_config=data['library_config'], colors=10, training_images=10, transfer_images=12,
                equations=results, primary_sensitivity=sensitivity,
                limits=data['protocol']['identifiability'], selection='All candidates reported. Primary clipped gain from left was declared before fitting. Other model rankings are descriptive; no post-selection probability claim.')

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',type=Path,default=ROOT/'docs/research/COLOR-LAW-DATA.json')
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();raw=args.data.read_bytes();result=study(json.loads(raw))
    result['data_sha256']=hashlib.sha256(raw).hexdigest()
    result['analysis_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with args.output.open('x') as f: f.write(json.dumps(result,indent=2)+'\n')
