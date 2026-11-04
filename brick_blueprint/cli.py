"""Command-line interface; no downloads, uploads, or GUI automation."""
import argparse
import json
from pathlib import Path
import subprocess
import zipfile
from . import __version__
from .pipeline import render
from .presets import all_presets
from .camera_presets import all_camera_presets
from .tray import render_tray
from .print_export import export_print
from .doctor import diagnose
from .style import MATERIAL_PROFILES

def rgb(text):
    text=text.lstrip('#')
    if len(text)!=6:raise argparse.ArgumentTypeError('Use a six-digit RGB hex color')
    try:return tuple(int(text[i:i+2],16) for i in (0,2,4))
    except ValueError:raise argparse.ArgumentTypeError('Use a six-digit RGB hex color')

def xyz(text):
    try:
        value=tuple(float(v) for v in text.split(','))
        if len(value)!=3:raise ValueError()
        return value
    except ValueError:raise argparse.ArgumentTypeError('Use three comma-separated LDraw coordinates')

def camera_options(parser, explicit=False):
    parser.add_argument('--camera-preset',choices=list(all_camera_presets()),help='Camera recipe, independent of --preset paper style; instruction is recommended for parts')
    parser.add_argument('--projection',choices=['perspective','orthographic'])
    parser.add_argument('--field-of-view',type=float,help='Vertical full-page FOV in degrees; perspective default 30')
    parser.add_argument('--near-clip',type=float,help='Minimum distance from eye in LDU; default 0.1; crossing geometry is rejected')
    if explicit:
        parser.add_argument('--camera-distance',type=float,help='Eye-to-target distance in LDU; excludes --scale; default fits page')
        parser.add_argument('--camera-target',type=xyz,help='Look-at point x,y,z in LDraw coordinates; default geometry centre')
        parser.add_argument('--camera-roll',type=float,help='Camera roll in degrees, -180..180; perspective render only')
        parser.add_argument('--principal-point',type=xy,help='Optical centre x,y in page points; requires explicit camera distance; may lie outside a cropped image')

def xy(text):
    try:
        value=tuple(float(v) for v in text.split(','))
        if len(value)!=2:raise ValueError()
        return value
    except ValueError:raise argparse.ArgumentTypeError('Use two comma-separated page coordinates')

def material_options(parser):
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--material-profile',choices=MATERIAL_PROFILES,
                       help='Opaque colors: research (default, eleven measured colors), research-angular (experimental slopes), or legacy')
    group.add_argument('--style',dest='style_path',type=Path,help='Custom complete style JSON, replacing the built-in material profile')

