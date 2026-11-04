"""Show measured presentation presets using only the original kiosk's parts.

Four quantity-1 real-part specimens share one physical scale in fourteen trays.
The foldout exception shows an explicitly labeled original canopy subassembly.
This is a controlled tool demonstration, not an actual-source-step reconstruction.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from brick_blueprint.pipeline import render
from brick_blueprint.presets import all_presets
from brick_blueprint.tray import render_tray


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--previews',action='store_true')
    parser.add_argument('--font',type=Path)
    parser.add_argument('--pdftoppm',default='pdftoppm')
    args=parser.parse_args()
    if args.output.exists():parser.error('Choose a new output directory')
    if args.previews:
        if not args.font or not args.font.is_file():parser.error('--previews requires a local --font')
        if importlib.util.find_spec('PIL') is None:parser.error('--previews requires optional Pillow')
        if shutil.which(args.pdftoppm) is None:parser.error('--previews requires an existing pdftoppm executable')
        from PIL import Image,ImageDraw,ImageFont,__version__ as pillow_version
        from preview_images import open_png
        try:ImageFont.truetype(str(args.font),20)
        except OSError as error:parser.error('Cannot read editorial font: '+str(error))
    args.output.mkdir(parents=True)
    receipts=[]
    # Keep source data order but place the lone subassembly exception last.
    presets=all_presets()
    keys=[k for k,p in presets.items() if p['panels']['parts'] is not None]
    keys += [k for k,p in presets.items() if p['panels']['parts'] is None]
    for key in keys:
        folder=args.output/key
        common=dict(library=args.library,output=folder,cache_dir=ROOT/'.brickblueprint-cache',
                    camera_preset="instruction",underpaint=True,preset=key,width=360,height=240,
                    line_width=.4,scale=.95)
        if presets[key]['panels']['parts'] is None:
            receipt=render(ROOT/'examples/kiosk/canopy.ldr',layout='callout',panel_role='subassembly',quantity=1,**common)
            role='Original canopy / subassembly card'
        else:
            receipt=render_tray(ROOT/'examples/kiosk/presentation-tray.json',columns=2,gap=12,**common)
            role='Four original-sample parts / common scale'
        receipts.append(dict(preset=key,name=presets[key]['name'],role=role,
                             receipt_sha256=sha(folder/'render.json'),
                             svg_sha256=receipt['pdf']['SVG_sha256'],pdf_sha256=receipt['pdf']['PDF_sha256']))
        print(key,flush=True)
    result=dict(recipe_sha256=sha(__file__),generator_sha256=sha(ROOT/'examples/generate_kiosk.py'),
                scope=__doc__,scenes=receipts)
    if args.previews:
        def text(draw,xy,value,size=20,weight=400):
            face=ImageFont.truetype(str(args.font),size)
            try:
                axes=face.get_variation_axes()
                face.set_variation_by_axes([min(a['maximum'],max(a['minimum'],weight)) if a['name']==b'Weight' else a['default'] for a in axes])
            except (OSError,AttributeError):pass
            draw.text(xy,value,font=face,fill='#173342')
        board=Image.new('RGB',(1760,1690),'#f5f9fc');draw=ImageDraw.Draw(board)
        text(draw,(25,15),'FIFTEEN PAPER STYLES. ORIGINAL SPECIMENS.',32,600)
        text(draw,(25,60),'Four fixed parts in 14 trays; one original canopy card. Shared camera and shading approximation.',21)
        for index,row in enumerate(receipts):
            folder=args.output/row['preset']
            subprocess.run([args.pdftoppm,'-r','144','-singlefile','-png',str(folder/'model.pdf'),str(folder/'preview')],
                           capture_output=True,check=True,timeout=120)
            with open_png(folder/'preview.png') as image:rgb=image.convert('RGB')
            x=20+index%4*435;y=115+index//4*390
            draw.rounded_rectangle((x,y,x+415,y+370),radius=12,fill='white',outline='#d6e1e9')
            text(draw,(x+12,y+12),row['preset'],22,500)
            text(draw,(x+12,y+47),row['role'],16)
            board.paste(rgb.resize((396,264),Image.Resampling.LANCZOS),(x+9,y+83))
            row['preview_sha256']=sha(folder/'preview.png')
        board.save(args.output/'kiosk-presets.png',optimize=True)
        version=subprocess.run([args.pdftoppm,'-v'],capture_output=True,text=True,timeout=30)
        result['previews']=dict(board_sha256=sha(args.output/'kiosk-presets.png'),font_sha256=sha(args.font),
                                font_file=args.font.name,pillow_version=pillow_version,dpi=144,
                                pdftoppm_version=(version.stderr or version.stdout).splitlines()[0])
    (args.output/'kiosk-presets.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
