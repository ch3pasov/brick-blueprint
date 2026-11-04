"""Recreate the current actual-step PNG facade from its vector PDF renders.

Optional editorial tooling: Pillow, Poppler and a caller-supplied local font.
Input is the presets group produced by render_gallery.py. No source scans, GUI,
downloads, font programs or existing output images are copied into the result.
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


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True,type=Path,help='Vector render_gallery.py output folder')
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--font',required=True,type=Path)
    parser.add_argument('--pdftoppm',default='pdftoppm')
    args=parser.parse_args()
    if args.output.exists():parser.error('Choose a new output directory')
    if importlib.util.find_spec('PIL') is None:parser.error('This optional composition step requires Pillow')
    if shutil.which(args.pdftoppm) is None:parser.error('Supply an existing pdftoppm executable')
    from PIL import Image,ImageDraw,ImageFont,__version__ as pillow_version
    from preview_images import open_png
    try:ImageFont.truetype(str(args.font),20)
    except OSError as error:parser.error('Cannot read editorial font: '+str(error))
    rows=json.loads((ROOT/'docs/ACTUAL-STEP-EXAMPLES.json').read_text())['examples']
    assets={a['file']:a for a in json.loads((ROOT/'docs/gallery/images.json').read_text())['assets']}
    for row in rows:
        for name in ('model.pdf','model.svg','render.json'):
            if not (args.input/row['preset']/name).is_file():parser.error('Missing vector input: '+row['preset']+'/'+name)
    args.output.mkdir(parents=True)
    def text(draw,xy,content,size=21):
        face=ImageFont.truetype(str(args.font),size)
        try:face.set_variation_by_axes([600 if size>=30 and axis['name']==b'Weight' else
                                       400 if axis['name']==b'Weight' else axis['default']
                                       for axis in face.get_variation_axes()])
        except (OSError,AttributeError):pass
        draw.text(xy,content,font=face,fill='#173242')
    board=Image.new('RGB',(1760,1690),'#f5f7f8');draw=ImageDraw.Draw(board)
    text(draw,(25,15),'REAL STEPS. DISTINCT PAPER STYLES.',32)
    text(draw,(25,60),'Our vector renders of source-step parts and quantities. Camera and materials remain our approximation.',21)
    provenance=[]
    for index,row in enumerate(rows):
        key=row['preset'];folder=args.input/key;preview=args.output/(key+'.png')
        # Rasterize directly into the new output folder, then strip ancillary
        # metadata by saving only RGB pixels with the same filename.
        subprocess.run([args.pdftoppm,'-r','144','-singlefile','-png',str(folder/'model.pdf'),str(preview.with_suffix(''))],
                       check=True,capture_output=True,timeout=120)
        with open_png(preview) as image:rgb=image.convert('RGB')
        rgb.save(preview,optimize=True)
        label=assets['docs/images/'+key+'.png']['description'].split(';',1)[0]
        subtitle=(f"PDF p{row['pdf_page']} · step {row['step']} · individual parts"
                  if 'manifest' in row else 'Foldout exception: no invented parts tray')
        x=20+index%4*435;y=115+index//4*390
        draw.rounded_rectangle((x,y,x+415,y+370),radius=10,fill='white',outline='#d8e2e8')
        text(draw,(x+12,y+12),label,20);text(draw,(x+12,y+44),subtitle,16)
        board.paste(rgb.resize((396,264),Image.Resampling.LANCZOS),(x+9,y+83))
        provenance.append(dict(preset=key,pdf_sha256=sha(folder/'model.pdf'),
                               svg_sha256=sha(folder/'model.svg'),
                               receipt_sha256=sha(folder/'render.json'),png_sha256=sha(preview)))
    board.save(args.output/'presets.png',optimize=True)
    version=subprocess.run([args.pdftoppm,'-v'],capture_output=True,text=True,timeout=30)
    report=dict(recipe_sha256=sha(__file__),font_sha256=sha(args.font),font_file=args.font.name,
                dpi=144,pillow_version=pillow_version,
                pdftoppm_version=(version.stderr or version.stdout).splitlines()[0],
                board_sha256=sha(args.output/'presets.png'),items=provenance)
    (args.output/'previews.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(previews=len(rows),board_sha256=report['board_sha256']),indent=2))


if __name__=='__main__':main()
