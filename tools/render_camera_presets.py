"""Generate instruction-camera examples using an external LDraw library.

Only native vector artwork and numeric receipts are generated. Official pixels
are kept outside the public repository.
"""
import argparse
import json
import hashlib
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from brick_blueprint.pipeline import render
from brick_blueprint.camera_presets import all_camera_presets
from brick_blueprint import __version__


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists():parser.error('Choose a new output directory')
    args.output.mkdir(parents=True)
    rows=[]
    for name in all_camera_presets():
        for key,model in [('plate',ROOT/'examples/parts/blue-plate-2x8.ldr'),
                          ('kiosk',ROOT/'examples/kiosk/kiosk.mpd')]:
            out=args.output/(key+'-'+name)
            r=render(model,args.library,out,camera_preset=name,width=400,height=300,
                     preset='creator-blue',line_width=.6,glass_opacity=.9,
                     cache_dir=ROOT/'.brickblueprint-cache')
            rows.append(dict(id=out.name,camera=r['camera'],model_sha256=r['model_sha256'],
                             receipt_sha256=hashlib.sha256((out/'render.json').read_bytes()).hexdigest()))
            print(out.name,flush=True)
    (args.output/'camera-presets.json').write_text(json.dumps(dict(version=__version__,
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),renders=rows),indent=2)+'\n')


if __name__=='__main__':main()
