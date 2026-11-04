"""Measure the effect of underpainting on a pair of native 500 x 320 pt model plates.

Needs NumPy, Pillow and Poppler's pdftoppm. The original PDF display test used
Poppler 26.05.0. Other viewers can sample exactly the same paths differently.
"""
import argparse
import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brick_blueprint.pdf import export_pdf

SAMPLE = 6


def make_pages(svg, directory):
    tree = ET.parse(svg)
    root = tree.getroot()
    if root.get('viewBox') != '0 0 1000 640':
        raise ValueError('This experiment uses the 500 x 320 pt gallery page.')
    background = root.find('{*}rect')
    if background is None or background.get('width') != '1000' or background.get('height') != '640':
        raise ValueError('The gallery page needs a full-page background rectangle.')
    pages = {}
    for name, color in [('page', None), ('black', '#000000'), ('white', '#ffffff')]:
        if color is not None:
            background.set('fill', color)
        variant = directory / (name + '.svg')
        tree.write(variant, encoding='utf-8')
        pages[name] = variant.with_suffix('.pdf')
        export_pdf(variant, pages[name])
    return pages


def pixels(page, width):
    prefix = page.with_name(f'{page.stem}-{width}')
    subprocess.run(['pdftoppm', '-scale-to', str(width), '-png', '-singlefile',
                    str(page), str(prefix)], check=True, timeout=180)
    with Image.open(prefix.with_suffix('.png')) as bitmap:
        if bitmap.size != (width, width * 320 // 500):
            raise ValueError('Unexpected raster dimensions.')
        return np.array(bitmap.convert('RGB'))


def box_average(image):
    height, width = image.shape[:2]
    blocks = image.reshape((height // SAMPLE, SAMPLE, width // SAMPLE, SAMPLE) + image.shape[2:])
    return blocks.mean(axis=(1, 3), dtype=np.float32)


def backdrop_response(pages, width):
    black = pixels(pages['black'], width)
    white = pixels(pages['white'], width)
    # A short strip bounds the extra memory used by the channel subtraction.
    result = np.empty(black.shape[:2], dtype=np.uint8)
    for y in range(0, len(result), 128):
        band = slice(y, y + 128)
        result[band] = np.max(np.abs(white[band].astype(np.int16) - black[band]), axis=2)
    return result


def measure(plain_svg, painted_svg, width):
    with tempfile.TemporaryDirectory(prefix='blueprint-coverage-') as temp:
        pages = {}
        for name, svg in [('plain', plain_svg), ('underpaint', painted_svg)]:
            folder = Path(temp) / name
            folder.mkdir()
            pages[name] = make_pages(svg, folder)
        reference = box_average(pixels(pages['plain']['page'], width * SAMPLE))
        interior = box_average(backdrop_response(pages['plain'], width * SAMPLE)) <= 5
        if not interior.any():
            raise ValueError('There are no opaque interior pixels at this size.')
        result = dict(width=width, format='pdf', interior_pixels=int(interior.sum()))
        for name, variants in pages.items():
            influence = backdrop_response(variants, width)
            error = np.abs(pixels(variants['page'], width) - reference)
            result[name] = dict(leaks_24=int(((influence >= 24) & interior).sum()),
                                interior_MAE=float(error[interior].mean()),
                                full_MAE=float(error.mean()))
        return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plain', type=Path, help='Full native SVG without the base paint')
    parser.add_argument('underpaint', type=Path, help='Same render with base paint enabled')
    parser.add_argument('--width', type=int, default=500, choices=[250, 500, 1000])
    args = parser.parse_args()
    print(json.dumps(measure(args.plain, args.underpaint, args.width), indent=2))
