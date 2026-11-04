"""Render the five README models using the same camera and material profile."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brick_blueprint.pipeline import render


# Model, backdrop, printed label. The backdrop is independent of the shading.
SCENES = [
    ('kiosk', 'kiosk/kiosk.mpd', 'd4edfc', 'Little Blue Kiosk'),
    ('harbor-pilot', 'portfolio/harbor-pilot.ldr', 'd8e9ee', 'Harbor Pilot'),
    ('rangefinder', 'portfolio/rangefinder.ldr', 'f2dfc5', 'Pocket Rangefinder'),
    ('signal-rocket', 'portfolio/signal-rocket.ldr', 'dce4ee', 'Signal Rocket'),
    ('courtyard', 'portfolio/courtyard.ldr', 'e3ead6', 'Courtyard in Bloom'),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = []
    for slug, model, background, title in SCENES:
        destination = args.output / slug
        receipt = render(ROOT / 'examples' / model, args.library, destination,
                         width=500, height=320, camera_preset='instruction',
                         line_width=0.55, glass_opacity=0.75, underpaint=True,
                         background=tuple(bytes.fromhex(background)))
        svg = (destination / 'model.svg').read_bytes()
        manifest.append(dict(id=slug, title=title, model='examples/' + model,
                             parts=receipt['parts'], model_sha256=receipt['model_sha256'],
                             svg_sha256=hashlib.sha256(svg).hexdigest(),
                             renderer=receipt['version'], camera=receipt['camera'],
                             underpaint=receipt['underpaint'],
                             image_xobjects=receipt['pdf']['image_XObjects']))
        print(title, flush=True)
    (args.output / 'portfolio.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
