"""Shared material rules with an explicit measured-reference/legacy boundary."""
from collections import Counter
import hashlib
import json
from pathlib import Path
from .instruction_style import GlobalStyle
from .angular_style import angular_color

MATERIAL_PROFILES = ('research', 'research-angular', 'legacy')


def load_style(style_path=None, material_profile=None):
 if style_path is not None and material_profile is not None:
  raise ValueError('Choose either --style or --material-profile, not both')
 if material_profile is not None and material_profile not in MATERIAL_PROFILES:
  raise ValueError('Unknown material profile: '+str(material_profile))
 profile='custom' if style_path is not None else (material_profile or 'research')
 path=Path(style_path) if style_path is not None else Path(__file__).with_name('legacy-style.json' if profile=='legacy' else 'default-style.json')
 return Style(path, profile=profile)


class Style(GlobalStyle):
 def __init__(self,path,profile='custom'):
  super().__init__(path);self.profile=profile;self.uses=Counter();self.research=None;self.angular=None
  if profile in ('research', 'research-angular'):
   source=Path(__file__).with_name('material-research.json');raw=source.read_bytes()
   self.research=json.loads(raw);self.research_hash=hashlib.sha256(raw).hexdigest()
   bindings=self.research['bindings']
   if set(self.data['palette'])!={str(r['ldraw_color']) for r in bindings}:
    raise ValueError('Research material profile does not match its evidence record')
   for row in bindings:
    p=self.data['palette'][str(row['ldraw_color'])]
    if any(p[k]!=row['anchor_RGB'][f] for k,f in [('side','left'),('top','top'),('front','right')]):
     raise ValueError('Research material anchors do not match their evidence record')
   if self.data['stud_wall']['rgb']!=self.research['stud_wall_reference']['reference_RGB']:
    raise ValueError('Research stud-wall color does not match its evidence record')
  if profile=='research-angular':
   raw=Path(__file__).with_name('angular-material.json').read_bytes()
   self.angular=json.loads(raw);self.angular_hash=hashlib.sha256(raw).hexdigest()
   if self.angular['schema_version']!=1 or self.angular['palette_sha256']!=self.sha256:
    raise ValueError('Angular material profile does not match its measured palette')

 def light_ink(self,nominal):
  return super().light_ink(nominal) and max(nominal)-min(nominal)<=.5*max(nominal)

 def face(self,colour,nominal,normal,feature,state="unknown",alpha=1):
  if state not in self.data['step_states']:raise ValueError('Explicit new/existing/unknown state required')
  if self.research and feature in ('stud_cylinder_wall','sideways_stud_cylinder_wall'):
   reference=self.research['stud_wall_reference']
   measured=alpha>=.999999 and feature=='stud_cylinder_wall'
   self.uses['opaque_vertical_stud_reference' if measured else 'legacy_unmeasured_stud_wall']+=1
   self.coverage[(colour,feature,'bounded opaque vertical stud reference' if measured else 'unmeasured transparent/sideways stud convention')]+=1
   return tuple(reference['reference_RGB'] if measured else reference['transparent_or_sideways_RGB'])
  if self.research and alpha<.999999 and feature not in ('stud_cylinder_wall','sideways_stud_cylinder_wall'):
   self.uses['transparent_nominal_fallback']+=1
   self.coverage[(colour,feature,'uncalibrated transparent nominal RGB')]+=1
   return nominal
  if self.angular and feature=='body' and str(colour) in self.data['palette']:
   value=angular_color(self.data['palette'][str(colour)],colour,normal,self.angular['method'])
   if value is not None:
    rgb,category=value
    self.uses[category]+=1
    self.coverage[(colour,feature,'opt-in angular: '+category)]+=1
    return rgb
   self.uses['angular_lower_surface_fallback']+=1
  if feature in ('stud_cylinder_wall','sideways_stud_cylinder_wall'):
   self.uses['legacy_stud_wall_convention']+=1
  elif str(colour) in self.data['palette']:
   # Counts describe submitted triangles, including hidden surfaces. They are
   # scope metadata, never an image-quality or visible-area percentage.
   self.uses['axis_anchor' if sum(abs(v)>1e-8 for v in normal)==1 else 'interpolated_orientation']+=1
  else:self.uses['nominal_fallback']+=1
  if feature=="sideways_stud_cylinder_wall":feature="stud_cylinder_wall"
  return super().face(colour,nominal,normal,feature,state,alpha)

 def receipt(self):
  report=super().receipt();report.pop('config_path')
  report.update(profile=self.profile,counts_scope='submitted triangles, not visible area',usage=dict(self.uses))
  if self.research:
   covered={k[0] for k in self.coverage}
   report.update(research_profile=self.research['profile_id'],evidence_sha256=self.research_hash,
                 data_sha256=self.research['data_sha256'],
                 bindings=[r for r in self.research['bindings'] if r['ldraw_color'] in covered],
                 coordinate_rule=self.research['coordinate_rule'],
                 interpolation_status=self.research['interpolation_status'],
                 other_faces_status=self.research['other_faces_status'],
                 upper_stud_cap_status=self.research['upper_stud_cap_status'],
                 stud_wall_reference=self.research['stud_wall_reference'])
  if self.angular:
   report.update(angular_profile=self.angular['profile_id'],angular_evidence_sha256=self.angular_hash,
                 angular_data_sha256=self.angular['data_sha256'],
                 interpolation_status='opt-in piecewise linear-light directional interpolation; encoded-RGB azimuth blend',
                 angular_scope=self.angular['scope'],angular_limits=self.angular['limits'])
  return report
