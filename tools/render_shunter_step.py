"""Compose the final shunter step from native SVGs and their render receipts."""
from pathlib import Path
import argparse
import hashlib
import io
import json
import math
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brick_blueprint.ldraw import load_model, mv
from brick_blueprint.pipeline import render
from brick_blueprint.tray import render_tray

NS = 'http://www.w3.org/2000/svg'
XLINK = 'http://www.w3.org/1999/xlink'
ET.register_namespace('', NS)
ET.register_namespace('xlink', XLINK)
PAPER = '#d4edfc'
INK = '#193849'
SCENE_X, SCENE_Y, SCENE_SCALE = 165, 32, 0.85


def node(parent, name, **attrs):
    return ET.SubElement(parent, '{' + NS + '}' + name,
                         {key.replace('_', '-'): str(value) for key, value in attrs.items()})


def words(parent, content, x, y, size, *, bold=False, end=False):
    label = node(parent, 'text', x=x, y=y, font_size=size, fill=INK,
                 font_family='Arial, Helvetica, sans-serif', font_weight='bold' if bold else 'normal')
    if end:
        label.set('text-anchor', 'end')
    label.text = content


def insert_artwork(page, folder, prefix, transform):
    data = (folder / 'model.svg').read_bytes()
    record = json.loads((folder / 'render.json').read_bytes())
    if hashlib.sha256(data).hexdigest() != record['pdf']['SVG_sha256']:
        raise ValueError('Illustration and render receipt differ')
    drawing = ET.fromstring(data)
    background = drawing.find('{' + NS + '}rect')
    if background is None or background.get('fill', '').lower() != PAPER:
        raise ValueError('Expected the modern-blue page color')
    drawing.remove(background)
    group = node(page, 'g', transform=transform)
    for entry in drawing.iter():
        if 'id' in entry.attrib:
            entry.set('id', prefix + entry.get('id'))
        href = '{' + XLINK + '}href'
        if href in entry.attrib:
            value = entry.get(href)
            if not value.startswith('#'):
                raise ValueError('Expected an internal vector reference')
            entry.set(href, '#' + prefix + value[1:])
    group.extend(child for child in drawing if child.tag != '{' + NS + '}title')
    return record


def at_camera(camera, point):
    delta = [v-t for v,t in zip(point, camera['target_ldu'])]
    distance = camera['distance_ldu']
    back = [(v-t)/distance for v,t in zip(camera['position_ldu'], camera['target_ldu'])]
    scale = camera['focal_length_points']/(distance - sum(a*b for a,b in zip(delta, back)))
    offsets = [sum(a*b for a,b in zip(delta, camera[axis])) for axis in ('right','down')]
    local = [2*(center + scale*offset) for center,offset in zip(camera['principal_point_points'], offsets)]
    return (SCENE_X + SCENE_SCALE*local[0], SCENE_Y + SCENE_SCALE*local[1])


def arrow(page, tail, tip):
    dx, dy = tip[0]-tail[0], tip[1]-tail[1]
    length = math.hypot(dx,dy)
    dx, dy = dx/length,dy/length
    def corner(along, across):
        return (tip[0]-along*dx-across*dy, tip[1]-along*dy+across*dx)
    points = [corner(length,1.8),corner(14,1.8),corner(16,5.8),tip,
              corner(16,-5.8),corner(14,-1.8),corner(length,-1.8)]
    node(page,'polygon',points=' '.join(f'{x:.3f},{y:.3f}' for x,y in points),fill='#ba3027')


def compose(model, tray, destination, tiles):
    page=ET.Element('{' + NS + '}svg',{'width':'1000','height':'680','viewBox':'0 0 1000 680'})
    node(page,'title').text='Quayside Shunter · Fit the headlamps'
    node(page,'desc').text=('The inventory shows two round yellow tiles. Two arrows point to the lamps '
                            'on the front of the green locomotive. The geometry comes from the LDraw model.')
    node(page,'rect',width=1000,height=680,fill=PAPER)
    words(page,'Quayside Shunter',34,49,32,bold=True)
    words(page,'Brick Blueprint',966,48,21,end=True)
    node(page,'rect',x=34,y=66,width=932,height=1.3,fill='#829eac')
    scene=insert_artwork(page,model,'train-',f'translate({SCENE_X} {SCENE_Y}) scale({SCENE_SCALE})')
    words(page,'12',32,169,90,bold=True)
    words(page,'Fit the headlamps',35,214,26,bold=True)
    inventory=insert_artwork(page,tray,'tray-','translate(11 225)')
    if len(inventory['items'])!=1 or inventory['items'][0]['quantity']!=2:
        raise ValueError('The final step uses two identical tiles')
    words(page,'Press one tile onto',35,487,21)
    words(page,'each stud at the front.',35,516,21)
    for tile in tiles:
        normal = mv(tile['matrix'], (0,-1,0))
        points = [tuple(v + n*distance for v,n in zip(tile['xyz'],normal)) for distance in (52,6)]
        arrow(page, at_camera(scene['camera'],points[0]), at_camera(scene['camera'],points[1]))
    node(page,'rect',x=34,y=620,width=932,height=1.3,fill='#829eac')
    words(page,'65 placements',34,654,20)
    words(page,'12 / 12',966,654,20,end=True)
    destination.write_bytes(ET.tostring(page,encoding='utf-8',xml_declaration=True))
    return page


