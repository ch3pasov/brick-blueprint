"""Strict shared material/geometry/state style. No scene IDs or source pixels."""
import json,math,hashlib,collections
from pathlib import Path
TOP={'schema_version','family','sampling','palette','fallback','explicit_colour','stud_wall','edges','step_states','annotation','arrows','page'}
def rgb(v):
 if not isinstance(v,list)or len(v)!=3 or any(isinstance(x,bool)or not isinstance(x,(int,float))or not math.isfinite(x)or not 0<=x<=255 for x in v):raise ValueError('RGB must be three finite 0..255 values')
 return tuple(v)
def exact(d,keys,label):
 if not isinstance(d,dict)or set(d)!=set(keys):raise ValueError(label+' has unsupported/missing keys: '+str(set(d) ^ set(keys)if isinstance(d,dict)else type(d)))
def validate_config(d):
 exact(d,TOP,'shared style')
 if type(d['schema_version']) is not int or d['schema_version']!=1:raise ValueError('Unsupported shared style version')
 exact(d['sampling'],{'geometry_supersample','reduction','codec'},'shared sampling')
 if d['sampling']!={'geometry_supersample':2,'reduction':'box','codec':'RGB8_stored_DEFLATE'}:raise ValueError('Unsupported shared sampling policy')
 if not isinstance(d['palette'],dict):raise ValueError('Material palette must be an object')
 for key,p in d['palette'].items():
  if not isinstance(key,str) or not key.isascii() or not key.isdigit():raise ValueError('Only numeric nominal material IDs in palette')
  exact(p,{'side','top','front','confidence'},'material palette');[rgb(p[k])for k in('side','top','front')]
 exact(d['fallback'],{'mode','confidence','normal_gains'},'fallback')
 if d['fallback']['mode']!='installed_nominal_palette':raise ValueError('Unsupported fallback')
 if d['fallback']['normal_gains']!=[1,1,1] or any(isinstance(v,bool) for v in d['fallback']['normal_gains']):raise ValueError('Nominal fallback must be explicit identity, no hidden target fit')
 exact(d['explicit_colour'],{'black_rgb','confidence'},'explicit colour');rgb(d['explicit_colour']['black_rgb'])
 exact(d['stud_wall'],{'rgb','applies_when','confidence'},'stud wall');rgb(d['stud_wall']['rgb'])
 if d['stud_wall']['applies_when']!='cylinder_axis_parallel_world_vertical':raise ValueError('Unsupported geometric stud-wall applicability')
 exact(d['edges'],{'dark_rgb','light_rgb','width_points','light_if_nominal_Y_below','light_if_nominal_max_below','confidence'},'edges');rgb(d['edges']['dark_rgb']);rgb(d['edges']['light_rgb'])
 exact(d['step_states'],{'new','existing','unknown'},'step states')
 for state,row in d['step_states'].items():
  exact(row,{'gain','bias'},'state transform')
  if row!={'gain':1,'bias':0} or any(isinstance(v,bool) for v in row.values()):raise ValueError('This admitted version has no source-supported universal fade; state material must remain identity')
 exact(d['annotation'],{'current_boundary_when','rgb','width_points','probe_width_factor','confidence'},'annotation');rgb(d['annotation']['rgb'])
 if d['annotation']['current_boundary_when']!='ordinary_ink_is_light_and_existing_context':raise ValueError('Unsupported current-boundary rule')
 exact(d['arrows'],{'internal_assembly','subassembly_placement'},'semantic arrow roles')
 for role,a in d['arrows'].items():exact(a,{'rgb','width_points','head_length_points','head_width_points'},'arrow style');rgb(a['rgb'])
 exact(d['page'],{'width_points','height_points','background_rgb','text_rgb','callout_rgb','font_name','step_font_points','count_font_points'},'page');[rgb(d['page'][k])for k in('background_rgb','text_rgb','callout_rgb')]
 for obj,key in[(d['edges'],'width_points'),(d['annotation'],'width_points'),(d['annotation'],'probe_width_factor')]+[(a,k)for a in d['arrows'].values()for k in('width_points','head_length_points','head_width_points')]:
  if isinstance(obj[key],bool)or not isinstance(obj[key],(int,float))or not math.isfinite(obj[key])or obj[key]<=0:raise ValueError('Invalid positive style scalar '+key)
 # These fields are read as scalars/strings later. Reject invalid types here
 # so a user-supplied JSON file produces a clear ValueError, not a traceback
 # during shading or silently false comparisons against NaN.
 for key in ('light_if_nominal_Y_below','light_if_nominal_max_below'):
  value=d['edges'][key]
  if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=255:
   raise ValueError('Invalid 0..255 edge threshold '+key)
 for key in ('width_points','height_points','step_font_points','count_font_points'):
  value=d['page'][key]
  if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0:
   raise ValueError('Invalid positive page scalar '+key)
 texts=[('family',d['family']),('page.font_name',d['page']['font_name'])]
 texts += [(section+'.confidence',d[section]['confidence']) for section in ('fallback','explicit_colour','stud_wall','edges','annotation')]
 texts += [('palette.'+key+'.confidence',row['confidence']) for key,row in d['palette'].items()]
 for label,value in texts:
  if not isinstance(value,str) or not value.strip():raise ValueError('Style text must be a nonempty string: '+label)
 return d