def main(argv=None):
    parser=argparse.ArgumentParser(description='Render an LDraw or assembly-only MPD model into compact, native-vector SVG and PDF.')
    parser.add_argument('--version',action='version',version=__version__)
    commands=parser.add_subparsers(dest='command',required=True)
    commands.add_parser('presets',help='List evidence-linked presentation presets')
    commands.add_parser('camera-presets',help='List built-in camera recipes and their evidence')
    doctor=commands.add_parser('doctor',help='Check Python, compiler and optional library/model; no downloads')
    doctor.add_argument('--library',type=Path)
    doctor.add_argument('--model',type=Path,help='Preflight an assembly using the supplied library')
    doctor.add_argument('--compile',dest='compile_native',action='store_true',help='Also compile bundled native tools into the cache')
    doctor.add_argument('--cache-dir',type=Path,default=Path('.brickblueprint-cache'))
    command=commands.add_parser('render',help='Render into a new output directory')
    command.add_argument('model',type=Path)
    command.add_argument('--preset',choices=list(all_presets()))
    command.add_argument('--layout',choices=['illustration','callout'],default='illustration')
    command.add_argument('--quantity',type=int,default=1)
    command.add_argument('--panel-role',choices=['parts','subassembly'])
    command.add_argument('--library',required=True,type=Path,help='LDraw directory or ZIP (not bundled)')
    command.add_argument('--output',required=True,type=Path)
    command.add_argument('--width',type=int,default=600,help='Page width in points (64..1000)')
    command.add_argument('--height',type=int,default=450,help='Page height in points (64..1000)')
    command.add_argument('--azimuth',type=float)
    command.add_argument('--elevation',type=float)
    command.add_argument('--line-width',type=float,help='Outline width in points')
    command.add_argument('--glass-opacity',type=float,help='Optional opacity for all transparent faces (0..1], except opaque stud walls')
    command.add_argument('--background',type=rgb,help='RGB hex, e.g. D4EDFC')
    command.add_argument('--scale',type=float,help='Points/LDU at target plane (uniform in orthographic); default fits page')
    camera_options(command,explicit=True)
    material_options(command)
    command.add_argument('--no-detail-filter',dest='detail_filter',action='store_false')
    command.add_argument('--cache-dir',type=Path,default=Path('.brickblueprint-cache'))
    command.add_argument('--timeout',type=int,default=300,help='Timeout per native rendering stage in seconds')
    tray=commands.add_parser('tray',help='Render a JSON parts list at one shared physical scale')
    tray.add_argument('manifest',type=Path)
    tray.add_argument('--library',required=True,type=Path)
    tray.add_argument('--output',required=True,type=Path)
    tray.add_argument('--preset',choices=list(all_presets()),default='modern-blue')
    tray.add_argument('--columns',type=int,default=3)
    tray.add_argument('--gap',type=float,default=18)
    tray.add_argument('--width',type=int,default=600)
    tray.add_argument('--height',type=int,default=450)
    tray.add_argument('--scale',type=float,help='Shared target-plane points/LDU; uniform in orthographic')
    camera_options(tray)
    material_options(tray)
    for parser_command in (command, tray):
        parser_command.add_argument('--png',action='store_true',help='Also write model.png (144 DPI by default)')
        parser_command.add_argument('--png-dpi',type=int,help='Write model.png at this resolution (1..600 DPI)')
        parser_command.add_argument('--underpaint',action='store_true',
                             help='Add opaque base paint to reduce fine seams in vector viewers')
    tray.add_argument('--line-width',type=float,default=.32)
    tray.add_argument('--azimuth',type=float)
    tray.add_argument('--elevation',type=float)
    tray.add_argument('--glass-opacity',type=float)
    tray.add_argument('--cache-dir',type=Path,default=Path('.brickblueprint-cache'))
    tray.add_argument('--timeout',type=int,default=300)
    printing=commands.add_parser('print',help='Export an existing renderer SVG as RGB, grayscale or ICC CMYK PDF')
    printing.add_argument('source',type=Path,help='model.svg produced by this tool')
    printing.add_argument('--output',required=True,type=Path)
    printing.add_argument('--mode',required=True,choices=['rgb','gray','cmyk'])
    printing.add_argument('--profile',type=Path,help='CMYK output ICC profile; required for CMYK')
    printing.add_argument('--intent',choices=['relative','perceptual','saturation','absolute'],default='relative')
    args=vars(parser.parse_args(argv))
    action=args.pop('command')
    if action=='presets':
        print(json.dumps(all_presets(),indent=2));return 0
    if action=='camera-presets':
        print(json.dumps(all_camera_presets(),indent=2));return 0
    args={k:v for k,v in args.items() if v is not None}
    if args.pop('png',False):
        args.setdefault('png_dpi',144)
    try:
        report=({'tray':render_tray,'render':render,'print':export_print,'doctor':diagnose}[action])(**args)
    except (ValueError,OSError,RuntimeError,subprocess.SubprocessError,RecursionError,zipfile.BadZipFile) as error:
        parser.exit(1,('Check failed: ' if action=='doctor' else 'Render failed: ')+str(error)+'\n')
    if action=='doctor':
        print(json.dumps(report,indent=2));return 0 if report['ready'] else 1
    if action=='print':
        print(json.dumps({'output':str(args['output']),'mode':report['pdf']['color_export']['mode'],'page_mm':report['page_mm'],'PDF_bytes':report['pdf']['PDF_bytes'],'raster_images':0},indent=2));return 0
    if action=='tray':
        print(json.dumps({'output':str(args['output']),'items':report['item_count'],
                          'rendered_parts':report['rendered_parts'],
                          'represented_parts':report['represented_parts'],
                          **({'png':report['png']} if 'png' in report else {}),
                          'PDF_bytes':report['pdf']['PDF_bytes'],'raster_images':0},indent=2));return 0
    print(json.dumps({'output':str(args['output']),'parts':report.get('parts',sum(i['parts'] for i in report.get('items',[]))),'triangles':report.get('triangles'),
                      **({'png':report['png']} if 'png' in report else {}),
                      'PDF_bytes':report['pdf']['PDF_bytes'],'raster_images':0},indent=2))
    return 0
