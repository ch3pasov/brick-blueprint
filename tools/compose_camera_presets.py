"""Preview the eight own camera-preset vectors (Pillow and Poppler required)."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from PIL import Image, ImageDraw, ImageFont


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--font',required=True,type=Path)
    p.add_argument('--pdftoppm',default='pdftoppm')
    a=p.parse_args()
    if a.output.exists():p.error('Choose a new preview directory')
    a.output.mkdir(parents=True)
    board=Image.new('RGB',(1760,900),'#F4F8FA');d=ImageDraw.Draw(board)
    def text(xy,t,size):
        face=ImageFont.truetype(str(a.font),size)
        try:
            face.set_variation_by_axes([600 if size>=30 else 400 if axis['name']==b'Weight' else axis['default'] for axis in face.get_variation_axes()])
        except (OSError,AttributeError):pass
        d.text(xy,t,font=face,fill='#173947')
    text((24,15),'INSTRUCTION CAMERAS, READY TO USE',32)
    text((24,59),'One model per row. 35 / 35 degrees. Real perspective; automatic camera distance.',22)
    order=['instruction','instruction-depth','presentation','orthographic'];labels=['2 deg / recommended','5 deg / mild depth','30 deg / presentation','Parallel control']
    rows=[]
    for iy,key in enumerate(['plate','kiosk']):
        for ix,name in enumerate(order):
            rid=key+'-'+name;folder=a.input/rid;dest=a.output/(rid+'.png')
            subprocess.run([a.pdftoppm,'-r','144','-singlefile','-png',str(folder/'model.pdf'),str(dest.with_suffix(''))],check=True,capture_output=True)
            with Image.open(dest) as im:im=im.convert('RGB');im.save(dest,optimize=True)
            x=ix*440+12;y=110+iy*386
            text((x+10,y),name,23);text((x+10,y+35),labels[ix],18)
            board.paste(im.resize((416,312),Image.Resampling.LANCZOS),(x,y+64))
            rows.append(dict(id=rid,png_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),receipt_sha256=hashlib.sha256((folder/'render.json').read_bytes()).hexdigest()))
    path=a.output/'camera-presets.png';board.save(path,optimize=True)
    (a.output/'previews.json').write_text(json.dumps(dict(rows=rows,board_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),font_sha256=hashlib.sha256(a.font.read_bytes()).hexdigest()),indent=2)+'\n')


if __name__=='__main__':main()
