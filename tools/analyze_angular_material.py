"""Replay numeric slope observations and the implemented opt-in material rule.

This is an arithmetic and renderer-consistency check. Original PDF pixels are
not included; fresh extraction requires the separately cited source files.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brick_blueprint.angular_style import sector_color
from brick_blueprint.style import load_style


def analyze(root=ROOT):
    path = root / 'docs/research/ANGULAR-MATERIAL-CANDIDATE.json'
    data = json.loads(path.read_text())
    style = load_style(material_profile='research-angular')
    n = 0

    def check(value, label):
        nonlocal n
        n += 1
        if not value:
            raise ValueError(label)

    check(style.angular['data_sha256'] == hashlib.sha256(path.read_bytes()).hexdigest(), 'data binding')
    check(style.angular['method'] == data['method'], 'method binding')
    for source in data['supporting_numeric_files']:
        check(hashlib.sha256((root / source['file']).read_bytes()).hexdigest() == source['sha256'], 'supporting data')
    seen = set()
    for row in data['rows']:
        check(row['image_hash'] not in seen, 'unique image accounting')
        seen.add(row['image_hash'])
        code = row['palette_code']
        p = style.data['palette'][str(code)]
        theta = math.radians(row['theta'])
        normal = (math.sin(theta), -math.cos(theta), 0) if row['side'] == 'left' else (0, -math.cos(theta), math.sin(theta))
        actual = style.face(code, (0, 0, 0), normal, 'body')
        expected = row['predictions']['candidate']
        check(max(abs(a - b) for a, b in zip(actual, expected)) < 1e-9, 'runtime prediction')
        # Independent directional-light solution A*cos(theta)+B*sin(theta)
        # between the two endpoints, rather than reusing interpolation weights.
        knots = data['method'][row['side'] + '_knots_deg']
        i = next(i for i in range(len(knots) - 1) if knots[i] <= row['theta'] <= knots[i + 1])
        a, b = [math.radians(k) for k in knots[i:i + 2]]
        endpoints = [sector_color(p, code, k, row['side'], data['method']) for k in knots[i:i + 2]]

        def decode(c):
            v = c / 255
            return v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4

        def encode(v):
            v = min(1, max(0, v))
            return 255 * (v * 12.92 if v <= .0031308 else 1.055 * v ** (1 / 2.4) - .055)

        determinant = math.cos(a) * math.sin(b) - math.cos(b) * math.sin(a)
        for channel in range(3):
            ca, cb = (decode(c[channel]) for c in endpoints)
            A = (ca * math.sin(b) - cb * math.sin(a)) / determinant
            B = (math.cos(a) * cb - math.cos(b) * ca) / determinant
            check(abs(encode(A * math.cos(theta) + B * math.sin(theta)) - expected[channel]) < 1e-8, 'independent light solve')
        check({(q['dx'], q['dy']) for q in row['measurements']} == {(x, y) for x in [-1, 0, 1] for y in [-1, 0, 1]}, 'complete window shifts')
        for q in row['measurements']:
            for name, prediction in row['predictions'].items():
                errors = [abs(a - b) for a, b in zip(prediction, q['RGB'])]
                saved = q['scores'][name]
                check(abs(sum(errors) / 3 - saved['MAE']) < 1e-10, 'MAE')
                check(max(errors) == saved['max_channel_error'], 'maximum channel')
                check(saved['pass'] == (sum(errors) / 3 <= 3 and max(errors) <= 10), 'window gate')
        for model in row['predictions']:
            check(row['pass'][model] == all(q['scores'][model]['pass'] for q in row['measurements']), 'all windows')
    for group, scores in data['scores'].items():
        rows = [r for r in data['rows'] if group == 'all' or r['batch'] == group]
        for name, saved in scores.items():
            check(saved['n'] == len(rows), 'cohort size')
            check(saved['pass'] == sum(r['pass'][name] for r in rows), 'cohort passes')
            mean = statistics.mean(next(q for q in r['measurements'] if q['dx'] == q['dy'] == 0)['scores'][name]['MAE'] for r in rows)
            check(abs(mean - saved['MAE']) < 1e-10, 'cohort mean')
    return {'status': 'PASS', 'checks': n, 'data_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'scope': 'Numerical replay and implemented material consistency; not fresh source-pixel extraction.',
            'scores': data['scores']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = analyze()
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
