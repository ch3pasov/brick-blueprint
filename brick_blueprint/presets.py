"""Evidence-linked presentation presets, not universal theme specifications."""
from pathlib import Path
import copy
import json

def all_presets():
    return json.loads(Path(__file__).with_name('presets.json').read_text())['presets']

def get_preset(name):
    values=all_presets()
    if name not in values:raise ValueError('Unknown preset: '+name)
    return copy.deepcopy(values[name])

def rgb_hex(value):
    return tuple(int(value[i:i+2],16) for i in (1,3,5))
