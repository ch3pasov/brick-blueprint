"""Render the frozen four-color experiment using an external LDraw library.

Each material has two explicitly different inputs: nominal LDraw RGB, or a
measured left face. Both illustrations use identical geometry and camera.
No official artwork is read or copied.
"""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from brick_blueprint.pipeline import render
from brick_blueprint import __version__

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--library',required=True,type=Path)
    ap.add_argument('--data',type=Path,default=ROOT/'docs/research/PALETTE-HOLDOUT-2025.json')
    ap.add_argument('--output',required=True,type=Path)
    args=ap.parse_args()
    if args.output.exists():ap.error('Choose a new output folder')
    args.output.mkdir(parents=True)
    data=json.loads(args.data.read_text());records=[]
    for row in data['observations']:
        if not row['primary']:continue
        code=row['identity']['code'];model=args.output/f'{code}.ldr'
        model.write_text(f'0 New color control\n1 {code} 0 0 0 1 0 0 0 1 0 0 0 1 3003.dat\n')
        for key in ('nominal_current','measured_left_law'):
            values=row[key]['prediction'];left,top,right=values
            style=json.loads((ROOT/'brick_blueprint/default-style.json').read_text())
            style['palette']={str(code):dict(side=left,top=top,front=right,confidence='Frozen formula output; primary color never in fitting. Measured-left variant explicitly requires observed left input.')}
            sp=args.output/f'{code}-{key}-style.json';sp.write_text(json.dumps(style,indent=2)+'\n')
            folder=args.output/f'{code}-{key}'
            receipt=render(model,args.library,folder,style_path=sp,camera_preset='instruction',width=300,height=240,line_width=.4,background=tuple(data['drawing_background_RGB']),cache_dir=ROOT/'.brickblueprint-cache')
            assert receipt['pdf']['image_XObjects']==0
            records.append(dict(id=f'palette-holdout-{code}-{key}',folder=folder.name,code=code,variant=key,prediction=values,input_RGB=row['identity']['input_RGB']if key=='nominal_current'else row['faces']['left'],camera=receipt['camera'],model_sha256=receipt['model_sha256'],receipt_sha256=hashlib.sha256((folder/'render.json').read_bytes()).hexdigest(),PDF_sha256=receipt['pdf']['PDF_sha256']))
            print(code,key,flush=True)
    (args.output/'renders.json').write_text(json.dumps(dict(version=__version__,recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),data_sha256=hashlib.sha256(args.data.read_bytes()).hexdigest(),records=records),indent=2)+'\n')

if __name__=='__main__':main()
