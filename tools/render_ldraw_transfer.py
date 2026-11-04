"""Render all nested color-holdout predictions; no official artwork is used."""
from pathlib import Path
import argparse,json,hashlib,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from brick_blueprint.pipeline import render
from brick_blueprint import __version__

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--library',required=True,type=Path);p.add_argument('--data',required=True,type=Path);p.add_argument('--results',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
 if a.output.exists():p.error('Choose a new output directory')
 a.output.mkdir(parents=True);data=json.loads(a.data.read_text());results=json.loads(a.results.read_text());records=[]
 for row,fold in zip(data['colors'],results['folds']):
  assert row['code']==fold['color_code']
  code=row['code'];model=a.output/f'{code}.ldr';model.write_text(f'0 Whole-color held-out RGB prediction\n1 {code} 0 0 0 1 0 0 0 1 0 0 0 1 3003.dat\n')
  style=json.loads((ROOT/'brick_blueprint/default-style.json').read_text());L,T,R=fold['prediction']
  style['palette']={str(code):dict(side=L,top=T,front=R,confidence='Computed from RGB-only outer-fold model; entire color excluded from fitting and model selection.')}
  sp=a.output/f'{code}-style.json';sp.write_text(json.dumps(style,indent=2)+'\n');folder=a.output/f'color-{code}'
  r=render(model,a.library,folder,style_path=sp,camera_preset='instruction',width=300,height=240,line_width=.4,background=(255,255,255),cache_dir=ROOT/'.brickblueprint-cache')
  assert r['pdf']['image_XObjects']==0
  records.append(dict(id=f'ldraw-transfer-{code}',folder=folder.name,code=code,input_RGB=row['input_RGB'],prediction=fold['prediction'],model=fold['model'],camera=r['camera'],model_sha256=r['model_sha256'],receipt_sha256=hashlib.sha256((folder/'render.json').read_bytes()).hexdigest(),PDF_sha256=r['pdf']['PDF_sha256']))
  print('color',code,flush=True)
 (a.output/'renders.json').write_text(json.dumps(dict(version=__version__,recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),data_sha256=hashlib.sha256(a.data.read_bytes()).hexdigest(),results_sha256=hashlib.sha256(a.results.read_bytes()).hexdigest(),records=records),indent=2)+'\n')
if __name__=='__main__':main()
