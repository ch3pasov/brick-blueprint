"""Optional research tool; requires Pillow, numpy, pdfplumber and Poppler.
No proprietary font program is extracted or distributed.
"""
from pathlib import Path
import json,hashlib,subprocess,math
from PIL import Image,ImageDraw,ImageFont,ImageChops
import numpy as np
import pdfplumber
import argparse
from preview_images import open_png
ap=argparse.ArgumentParser(description='Compare private PDF label crops with supplied OFL fonts. Outputs include private reference crops: keep --work outside the public repository.')
ap.add_argument('--work',type=Path,required=True);ap.add_argument('--font-dir',type=Path,required=True)
ap.add_argument('--chalet-pdf',type=Path,required=True);ap.add_argument('--cera-pdf',type=Path,required=True)
ap.add_argument('--pdftoppm',default='pdftoppm');ap.add_argument('--preview-dir',type=Path,required=True)
args=ap.parse_args();B=args.work;B.mkdir(parents=True,exist_ok=True);out=args.preview_dir;out.mkdir(parents=True,exist_ok=True);pop=args.pdftoppm;fontdir=args.font_dir
refs=[]
for family,rel,wanted in [('Chalet',args.chalet_pdf,'LEGOChalet60-Bold'),('Cera',args.cera_pdf,'CeraPro-Medium')]:
 path=Path(rel);found={}
 with pdfplumber.open(path) as doc:
  for pi,pg in enumerate(doc.pages[:45]):
   for w in pg.extract_words(extra_attrs=['fontname','size']):
    if w['text'] in ['1x','2x','4x'] and w['text'] not in found and wanted in w['fontname'] and abs(w['size']-8)<.01:
     found[w['text']]=(pi+1,w)
   if len(found)==3:break
 for s,(p,w) in found.items():
  x,y=math.floor((w['x0']-2)*10),math.floor((w['top']-2)*10);W,H=math.ceil((w['x1']-w['x0']+4)*10),140
  dest=B/f'{family}-{s}'
  subprocess.run([pop,'-f',str(p),'-l',str(p),'-r','720','-x',str(x),'-y',str(y),'-W',str(W),'-H',str(H),'-singlefile','-png',str(path),str(dest)],check=True,capture_output=True)
  im=open_png(str(dest)+'.png').convert('L');mask=im.point(lambda v:255 if v<80 else 0);# Keep the two largest connected ink components (digit and x), excluding nearby artwork.
  arr=np.asarray(mask)>0;seen=set();components=[]
  for yy,xx in zip(*np.where(arr)):
   if (int(yy),int(xx)) in seen:continue
   todo=[(int(yy),int(xx))];seen.add(todo[0]);comp=[]
   while todo:
    cy,cx=todo.pop();comp.append((cy,cx))
    for dy in [-1,0,1]:
     for dx in [-1,0,1]:
      q=(cy+dy,cx+dx)
      if 0<=q[0]<arr.shape[0] and 0<=q[1]<arr.shape[1] and arr[q] and q not in seen:seen.add(q);todo.append(q)
   components.append(comp)
  clean=np.zeros(arr.shape,dtype=np.uint8)
  for comp in sorted(components,key=len,reverse=True)[:2]:
   for q in comp:clean[q]=255
  mask=Image.fromarray(clean);mask=mask.crop(mask.getbbox());mask.save(B/f'{family}-{s}-mask.png')
  refs.append(dict(family=family,text=s,font=w['fontname'],size_pt=w['size'],advance_pt=w['x1']-w['x0'],pdf_page=p,pdf=path.name,pdf_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),ink_size=mask.size))
