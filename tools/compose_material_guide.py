"""Compose two editable SVG plates from the eleven native opaque-brick renders."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.verify_gallery import matches_vector_source
from brick_blueprint.compact_paths import SCALE, expand

FACE_POINTS = {'left': (180, 285), 'top': (278, 144), 'right': (382, 300)}
SVG = 'http://www.w3.org/2000/svg'
XLINK = 'http://www.w3.org/1999/xlink'
ET.register_namespace('', SVG)
ET.register_namespace('xlink', XLINK)


def element(parent, name, **attrs):
    return ET.SubElement(parent, f'{{{SVG}}}{name}', {k.replace('_', '-'): str(v) for k, v in attrs.items()})


def sheet(width, height, title, description):
    root = ET.Element(f'{{{SVG}}}svg', width=str(width), height=str(height), viewBox=f'0 0 {width} {height}')
    element(root, 'title').text = title
    element(root, 'desc').text = description
    element(root, 'rect', width=width, height=height, fill='#f1f6f8')
    return root


def text(parent, x, y, words, size, weight='normal', anchor='start'):
    node = element(parent, 'text', x=x, y=y, font_size=size, font_weight=weight,
                   text_anchor=anchor, font_family='Arial, Helvetica, sans-serif', fill='#193a49')
    node.text = words


def brick(parent, paths, transform, defs, shapes):
    """Reuse equal native path data while preserving each draw's paint and order."""
    group = element(parent, 'g', transform=transform)
    for path in paths:
        d = path.attrib['d']
        if d not in shapes:
            shapes[d] = 'shape-' + str(len(shapes) + 1)
            element(defs, 'path', id=shapes[d], d=d)
        use = element(group, 'use', fill=path.attrib['fill'])
        use.set(f'{{{XLINK}}}href', '#' + shapes[d])


def rgb_triplet(values):
    return ', '.join(str(math.floor(x + 0.5)) for x in values)


def face_key(row, paths):
    root = sheet(880, 460, 'Where the three face colors appear',
                 'A native orange 2 by 2 brick. Leader lines point to sampled face interiors.')
    defs = element(root, 'defs')
    brick(root, paths, 'translate(200 60) scale(.81)', defs, {})
    # Input positions are on the 600 x 480 native brick page.
    labels = [('left', 27, 258, 'start', [(235, 294), (271, 294)]),
              ('top', 428, 37, 'middle', [(428, 83), (428, 112)]),
              ('right', 663, 258, 'start', [(643, 295), (616, 295)])]
    for face, x, y, anchor, route in labels:
        fx, fy = FACE_POINTS[face]
        end = (200 + .81 * fx, 60 + .81 * fy)
        line = ' '.join(f'{a:g},{b:g}' for a, b in [*route, end])
        for color, width in [('#ffffff', 5), ('#254957', 2)]:
            element(root, 'polyline', points=line, fill='none', stroke=color, stroke_width=width)
        element(root, 'circle', cx=end[0], cy=end[1], r=5, fill='#ffffff', stroke='#254957', stroke_width=2)
        text(root, x, y, face.capitalize(), 30, 'bold', anchor)
        text(root, x, y + 33, rgb_triplet(row['anchor_RGB'][face]), 26, anchor=anchor)
    text(root, 30, 437, 'Orange  ·  LDraw 25', 24)
    text(root, 850, 437, '8-bit RGB', 24, anchor='end')
    return root


