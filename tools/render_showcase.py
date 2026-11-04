"""Reproduce the original kiosk portfolio without downloads or GUI applications.

Vectors use only the core renderer. --previews additionally uses Pillow, Poppler
and a caller-supplied editorial font. Generated files stay in a new output folder.
"""
import argparse
import hashlib
import json
import importlib.util
from pathlib import Path
import subprocess
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from brick_blueprint.pipeline import render
from brick_blueprint.tray import render_tray
from brick_blueprint.ldraw import parse_model


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def make_previews(output, scenes, *, font, pdftoppm, stages):
    from PIL import Image, ImageChops, ImageDraw, ImageFont, __version__ as pillow_version
    from preview_images import open_png

    images={}
    for name in scenes:
        folder=output/name
        subprocess.run([pdftoppm,'-r','144','-singlefile','-png',str(folder/'model.pdf'),str(folder/'preview')],
                       check=True,capture_output=True,timeout=120)
        with open_png(folder/'preview.png') as image:images[name]=image.convert('RGB')

    def text(draw,xy,content,size,fill='#173342',weight=400):
        face=ImageFont.truetype(str(font),size)
        try:
            axes=face.get_variation_axes()
            values=[min(axis['maximum'],max(axis['minimum'],weight))
                    if axis['name']==b'Weight' else axis['default'] for axis in axes]
            face.set_variation_by_axes(values)
        except (OSError,AttributeError):pass  # Static caller-supplied font.
        draw.text(xy,content,font=face,fill=fill)

    def thumbnail(image,box):
        result=image.copy();result.thumbnail(box,Image.Resampling.LANCZOS);return result

    hero=Image.new('RGB',(1600,900),'#D4EDFC');draw=ImageDraw.Draw(hero)
    text(draw,(64,54),'LDRAW TO PAPER',22)
    text(draw,(59,110),'Brick',96,weight=600);text(draw,(59,218),'Blueprint',96,weight=600)
    text(draw,(64,378),'Instruction-style illustrations.',32)
    draw.rounded_rectangle((64,465,478,526),radius=14,fill='#173342')
    text(draw,(88,477),'SVG  +  PDF',28,fill='white',weight=500)
    text(draw,(64,585),'41 placed parts',27)
    text(draw,(64,635),'Editable LDraw / MPD',27)
    text(draw,(64,685),'CPU only',27)
    text(draw,(64,812),'Original kiosk sample. External LDraw geometry.',20)
    model=images['kiosk']
    background=Image.new('RGB',model.size,model.getpixel((0,0)))
    ink=ImageChops.difference(model,background).getbbox()
    if not ink:raise ValueError('Empty showcase preview')
    model=thumbnail(model.crop(ink),(830,740))
    hero.paste(model,(704+(830-model.width)//2,96+(740-model.height)//2))
    hero.save(output/'kiosk-hero.png',optimize=True)

    camera_names=['kiosk-camera-front','kiosk-camera-back','kiosk-camera-under']
    strip=Image.new('RGB',(1500,530),'#f5f9fc');draw=ImageDraw.Draw(strip)
    text(draw,(28,18),'ONE MODEL. THREE CAMERAS.',31,weight=600)
    text(draw,(28,65),'41 parts at the same target-plane scale.',21)
    for i,(name,label) in enumerate(zip(camera_names,['Front / 35 deg, 35 deg','Back / 215 deg, 35 deg','Below / 35 deg, -20 deg'])):
        image=thumbnail(images[name],(480,350));strip.paste(image,(10+i*500+(480-image.width)//2,122))
        text(draw,(24+i*500,487),label,20)
    strip.save(output/'kiosk-cameras.png',optimize=True)

    if stages:
        labels=['Foundation','Lower walls','Counter','Glazing','Upper walls','Header','Canopy','Bollards']
        board=Image.new('RGB',(1760,960),'#f5f9fc');draw=ImageDraw.Draw(board)
        text(draw,(24,14),'EIGHT SAVED DESIGN STAGES',31,weight=600)
        text(draw,(24,59),'Original model checkpoints. The renderer illustrates them; it does not infer instructions.',21)
        for i,label in enumerate(labels):
            x=20+(i%4)*435;y=110+(i//4)*415
            draw.rounded_rectangle((x,y,x+415,y+395),radius=12,fill='white',outline='#d6e1e9')
            text(draw,(x+14,y+12),f'{i+1:02d}  {label}',22,weight=500)
            image=thumbnail(images[f'kiosk-stage-{i+1:02d}'],(395,320))
            board.paste(image,(x+10+(395-image.width)//2,y+63))
        board.save(output/'kiosk-stages.png',optimize=True)
    with open_png(output/'kiosk-inventory/preview.png') as image:
        image.convert('RGB').save(output/'kiosk-inventory.png',optimize=True)
    version=subprocess.run([pdftoppm,'-v'],capture_output=True,text=True,timeout=30)
    return dict(pillow_version=pillow_version,
                pdftoppm_version=(version.stderr or version.stdout).splitlines()[0],
                dpi=144,font_sha256=sha(font),font_file=Path(font).name,
                images={p.name:sha(p) for p in sorted(output.glob('*.png'))},
                note='Editorial PNG composition from our PDF previews; no source instruction images or fonts bundled.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--stages',action='store_true',help='Also render the eight saved design checkpoints')
    parser.add_argument('--previews',action='store_true')
    parser.add_argument('--font',type=Path,help='Local editorial font; required by --previews')
    parser.add_argument('--pdftoppm',default='pdftoppm')
    args=parser.parse_args()
    if args.output.exists():parser.error('Choose a new output directory to preserve previous results')
    if args.previews and (args.font is None or not args.font.is_file()):parser.error('--previews requires a readable local --font')
    if args.previews:
        if importlib.util.find_spec('PIL') is None:parser.error('--previews requires optional Pillow; vectors do not')
        if shutil.which(args.pdftoppm) is None:parser.error('--previews requires an existing pdftoppm executable')
        from PIL import ImageFont
        try:ImageFont.truetype(str(args.font),20)
        except OSError as error:parser.error('Cannot read editorial font: '+str(error))
    args.output.mkdir(parents=True)
    scenes=[]
    common=dict(library=args.library,cache_dir=ROOT/'.brickblueprint-cache',preset='modern-blue',
                camera_preset="instruction",line_width=.55,glass_opacity=.75,underpaint=True)
    def scene(name,model,**options):
        receipt = render(model,output=args.output/name,**{**common,**options})
        scenes.append(name);print(name,flush=True)
        return receipt
    for name,suffix in [('kiosk','mpd'),('kiosk-flat','ldr')]:
        scene(name,ROOT/f'examples/kiosk/kiosk.{suffix}',width=760,height=600)
    equivalent={name:sha(args.output/'kiosk'/name)==sha(args.output/'kiosk-flat'/name) for name in ('model.svg','model.pdf')}
    if not all(equivalent.values()):raise RuntimeError('Flat and MPD vectors differ')
    front_camera = None
    for suffix,az,el in [('front',35,35),('back',215,35),('under',35,-20)]:
        view = scene('kiosk-camera-'+suffix,ROOT/'examples/kiosk/kiosk.mpd',width=440,height=350,
              azimuth=az,elevation=el,scale=1.35)
        if suffix == 'front':
            front_camera = view['camera']
    render_tray(ROOT/'examples/kiosk/bom-tray.json',args.library,args.output/'kiosk-inventory',
                preset='modern-blue',width=780,height=650,columns=4,gap=16,line_width=.4,
                camera_preset='instruction',underpaint=True,cache_dir=ROOT/'.brickblueprint-cache')
    scenes.append('kiosk-inventory');print('kiosk-inventory',flush=True)
    if args.stages:
        folder=args.output/'models';folder.mkdir()
        parts=parse_model(ROOT/'examples/kiosk/kiosk.ldr')
        for step in range(1,9):
            model=folder/f'stage-{step:02d}.ldr'
            rows=['0 Original kiosk prefix; generated from the saved design.']
            for p in parts:
                if p['step']<=step:
                    rows.append('1 '+' '.join(map(str,[p['ldraw_color'],*p['xyz'],*p['matrix']]))+' '+p['part'])
            model.write_text('\n'.join(rows)+'\n')
            # A shared target and distance keep earlier parts fixed on the page.
            scene(f'kiosk-stage-{step:02d}',model,width=440,height=350,
                  camera_target=front_camera['target_ldu'],camera_distance=front_camera['distance_ldu'])
    report=dict(schema_version=1,scenes=scenes,flat_mpd_identical=equivalent,
                generator_sha256=sha(ROOT/'examples/generate_kiosk.py'),
                recipe_sha256=sha(__file__),
                models={p.name:sha(p) for p in (ROOT/'examples/kiosk').glob('kiosk.*')},
                render_receipts={name:sha(args.output/name/'render.json') for name in scenes})
    if args.previews:
        report['previews']=make_previews(args.output,scenes,font=args.font,pdftoppm=args.pdftoppm,stages=args.stages)
    (args.output/'showcase.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(scenes=len(scenes),flat_mpd_identical=equivalent),indent=2))


if __name__=='__main__':main()
