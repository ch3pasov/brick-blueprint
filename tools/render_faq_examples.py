"""Render the unchanged FAQ models from multiple viewpoints.
Core vectors need only the usual renderer dependencies. --previews additionally
requires Pillow and pdftoppm; no official instruction images are used here.
"""
from pathlib import Path
import argparse,sys,subprocess
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R))
from brick_blueprint.pipeline import render
from preview_images import open_png
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--library',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--previews',action='store_true');ap.add_argument('--pdftoppm',default='pdftoppm');ap.add_argument('--font',type=Path);args=ap.parse_args()
if args.output.exists():ap.error('Choose a new output directory')
if args.previews and not args.font:ap.error('--previews requires a local --font for editorial captions')
args.output.mkdir(parents=True)
rows=[('brick30','parts/brick-2x4.ldr',35,30,2.6),('brick35','parts/brick-2x4.ldr',35,35,2.6),('brick-under','parts/brick-2x4.ldr',35,-25,2.6),('garden30-v2','garden.ldr',35,30,1.6),('garden35-v2','garden.ldr',35,35,1.6),('garden-back-v2','garden.ldr',215,35,1.6)]
for name,model,az,el,scale in rows:
 render(R/'examples'/model,args.library,args.output/name,projection="orthographic",material_profile="legacy",cache_dir=R/'.brickblueprint-cache',azimuth=az,elevation=el,scale=scale,width=440,height=350,line_width=.55,background=(212,237,252));print(name,flush=True)
if args.previews:
 from PIL import Image,ImageDraw,ImageFont
 images={}
 for name,*_ in rows:
  p=args.output/name;subprocess.run([args.pdftoppm,'-r','144','-singlefile','-png',str(p/'model.pdf'),str(p/'preview')],check=True,capture_output=True);images[name]=open_png(p/'preview.png').convert('RGB')
 for file,names,title,sub,labels in [
 ('faq-camera-bricks',['brick30','brick35','brick-under'],'One real brick, three views','Same 3D geometry and scale. Only the camera changes.',['Current view / 30 deg','Slightly higher / 35 deg','From below / cavity becomes visible']),
 ('faq-camera-garden',['garden30-v2','garden35-v2','garden-back-v2'],'One LEGO assembly, three views','The 41 parts stay in place. Hidden faces appear when the camera moves.',['Current view / 30 deg','Slightly higher / 35 deg','From behind / 35 deg'])]:
  im=Image.new('RGB',(1500,570),'#f5f9fc');d=ImageDraw.Draw(im)
  def label(x,y,s,n):d.text((x,y),s,font=ImageFont.truetype(str(args.font),n),fill='#173342')
  label(25,18,title,32);label(25,66,sub,21)
  for i,name in enumerate(names):
   thumb=images[name].copy();thumb.thumbnail((480,382),Image.Resampling.LANCZOS);im.paste(thumb,(10+i*500+(480-thumb.width)//2,125));label(20+i*500,523,labels[i],21)
  im.save(args.output/(file+'.png'))
