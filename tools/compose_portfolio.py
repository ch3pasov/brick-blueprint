"""Lay out the README cover and collect the native SVG editions and credits."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')


def digest(content):
    return hashlib.sha256(content).hexdigest()


def cover(kiosk):
    """Place the unaltered kiosk paths on a wider sheet with a typographic key."""
    header = '''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="420" viewBox="0 0 1000 420">
<title>Brick Blueprint · Little Blue Kiosk</title>
<desc>A 41-piece market stall with glass side walls, a striped blue canopy and a pair of red and yellow bollards.</desc>
<rect width="1000" height="420" fill="#d4edfc"/>
<g fill="#183b50" font-family="Arial, Helvetica, sans-serif">
<path d="M34 28H966 M34 343H966" fill="none" stroke="#7197ad" stroke-width="1.4"/>
<text x="32" y="139" font-size="94" font-weight="bold">Brick</text>
<text x="32" y="232" font-size="94" font-weight="bold">Blueprint</text>
<text x="37" y="300" font-size="34">LDraw to SVG and PDF</text>
<text x="36" y="392" font-size="34" font-weight="bold">Little Blue Kiosk</text>
<text x="964" y="392" font-size="32" text-anchor="end">41 parts</text>
</g></svg>'''
    page = ET.fromstring(header)
    art = ET.SubElement(page, '{'+NS+'}g', {'transform':'translate(478 21) scale(.495)'})
    for element in ET.fromstring(kiosk):
        if element.tag.rsplit('}', 1)[-1] not in {'title','desc','rect'}:
            art.append(element)
    return ET.tostring(page, encoding='utf-8')


def compose(source, destination):
    scenes = json.loads((source/'portfolio.json').read_text())
    destination.mkdir(parents=True, exist_ok=False)
    dependencies = {}
    for scene in scenes:
        slug = scene['id']
        folder = source/slug
        svg = (folder/'model.svg').read_bytes()
        receipt = json.loads((folder/'render.json').read_bytes())
        if digest(svg) != scene['svg_sha256'] or digest(svg) != receipt['pdf']['SVG_sha256']:
            raise ValueError('Native SVG hash differs for ' + slug)
        if receipt['model_sha256'] != scene['model_sha256'] or receipt['pdf']['image_XObjects']:
            raise ValueError('Unexpected model or raster output for ' + slug)
        (destination/(slug+'.svg')).write_bytes(svg)
        for entry in receipt['dependencies']:
            dependencies[(entry['file'],entry['sha256'])] = entry
        scene['geometry'] = [r['file'] for r in receipt['dependencies']]
        scene['style_sha256'] = receipt['style_sha256']
        scene['environment'] = receipt['execution']
        scene['library_config'] = receipt['library_config']
    hero = cover((destination/'kiosk.svg').read_bytes())
    (destination/'cover.svg').write_bytes(hero)
    catalog = dict(models=scenes, cover_sha256=digest(hero),
                   geometry_source='https://www.ldraw.org/', geometry_changes='Projected, shaded and outlined for vector illustration.',
                   dependencies=[dependencies[key] for key in sorted(dependencies)])
    (destination/'sources.json').write_text(json.dumps(catalog, indent=2, ensure_ascii=False)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('renders', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    compose(args.renders, args.destination)