def palette(bindings, renders):
    root = sheet(960, 890, 'Eleven measured materials',
                 'The same native 2 by 2 brick in each measured opaque material, labeled by LDraw color code.')
    defs = element(root, 'defs')
    shapes = {}
    text(root, 24, 55, 'Eleven measured materials', 40, 'bold')
    text(root, 26, 91, 'One brick, one camera  ·  LDraw color codes', 24)
    for index, row in enumerate(bindings):
        x = 16 + (index % 3) * 312
        y = 109 + (index // 3) * 192
        element(root, 'rect', x=x, y=y, width=304, height=184, rx=9, fill='#ffffff')
        code = row['ldraw_color']
        name = row['ldraw_name'].replace('_', ' ')
        text(root, x + 15, y + 29, name, 21, 'bold')
        text(root, x + 285, y + 29, str(code), 20, anchor='end')
        brick(root, renders[code], f'translate({x + 51} {y + 28}) scale(.337)', defs, shapes)
    key = element(root, 'g', transform='translate(640 685)')
    element(key, 'rect', width=304, height=184, rx=9, fill='#e1eaef')
    text(key, 17, 41, 'The specimen', 22, 'bold')
    text(key, 17, 81, '2 × 2 brick · 3003.dat', 20)
    text(key, 17, 118, '35° azimuth and elevation', 19)
    text(key, 17, 151, '2° field of view', 19)
    return root


def sample_faces(paths, anchors):
    """Check final paint at the three indicated face interiors in native SVG units."""
    points = {face: (x * SCALE, y * SCALE) for face, (x, y) in FACE_POINTS.items()}
    sampled = {}
    for path in paths:
        winding = dict.fromkeys(points, 0)
        for cmd in expand(path.attrib['d']):
            if cmd[0] == 'M':
                start = previous = cmd[1:]
                continue
            end = start if cmd[0] == 'Z' else cmd[1:]
            x, y = previous
            u, v = end
            for face, (px, py) in points.items():
                cross = (u - x) * (py - y) - (px - x) * (v - y)
                if y <= py < v and cross > 0:
                    winding[face] += 1
                elif v <= py < y and cross < 0:
                    winding[face] -= 1
            previous = end
        for face, count in winding.items():
            if count:
                sampled[face] = path.attrib['fill'].lower()
    expected = {face: '#' + bytes(math.floor(v + .5) for v in rgb).hex()
                for face, rgb in anchors.items()}
    if sampled != expected:
        raise ValueError('Face paint differs at the measured sample positions.')


def check_renderer_output(folder, digest, reference, require_reference_bytes):
    if digest == reference['pdf']['SVG_sha256']:
        return
    if require_reference_bytes:
        raise ValueError('SVG bytes differ from the reference: ' + folder.name)
    # Two C++ compilers can round clipping intersections differently. In that
    # case use the generating receipt and the reviewed input to the native core.
    receipt = json.loads((folder / 'render.json').read_bytes())
    if digest != receipt['pdf']['SVG_sha256'] or receipt['pdf']['image_XObjects'] != 0:
        raise ValueError('SVG differs from its own native render receipt: ' + folder.name)
    for key in ('scene_sha256', 'model_sha256', 'style_sha256', 'line_width_points', 'page_points'):
        if receipt[key] != reference[key]:
            raise ValueError(f'Render input differs for {folder.name}: {key}')
    if not matches_vector_source(receipt['execution']['package_source_sha256'],reference['execution']['package_source_sha256']):
        raise ValueError('Different renderer source for ' + folder.name)


def compose(source, destination, *, require_reference_bytes=False):
    if destination.exists():
        raise FileExistsError('Choose a new output directory.')
    data = json.loads((ROOT / 'brick_blueprint/material-research.json').read_bytes())
    renders = {}
    for row in data['bindings']:
        code = row['ldraw_color']
        name = f'brick-{code}-research'
        file = source / name / 'model.svg'
        native = file.read_bytes()
        reference = json.loads((ROOT / 'docs/gallery' / f'material-current-{name}.json').read_bytes())
        check_renderer_output(file.parent, hashlib.sha256(native).hexdigest(), reference, require_reference_bytes)
        root = ET.fromstring(native)
        if root.get('viewBox') != '0 0 600 480':
            raise ValueError('Unexpected brick viewport: ' + name)
        # The pinned opaque controls contain only flat filled paths in these two groups.
        renders[code] = [path for group in root.findall(f'{{{SVG}}}g') for path in group]
        if not renders[code] or any(path.tag != f'{{{SVG}}}path' or set(path.attrib) != {'fill', 'd'}
                                    for path in renders[code]):
            raise ValueError('Unexpected drawing operation: ' + name)
        sample_faces(renders[code], row['anchor_RGB'])
    orange = next(row for row in data['bindings'] if row['ldraw_color'] == 25)
    plates = {'brick-face-guide.svg': face_key(orange, renders[25]),
              'material-palette.svg': palette(data['bindings'], renders)}
    destination.mkdir(parents=True)
    for name, drawing in plates.items():
        (destination / name).write_bytes(ET.tostring(drawing, encoding='utf-8'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('renders', type=Path, help='Output from render_material_examples.py')
    parser.add_argument('destination', type=Path)
    parser.add_argument('--require-reference-bytes', action='store_true',
                        help='Require byte-identical input SVGs from the reference toolchain')
    args = parser.parse_args()
    compose(args.renders, args.destination, require_reference_bytes=args.require_reference_bytes)
