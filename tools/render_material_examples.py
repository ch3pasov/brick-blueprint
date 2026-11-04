"""Render the measured material palette and two application examples.

No source instruction pictures are read or copied. Supply an external LDraw
library. Optional previews need Pillow, Poppler and a caller-supplied font.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from brick_blueprint.pipeline import render
from brick_blueprint import __version__


def previews(output, rows, *, font, pdftoppm):
    from PIL import Image, ImageChops, ImageDraw, ImageFont
    from preview_images import open_png
    def text(draw, xy, value, size=20):
        face=ImageFont.truetype(str(font),size)
        try:
            face.set_variation_by_axes([600 if size>=30 and axis['name']==b'Weight' else
                                        400 if axis['name']==b'Weight' else axis['default']
                                        for axis in face.get_variation_axes()])
        except (OSError,AttributeError):pass
        draw.text(xy,value,font=face,fill='#173342')
    def illustration(name, size):
        folder=output/(name+'-research')
        preview=folder/'preview.png'
        if not preview.exists():
            subprocess.run([pdftoppm,'-scale-to','1200','-singlefile','-png',str(folder/'model.pdf'),str(folder/'preview')],check=True,capture_output=True,timeout=120)
        with open_png(preview) as image:
            im=image.convert('RGB')
            im=im.crop((2,2,im.width-2,im.height-2))
        box=ImageChops.difference(im,Image.new('RGB',im.size,im.getpixel((0,0)))).getbbox()
        im=im.crop(box);im.thumbnail(size,Image.Resampling.LANCZOS)
        return im
    materials=[row for row in rows if row['id'] not in ('brick-2x4','kiosk')]
    board=Image.new('RGB',(1520,130+258*((len(materials)+1)//2)),'#f5f9fc');draw=ImageDraw.Draw(board)
    text(draw,(24,15),f'{len(materials)} COLORS. THREE MEASURED FACES.',32)
    text(draw,(24,61),'Brick Blueprint / instruction camera: 35 / 35 degrees, 2 degree FOV.',21)
    bindings=json.loads((ROOT/'brick_blueprint/material-research.json').read_text())['bindings']
    for index,row in enumerate(materials):
        x=20+(index%2)*750;y=112+(index//2)*258
        draw.rounded_rectangle((x,y,x+730,y+240),radius=10,fill='white',outline='#d5e0e8')
        text(draw,(x+14,y+10),row['name'].replace('_',' '),22)
        asset=illustration(row['id'],(310,178));board.paste(asset,(x+20+(310-asset.width)//2,y+48+(178-asset.height)//2))
        binding=next(b for b in bindings if row['id']=='brick-'+str(b['ldraw_color']))
        for j,(key,label) in enumerate((('left','Left'),('top','Top'),('right','Right'))):
            rgb=binding['anchor_RGB'][key]
            text(draw,(x+365,y+65+j*46),label+': '+', '.join(f'{v:g}' for v in rgb),21)
    board.save(output/'material-current-colors.png',optimize=True)
    for name,title in [('kiosk','MEASURED MATERIALS IN AN ASSEMBLY'),('brick-2x4','THE SAME MATERIAL ON A 2 X 4 BRICK')]:
        im=Image.new('RGB',(1000,650),'#f5f9fc');draw=ImageDraw.Draw(im)
        text(draw,(26,18),title,30)
        text(draw,(26,64),'Instruction camera / measured anchors where available',22)
        asset=illustration(name,(900,490))
        im.paste(asset,((1000-asset.width)//2,120+(490-asset.height)//2))
        im.save(output/(name+'-current-materials.png'),optimize=True)
    # Current README hero: same model as the comparison, with no old image reused.
    asset=illustration('kiosk',(850,760))
    hero=Image.new('RGB',(1600,900),'#D4EDFC');draw=ImageDraw.Draw(hero)
    text(draw,(64,64),'LDRAW TO PAPER',25)
    text(draw,(58,130),'Brick',95);text(draw,(58,244),'Blueprint',95)
    text(draw,(64,420),'Perspective. Crisp vectors.',30)
    text(draw,(64,505),'SVG + PDF',36)
    text(draw,(64,618),'41 placed parts / CPU renderer',25)
    text(draw,(64,668),f'{len(materials)} colors tied to research',25)
    text(draw,(64,815),'Renderer '+__version__+' / original kiosk sample',20)
    hero.paste(asset,(715+(850-asset.width)//2,80+(760-asset.height)//2))
    hero.save(output/'kiosk-current-hero.png',optimize=True)
    return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.glob('*.png')}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--library',required=True,type=Path);ap.add_argument('--output',required=True,type=Path)
    ap.add_argument('--previews',action='store_true');ap.add_argument('--pdftoppm',default='pdftoppm');ap.add_argument('--font',type=Path)
    args=ap.parse_args()
    if args.output.exists():ap.error('Choose a new output directory')
    if args.previews and (args.font is None or not args.font.is_file()):ap.error('--previews requires a readable --font')
    args.output.mkdir(parents=True);models=args.output/'models';models.mkdir()
    evidence=json.loads((ROOT/'brick_blueprint/material-research.json').read_text());rows=[]
    sources=[]
    for binding in evidence['bindings']:
        code=binding['ldraw_color'];name=f'brick-{code}';model=models/(name+'.ldr')
        model.write_text(f'0 Material comparison: single 2 x 2 brick\n1 {code} 0 0 0 1 0 0 0 1 0 0 0 1 3003.dat\n')
        sources.append((name,binding['ldraw_name'],model,300,240))
    model=models/'brick-2x4.ldr';model.write_text('0 Material transfer: single 2 x 4 brick\n1 72 0 0 0 1 0 0 0 1 0 0 0 1 3001.dat\n')
    sources += [('brick-2x4','2 x 4 control',model,500,380),('kiosk','Original kiosk',ROOT/'examples/kiosk/kiosk.mpd',500,380)]
    for name,label,model,width,height in sources:
        pair={}
        for profile in ('research',):
            folder=args.output/(name+'-'+profile)
            receipt=render(model,args.library,folder,material_profile=profile,width=width,height=height,
                camera_preset='instruction',line_width=.4 if width==300 else .5,glass_opacity=.9,cache_dir=ROOT/'.brickblueprint-cache')
            assert receipt['pdf']['image_XObjects']==0
            pair[profile]=receipt
        rows.append({'id':name,'name':label,'camera':pair['research']['camera'],
            'model_sha256':pair['research']['model_sha256'],
            'renders':{profile:{'receipt_sha256':hashlib.sha256((args.output/(name+'-'+profile)/'render.json').read_bytes()).hexdigest(),'PDF_sha256':r['pdf']['PDF_sha256'],'SVG_sha256':r['pdf']['SVG_sha256'],'style_sha256':r['style_sha256']}for profile,r in pair.items()}})
        print(name,flush=True)
    report={'version':__version__,'recipe_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'scenes':rows,
            'material_data_sha256':evidence['data_sha256'],'material_evidence_sha256':hashlib.sha256((ROOT/'brick_blueprint/material-research.json').read_bytes()).hexdigest(),'limits':'Opaque measured axis anchors only; intermediate normals and opposite faces use declared illustration extensions. Sources are not fitted or copied at render time.'}
    if args.previews:
        report['previews']=previews(args.output,rows,font=args.font,pdftoppm=args.pdftoppm)
        report['editorial_font']={'file':args.font.name,'sha256':hashlib.sha256(args.font.read_bytes()).hexdigest(),
                                  'variable_weight':'600 at sizes>=30, otherwise400; static fonts unchanged'}
    (args.output/'material-examples.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
