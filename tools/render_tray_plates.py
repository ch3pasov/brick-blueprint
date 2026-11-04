"""Render three small inventory plates from real instruction steps."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brick_blueprint.tray import render_tray


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    source = json.loads((ROOT / 'docs/ACTUAL-STEP-EXAMPLES.json').read_text())
    index = []
    for style in ('modern-blue', 'speed-chamfer', 'botanicals-slate'):
        row = next(sample for sample in source['examples'] if sample['preset'] == style)
        manifest = ROOT / row['manifest']
        folder = args.output / style
        receipt = render_tray(manifest, args.library, folder, preset=style,
                              camera_preset='instruction', width=320, height=180,
                              columns=2, gap=12, line_width=0.45)
        svg = (folder / 'model.svg').read_bytes()
        sha = hashlib.sha256(svg).hexdigest()
        if sha != receipt['pdf']['SVG_sha256'] or receipt['pdf']['image_XObjects']:
            raise ValueError('Unexpected output for ' + style)
        (args.output / (style + '.svg')).write_bytes(svg)
        index.append(dict(preset=style, set=row['set'], page=row['pdf_page'],
                          step=row['step'], manifest=row['manifest'], svg_sha256=sha,
                          model_sha256=[entry['model_sha256'] for entry in receipt['items']],
                          points_per_ldu=receipt['points_per_ldu'],
                          dependencies=sorted({dep['file'] for item in receipt['items']
                                               for dep in item['dependencies']})))
    (args.output / 'trays.json').write_text(json.dumps(index, indent=2) + '\n')


if __name__ == '__main__':
    main()
