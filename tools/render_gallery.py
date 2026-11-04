"""Reproduce showcase vectors using a separately supplied LDraw library."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from brick_blueprint.pipeline import render
from brick_blueprint.presets import all_presets
from brick_blueprint.tray import render_tray
from brick_blueprint import __version__

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--group',choices=['all','presets','assemblies'],default='all',
                        help='Limit a reproduction to the current preset facade or assembly examples')
    parser.add_argument('--appearance',choices=['legacy','current'],default='legacy',
                        help='Preserved orthographic/legacy recipes, or the current perspective/research renderer')
    args=parser.parse_args()
    if args.output.exists():parser.error('Choose a new output directory to preserve previous renders')
    args.output.mkdir(parents=True)
    common={'projection':'orthographic','material_profile':'legacy','library':args.library,'cache_dir':ROOT/'.brickblueprint-cache','azimuth':35,'elevation':30}
    if args.appearance=='current':common.update(projection='perspective',material_profile='research',elevation=35)
    if args.group in ('all','assemblies'):
        render(ROOT/'examples/lighthouse.ldr',output=args.output/'lighthouse',preset='creator-blue',width=850,height=650,line_width=.65,glass_opacity=.85,**common)
        print('lighthouse',flush=True)
    for key,style in (all_presets().items() if args.group in ('all','presets') else []):
        if style['panels']['parts'] is not None:
            manifest=ROOT/'examples/source-steps'/(key+'.json')
            count=len(json.loads(manifest.read_text())['items'])
            render_tray(manifest,output=args.output/key,preset=key,
                        width=360,height=240,columns=min(3,count),gap=12,line_width=.4,
                        **{**common,'elevation':35,**({'field_of_view':2} if args.appearance=='current' else {})})
        else:
            render(ROOT/'examples/source-steps/xwing.ldr',output=args.output/key,preset=key,
                   width=360,height=240,line_width=.4,**{**common,'elevation':35})
        print(key,flush=True)
    for key in (('modern-blue','friends-aqua','fortnite-lilac','botanicals-slate','minecraft-green','display-slate') if args.group in ('all','assemblies') else []):
        render(ROOT/'examples/garden.ldr',output=args.output/(key+'-subassembly'),preset=key,layout='callout',panel_role='subassembly',quantity=2,width=300,height=270,line_width=.55,**common)
        print(key+' subassembly',flush=True)
    (args.output/'gallery-recipe.json').write_text(json.dumps({
        'version':__version__,'appearance':args.appearance,'group':args.group,
        'camera_recipe':{'current_trays':'35/35, FOV2 exploratory weak-perspective recipe; two Classic sources only','current_assemblies':'35/35, FOV30 generic illustration recipe','legacy':'historical orthographic'},
        'recipe_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'renders':{p.parent.name:hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in sorted(args.output.glob('*/render.json'))}},indent=2)+'\n')

if __name__=='__main__':main()