class GlobalStyle:
 def __init__(self,path):
  self.path=Path(path).resolve();self.data=validate_config(json.loads(self.path.read_text()));self.sha256=hashlib.sha256(self.path.read_bytes()).hexdigest();self.coverage=collections.Counter()
 def light_ink(self,nominal):
  e=self.data['edges'];return sum(v*w for v,w in zip(nominal,(.2126,.7152,.0722)))<e['light_if_nominal_Y_below']and max(nominal)<e['light_if_nominal_max_below']
 def face(self,colour,nominal,normal,feature,state='unknown',alpha=1):
  if state not in self.data['step_states']:raise ValueError('Explicit new/existing/unknown state required')
  if feature=='stud_cylinder_wall':value=rgb(self.data['stud_wall']['rgb']);confidence=self.data['stud_wall']['confidence']
  elif feature=='explicit_colour_surface'and colour==0:value=rgb(self.data['explicit_colour']['black_rgb']);confidence=self.data['explicit_colour']['confidence']
  else:
   p=self.data['palette'].get(str(colour))
   if p:
    weights=[abs(normal[0]),abs(normal[1]),abs(normal[2])];total=sum(weights);value=tuple(sum(w*p[k][c]for w,k in zip(weights,('side','top','front')))/total for c in range(3));confidence=p['confidence']
   else:value=nominal;confidence=self.data['fallback']['confidence']
  if feature=='sideways_stud_cylinder_wall':confidence+='; sideways_stud_wall_uncalibrated'
  if alpha<.999999:confidence+='; transparent_uncalibrated'
  self.coverage[(colour,feature,confidence)]+=1
  return value
 def edge(self,nominal,feature,explicit=False):
  light=self.light_ink(nominal);ordinary=rgb(self.data['edges']['light_rgb'if light else'dark_rgb'])
  # Explicit painted lines retain the common dark convention. They are not a
  # source mask and do not inherit the root black material's light polarity.
  if explicit:ordinary=rgb(self.data['edges']['dark_rgb'])
  return ordinary, bool(light and feature=='body'and not explicit)
 def receipt(self):return{'config_path':str(self.path),'config_sha256':self.sha256,'family':self.data['family'],'coverage':[{'nominal_colour':k[0],'feature':k[1],'confidence':k[2],'triangles':v}for k,v in sorted(self.coverage.items())],'fallback_colours':sorted({k[0]for k in self.coverage if k[2].startswith('uncalibrated')}),'source_pixel_inputs':False,'instance_selectors':False,'step_material_fade':False}
