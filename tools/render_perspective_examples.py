"""Reproduce the original-kiosk projection comparison; preserve existing outputs."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from brick_blueprint.pipeline import render

ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('Output already exists; choose a new directory')
    common=dict(material_profile='research',model=ROOT/'examples/kiosk/kiosk.mpd',library=args.library,
                width=400,height=300,azimuth=35,elevation=35,line_width=.6,
                glass_opacity=.9,cache_dir=ROOT/'.brickblueprint-cache')
    perspective=render(output=args.output/'kiosk-perspective',field_of_view=30,**common)
    orthographic=render(output=args.output/'kiosk-orthographic',projection='orthographic',
                        scale=perspective['points_per_ldu'],**common)
    (args.output/'comparison.json').write_text(json.dumps({
        'model_sha256':perspective['model_sha256'],
        'same_target_plane_scale':perspective['points_per_ldu'],
        'perspective_camera':perspective['camera'],
        'orthographic_camera':orthographic['camera'],
        'note':'Same geometry, page, angles, reference scale, materials and ink width. No independent image fitting.'
    },indent=2)+'\n')
    print(args.output)
if __name__=='__main__':main()
