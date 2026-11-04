"""Verify the 17-row color CSV. Optional local PDFs and an LDraw library check its sources."""
import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

from check_source_manuals import check_image, file_hash, pdf_files

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brick_blueprint.ldraw import Library

RESEARCH = ROOT / 'docs/research'
FACES = ('left', 'top', 'right')


def load(filename):
    return json.loads((RESEARCH / filename).read_bytes())


def observations():
    main = load('LDRAW-TRANSFER-DATA.json')
    extra = load('PALETTE-HOLDOUT-2025.json')
    records = {}
    for row in main['colors']:
        cohort = {'ten-color source': 'base10', 'three-color extension': 'control3'}[row['source_batch']]
        records[row['code']] = (cohort, row['source'], row['input_RGB'], row['faces'], row['shifts'])
    for row in extra['observations']:
        if row['primary']:
            identity = row['identity']
            records[identity['code']] = ('holdout4', row['source'], identity['input_RGB'], row['faces'], row['shifts'])
    return records, main['library_config']['sha256'], extra['measurement_protocol']['native_ROIs']


def rgb_text(rgb):
    return '(' + ', '.join(f'{channel:g}' for channel in rgb) + ')'


def check_table(path):
    records, palette_hash, boxes = observations()
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        header = reader.fieldnames or []
        first = ['LDraw_RGB', 'instruction_left_RGB', 'instruction_top_RGB', 'instruction_right_RGB']
        if len(header) != 31 or len(header) != len(set(header)) or header[:4] != first or header[-1] != 'native_height_px':
            raise ValueError('Unexpected CSV columns or order.')
        if 'LDraw_color_name' not in header:
            raise ValueError('Missing LDraw color names.')
        rows = list(reader)
    if [int(r['LDraw_CODE']) for r in rows] != list(records):
        raise ValueError('Color IDs, row order or coverage differ from the study.')
    groups = defaultdict(list)
    for row in rows:
        code = int(row['LDraw_CODE'])
        cohort, source, nominal, faces, shifts = records[code]
        pixels = source.get('decoded_pixel_sha256') or source['decoded_sha256']
        expected = {
            'source_image_id': f"{source['set']}-p{source['page']}-{source['image']}",
            'source_pdf_url': f"{source['url']}#page={source['page']}", 'source_pdf_sha256': source['source_sha256'],
            'decoded_image_sha256': pixels, 'sRGB_profile_sha256': source['profile_sha256'],
            'LDConfig_sha256': palette_hash, 'cohort': cohort, 'LDraw_part': '3003.dat',
            'native_width_px': str(source['native_size'][0]), 'native_height_px': str(source['native_size'][1]),
        }
        for key, rgb in [('LDraw', nominal), *((f, faces[f]) for f in FACES)]:
            label = 'LDraw_RGB' if key == 'LDraw' else 'instruction_' + key + '_RGB'
            expected[label] = rgb_text(rgb)
            if [float(row[f'{key}_{c}']) for c in 'RGB'] != rgb:
                raise ValueError(f'LDraw {code}: the numeric {key} channels differ.')
        for face in FACES:
            expected[f'ROI_{face}_xyxy'] = ','.join(str(x) for x in boxes[face])
        for key, value in expected.items():
            if row[key] != value:
                raise ValueError(f'LDraw {code}: {key} differs from the source record.')
        groups[source['source_sha256']].append(dict(
            code=code, page=source['page'], image=source['image'], size=source['native_size'],
            encoded=source['encoded_sha256'], pixel_sha256=pixels, icc_sha256=source['profile_sha256'],
            patches=[(face, boxes[face], faces[face], shifts[face]) for face in FACES]))
    return rows, groups


def check_pdfs(groups, inputs):
    import pypdf

    remaining = set(groups)
    for path in pdf_files(inputs):
        digest = file_hash(path)
        if digest not in remaining:
            continue
        with path.open('rb') as stream:
            reader = pypdf.PdfReader(stream)
            for row in groups[digest]:
                failed = check_image(reader, row)
                if failed:
                    raise ValueError(f"LDraw {row['code']}, page {row['page']}: " + ', '.join(failed))
        remaining.remove(digest)
        if not remaining:
            return len(groups)
    raise ValueError('Missing PDF editions: ' + ', '.join(sorted(remaining)))


def check_palette(rows, library):
    with Library(library) as source:
        for row in rows:
            code = int(row['LDraw_CODE'])
            definition = source.colors[code]
            if (definition['name'] != row['LDraw_color_name'] or
                    list(bytes.fromhex(definition['value'])) != [int(row['LDraw_' + c]) for c in 'RGB']):
                raise ValueError(f'LDraw {code}: palette name or VALUE differs.')
        return source.config_receipt['sha256']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, default=RESEARCH / 'face-colors.csv')
    parser.add_argument('--manuals', nargs='+', type=Path, help='Local PDFs or directories to search by SHA-256')
    parser.add_argument('--library', type=Path, help='Complete LDraw library to check color codes, names and RGB')
    args = parser.parse_args()
    try:
        rows, groups = check_table(args.csv)
        report = {'materials': len(rows), 'numeric_channels': 12 * len(rows), 'source_editions': len(groups)}
        if args.library:
            report['checked_library_sha256'] = check_palette(rows, args.library)
        if args.manuals:
            report['PDFs_verified'] = check_pdfs(groups, args.manuals)
            report['face_windows_verified'] = 3 * len(rows)
            report['shifted_windows_including_center'] = 27 * len(rows)
    except (KeyError, IndexError, OSError, ImportError, TypeError, ValueError) as error:
        parser.exit(1, f'Color table check failed: {error}\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
