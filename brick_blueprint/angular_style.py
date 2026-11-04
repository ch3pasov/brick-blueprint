"""Bounded empirical interpolation of measured opaque slope colors.

The two principal normal sectors have source observations. Blending between
them, and mirroring them onto opposite sides, is an illustration convention.
No source pixels, element IDs, cameras or scene-specific masks are inputs.
"""
import math


def decode_srgb(value):
    value /= 255.0
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def encode_srgb(value):
    value = max(0.0, min(1.0, value))
    return 255 * (12.92 * value if value <= 0.0031308 else 1.055 * value ** (1 / 2.4) - 0.055)


def sector_color(palette, color, inclination, side, method):
    """Return unquantized RGB for a 0..90 degree principal slope."""
    if not math.isfinite(inclination) or not 0 <= inclination <= 90:
        raise ValueError('Slope inclination must be finite and within 0..90 degrees')
    if side not in ('left', 'right'):
        raise ValueError('Slope side must be left or right')
    dark, top, right = (palette[k] for k in ('side', 'top', 'front'))

    def affine(name):
        gain, bias = method[name]
        return [max(0, min(255, gain * c + bias)) for c in dark]

    if side == 'left':
        knots = method['left_knots_deg']
        middle = method['white26_override'] if int(color) == 15 else affine('left26_affine')
        colors = [top, middle, affine('left45_affine'), dark]
    else:
        knots = method['right_knots_deg']
        colors = [top, affine('right45_affine'), right]
    # Preserve measured anchors exactly, without a transfer round-trip.
    for angle, rgb in zip(knots, colors):
        if inclination == angle:
            return tuple(rgb)
    i = next(i for i in range(len(knots) - 1) if knots[i] <= inclination <= knots[i + 1])
    a, b = knots[i:i + 2]
    denominator = math.sin(math.radians(b - a))
    w0 = math.sin(math.radians(b - inclination)) / denominator
    w1 = math.sin(math.radians(inclination - a)) / denominator
    return tuple(encode_srgb(w0 * decode_srgb(x) + w1 * decode_srgb(y))
                 for x, y in zip(colors[i], colors[i + 1]))


def angular_color(palette, color, normal, method):
    """Continuous upper-hemisphere color and an explicit evidence category.

Lower surfaces return None so the caller retains its established convention.
The encoded-RGB azimuth blend preserves the existing vertical-wall colors.
"""
    x, y, z = normal
    if not all(math.isfinite(v) for v in normal) or x == y == z == 0:
        raise ValueError('Surface normal must be finite and nonzero')
    if y > 0:
        return None
    horizontal = math.hypot(x, z)
    if horizontal == 0:
        return tuple(palette['top']), 'axis_anchor'
    theta = math.degrees(math.atan2(horizontal, -y))
    ax, az = abs(x), abs(z)
    left = sector_color(palette, color, theta, 'left', method)
    right = sector_color(palette, color, theta, 'right', method)
    rgb = tuple((ax * l + az * r) / (ax + az) for l, r in zip(left, right))
    if y == 0:
        category = 'axis_anchor' if x == 0 or z == 0 else 'unmeasured_azimuth_blend'
    elif x < 0 or z < 0:
        category = 'unmeasured_mirrored_direction'
    elif ax > 0 and az > 0:
        category = 'unmeasured_azimuth_blend'
    else:
        category = 'empirical_principal_slope'
    return rgb, category
