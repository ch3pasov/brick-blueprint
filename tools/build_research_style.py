"""Build the bounded three-face material profile from published numeric data.

No official image pixels or external library are needed. The LDraw mapping is
an explicit model-authoring association, not recovered manufacturer shader IDs.
"""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
MAPPING = {
    'dark gray': (72, 'Dark_Bluish_Grey', 0, '4211060'),
    'yellow': (14, 'Yellow', 1, '300324'),
    'light gray': (71, 'Light_Bluish_Grey', 18, '4211387'),
    'black': (0, 'Black', 20, '300326'),
    'white': (15, 'White', 21, '300301'),
    'red': (4, 'Red', 22, '300321'),
    'dark tan': (28, 'Dark_Tan', 23, '4255416'),
    'brown': (70, 'Reddish_Brown', 25, '4211210'),
    'yellow orange': (191, 'Bright_Light_Orange', 30, '6295078'),
    'orange': (25, 'Orange', 38, '4153825'),
}


def build():
    source = ROOT/'docs/THREE-FACE-SHADING.json'
    raw = source.read_bytes()
    data = json.loads(raw)
    style = json.loads((ROOT/'brick_blueprint/legacy-style.json').read_text())
    style['family'] = 'Brick Blueprint measured sRGB reference v4'
    style['palette'] = {}
    bindings = []
    for label, (code, name, number, element) in MAPPING.items():
        row = next(r for r in data['observations'] if r['i'] == number)
        assert row['color_label_visual'] == label
        style['palette'][str(code)] = {
            'side': row['faces']['left'], 'top': row['faces']['top'],
            'front': row['faces']['right'],
            'confidence': 'observed opaque RGB anchors; normal interpolation and opposite faces are illustration extensions',
        }
        bindings.append({
            'ldraw_color': code, 'ldraw_name': name,
            'source_visual_label': label, 'observation_id': number,
            'catalogue_element_association': element,
            'source_set': row['set'], 'source_page': row['page'],
            'source_image': row['image'], 'source_url': row['url'],
            'source_pdf_sha256': row['source_sha256'],
            'source_image_sha256': row['encoded_sha256'],
            'profile_sha256': row['profile_sha256'],
            'anchor_RGB': {k: row['faces'][k] for k in ('left', 'top', 'right')},
        })
    # A new material enters only after its independently selected 2x4 controls
    # pass the declared central and window-shift gates. The ten-color formula
    # experiment remains frozen; its coefficients are not a runtime palette.
    holdout_path = ROOT/'docs/research/NEW-COLOR-HOLDOUT.json'
    transfer_path = ROOT/'docs/research/NEW-COLOR-GEOMETRY-TRANSFER.json'
    holdout = json.loads(holdout_path.read_bytes())
    transfer = json.loads(transfer_path.read_bytes())
    tan = next(r for r in holdout['measurements']['observations'] if r['id'] == 'C21')
    gate = transfer['results']['summary']['19']
    assert tan['identity']['LDraw_code'] == 19 and tan['identity']['element'] == '4114306'
    assert tan['identity']['visual_catalogue_and_label_check'] and tan['profile_matches']
    assert gate['central_gate_pass'] and gate['all_nine_shifts_pass']
    assert gate['MAE'] <= 3 and gate['max_shift_channel_error'] <= 10
    extension = {
        'data_file': str(holdout_path.relative_to(ROOT)),
        'data_sha256': hashlib.sha256(holdout_path.read_bytes()).hexdigest(),
        'control_file': str(transfer_path.relative_to(ROOT)),
        'control_sha256': hashlib.sha256(transfer_path.read_bytes()).hexdigest(),
        'three_face_MAE': gate['MAE'],
        'max_shift_channel_error': gate['max_shift_channel_error'],
        'all_nine_shifts_pass': True,
        'scope': 'Tan19 only; two 2x4 images in Architecture2025 and Botanicals2026; identical output face medians are not independent colors',
    }
    style['palette']['19'] = {
        'side': tan['faces']['left'], 'top': tan['faces']['top'], 'front': tan['faces']['right'],
        'confidence': 'observed opaque RGB anchors; 2x4 transfer gate passed; normal interpolation and opposite faces are illustration extensions',
    }
    src = tan['source']
    bindings.append({
        'ldraw_color': 19, 'ldraw_name': 'Tan', 'source_visual_label': 'tan',
        'observation_id': 'C21', 'catalogue_element_association': '4114306',
        'source_set': src['set'], 'source_page': src['page'], 'source_image': src['image'],
        'source_url': src['url'], 'source_pdf_sha256': src['source_sha256'],
        'source_image_sha256': src['encoded_sha256'], 'profile_sha256': src['profile_sha256'],
        'anchor_RGB': {k: tan['faces'][k] for k in ('left', 'top', 'right')},
        'geometry_transfer_validation': extension,
    })
    studs_path = ROOT/'docs/research/STUD-SURFACE-STUDY.json'
    studs_raw = studs_path.read_bytes()
    studs = json.loads(studs_raw)
    style['stud_wall']['rgb'] = studs['reference_RGB']
    style['stud_wall']['confidence'] = 'bounded opaque vertical stud reference; two Classic2024 books plus new-color holdout'
    # The adapter keeps legacy RGB7 for transparent or sideways stud walls.
    # These surfaces are outside the measured reference scope.
    evidence = {
        'profile_id': 'measured-srgb-reference-v4',
        'data_file': 'docs/THREE-FACE-SHADING.json',
        'data_sha256': hashlib.sha256(raw).hexdigest(),
        'scope': 'Ten-color baseline plus Tan19 validated on 2x4 geometry; eleven opaque materials, one common brick pose',
        'extension': extension,
        'coordinate_rule': 'abs(world normal X/Y/Z) weights left/top/right anchors; +X is left and +Z right in the reference positive-X/positive-Z camera quadrant',
        'interpolation_status': 'convex encoded-RGB illustration interpolation, not a recovered light law',
        'other_faces_status': 'opposite faces share absolute-axis weights; their lighting is unmeasured',
        'upper_stud_cap_status': 'uses the planar-top anchor; two Classic2024 source cases agree within one RGB level in cap/plane medians; other materials unmeasured',
        'stud_wall_reference': {'data_file':'docs/research/STUD-SURFACE-STUDY.json',
                                'data_sha256':hashlib.sha256(studs_raw).hexdigest(),
                                'reference_RGB':studs['reference_RGB'],
                                'scope':studs['scope'],
                                'transparent_or_sideways_RGB':[7,7,7]},
        'unmeasured_colors': 'nominal supplied library RGB, without fitted shading',
        'transparent_colors': 'nominal supplied library RGB and existing shell approximation',
        'bindings': bindings,
    }
    return style, evidence


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Build or check the measured material profile.')
    parser.add_argument('--check', action='store_true', help='Check packaged values without changing files.')
    args = parser.parse_args()
    style, evidence = build()
    for name, value in [('default-style.json', style), ('material-research.json', evidence)]:
        target = ROOT/'brick_blueprint'/name
        if args.check:
            if json.loads(target.read_text()) != value:
                parser.exit(1, f'Packaged {name} differs from the research data.\n')
        else:
            target.write_text(json.dumps(value, indent=2)+'\n')
    print(('Verified' if args.check else 'Built') + f' {len(style["palette"])} opaque material anchors from checked research data.')
