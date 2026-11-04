"""Repeat the geometry-only top-color measurement on a supplied native image.

Requires NumPy and Pillow for research only. No images are bundled or downloaded.
The decoded source pixels must match one of the two declared source hashes.
The output is a numeric report and a geometry mask, not a source illustration.
"""
from pathlib import Path
import argparse
import hashlib
import json

import numpy as np
from PIL import Image

from analyze_volume_camera import basis

ROOT = Path(__file__).resolve().parents[1]


def top_mask(size, camera, pixel_aspect, half_width):
    """Intersect pixel rays with the top plane; reject stud-cylinder occlusion."""
    width, height = size
    yy, xx = np.indices((height, width))
    p = np.asarray(camera, dtype=float)
    rotation = basis(*p[:3])
    origin = -rotation.T @ np.array([p[5], p[6], np.exp(p[3])])
    uv = np.stack([xx, yy * pixel_aspect], axis=-1)
    ray = np.concatenate([(uv - p[7:9]) / np.exp(p[4]),
                          np.ones((height, width, 1))], axis=-1) @ rotation
    distance = (-12 - origin[1]) / ray[:, :, 1]
    plane = origin + ray * distance[:, :, None]
    inside = ((distance > 0) & (abs(plane[:, :, 0]) < half_width)
              & (abs(plane[:, :, 2]) < 20))
    blocked = np.zeros_like(inside)
    for center_x in range(-half_width + 10, half_width, 20):
        for center_z in (-10, 10):
            ox, oz = origin[0] - center_x, origin[2] - center_z
            dx, dz = ray[:, :, 0], ray[:, :, 2]
            a = dx * dx + dz * dz
            b = 2 * (ox * dx + oz * dz)
            c = ox * ox + oz * oz - 36
            discriminant = b * b - 4 * a * c
            for sign in (-1, 1):
                hit = (-b + sign * np.sqrt(np.maximum(discriminant, 0))) / (2 * a)
                hit_y = origin[1] + ray[:, :, 1] * hit
                blocked |= ((discriminant >= 0) & (hit > 0) & (hit < distance)
                            & (hit_y >= -16) & (hit_y <= -12))
            cap_distance = (-16 - origin[1]) / ray[:, :, 1]
            cap = origin + ray * cap_distance[:, :, None]
            blocked |= ((cap_distance > 0) & (cap_distance < distance)
                        & ((cap[:, :, 0] - center_x) ** 2
                           + (cap[:, :, 2] - center_z) ** 2 <= 36))
    return inside & ~blocked


def erode(mask, margin):
    height, width = mask.shape
    padded = np.pad(mask, margin)
    result = np.ones_like(mask)
    for dy in range(-margin, margin + 1):
        for dx in range(-margin, margin + 1):
            result &= padded[margin + dy:margin + dy + height,
                             margin + dx:margin + dx + width]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, choices=['11038-p19-X1', '11037-p8-X2'])
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    evidence_path = ROOT / 'docs/research/LARGE-TOP-TRANSFER.json'
    evidence = json.loads(evidence_path.read_text())
    source = next(s for s in evidence['source_RGB'] if s['id'] == args.source)
    protocol = next(s for s in evidence['protocol']['sources'] if s['id'] == args.source)
    with Image.open(args.image) as raw:
        image = raw.convert('RGB')
    if list(image.size) != source['size'] or hashlib.sha256(image.tobytes()).hexdigest() != source['decoded_RGB_sha256']:
        parser.error('Decoded native RGB does not match the declared source. Do not resize or color-convert it.')
    camera_path = ROOT / 'docs/research/VOLUME-CAMERA-RESULTS.json'
    cameras = json.loads(camera_path.read_text())
    row = next(r for r in cameras['rows'] if r['id'] == args.source
               and r['threshold'] == protocol['camera_threshold'])
    mask = top_mask(image.size, row['camera']['parameters'], row['pixel_aspect_y_x'],
                    protocol['half_width'])
    pixels = np.array(image)
    measurements = []
    palette = json.loads((ROOT / 'brick_blueprint/default-style.json').read_text())['palette']
    reference = np.array(palette[str(protocol['color'])]['top'])
    for margin in evidence['protocol']['sensitivity_margins']:
        selected = pixels[erode(mask, margin)]
        if not len(selected):
            parser.error('The declared geometry mask is empty')
        median = np.median(selected, axis=0)
        measurements.append({'margin_pixels': margin, 'pixel_count': len(selected),
                             'median_RGB': median.tolist(), 'reference_RGB': reference.tolist(),
                             'reference_error': (reference - median).tolist()})
    args.output.mkdir(parents=True, exist_ok=False)
    primary = erode(mask, evidence['protocol']['primary_margin_native_pixels'])
    Image.fromarray((primary * 255).astype('uint8')).save(args.output / 'geometry-mask.png')
    report = {'id': args.source, 'measurements': measurements,
              'visible_pixels_before_erosion': int(mask.sum()),
              'source_decoded_RGB_sha256': source['decoded_RGB_sha256'],
              'camera_results_sha256': hashlib.sha256(camera_path.read_bytes()).hexdigest(),
              'protocol_data_sha256': hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
              'mask_sha256': hashlib.sha256((args.output / 'geometry-mask.png').read_bytes()).hexdigest()}
    (args.output / 'measurement.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
