"""Write an exact integer-coordinate edition of the native Lighthouse Point SVG."""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brick_blueprint.compact_paths import SCALE, expand

SVG = 'http://www.w3.org/2000/svg'
ET.register_namespace('', SVG)
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')
GRID = 1000


def pair(x, y):
    return f'{x} {y}' if y >= 0 else f'{x}{y}'


def integer_path(data):
    """Choose short SVG commands without moving, adding or removing vertices."""
    commands = expand(data)
    out = []
    previous = ''
    x = y = start_x = start_y = 0
    for command, *coords in commands:
        if command == 'Z':
            out.append('z')
            x, y = start_x, start_y
            previous = 'z'
            continue
        if any(value % (SCALE // GRID) for value in coords):
            raise ValueError('A native path has finer precision than the recorded grid')
        nx, ny = [value // (SCALE // GRID) for value in coords]
        dx, dy = nx-x, ny-y
        if command == 'M':
            options = [('M', pair(nx,ny)), ('m', pair(dx,dy))]
            start_x, start_y = nx, ny
        else:
            options = [('L', pair(nx,ny)), ('l', pair(dx,dy))]
            if dx == 0:
                options.extend([('V', str(ny)), ('v', str(dy))])
            if dy == 0:
                options.extend([('H', str(nx)), ('h', str(dx))])

        def spelling(op, args):
            # After a moveto, another coordinate pair implies a lineto.
            implicit = previous == op or (previous, op) in [('M','L'), ('m','l')]
            if command == 'L' and implicit:
                return ('' if args.startswith('-') else ' ') + args
            return op + args

        op, args = min(options,key=lambda item: len(spelling(*item)))
        out.append(spelling(op,args))
        previous, x, y = op, nx, ny
    encoded = ''.join(out)
    expected = [tuple([op] + [v*GRID for v in values]) for op,*values in commands]
    if expand(encoded) != expected:
        raise ValueError('Encoded path no longer reproduces the native commands')
    return encoded, len(commands)


def compose(folder, destination):
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Choose a new SVG filename')
    raw = (folder/'model.svg').read_bytes()
    receipt = json.loads((folder/'render.json').read_bytes())
    model = ROOT/'examples/lighthouse.ldr'
    if receipt['model_sha256'] != hashlib.sha256(model.read_bytes()).hexdigest() or receipt['parts'] != 537:
        raise ValueError('This recipe uses the checked-in 537-placement scene')
    if receipt['pdf']['SVG_sha256'] != hashlib.sha256(raw).hexdigest() or receipt['pdf']['image_XObjects'] != 0:
        raise ValueError('Expected an unaltered native SVG and its render receipt')

    root = ET.fromstring(raw)
    width, height = receipt['page_points']
    if root.get('viewBox') != f'0 0 {2*width:g} {2*height:g}':
        raise ValueError('Unexpected native page coordinates')
    root.set('viewBox',f'0 0 {2*width*GRID:g} {2*height*GRID:g}')
    tags = {'svg','title','rect','defs','g','use','path','circle'}
    counts = dict(paths=0, expanded_commands=0)
    for element in root.iter():
        if element.tag.rsplit('}',1)[-1] not in tags or 'transform' in element.attrib:
            raise ValueError('Unexpected native drawing element or transform')
        if element is root:
            continue
        for key in ('x','y','cx','cy','r','rx','ry','width','height','stroke-width'):
            if key in element.attrib:
                element.set(key,format(Decimal(element.get(key))*GRID,'f'))
        if 'd' in element.attrib:
            encoded, count = integer_path(element.get('d'))
            element.set('d',encoded)
            counts['paths'] += 1
            counts['expanded_commands'] += count
    root.find('{' + SVG + '}title').text = 'Lighthouse Point'
    description = ET.Element('{' + SVG + '}desc')
    description.text = ('Two blue houses and a striped lighthouse stand on a rocky island. '
                        'Two people watch a brick-built whale beside the landing.')
    root.insert(1,description)
    destination.parent.mkdir(parents=True,exist_ok=True)
    output = ET.tostring(root,encoding='utf-8',xml_declaration=True)
    with destination.open('xb') as file:
        file.write(output)
    return counts


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('render_folder',type=Path)
    parser.add_argument('destination',type=Path)
    args = parser.parse_args()
    print(json.dumps(compose(args.render_folder,args.destination),indent=2))
