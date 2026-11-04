"""Compose own color-law previews; requires local Pillow, Poppler and a font."""
from pathlib import Path
import argparse,hashlib,json,subprocess
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--renders',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--font',type=Path,required=True);p.add_argument('--pdftoppm',default='pdftoppm');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 manifest=json.loads((a.renders/'color-law-renders.json').read_text());data=json.loads((ROOT/'docs/research/COLOR-LAW-DATA.json').read_text());preview={};boxes=[]
 for row in manifest['records']:
  folder=a.renders/row['folder'];subprocess.run([a.pdftoppm,'-r','144','-singlefile','-png',str(folder/'model.pdf'),str(a.output/row['id'])],capture_output=True,check=True)
  im=Image.open(a.output/(row['id']+'.png')).convert('RGB');preview[(row['code'],row['mode'])]=im;yy,xx=np.where(np.any(np.array(im)<245,axis=2));boxes.append([xx.min()-8,yy.min()-8,xx.max()+9,yy.max()+9])
 bbox=list(map(int,[min(b[0]for b in boxes),min(b[1]for b in boxes),max(b[2]for b in boxes),max(b[3]for b in boxes)]));font=lambda n:ImageFont.truetype(str(a.font),n)
 board=Image.new('RGB',(1390,1430),'#F4F8FA');d=ImageDraw.Draw(board);d.text((20,12),'HELD-OUT COLOR PREDICTIONS',font=font(34),fill='#183744')
 for j,h in enumerate(['Measured palette','From measured left face','From nominal LDraw RGB']):d.text((20+j*450,63),h,font=font(24),fill='#183744')
 for i,code in enumerate([191,70,28,0]):
  row=next(r for r in data['colors']if r['ldraw_code']==code);y=108+i*307;d.text((20,y),f"{row['label'].title()} / LDraw {code}",font=font(23),fill='#183744')
  for j,mode in enumerate(['reference','face-law','ldraw-law']):
   x=20+j*450;im=preview[(code,mode)].crop(bbox);im.thumbnail((405,236),Image.Resampling.LANCZOS);board.paste(im,(x+(420-im.width)//2,y+34+(236-im.height)//2))
   rgb=next(r['face_RGB']for r in manifest['records']if r['code']==code and r['mode']==mode)
   if mode!='reference':
    faces=['top','right']if mode=='face-law'else['left','top','right'];mae=np.mean([abs(np.array(rgb[f])-row['source']['faces'][f])for f in faces]);d.text((x+35,y+276),('MAE T/R: 'if mode=='face-law'else'MAE L/T/R: ')+f'{mae:.2f} RGB',font=font(21),fill='#147C9C'if mode=='face-law'else'#B75521')
 d.text((20,1350),'Identical geometry, camera and scale. Measured-left input is supplied, not predicted.',font=font(24),fill='#183744');d.text((20,1387),'Each formula omits the shown color. These samples do not establish a universal shader.',font=font(24),fill='#183744');board.save(a.output/'color-law-own.png')
 (a.output/'previews.json').write_text(json.dumps(dict(board_sha256=hashlib.sha256((a.output/'color-law-own.png').read_bytes()).hexdigest(),recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),font_sha256=hashlib.sha256(a.font.read_bytes()).hexdigest(),common_crop=bbox,renders=[r['id']for r in manifest['records']],source_artwork_included=False),indent=2)+'\n')
if __name__=='__main__':main()
