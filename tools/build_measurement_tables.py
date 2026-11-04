"""Generate the paper's machine-readable-to-Markdown tables without fitting any model."""
import argparse
import json
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / 'docs'
OUT = DOCS / 'research' / 'MEASUREMENT-TABLES.md'


def read(name):
    return json.loads((DOCS / 'research' / name).read_text())


def source_link(row):
    return f"[{row['set']} · p. {row['page']}]({row['url']}#page={row['page']})"


def format_rgb(channels):
    return ', '.join(f'{value:g}' for value in channels)


def markdown():
    sections = [
        '# Measurement tables',
        'Values are taken from the saved analyses. Each link opens the page measured in the official book. Page numbers count from the first page of the PDF.',
        '## Assembly projection',
        'At the middle threshold, we compare RMS errors at original image resolution. The checkerboard split withholds dispersed points. The band split withholds contiguous regions. The two splits share the same source image.',
        '| Source | Centers | Parallel, checker | Perspective, checker | Parallel, bands | Perspective, bands |',
        '|---|---:|---:|---:|---:|---:|',
    ]
    for row in read('PERSPECTIVE-RESULTS.json')['measurements']:
        trial = row['trials'][1]
        values = [trial[model][metric] for metric in ('checker_rms', 'spatial_rms')
                  for model in ('affine', 'projective')]
        sections.append('| ' + ' | '.join([source_link(row['source']), str(trial['n']),
                                           *(f'{v:.3f}' for v in values)]) + ' |')
    sections.extend([
        '', '[All thresholds and both splits](PERSPECTIVE-RESULTS.json)',
        '', '## Inventory illustrations', '',
        'Each row is a distinct measured cap-grid asset in the primary catalogue sample. Azimuth and elevation are equivalent local orthographic angles. The same artwork can occur on several pages. Repeated thresholds and caps in a single asset share a camera.', '',
        '| Source | PDF image | Grid | Measured caps | Azimuth | Elevation |',
        '|---|---|---:|---:|---:|---:|',
    ])
    for record in read('CAMERA-CATALOGUE-DATA.json')['records']:
        if not record['primary_cap_set']:
            continue
        trial = next(t for t in record['trials'] if t['threshold'] == record['primary_threshold'])
        a,e = trial['reference_angles_deg']
        sections.append(f"| {source_link(record['source'])} | {record['source']['name']} | "
                        f"{' × '.join(map(str, record['grid']))} | {len(trial['centers'])} | {a:.2f}° | {e:.2f}° |")
    sections.extend([
        '', '[Selection, thresholds and all coordinates](CAMERA-CATALOGUE-DATA.json)',
        '', '## Nominal RGB and measured faces', '',
        'Each row represents one distinct material. The first RGB comes from the LDraw palette. The other three are observed in the instructions. Half levels are medians of pixel samples. The face-to-face formula uses the **left** column as its input.', '',
        '| LDraw code | Nominal RGB | Left | Top | Right |',
        '|---:|---|---|---|---|',
    ])
    for row in read('FACE-LAW-17.json')['rows']:
        triplets = [row['input_RGB'], *(row['faces'][face] for face in ('left','top','right'))]
        sections.append(f"| {row['code']} | " + ' | '.join(map(format_rgb, triplets)) + ' |')
    sections += ['', '[Full precision and model errors](FACE-LAW-17.json) · [Research paper](../RESEARCH-PREPRINT.md)']
    # Blank lines before each of the introductory paragraphs and first table.
    return '\n'.join(sections[:1] + ['',sections[1],'',sections[2],'',sections[3],''] + sections[4:]) + '\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = markdown()
    if args.check:
        if result != OUT.read_text():
            raise SystemExit('Measurement tables have changed. Regenerate and review the differences.')
    else:
        OUT.write_text(result)
