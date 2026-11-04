"""Render measured, held-out face-law and held-out nominal-LDraw controls.

Only own DAT renders. Supply the library separately. Formula fits omit the
displayed color entirely; measured-left input is disclosed, never a prediction.
"""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from brick_blueprint.pipeline import render
from brick_blueprint import __version__

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--library',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 a.output.mkdir(parents=True,exist_ok=False)
 data=json.loads((ROOT/'docs/research/COLOR-LAW-DATA.json').read_text());results=json.loads((ROOT/'docs/research/COLOR-LAW-RESULTS.json').read_text())
 def prediction(source,target,label):
  r=next(r for r in results['equations']if r['source']==source and r['target']==target and r['model']['model']=='gain')
  return next(f for f in r['folds']if f['color']==label)['predicted_RGB']
 records=[]
 for code in [191,70,28,0]:
  row=next(r for r in data['colors']if r['ldraw_code']==code);model=a.output/f'brick-{code}.ldr'
  model.write_text(f'0 Fixed camera color law control\n1 {code} 0 0 0 1 0 0 0 1 0 0 0 1 3003.dat\n')
  measured=row['source']['faces'];label=row['label'];camera=None
  for mode in ['reference','face-law','ldraw-law']:
   rgb={k:measured[k]for k in['left','top','right']}if mode=='reference'else{
    k:measured[k]if mode=='face-law'and k=='left'else prediction('left'if mode=='face-law'else'ldraw',k,label)for k in['left','top','right']}
   style=json.loads((ROOT/'brick_blueprint/default-style.json').read_text())
   style['palette'][str(code)].update(side=rgb['left'],top=rgb['top'],front=rgb['right'])
   style['palette'][str(code)]['confidence']=('measured reference anchors' if mode=='reference' else
       'held-out color formula control; measured left is supplied' if mode=='face-law' else
       'held-out color formula control from nominal LDraw RGB')
   sp=a.output/f'{code}-{mode}.json';sp.write_text(json.dumps(style,indent=2)+'\n')
   folder=a.output/f'{code}-{mode}'
   receipt=render(model,a.library,folder,style_path=sp,projection='perspective',azimuth=35,elevation=35,field_of_view=2,width=300,height=240,line_width=.4,background=(255,255,255),cache_dir=ROOT/'.brickblueprint-cache')
   if camera is None:camera=receipt['camera']
   assert camera==receipt['camera']and receipt['pdf']['image_XObjects']==0
   records.append(dict(id=f'color-law-{code}-{mode}',folder=folder.name,code=code,label=label,mode=mode,face_RGB=rgb,camera=camera,model_sha256=receipt['model_sha256'],receipt_sha256=hashlib.sha256((folder/'render.json').read_bytes()).hexdigest()))
  print(label,flush=True)
 (a.output/'color-law-renders.json').write_text(json.dumps(dict(version=__version__,recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),data_sha256=hashlib.sha256((ROOT/'docs/research/COLOR-LAW-RESULTS.json').read_bytes()).hexdigest(),records=records,scope='Reference uses measured anchors. Face-law uses measured left and held-out top/right predictions. LDraw-law predicts every face from nominal RGB. All formula coefficients omit the shown color.'),indent=2)+'\n')
if __name__=='__main__':main()
