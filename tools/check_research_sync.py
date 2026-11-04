"""Verify the declared research/render boundary; no GUI, network or rendering kernel.

Checks source data -> packaged palette -> default projected scene -> current
example receipts and image hashes. This is consistency, not source validity or
proof that the entire illustration matches an official instruction.
"""
from pathlib import Path
import contextlib,hashlib,inspect,io,json,sys,tempfile
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tools'))
from brick_blueprint import __version__,cli
from brick_blueprint.project import project
from brick_blueprint.tray import render_tray
from brick_blueprint.style import load_style
from brick_blueprint.camera_presets import resolve_camera
from build_research_style import build

def check():
 contract=json.loads((ROOT/'docs/research/RENDER-CONTRACT.json').read_text());checks=[]
 def test(name,actual,expected):checks.append({'check':name,'pass':actual==expected})
 test('renderer version',__version__,contract['renderer_version'])
 package=ROOT/'brick_blueprint'
 source_rows=[(p.relative_to(package).as_posix(),hashlib.sha256(p.read_bytes()).hexdigest())
              for p in sorted(package.rglob('*'),key=lambda p:p.relative_to(package).as_posix())
              if p.is_file() and (p.suffix in {'.py','.json','.cpp','.h'} or p.name=='LICENSE')]
 package_sha=hashlib.sha256(json.dumps(source_rows,separators=(',',':')).encode()).hexdigest()
 test('active source package',package_sha,contract['active_package_source_sha256'])
 # Research observations retain the runtime that produced them. Do not relabel
 # frozen artifacts when adding an opt-in camera recipe to the active renderer.
 vector_reference=contract['vector_reference_package_source_sha256']
 evidence_version=contract['evidence_snapshot']['renderer_version']
 evidence_package_sha=contract['evidence_snapshot']['package_source_sha256']
 for path,expected in contract['data_hashes'].items():test(path,hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),expected)
 style,evidence=build()
 for name,data in [('default-style.json',style),('material-research.json',evidence)]:test('generated '+name,json.loads((ROOT/'brick_blueprint'/name).read_text()),data)
 test('default material profile',load_style().profile,contract['material_profile'])
 for fn in (project,render_tray):
  args=inspect.signature(fn).parameters
  resolved,_=resolve_camera(**{key:args[key].default for key in ('azimuth','elevation','projection')})
  for key in ('azimuth','elevation','projection'):test(fn.__name__+'/'+key,resolved[key],contract['camera'][key])
 # Actual projection with omitted camera/style parameters, no C++ compilation.
 with tempfile.TemporaryDirectory() as d:
  receipt=project(ROOT/'examples/demo.ldr',ROOT/'examples/library',Path(d)/'default.scene')
 for key,value in contract['camera'].items():test('default scene/'+key,receipt['camera'][key],value)
 test('default scene/profile',receipt['materials']['profile'],contract['material_profile'])
 # Parse CLI defaults through the real entrypoint; replace only the expensive action.
 report={'parts':1,'pdf':{'PDF_bytes':0},'item_count':1,'rendered_parts':1,'represented_parts':1}
 for action,name in [('render','render'),('tray','render_tray')]:
  with patch.object(cli,name,return_value=report) as fn,contextlib.redirect_stdout(io.StringIO()):cli.main([action,'fixture','--library','library','--output','output'])
  resolved,_=resolve_camera(**{key:fn.call_args.kwargs.get(key) for key in ('azimuth','elevation','projection')})
  for key in ('azimuth','elevation','projection'):test('CLI '+action+'/'+key,resolved[key],contract['camera'][key])
 examples=json.loads((ROOT/'docs/gallery/material-current-examples.json').read_text())
 test('examples version',examples['version'],__version__)
 test('example recipe',examples['recipe_sha256'],hashlib.sha256((ROOT/'tools/render_material_examples.py').read_bytes()).hexdigest())
 for scene in examples['scenes']:
  for mode,expected in scene['renders'].items():
   path=ROOT/'docs/gallery'/f'material-current-{scene["id"]}-{mode}.json';saved=json.loads(path.read_text())
   test(path.name+'/receipt',hashlib.sha256(path.read_bytes()).hexdigest(),expected['receipt_sha256'])
   test(path.name+'/camera',saved['camera'],scene['camera']);test(path.name+'/model',saved['model_sha256'],scene['model_sha256'])
   test(path.name+'/version',saved['version'],__version__)
   test(path.name+'/package-source',saved['execution']['package_source_sha256'],vector_reference)
   test(path.name+'/profile',saved['materials']['profile'],mode)
   test(path.name+'/measured profile',mode,'research')
   test(path.name+'/preset',saved['camera']['preset']['name'],'instruction')
   test(path.name+'/style',saved['style_sha256'],hashlib.sha256((ROOT/'brick_blueprint/default-style.json').read_bytes()).hexdigest())
 for name,expected in examples['previews'].items():test(name,hashlib.sha256((ROOT/'docs/images'/name).read_bytes()).hexdigest(),expected)
 calibrated=json.loads((ROOT/'docs/gallery/camera-calibrations.json').read_text())
 test('calibration version',calibrated['version'],evidence_version)
 test('calibration recipe',calibrated['recipe_sha256'],hashlib.sha256((ROOT/'tools/render_camera_calibrations.py').read_bytes()).hexdigest())
 test('calibration numerical source',calibrated['numerical_results_sha256'],hashlib.sha256((ROOT/'docs/research/VOLUME-CAMERA-RESULTS.json').read_bytes()).hexdigest())
 for row in calibrated['renders']:
  path=ROOT/'docs/gallery'/('camera-calibrated-'+row['id']+'.json');saved=json.loads(path.read_text())
  test(path.name+'/receipt',hashlib.sha256(path.read_bytes()).hexdigest(),row['receipt_sha256'])
  test(path.name+'/version',saved['version'],evidence_version)
  test(path.name+'/package-source',saved['execution']['package_source_sha256'],evidence_package_sha)
  test(path.name+'/camera',saved['camera'],row['camera'])
  test(path.name+'/native-vectors',saved['pdf']['image_XObjects'],0)
 for name,expected in calibrated['previews'].items():test(name,hashlib.sha256((ROOT/'docs/images'/name).read_bytes()).hexdigest(),expected)
 projection_pair=[]
 for mode in ('orthographic','perspective'):
  saved=json.loads((ROOT/'docs/gallery'/('camera-current-kiosk-'+mode+'.json')).read_text())
  projection_pair.append(saved)
  test('projection pair/'+mode+'/version',saved['version'],evidence_version)
  test('projection pair/'+mode+'/package',saved['execution']['package_source_sha256'],evidence_package_sha)
  test('projection pair/'+mode+'/projection',saved['camera']['projection'],mode)
  test('projection pair/'+mode+'/native',saved['pdf']['image_XObjects'],0)
 for field in ('model_sha256','points_per_ldu','style_sha256','line_width_points'):
  test('projection pair/same '+field,projection_pair[0][field],projection_pair[1][field])
 current=json.loads((ROOT/'docs/gallery/current-presets.json').read_text())
 recipe=current['render_recipe'];previews=current['previews']
 test('current presets/version',recipe['version'],evidence_version)
 test('current presets/appearance',recipe['appearance'],'current')
 test('current presets/render recipe',recipe['recipe_sha256'],hashlib.sha256((ROOT/'tools/render_gallery.py').read_bytes()).hexdigest())
 test('current presets/preview recipe',previews['recipe_sha256'],hashlib.sha256((ROOT/'tools/compose_preset_gallery.py').read_bytes()).hexdigest())
 test('current presets/board',previews['board_sha256'],hashlib.sha256((ROOT/'docs/images/presets-current.png').read_bytes()).hexdigest())
 test('current presets/inventory',sorted(recipe['renders']),sorted(r['preset']for r in previews['items']))
 for row in previews['items']:
  key=row['preset'];path=ROOT/'docs/gallery'/('current-preset-'+key+'.json');saved=json.loads(path.read_text())
  test(path.name+'/recipe receipt',hashlib.sha256(path.read_bytes()).hexdigest(),recipe['renders'][key])
  test(path.name+'/preview receipt',hashlib.sha256(path.read_bytes()).hexdigest(),row['receipt_sha256'])
  test(path.name+'/version',saved['version'],evidence_version)
  test(path.name+'/package-source',saved['execution']['package_source_sha256'],evidence_package_sha)
  test(path.name+'/native-vectors',saved['pdf']['image_XObjects'],0)
  artwork=ROOT/'docs/paper-styles'/(key+'.svg')
  test('paper styles/'+key+'/native SVG',hashlib.sha256(artwork.read_bytes()).hexdigest(),saved['pdf']['SVG_sha256'])
  test(path.name+'/PNG',hashlib.sha256((ROOT/'docs/images'/('current-preset-'+key+'.png')).read_bytes()).hexdigest(),row['png_sha256'])
  expected_camera=contract['preset_tray_camera'] if 'items'in saved else contract['camera']
  for index,item in enumerate(saved.get('items',[saved])):
   for field in ('azimuth','elevation','projection','field_of_view_vertical_degrees'):
    test(path.name+'/'+str(index)+'/'+field,item['camera'][field],expected_camera[field])
   test(path.name+'/'+str(index)+'/profile',item['materials']['profile'],'research')
   test(path.name+'/'+str(index)+'/style',item['style_sha256'],hashlib.sha256((ROOT/'brick_blueprint/default-style.json').read_bytes()).hexdigest())
   if 'points_per_ldu'in saved and 'items'in saved:test(path.name+'/'+str(index)+'/common scale',item['points_per_ldu'],saved['points_per_ldu'])
 strength=json.loads((ROOT/'docs/research/CAMERA-STRENGTH.json').read_text())
 for row in strength['native_replays']:
  path=ROOT/'docs/gallery'/(row['id']+'.json');saved=json.loads(path.read_text())
  test(path.name+'/receipt',hashlib.sha256(path.read_bytes()).hexdigest(),row['receipt_sha256'])
  test(path.name+'/version',saved['version'],evidence_version)
  test(path.name+'/package-source',saved['execution']['package_source_sha256'],evidence_package_sha)
  expected_projection='orthographic' if row['FOV']==0 else 'perspective'
  test(path.name+'/projection',saved['camera']['projection'],expected_projection)
  if expected_projection=='orthographic':
   test(path.name+'/FOV not a pinhole parameter','field_of_view_vertical_degrees' not in saved['camera'],True)
  else:
   test(path.name+'/FOV',saved['camera']['field_of_view_vertical_degrees'],row['FOV'])
  test(path.name+'/model',saved['model_sha256'],row['model_sha256'])
  test(path.name+'/native-vectors',saved['pdf']['image_XObjects'],0)
 # Whole-color transfer study and the native illustrations of its predictions.
 data=json.loads((ROOT/'docs/research/COLOR-LAW-DATA.json').read_text())
 law=json.loads((ROOT/'docs/research/COLOR-LAW-RESULTS.json').read_text())
 test('color law/data',law['data_sha256'],hashlib.sha256((ROOT/'docs/research/COLOR-LAW-DATA.json').read_bytes()).hexdigest())
 test('color law/analysis',law['analysis_sha256'],hashlib.sha256((ROOT/'tools/analyze_color_law.py').read_bytes()).hexdigest())
 archive=json.loads((ROOT/'docs/research/COLOR-LAW-SOURCE-ARCHIVE.json').read_text())['sources']
 for path,expected in data['sources'].items():
  snapshot=archive.get(path)
  if snapshot:test('color law/archive declared hash '+path,snapshot['sha256'],expected)
  source=ROOT/(snapshot['archive'] if snapshot else path)
  test('color law/source '+path,hashlib.sha256(source.read_bytes()).hexdigest(),expected)
 test('color law/protocol',law['protocol_sha256'],hashlib.sha256((ROOT/'docs/research/COLOR-LAW-PROTOCOL.json').read_bytes()).hexdigest())
 test('color law/unique colors',len(data['colors']),10)
 test('color law/candidate relations',len(law['equations']),63)
 labels=sorted(r['label']for r in data['colors'])
 for row in law['equations']:
  name='color law/'+row['source']+'/'+row['target']+'/'+row['model']['model']
  test(name+'/fold inventory',sorted(f['color']for f in row['folds']),labels)
  test(name+'/transfer inventory',len(row['transfer_rows']),12)
 test('color law/sensitivity cases',len(law['primary_sensitivity']),162)
 test('color law/Dark Tan identity',next(r['ldraw_code']for r in data['colors']if r['label']=='dark tan'),28)
 colors=json.loads((ROOT/'docs/gallery/color-law-renders.json').read_text())
 test('color render/version',colors['version'],evidence_version)
 test('color render/recipe',colors['recipe_sha256'],hashlib.sha256((ROOT/'tools/render_color_law.py').read_bytes()).hexdigest())
 test('color render/numeric inputs',colors['data_sha256'],hashlib.sha256((ROOT/'docs/research/COLOR-LAW-RESULTS.json').read_bytes()).hexdigest())
 test('color render/inventory',len(colors['records']),12)
 for row in colors['records']:
  path=ROOT/'docs/gallery'/(row['id']+'.json');saved=json.loads(path.read_text())
  test(row['id']+'/receipt',hashlib.sha256(path.read_bytes()).hexdigest(),row['receipt_sha256'])
  test(row['id']+'/version',saved['version'],evidence_version)
  test(row['id']+'/package',saved['execution']['package_source_sha256'],evidence_package_sha)
  test(row['id']+'/camera',saved['camera'],row['camera'])
  test(row['id']+'/model',saved['model_sha256'],row['model_sha256'])
  test(row['id']+'/native',saved['pdf']['image_XObjects'],0)
  observed=next(c['source']['faces']for c in data['colors']if c['ldraw_code']==row['code'])
  for target in ('left','top','right'):
   expected=observed[target]
   if row['mode']=='ldraw-law' or row['mode']=='face-law' and target!='left':
    source='ldraw'if row['mode']=='ldraw-law'else'left'
    equation=next(e for e in law['equations']if e['source']==source and e['target']==target and e['model']['model']=='gain')
    expected=next(f['predicted_RGB']for f in equation['folds']if f['color']==row['label'])
   test(row['id']+'/'+target+' prediction',row['face_RGB'][target],expected)
 for code in {r['code']for r in colors['records']}:
  group=[r for r in colors['records']if r['code']==code]
  test('color render/'+str(code)+'/same camera',all(r['camera']==group[0]['camera']for r in group),True)
  test('color render/'+str(code)+'/same geometry',len({r['model_sha256']for r in group}),1)
 previews=json.loads((ROOT/'docs/gallery/color-law-previews.json').read_text())
 test('color board/hash',previews['board_sha256'],hashlib.sha256((ROOT/'docs/images/color-law-own.png').read_bytes()).hexdigest())
 test('color board/recipe',previews['recipe_sha256'],hashlib.sha256((ROOT/'tools/compose_color_law.py').read_bytes()).hexdigest())
 from check_new_color_holdout import check as check_holdout
 holdout=check_holdout()
 test('frozen new-color numeric replay',holdout['status'],'PASS')
 from check_palette_holdout import check as check_palette_holdout
 palette_holdout=check_palette_holdout()
 test('four-color frozen numeric replay',palette_holdout['status'],'PASS')
 test('four-color nominal RGB gate fails',palette_holdout['nominal_gate'],False)
 for face in ('top','right'):test('four-color measured-left '+face,palette_holdout['face_law_gates'][face]['all81_pass'],True)
 new_examples=json.loads((ROOT/'docs/gallery/palette-holdout-renders.json').read_text())
 test('palette example count',len(new_examples['records']),8)
 test('palette example recipe',new_examples['recipe_sha256'],hashlib.sha256((ROOT/'tools/render_palette_holdouts.py').read_bytes()).hexdigest())
 test('palette example data',new_examples['data_sha256'],hashlib.sha256((ROOT/'docs/research/PALETTE-HOLDOUT-2025.json').read_bytes()).hexdigest())
 for row in new_examples['records']:
  saved_path=ROOT/'docs/gallery'/(row['id']+'.json');saved=json.loads(saved_path.read_text())
  test(row['id']+'/receipt',hashlib.sha256(saved_path.read_bytes()).hexdigest(),row['receipt_sha256'])
  test(row['id']+'/camera',saved['camera'],row['camera'])
  test(row['id']+'/model',saved['model_sha256'],row['model_sha256'])
  test(row['id']+'/native',saved['pdf']['image_XObjects'],0)
  test(row['id']+'/package',saved['execution']['package_source_sha256'],vector_reference)
 for code in {r['code']for r in new_examples['records']}:
  pair=[r for r in new_examples['records']if r['code']==code]
  test('palette paired cameras '+str(code),pair[0]['camera'],pair[1]['camera'])
  test('palette paired model '+str(code),pair[0]['model_sha256'],pair[1]['model_sha256'])
 test('new-color primary material count',len(holdout['geometry_gate']),2)
 edge_study=json.loads((ROOT/'docs/research/CAMERA-EDGE-STUDY.json').read_text())
 test('edge study unique assets',len({s['decoded_rgb_sha256']for s in edge_study['sources']}),7)
 test('edge study runtime',edge_study['summary']['renderer_version'],evidence_version)
 test('edge study working-view limitation','not an established exact universal' in edge_study['summary']['conclusion'],True)
 for row in edge_study['native_camera_replay']:
  path=ROOT/'docs/gallery'/('camera-edge-'+row['key']+'.json');saved=json.loads(path.read_text())
  test(path.name+'/receipt',hashlib.sha256(path.read_bytes()).hexdigest(),row['receipt_sha256'])
  test(path.name+'/version',saved['version'],evidence_version)
  test(path.name+'/runtime',saved['execution']['package_source_sha256'],evidence_package_sha)
  test(path.name+'/model',saved['model_sha256'],row['model_sha256'])
  test(path.name+'/native',saved['pdf']['image_XObjects'],0)
  test(path.name+'/replay error',row['camera_replay_max_error_px']<1e-8,True)
 control=json.loads((ROOT/'docs/gallery/camera-resolution-known.json').read_text())
 test('resolution known camera/version',control['version'],evidence_version)
 test('resolution known camera/runtime',control['execution']['package_source_sha256'],evidence_package_sha)
 for field in ('azimuth','elevation'):test('resolution known camera/'+field,control['camera'][field],35)
 test('resolution known camera/native',control['pdf']['image_XObjects'],0)
 from analyze_sloped_faces import analyze as analyze_slopes
 slopes=analyze_slopes(ROOT)
 test('slope arithmetic replay',slopes['status'],'PASS')
 test('slope unique decoded images',slopes['stats']['unique_pixels'],44)
 test('slope fresh dark-anchor source controls',slopes['stats']['final_dark_anchor_scores']['all_shifts_pass'],5)
 test('slope probe not promoted',json.loads((ROOT/'docs/research/SLOPED-FACE-STUDY.json').read_text())['native_probe']['default_runtime_changed'],False)
 test('default interpolation declared','convex' in load_style().research['interpolation_status'],True)
 from analyze_angular_shading import analyze as analyze_angular
 angular=analyze_angular(ROOT)
 test('angular arithmetic replay',angular['status'],'PASS')
 test('angular unique images',angular['counts']['unique_pixel_images'],39)
 test('angular known palette images',angular['counts']['known_palette_unique'],38)
 test('angular steep baseline passes',angular['scores']['steep']['baseline']['all_shifts_pass'],6)
 test('angular steep linear passes',angular['scores']['steep']['piecewise_angle']['all_shifts_pass'],4)
 test('angular shallow baseline passes',angular['scores']['shallow']['baseline']['all_shifts_pass'],26)
 test('angular shallow linear passes',angular['scores']['shallow']['piecewise_angle']['all_shifts_pass'],23)
 test('angular low linear passes',angular['scores']['low']['piecewise_angle']['all_shifts_pass'],1)
 from analyze_angular_material import analyze as analyze_material
 material=analyze_material(ROOT)
 test('opt-in angular runtime replay',material['status'],'PASS')
 test('opt-in angular prospective white shape',material['scores']['angular-model-holdout']['candidate']['pass'],4)
 test('opt-in angular prospective low shape',material['scores']['low-slope-geometry-holdout']['candidate']['pass'],4)
 angular_examples=json.loads((ROOT/'docs/gallery/angular-examples.json').read_text())
 test('angular examples version',angular_examples['version'],evidence_version)
 test('angular examples recipe',angular_examples['recipe_sha256'],hashlib.sha256((ROOT/'tools/render_angular_material_examples.py').read_bytes()).hexdigest())
 for row in angular_examples['rows']:
  pair=[]
  for mode,entry in row['renders'].items():
   path=ROOT/'docs/gallery'/('angular-'+row['id']+'-'+mode+'.json');saved=json.loads(path.read_text());pair.append(saved)
   test(path.name+'/receipt',hashlib.sha256(path.read_bytes()).hexdigest(),entry['receipt_sha256'])
   test(path.name+'/version',saved['version'],evidence_version)
   test(path.name+'/package',saved['execution']['package_source_sha256'],evidence_package_sha)
   test(path.name+'/profile',saved['materials']['profile'],mode)
   test(path.name+'/vector',saved['pdf']['image_XObjects'],0)
  for field in ('camera','model_sha256','line_width_points','points_per_ldu'):
   test(row['id']+'/same '+field,pair[0][field],pair[1][field])
 test('angular example preview',angular_examples['preview_sha256'],hashlib.sha256((ROOT/'docs/images/angular-material-pairs.png').read_bytes()).hexdigest())
 camera_examples=json.loads((ROOT/'docs/gallery/camera-presets.json').read_text())
 test('camera recipe/version',camera_examples['version'],__version__)
 test('camera recipe/generator',camera_examples['recipe_sha256'],hashlib.sha256((ROOT/'tools/render_camera_presets.py').read_bytes()).hexdigest())
 for row in camera_examples['renders']:
  path=ROOT/'docs/gallery'/('preset-camera-'+row['id']+'.json');saved=json.loads(path.read_text())
  test(path.name+'/receipt',hashlib.sha256(path.read_bytes()).hexdigest(),row['receipt_sha256'])
  test(path.name+'/version',saved['version'],__version__)
  test(path.name+'/source-package',saved['execution']['package_source_sha256'],vector_reference)
  test(path.name+'/camera',saved['camera'],row['camera'])
  if row['id'] in ('plate-orthographic','plate-instruction','plate-presentation'):
   plate=ROOT/'docs/images'/(row['id']+'.svg')
   test(plate.name+'/native gallery artwork',hashlib.sha256(plate.read_bytes()).hexdigest(),saved['pdf']['SVG_sha256'])
  test(path.name+'/vector',saved['pdf']['image_XObjects'],0)
  settings,_=resolve_camera(saved['camera']['preset']['name'])
  for k in ('azimuth','elevation','projection'):test(path.name+'/'+k,saved['camera'][k],settings[k])
  if settings['projection']=='perspective':test(path.name+'/FOV',saved['camera']['field_of_view_vertical_degrees'],settings['field_of_view'])
 coverage=json.loads((ROOT/'docs/portfolio/surface-coverage.json').read_text())
 test('gallery coverage renderer',coverage['renderer_source_sha256'],vector_reference)
 for model in json.loads((ROOT/'docs/portfolio/sources.json').read_text())['models']:
  name=model['id']
  rows=[row for row in coverage['measurements'] if row['group']=='gallery' and row['model']==name]
  test('gallery coverage sizes and formats/'+name,
       sorted((row['format'],row['width']) for row in rows),
       [(fmt,w) for fmt in ('pdf','svg') for w in (250,500,1000)])
  for row in rows:
   if row['format']=='svg':test('gallery vector/'+name+'/'+str(row['width']),row['underpaint']['sha256'],model['svg_sha256'])
   test('gallery interior/'+name+'/'+row['format']+'/'+str(row['width']),
        row['underpaint']['leaks_24']<row['plain']['leaks_24'] and row['underpaint']['interior_MAE']<row['plain']['interior_MAE'],True)
 boat=next(r for r in coverage['measurements'] if r['model']=='harbor-pilot' and r['format']=='svg')
 test('paired plain hull',hashlib.sha256((ROOT/'docs/images/harbor-pilot-standard.svg').read_bytes()).hexdigest(),boat['plain']['sha256'])
 # The RGB-only conversion experiment is kept separate from the measured
 # runtime palette. Current native examples carry the actual generating code.
 transfer_data=ROOT/'docs/research/LDRAW-TRANSFER-DATA.json'
 transfer_results=ROOT/'docs/research/LDRAW-TRANSFER-RESULTS.json'
 transfer=json.loads(transfer_results.read_text())
 transfer_input=json.loads(transfer_data.read_text())
 test('RGB transfer/data',transfer['data_sha256'],hashlib.sha256(transfer_data.read_bytes()).hexdigest())
 test('RGB transfer/analysis',transfer['analysis_sha256'],hashlib.sha256((ROOT/'tools/analyze_ldraw_transfer.py').read_bytes()).hexdigest())
 test('RGB transfer/colors',len(transfer_input['colors']),13)
 test('RGB transfer/candidates',len(transfer['candidates']),54)
 for i,fold in enumerate(transfer['folds']):
  test('RGB transfer/whole color excluded '+str(i),fold['training_indices'],[j for j in range(13)if j!=i])
  test('RGB transfer/color identity '+str(i),fold['color_code'],transfer_input['colors'][i]['code'])
  scalar=sum(abs(a-b)for pa,ob in zip(fold['prediction'],fold['observed'])for a,b in zip(pa,ob))/9
  test('RGB transfer/MAE '+str(i),abs(scalar-fold['MAE'])<1e-10,True)
 transfer_renders=json.loads((ROOT/'docs/gallery/ldraw-transfer-renders.json').read_text())
 test('RGB transfer/render recipe',transfer_renders['recipe_sha256'],hashlib.sha256((ROOT/'tools/render_ldraw_transfer.py').read_bytes()).hexdigest())
 test('RGB transfer/render input',transfer_renders['results_sha256'],hashlib.sha256(transfer_results.read_bytes()).hexdigest())
 for row,fold in zip(transfer_renders['records'],transfer['folds']):
  path=ROOT/'docs/gallery'/(row['id']+'.json');saved=json.loads(path.read_text())
  test(row['id']+'/receipt',hashlib.sha256(path.read_bytes()).hexdigest(),row['receipt_sha256'])
  test(row['id']+'/version',saved['version'],__version__)
  test(row['id']+'/source',saved['execution']['package_source_sha256'],vector_reference)
  test(row['id']+'/native',saved['pdf']['image_XObjects'],0)
  test(row['id']+'/prediction',row['prediction'],fold['prediction'])
  test(row['id']+'/camera',saved['camera']['preset']['name'],'instruction')
 preprint=(ROOT/'docs/RESEARCH-PREPRINT.md').read_text()
 test('preprint version text','preprint '+contract['preprint_version'] in preprint,True)
 test('preprint renderer version',contract['renderer_version'] in preprint,True)
 from build_research_brief import consistency as brief_consistency
 test('one-page brief matches reviewed research and generated text',brief_consistency(),[])
 return {'status':'PASS' if all(c['pass']for c in checks) else 'FAIL','checks':len(checks),'failed':[c['check']for c in checks if not c['pass']],'limits':contract['unresolved']}

if __name__=='__main__':
 result=check();print(json.dumps(result,indent=2));raise SystemExit(result['status']!='PASS')
