"""Export comparable RGB/gray and optional ICC CMYK vectors from one renderer SVG.

No model is rerendered. Optional PNG comparison uses Poppler, Pillow and a local
editorial font. Output goes to a new folder; no profile or font is downloaded.
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
from brick_blueprint.print_export import export_print,validate


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--profile',type=Path,help='Add CMYK using this caller-selected output profile')
    parser.add_argument('--previews',action='store_true')
    parser.add_argument('--font',type=Path)
    parser.add_argument('--pdftoppm',default='pdftoppm')
    args=parser.parse_args()
    if args.output.exists():parser.error('Choose a new output directory')
    validate(args.source)
    if args.profile and not args.profile.is_file():parser.error('CMYK profile does not exist')
    if args.previews:
        if not args.font or not args.font.is_file():parser.error('--previews requires a local --font')
        if importlib.util.find_spec('PIL') is None:parser.error('--previews requires optional Pillow')
        if shutil.which(args.pdftoppm) is None:parser.error('--previews requires an existing pdftoppm executable')
        from PIL import Image,ImageDraw,ImageFont,__version__ as pillow_version
        from preview_images import open_png
        try:ImageFont.truetype(str(args.font),20)
        except OSError as error:parser.error('Cannot read editorial font: '+str(error))
    args.output.mkdir(parents=True)
    modes=['rgb','gray']+(['cmyk'] if args.profile else [])
    results={}
    for mode in modes:
        receipt=export_print(args.source,args.output/mode,mode=mode,
                             profile=args.profile if mode=='cmyk' else None)
        results[mode]=dict(receipt_sha256=sha(args.output/mode/'print.json'),
                           PDF_sha256=receipt['pdf']['PDF_sha256'],
                           page_points=receipt['page_points'],PDF_bytes=receipt['pdf']['PDF_bytes'],
                           image_XObjects=receipt['pdf']['image_XObjects'])
    result=dict(recipe_sha256=sha(__file__),source_svg_sha256=sha(args.source),modes=results,
                scope='Same vector geometry and physical page size; generic screen comparison, not a physical or calibrated printer proof.')
    if args.previews:
        board=Image.new('RGB',(500*len(modes),620),'#f5f9fc');draw=ImageDraw.Draw(board)
        def text(x,y,value,size=22,weight=400):
            face=ImageFont.truetype(str(args.font),size)
            try:
                axes=face.get_variation_axes()
                face.set_variation_by_axes([min(a['maximum'],max(a['minimum'],weight)) if a['name']==b'Weight' else a['default'] for a in axes])
            except (OSError,AttributeError):pass
            draw.text((x,y),value,font=face,fill='#173342')
        text(26,16,'ONE SVG. VECTOR PRINT EXPORTS.',30,600)
        text(26,63,'Screen previews of actual PDFs. Same paths and page size.',21)
        for index,mode in enumerate(modes):
            folder=args.output/mode
            subprocess.run([args.pdftoppm,'-r','144','-singlefile','-png',str(folder/'print.pdf'),str(folder/'preview')],
                           check=True,capture_output=True,timeout=120)
            with open_png(folder/'preview.png') as image:rgb=image.convert('RGB')
            rgb.thumbnail((480,410),Image.Resampling.LANCZOS)
            board.paste(rgb,(index*500+10+(480-rgb.width)//2,125))
            text(index*500+22,551,dict(rgb='RGB / source colors',gray='Grayscale / luminance',cmyk='CMYK / supplied ICC')[mode],23,500)
        text(26,590,'No physical print, PDF/X or universal color-match claim.',17)
        board.save(args.output/'kiosk-print-comparison.png',optimize=True)
        version=subprocess.run([args.pdftoppm,'-v'],capture_output=True,text=True,timeout=30)
        result['previews']=dict(board_sha256=sha(args.output/'kiosk-print-comparison.png'),font_sha256=sha(args.font),
                                font_file=args.font.name,dpi=144,pillow_version=pillow_version,
                                pdftoppm_version=(version.stderr or version.stdout).splitlines()[0])
    (args.output/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(modes=modes,vector_only=all(v['image_XObjects']==0 for v in results.values())),indent=2))


if __name__=='__main__':main()
