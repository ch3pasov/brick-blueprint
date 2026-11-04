"""Render the two specifically fitted camera examples; not universal camera presets.

Uses only numerical calibration recipes and caller-supplied DAT geometry.
No official source artwork is read or downloaded. Each recipe is tied to its
single-brick geometry and original coordinate frame.
"""
from pathlib import Path
import argparse,hashlib,json,sys,subprocess
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from brick_blueprint import __version__
from brick_blueprint.pipeline import render

def previews(output, reports, font_path, pdftoppm):
 from PIL import Image,ImageDraw,ImageFont
 board=Image.new('RGB',(1600,720),'#F4F8FA');d=ImageDraw.Draw(board)
 def font(n):
  face=ImageFont.truetype(str(font_path),n)
  try:face.set_variation_by_axes([600 if n>=30 and axis['name']==b'Weight' else 400 if axis['name']==b'Weight' else axis['default']for axis in face.get_variation_axes()])
  except (OSError,AttributeError):pass
  return face
 d.text((30,22),'MEASURE A CAMERA. REPLAY IT AS VECTORS.',font=font(34),fill='#183744')
 d.text((30,77),'Two source-specific body-corner fits. Original DAT geometry; no source artwork.',font=font(23),fill='#183744')
 for i,r in enumerate(reports):
  folder=output/r['id'];subprocess.run([str(pdftoppm),'-r','216','-singlefile','-png',str(folder/'model.pdf'),str(folder/'preview')],check=True,capture_output=True)
  im=Image.open(folder/'preview.png').convert('RGB');im=im.resize((round(im.width*.73),round(im.height*.73)),Image.Resampling.LANCZOS);x=30+i*800
  d.text((x,133),r['id'],font=font(25),fill='#183744');board.paste(im,(x+(740-im.width)//2,178))
 d.text((30,665),'Same renderer as the study. Fitted camera parameters are estimates, not universal LEGO constants.',font=font(23),fill='#183744')
 path=output/'calibrated-bricks-own.png';board.save(path);return {path.name:hashlib.sha256(path.read_bytes()).hexdigest()}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--library',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--cache-dir',type=Path,default=ROOT/'.brickblueprint-cache')
 p.add_argument('--previews',action='store_true');p.add_argument('--font',type=Path);p.add_argument('--pdftoppm',default='pdftoppm');args=p.parse_args()
 if args.previews and not args.font:p.error('--previews requires --font with a caller-supplied font')
 args.output.mkdir(parents=True,exist_ok=False);data=ROOT/'docs/research/VOLUME-CAMERA-RESULTS.json';recipes=json.loads(data.read_text())['replay'];reports=[]
 for recipe in recipes:
  id=recipe['id'];model=args.output/f'{id}.ldr';model.write_text(f'0 Single brick numerical camera replay\n1 {recipe["color"]} 0 0 0 1 0 0 0 1 0 0 0 1 {recipe["part"]}\n');out=args.output/id
  r=render(model,args.library,out,cache_dir=args.cache_dir,**recipe['options']);reports.append({'id':id,'model_sha256':r['model_sha256'],'camera':r['camera'],'PDF_sha256':r['pdf']['PDF_sha256'],'receipt_sha256':hashlib.sha256((out/'render.json').read_bytes()).hexdigest(),'image_XObjects':r['pdf']['image_XObjects']})
 proof={'version':__version__,'numerical_results_sha256':hashlib.sha256(data.read_bytes()).hexdigest(),'recipe_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'renders':reports,'scope':'Two source-specific geometry-bound camera fits. Intrinsics are ill-conditioned; do not treat as universal LEGO constants.'}
 if args.previews:
  proof['previews']=previews(args.output,reports,args.font,args.pdftoppm)
  proof['editorial_font']={'file':args.font.name,'sha256':hashlib.sha256(args.font.read_bytes()).hexdigest()}
 (args.output/'camera-calibrations.json').write_text(json.dumps(proof,indent=2)+'\n')
 print(json.dumps({'output':str(args.output),'renders':len(reports),'native_vector':True}))
if __name__=='__main__':main()
