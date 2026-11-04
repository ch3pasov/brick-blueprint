"""Offline installed-wheel smoke check; never installs into the user environment."""
from pathlib import Path
import argparse
import base64
import csv
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile


def check(wheel, fixtures):
    wheel=Path(wheel).resolve();fixtures=Path(fixtures).resolve()
    with zipfile.ZipFile(wheel) as z:
        names=z.namelist()
        if len(names)!=len(set(names)):
            raise ValueError('Duplicate wheel entry')
        if any(n.startswith('/') or '..' in Path(n).parts or '\\' in n for n in names):
            raise ValueError('Unsafe wheel entry')
        if any(n.endswith(('.pyc','.pyo','.bin','.pdf','.png','.ttf','.otf','.icc')) for n in names):
            raise ValueError('Unexpected binary or research asset in wheel')
        records=[name for name in names if name.endswith('.dist-info/RECORD')]
        if len(records)!=1:
            raise ValueError('Expected one wheel RECORD')
        record=records[0];rows=list(csv.reader(io.StringIO(z.read(record).decode())))
        if {row[0] for row in rows}!=set(names) or len(rows)!=len(names):
            raise ValueError('Wheel RECORD inventory differs')
        for name,digest,size in rows:
            if name==record:
                if digest or size:raise ValueError('RECORD must leave its own hash/size empty')
                continue
            data=z.read(name)
            actual=base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip('=')
            if digest!='sha256='+actual or int(size)!=len(data):
                raise ValueError('Wheel RECORD hash or size differs')
        root='brick_blueprint/'
        vendor=root+'native/vendor/Clipper2/'
        provenance=json.loads(z.read(vendor+'PROVENANCE.json'))
        for name,expected in provenance['files'].items():
            if hashlib.sha256(z.read(vendor+name)).hexdigest()!=expected:
                raise ValueError('Pinned vendor payload differs')
        required={root+'native/vector_render.cpp',root+'native/union_q3_tiled.cpp',root+'native/opaque_underpaint.cpp',
                  root+'default-style.json',root+'presets.json',
                  root+'angular_style.py',root+'angular-material.json'}
        if required-set(names):
            raise ValueError('Missing runtime source/data')
        expected_presets=set(json.loads(z.read(root+'presets.json'))['presets'])
        source_rows=[(name[len(root):],hashlib.sha256(z.read(name)).hexdigest())
                     for name in sorted(names) if name.startswith(root)
                     and (Path(name).suffix in {'.py','.json','.cpp','.h'} or Path(name).name=='LICENSE')]
        package_source_sha256=hashlib.sha256(json.dumps(source_rows,separators=(',',':')).encode()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='brick-blueprint-wheel-') as temporary:
        temp=Path(temporary);installed=temp/'installed';data=temp/'fixtures'
        shutil.copytree(fixtures,data)
        completed=subprocess.run([sys.executable,'-m','pip','--no-cache-dir','install',
            '--no-index','--no-deps','--target',str(installed),str(wheel)],
            capture_output=True,text=True)
        if completed.returncode:
            raise RuntimeError('Offline wheel installation failed:\n'+completed.stderr)
        runner='''import sys,runpy
sys.path.insert(0,sys.argv.pop(1))
import brick_blueprint
assert brick_blueprint.__file__.startswith(sys.path[0])
sys.argv[0]='brick-blueprint'
runpy.run_module('brick_blueprint',run_name='__main__')
'''
        def cli(*args):
            done=subprocess.run([sys.executable,'-I','-S','-c',runner,str(installed),*map(str,args)],
                cwd=temp,capture_output=True,text=True)
            if done.returncode:
                raise RuntimeError('Installed CLI failed:\n'+done.stderr)
            return done.stdout
        version=cli('--version').strip()
        if set(json.loads(cli('presets')))!=expected_presets:
            raise ValueError('Installed preset inventory differs from wheel')
        diagnosis=json.loads(cli('doctor','--library',data/'library','--model',data/'demo.ldr'))
        if not diagnosis['ready']:
            raise ValueError('Installed readiness check failed')
        output=temp/'render'
        cli('render',data/'demo.ldr','--library',data/'library','--output',output,
            '--cache-dir',temp/'native-cache','--width','300','--height','240')
        report=json.loads((output/'render.json').read_text())
        if report['pdf']['image_XObjects']!=0 or report['parts']!=13:
            raise ValueError('Unexpected synthetic render output')
        if report['library_config']['sha256']!=hashlib.sha256((data/'library/LDConfig.ldr').read_bytes()).hexdigest():
            raise ValueError('Installed palette provenance differs')
        if report['execution']['package_source_sha256']!=package_source_sha256:
            raise ValueError('Installed runtime fingerprint differs from wheel payload')
        angular=temp/'angular'
        cli('render',data/'demo.ldr','--library',data/'library','--output',angular,
            '--cache-dir',temp/'native-cache','--width','300','--height','240',
            '--material-profile','research-angular')
        angular_report=json.loads((angular/'render.json').read_text())
        if angular_report['materials']['profile']!='research-angular':
            raise ValueError('Installed angular profile not selected')
        for key in ('camera','model_sha256','dependencies','parts','triangles'):
            if angular_report[key]!=report[key]:
                raise ValueError('Angular profile unexpectedly changed geometry or camera')
        if angular_report['pdf']['image_XObjects']!=0:
            raise ValueError('Installed angular output contains raster artwork')
        if not angular_report['materials'].get('angular_data_sha256'):
            raise ValueError('Installed angular evidence binding missing')
        cameras=json.loads(cli('camera-presets'))
        if set(cameras)!={'instruction','instruction-depth','presentation','orthographic'}:
            raise ValueError('Installed camera preset inventory differs')
        instruction=temp/'instruction'
        cli('render',data/'demo.ldr','--library',data/'library','--output',instruction,
            '--cache-dir',temp/'native-cache','--width','300','--height','240',
            '--camera-preset','instruction')
        ir=json.loads((instruction/'render.json').read_text())
        if ir['camera']['field_of_view_vertical_degrees']!=2 or ir['camera']['preset']['name']!='instruction':
            raise ValueError('Installed camera preset was not applied')
        if ir['pdf']['image_XObjects']!=0 or ir['model_sha256']!=report['model_sha256']:
            raise ValueError('Installed camera preset changed geometry or vector output type')
        underpaint = temp/'underpaint'
        cli('render',data/'demo.ldr','--library',data/'library','--output',underpaint,
            '--cache-dir',temp/'native-cache','--width','300','--height','240',
            '--camera-preset','instruction','--underpaint')
        painted = json.loads((underpaint/'render.json').read_text())
        if (painted['underpaint']['placement_masks'] < 1 or painted['camera'] != ir['camera']
                or painted['scene_sha256'] != ir['scene_sha256'] or painted['pdf']['image_XObjects'] != 0):
            raise ValueError('Installed underpaint control changed the scene or produced no vector masks')
        gray=temp/'gray'
        cli('print',output/'model.svg','--mode','gray','--output',gray)
        pdf=(gray/'print.pdf').read_bytes()
        if b'/DeviceGray' not in pdf or b'/Subtype /Image' in pdf:
            raise ValueError('Installed grayscale output is not vector DeviceGray')
        return {'status':'PASS','wheel_sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),
                'version':version,'wheel_entries':len(names),'vendor_files_verified':len(provenance['files']),
                'wheel_RECORD_entries_verified':len(rows),
                'presets':len(expected_presets),'synthetic_parts':report['parts'],
                'native_compilation_from_installed_sources':True,'site_packages_disabled_for_cli':True,
                'external_library_required':False,'network_used':False,
                'doctor_preflight':'PASS','package_source_sha256':package_source_sha256,
                'installed_package_fingerprint_matches_wheel':True,
                'vector_render':report['pdf'],'grayscale_export':'PASS',
                'angular_profile_installed_vector_check':'PASS',
                'camera_presets_installed_vector_check':'PASS',
                'underpaint_installed_vector_check':'PASS',
                'angular_geometry_and_camera_equal':True}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('wheel',type=Path)
    parser.add_argument('--fixtures',type=Path,default=Path(__file__).resolve().parents[1]/'examples')
    args=parser.parse_args(argv)
    try:
        report=check(args.wheel,args.fixtures)
    except (ValueError,OSError,KeyError,RuntimeError,zipfile.BadZipFile) as error:
        parser.exit(1,'Wheel check failed: '+str(error)+'\n')
    print(json.dumps(report,indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
