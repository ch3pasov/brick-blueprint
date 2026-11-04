"""Redraw the English research plates from stored observations (standard library)."""
import argparse
import json
import math
from pathlib import Path
from statistics import mean
import xml.etree.ElementTree as ET

DOCS = Path(__file__).resolve().parents[1] / 'docs'
BLUE = '#0e7290'
ORANGE = '#ae5025'
INK = '#193947'


def data(path):
    return json.loads((DOCS / path).read_text())


class Chart:
    def __init__(self, title, subtitle, height):
        self.root = ET.Element('svg', xmlns='http://www.w3.org/2000/svg',
                               viewBox=f'0 0 840 {height}', width='840', height=str(height))
        ET.SubElement(self.root, 'title').text = title
        ET.SubElement(self.root, 'desc').text = subtitle
        self.rect(0, 0, 840, height, '#f5f9fa')
        self.label(28, 42, title, 24)
        self.label(28, 71, subtitle, 15)

    def rect(self, x, y, w, h, color):
        ET.SubElement(self.root, 'rect', x=str(x), y=str(y), width=str(w), height=str(h), fill=color)

    def label(self, x, y, text, size=15, color=INK):
        ET.SubElement(self.root, 'text', x=str(x), y=str(y), fill=color,
                      **{'font-family':'Arial, Helvetica, sans-serif', 'font-size':str(size)}).text = str(text)

    def line(self, x1, y1, x2, y2, color):
        ET.SubElement(self.root, 'line', x1=str(x1), y1=str(y1), x2=str(x2), y2=str(y2), stroke=color)

    def dot(self, x, y, color):
        ET.SubElement(self.root, 'circle', cx=str(x), cy=str(y), r='4.5', fill=color)

    def save(self, folder, name):
        (folder / (name + '.svg')).write_bytes(ET.tostring(self.root, encoding='utf-8'))


def projection():
    chart = Chart('Which camera predicts the missing studs?',
                  'RMS error on withheld spatial bands, in native pixels. Log scale. Smaller is better.', 463)
    chart.label(260, 101, '●  Perspective', color=BLUE)
    chart.label(463, 101, '●  Parallel', color=ORANGE)
    def xpos(value):
        return 200 + 240 * math.log10(value / .04)
    for tick in (.05, .1, .2, .5, 1, 2, 5, 10):
        x = xpos(tick)
        chart.line(x, 119, x, 427, '#d4e2e6')
        chart.label(x - 8, 450, f'{tick:g}', 13)
    for i, row in enumerate(data('research/PERSPECTIVE-RESULTS.json')['measurements']):
        y = 132 + 24 * i
        chart.label(28, y + 4, row['id'], 14)
        trial = row['trials'][1]
        for model, color in [('projective', BLUE), ('affine', ORANGE)]:
            chart.dot(xpos(trial[model]['spatial_rms']), y, color)
    return chart


def faces():
    chart = Chart('Three faces of the same brick',
                  'Median RGB of interior patches in the 2 × 2 sample. Swatches show the nearest 8-bit value.', 480)
    anchors = [176, 390, 604]
    for x, label in zip(anchors, ['Left face', 'Top face', 'Right face']):
        chart.label(x, 106, label)
    seen = set()
    for row in data('THREE-FACE-SHADING.json')['observations']:
        name = row['color_label_visual']
        if name in seen:
            continue
        y = 123 + 34 * len(seen)
        seen.add(name)
        chart.label(28, y+17, 'Dark tan' if name == 'tan' else name.capitalize())
        for x, face in zip(anchors, ['left', 'top', 'right']):
            rgb = row['faces'][face]
            chart.rect(x, y, 41, 23, '#' + ''.join(f'{round(v):02x}' for v in rgb))
            chart.label(x+50, y+17, ', '.join(f'{v:g}' for v in rgb), 14)
    return chart


def angles():
    chart = Chart('How often does the simulated statistic exceed the observation?',
                  'Each curve uses 1,999 refits under a joint 35°/35° null. Dots mark the observed F.', 340)
    for i,row in enumerate(r for r in data('research/CAMERA-PVALUES.json')['rows'] if r['primary']):
        x0 = 64 + i*405
        y0 = 273
        b = row['bootstrap']
        chart.label(x0, 108, row['id'] + f"     p = {b['p']:.3f}", 17)
        chart.line(x0, y0-122, x0, y0, INK)
        chart.line(x0, y0, x0+297, y0, INK)
        points = []
        values = [t['F'] for t in b['trials']]
        for k in range(100):
            f = k/33
            frac = (1+sum(v >= f for v in values))/(1+len(values))
            points.append(f'{x0+k*3:.2f},{y0-122*frac:.2f}')
        ET.SubElement(chart.root, 'polyline', points=' '.join(points), fill='none', stroke=BLUE,
                      **{'stroke-width':'2.5'})
        chart.dot(x0+99*row['statistics']['F'], y0-122*b['p'], ORANGE)
        chart.label(x0-23, y0-118, '1', 13)
        chart.label(x0-23, y0+3, '0', 13)
        for f in range(4):
            chart.label(x0+99*f-3, y0+20, f, 13)
        chart.label(x0+138, y0+46, 'F', 14)
    return chart


def transfer():
    chart = Chart('How well do the colors transfer to a longer brick?',
                  'Mean absolute RGB error per channel across three face patches, on twelve 2 × 4 images.', 444)
    for i, row in enumerate(data('MATERIAL-TRANSFER.json')['observations']):
        y = 103 + 27*i
        errors = [abs(a-b) for face in row['faces'].values()
                  for a,b in zip(face['observed'], face['reference_prediction'])]
        value = mean(errors)
        chart.label(28, y+12, f"{row['set']}  p. {row['page']}  {row['image']}", 14)
        chart.rect(200, y, value*115, 14, BLUE)
        chart.label(211+value*115, y+12, f'{value:.2f}', 14)
    return chart


def resolution():
    chart = Chart('How much does raster resolution affect the angle estimate?',
                  'Known 35°/35° camera. Number of estimates within one degree on both axes, out of 36 attempts.', 319)
    for i,row in enumerate(data('research/CAMERA-EDGE-STUDY.json')['native_camera_controls']):
        y = 101+33*i
        chart.label(28, y+13, f"{row['method'].capitalize()}  ·  {row['density']}×", 15)
        value = row['within_one_degree']
        chart.rect(248, y, 432, 17, '#deeaef')
        chart.rect(248, y, value*12, 17, BLUE)
        chart.label(696, y+14, f'{value} / 36')
    return chart


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for name, draw in [('projection-errors', projection), ('face-colors', faces), ('angle-test', angles),
                       ('geometry-transfer', transfer), ('resolution-control', resolution)]:
        draw().save(args.output, name)