records=[];masks={}
for fam in ['jost','outfit','montserrat','leaguespartan']:
 path=next((fontdir/fam).glob('*.ttf'))
 for weight in [500,700]:
  f=ImageFont.truetype(str(path),80);f.set_variation_by_axes([weight])
  for s in ['1x','2x','4x']:
   im=Image.new('L',(250,180));ImageDraw.Draw(im).text((10,15),s,font=f,fill=255,stroke_width=0);mask=im.point(lambda v:255 if v>128 else 0);mask=mask.crop(mask.getbbox());masks[fam,weight,s]=mask
   target=next(r for r in refs if r['family']==('Cera' if weight==500 else 'Chalet') and r['text']==s)
   a=np.asarray(open_png(B/f"{target['family']}-{s}-mask.png"))>0;b=np.asarray(mask)>0
   # Register by ink center, integer shifts +/-3px. No stretching or scale fitting.
   score=0
   for dx in range(-3,4):
    for dy in range(-3,4):
     aa=np.zeros((180,260),bool);bb=aa.copy();ay=20;ax=60;by=ay+(a.shape[0]-b.shape[0])//2+dy;bx=ax+(a.shape[1]-b.shape[1])//2+dx
     aa[ay:ay+a.shape[0],ax:ax+a.shape[1]]=a;bb[by:by+b.shape[0],bx:bx+b.shape[1]]=b
     score=max(score,(aa&bb).sum()/(aa|bb).sum())
   records.append(dict(family=fam,weight=weight,text=s,advance_pt=f.getlength(s)/10,ink_size=mask.size,ink_iou=float(score),reference=target['family']))
# Private contact includes existing official source labels. Never copy to public tree.
board=Image.new('RGB',(1250,600),'white');d=ImageDraw.Draw(board)
for col,(target,weight) in enumerate([('Cera',500),('Chalet',700)]):
 x=col*625;d.text((x+20,10),target+' source / free candidates (same 8pt em)',fill='black',font_size=22)
 for row,fam in enumerate(['SOURCE','jost','outfit','montserrat','leaguespartan']):
  y=50+row*105;d.text((x+15,y+30),fam,fill='black',font_size=20)
  for k,s in enumerate(['1x','2x','4x']):
   mask=open_png(B/f'{target}-{s}-mask.png') if fam=='SOURCE' else masks[fam,weight,s]
   board.paste('black',(x+190+k*140,y+20),mask)
board.save(B/'font-reference-comparison.png')
# Public original specimen uses only OFL fonts; fixed pixels/em, not a print proof.
board=Image.new('RGB',(1440,990),'#f5f9fc');d=ImageDraw.Draw(board)
d.text((45,28),'FREE TYPEFACES / CONTROLLED SPECIMEN',fill='#173342',font_size=36)
d.text((45,80),'Same em size. Medium 500 above; Bold 700 below. Quantities + digits + body text.',fill='#536775',font_size=23)
for row,fam in enumerate(['jost','outfit','montserrat','leaguespartan']):
 y=130+row*200;d.rounded_rectangle((30,y,1410,y+185),radius=12,fill='white',outline='#d6e2ea');d.text((50,y+15),{'leaguespartan':'League Spartan'}.get(fam,fam.title()),fill='#216386',font_size=25)
 for j,weight in enumerate([500,700]):
  f=ImageFont.truetype(str(next((fontdir/fam).glob('*.ttf'))),44);f.set_variation_by_axes([weight]);d.text((280,y+15+j*76),'1x  2x  4x  0123456789   Build a brighter idea',font=f,fill='#142d39')
 d.text((50,y+65),'SIL OFL 1.1',fill='#536775',font_size=18)
d.text((45,955),'Original type specimen; no proprietary font outlines or official instruction artwork.',fill='#536775',font_size=20)
board.save(out/'faq-fonts.png')
(B/'FONT-MEASUREMENTS.json').write_text(json.dumps(dict(method='720dpi source raster, black threshold80, two largest connected ink components; FreeType 80px em, threshold128; ink IoU after +/-3px translation, no rescaling. Screening only; three labels per face, not a whole-typeface similarity metric.',references=refs,candidates=records),indent=2)+'\n')
print(json.dumps({f'{f}/{w}':round(sum(r['ink_iou'] for r in records if r['family']==f and r['weight']==w)/3,4) for f in ['jost','outfit','montserrat','leaguespartan'] for w in [500,700]},indent=2))
