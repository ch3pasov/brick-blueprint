"""Render matched vector pairs for the opt-in empirical slope profile.

Only supplied DAT geometry is read. Official instruction artwork is excluded.
Both images in each pair retain exactly the same camera, model and frame.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brick_blueprint import __version__
from brick_blueprint.pipeline import render

CASES = [
    ('white-low', '60477', 15, 270, '18.435 degree white slope'),
    ('gray-low', '60477', 71, 270, '18.435 degree light gray slope'),
    ('white-shallow', '85984', 15, 270, '30.964 degree white slope'),
    ('brown-steep', '3678b', 70, 270, '65.556 degree brown slope'),
    ('white-steep', '3678b', 15, 270, '65.556 degree white slope'),
    ('white-right', '30363', 15, 180, '18.435 degree right-facing slope'),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pdftoppm', default='pdftoppm')
    parser.add_argument('--font', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    rows = []
    for key, part, color, yaw, label in CASES:
        c, s = round(math.cos(math.radians(yaw))), round(math.sin(math.radians(yaw)))
        model = args.output / (key + '.ldr')
        model.write_text(f'0 Single-part angular material comparison\n1 {color} 0 0 0 {c} 0 {s} 0 1 0 {-s} 0 {c} {part}.dat\n')
        pair = {}
        for mode in ('research', 'research-angular'):
            folder = args.output / (key + '-' + mode)
            receipt = render(model, args.library, folder, material_profile=mode,
                             width=450, height=300, azimuth=35, elevation=35,
                             field_of_view=2, line_width=.65, background=(255, 255, 255),
                             cache_dir=ROOT / '.brickblueprint-cache')
            assert receipt['pdf']['image_XObjects'] == 0
            pair[mode] = receipt
            if args.font:
                subprocess.run([args.pdftoppm, '-r', '144', '-singlefile', '-png',
                                str(folder / 'model.pdf'), str(folder / 'preview')],
                               check=True, capture_output=True, timeout=60)
        a, b = pair.values()
        assert a['camera'] == b['camera'] and a['model_sha256'] == b['model_sha256']
        rows.append({'id': key, 'label': label, 'part': part, 'color': color, 'yaw': yaw,
                     'camera': a['camera'], 'model_sha256': a['model_sha256'],
                     'renders': {mode: {'folder': key + '-' + mode,
                         'receipt_sha256': hashlib.sha256((args.output / (key + '-' + mode) / 'render.json').read_bytes()).hexdigest(),
                         'PDF_sha256': receipt['pdf']['PDF_sha256'], 'SVG_sha256': receipt['pdf']['SVG_sha256']}
                         for mode, receipt in pair.items()}})
        print(key, flush=True)
    report = {'version': __version__, 'recipe_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'scope': 'Matched own geometry/cameras. Official source cameras are not fitted here. No source images bundled.', 'rows': rows}
    if args.font:
        from PIL import Image, ImageDraw, ImageFont
        font = lambda size: ImageFont.truetype(str(args.font), size)
        board = Image.new('RGB', (1160, 110 + 270 * len(rows)), '#f3f8fa')
        draw = ImageDraw.Draw(board)
        draw.text((25, 15), 'SLOPE COLORS. SAME CAMERA AND GEOMETRY.', font=font(30), fill='#183744')
        draw.text((25, 65), 'Research: three-face blend', font=font(23), fill='#183744')
        draw.text((590, 65), 'Research-angular: opt-in slope model', font=font(23), fill='#183744')
        for i, row in enumerate(rows):
            y = 110 + i * 270
            for j, mode in enumerate(('research', 'research-angular')):
                image = Image.open(args.output / row['renders'][mode]['folder'] / 'preview.png').convert('RGB')
                # Identical full-frame resize; no individual camera fit or crop.
                image = image.resize((330, 220), Image.Resampling.LANCZOS)
                board.paste(image, (100 + j * 570, y))
            draw.text((25, y + 228), row['label'], font=font(22), fill='#183744')
        output = args.output / 'angular-material-pairs.png'
        board.save(output)
        report['preview_sha256'] = hashlib.sha256(output.read_bytes()).hexdigest()
    (args.output / 'angular-examples.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
