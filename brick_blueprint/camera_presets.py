"""Camera recipes, independent of paper colors and material profiles.

FOV refers to the full output page. Distance and focal length are resolved by
the real pinhole camera, not by stretching a finished picture.
"""
from copy import deepcopy

_PRESETS = {
    'instruction': {
        'description': 'Recommended starting point for small instruction parts: weak perspective.',
        'settings': dict(projection='perspective', azimuth=35., elevation=35., field_of_view=2.),
        'evidence': 'CAMERA-STRENGTH: two Classic bricks; descriptive selection, not an exact LEGO camera constant.',
    },
    'instruction-depth': {
        'description': 'Mildly stronger depth; an alternative when the instruction view shows more convergence.',
        'settings': dict(projection='perspective', azimuth=35., elevation=35., field_of_view=5.),
        'evidence': 'CAMERA-STRENGTH: 5 degrees is best of the tested settings for the white brick, but worse for the brown brick. Not a theme-specific preset.',
    },
    'presentation': {
        'description': 'Stronger perspective for general illustration; preserves the previous unselected camera.',
        'settings': dict(projection='perspective', azimuth=35., elevation=35., field_of_view=30.),
        'evidence': 'Engineering default and matched LDView control; not fitted to official instructions.',
    },
    'orthographic': {
        'description': 'Parallel-projection control with constant scale at every depth.',
        'settings': dict(projection='orthographic', azimuth=35., elevation=35.),
        'evidence': 'Comparison control, not a claim that instruction cameras are orthographic.',
    },
}


def all_camera_presets():
    return deepcopy(_PRESETS)


def resolve_camera(preset=None, *, projection=None, azimuth=None, elevation=None,
                   field_of_view=None):
    if preset is not None and preset not in _PRESETS:
        raise ValueError('Unknown camera preset: '+str(preset))
    settings = dict(_PRESETS[preset or 'presentation']['settings'])
    explicit = {k: v for k, v in dict(projection=projection, azimuth=azimuth,
                elevation=elevation, field_of_view=field_of_view).items() if v is not None}
    # Explicit projection wins. Do not silently discard an explicit invalid FOV.
    if explicit.get('projection') == 'orthographic':
        settings.pop('field_of_view', None)
    settings.update(explicit)
    # No implicit preset FOV for a caller explicitly choosing perspective from
    # the orthographic control: retain the generic camera's documented fallback.
    settings.setdefault('field_of_view', None)
    receipt = None if preset is None else {
        'name': preset, 'revision': 1, 'settings': deepcopy(_PRESETS[preset]['settings']),
        'overrides': explicit, 'evidence': _PRESETS[preset]['evidence'],
        'framing': 'Full-page vertical FOV; automatic eye distance fits the drawing viewport. Frame and occupancy affect perspective strength.',
    }
    return settings, receipt