def write_pdf(page, folder):
    """Overlay the same labels and arrows on the renderer's two native PDFs."""
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.lib.colors import HexColor
    from pypdf import PdfReader, PdfWriter, Transformation

    width, height = 500, 340
    writer = PdfWriter()
    sheet = writer.add_blank_page(width=width, height=height)

    def editor_layer(elements):
        buffer = io.BytesIO()
        canvas = Canvas(buffer, pagesize=(width,height), invariant=True)
        for element in elements:
            tag = element.tag.rsplit('}',1)[-1]
            if tag not in ('rect','text','polygon'):
                continue
            field = element.attrib
            canvas.setFillColor(HexColor(field['fill']))
            if tag == 'rect':
                x,y,w,h = (float(field.get(k,0))/2 for k in ('x','y','width','height'))
                canvas.rect(x,height-y-h,w,h,stroke=0,fill=1)
            elif tag == 'text':
                font = 'Helvetica-Bold' if field['font-weight']=='bold' else 'Helvetica'
                canvas.setFont(font,float(field['font-size'])/2)
                draw = canvas.drawRightString if field.get('text-anchor')=='end' else canvas.drawString
                draw(float(field['x'])/2,height-float(field['y'])/2,element.text)
            else:
                path = canvas.beginPath()
                for i,vertex in enumerate(field['points'].split()):
                    x,y = (float(v)/2 for v in vertex.split(','))
                    (path.moveTo if i==0 else path.lineTo)(x,height-y)
                path.close()
                canvas.drawPath(path,stroke=0,fill=1)
        canvas.save()
        return PdfReader(buffer).pages[0]

    background = page.find('{' + NS + '}rect')
    sheet.merge_page(editor_layer([background]))
    for subdir,x,y,scale in [('assembly',SCENE_X,SCENE_Y,SCENE_SCALE),('inventory',11,225,1)]:
        native = PdfReader(folder/subdir/'model.pdf').pages[0]
        dy = height - y/2 - scale*float(native.mediabox.height)
        sheet.merge_transformed_page(native,Transformation().scale(scale).translate(x/2,dy))
    sheet.merge_page(editor_layer(e for e in page if e is not background))
    writer.add_metadata({'/Title':'Quayside Shunter · Fit the headlamps','/Author':'Brick Blueprint'})
    with (folder/'step-12.pdf').open('wb') as output:
        writer.write(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--pdf',action='store_true',help='Also compose a print sheet using pypdf and ReportLab')
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        parser.error('Choose a new output directory')
    if args.pdf:
        from importlib.util import find_spec
        if any(find_spec(name) is None for name in ('pypdf','reportlab')):
            parser.error('The optional PDF sheet needs pypdf and ReportLab')
    models = ROOT/'examples/shunter'
    model = models/'shunter.ldr'
    manifest = models/'lamps.json'
    parts,_ = load_model(model)
    tiles = [p for p in parts if p['step']==12]
    listed = json.loads(manifest.read_bytes())['items']
    if len(listed)!=1 or listed[0]['quantity']!=len(tiles) or len(tiles)!=2:
        raise ValueError('The inventory must describe both tiles added in step 12')
    example,_ = load_model(models/listed[0]['model'])
    if len(example)!=1:
        raise ValueError('The inventory entry must be a single tile')
    if len(parts)!=65 or max(p['step'] for p in parts)!=12:
        raise ValueError('The sheet is laid out for the 65-placement shunter')
    if any((p['part'],p['ldraw_color'])!=(example[0]['part'],example[0]['ldraw_color']) for p in tiles):
        raise ValueError('The inventory part or color differs from the assembly')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.shunter-',dir=args.output.parent) as temporary:
        output=Path(temporary)/'page'
        output.mkdir()
        common = dict(camera_preset='instruction',preset='modern-blue')
        render(model,args.library,output/'assembly',width=560,height=360,line_width=.55,
               glass_opacity=.72,underpaint=True,**common)
        render_tray(manifest,args.library,output/'inventory',columns=1,width=116,height=112,gap=5,**common)
        page = compose(output/'assembly',output/'inventory',output/'step-12.svg',tiles)
        if args.pdf:
            write_pdf(page,output)
        if args.output.exists() or args.output.is_symlink():
            raise FileExistsError('The output directory was created during rendering')
        output.rename(args.output)
    print(args.output/'step-12.svg')
    if args.pdf:
        print(args.output/'step-12.pdf')


if __name__ == '__main__':
    main()
