from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from brick_blueprint.ldraw import Library, parse_model
from brick_blueprint.project import project
from brick_blueprint.pipeline import render

ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'examples/library';MODEL=ROOT/'examples/demo.ldr';CACHE=ROOT/'.brickblueprint-cache'

class InputTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.b=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def model(self,text):
        p=self.b/'test.ldr';p.write_text(text);return p
    def test_empty_rejected(self):
        with self.assertRaisesRegex(ValueError,'Empty'):parse_model(self.model('0 Empty'))
    def test_empty_mpd_rejected(self):
        with self.assertRaisesRegex(ValueError,'MPD'):parse_model(self.model('0 FILE main.ldr'))
    def test_root_geometry_not_silently_dropped(self):
        with self.assertRaisesRegex(ValueError,'type-1'):parse_model(self.model('3 4 0 0 0 1 0 0 1 1 0'))
    def test_invalid_transform(self):
        for value in ['nan','inf','0']:
            with self.assertRaises(ValueError):parse_model(self.model(f'1 4 0 0 0 {value} 0 0 0 1 0 0 0 1 unit-box.dat'))
    def test_traversal_rejected(self):
        with Library(LIB) as lib:
            with self.assertRaisesRegex(ValueError,'Unsafe'):lib.resolve('../secrets.dat')
    def test_missing_part(self):
        with Library(LIB) as lib:
            with self.assertRaisesRegex(ValueError,'Missing'):lib.resolve('does-not-exist.dat')
    def test_directory_and_zip_identical(self):
        archive=self.b/'library.zip'
        with zipfile.ZipFile(archive,'w') as z:
            for p in LIB.rglob('*'):
                if p.is_file():z.write(p,'ldraw/'+p.relative_to(LIB).as_posix())
        a=project(MODEL,LIB,self.b/'a.scene');b=project(MODEL,archive,self.b/'b.scene')
        self.assertEqual(a['scene_sha256'],b['scene_sha256'])
    def test_ambiguous_zip_file_names_are_rejected(self):
        import warnings
        for duplicate in ('ldraw/parts/unit-box.dat','LDRAW/PARTS/UNIT-BOX.DAT'):
            archive=self.b/'ambiguous.zip'
            with zipfile.ZipFile(archive,'w') as z:
                for p in LIB.rglob('*'):
                    if p.is_file():z.write(p,'ldraw/'+p.relative_to(LIB).as_posix())
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore',UserWarning)
                    z.writestr(duplicate,(LIB/'parts/unit-box.dat').read_bytes())
            with self.subTest(duplicate=duplicate),self.assertRaisesRegex(ValueError,'Ambiguous'):
                Library(archive)
    def test_opacity_and_scale_validation(self):
        for opts in [{'glass_opacity':0},{'glass_opacity':1.1},{'width':0},{'scale':9999},{'line_width':float('nan')}]:
            with self.assertRaises(ValueError):project(MODEL,LIB,self.b/'bad.scene',**opts)
    def test_texmap_and_cycles_rejected(self):
        lib=self.b/'lib';shutil.copytree(LIB,lib)
        model=self.model('1 4 0 0 0 1 0 0 0 1 0 0 0 1 problem.dat')
        part=lib/'parts/problem.dat'
        for text,reason in [('0 !TEXMAP START PLANAR','texture'),('1 16 0 0 0 1 0 0 0 1 0 0 0 1 problem.dat','cycle')]:
            part.write_text(text)
            with self.assertRaisesRegex(ValueError,reason):project(model,lib,self.b/'bad.scene')
    def test_step_and_direct_color(self):
        p=self.model('0 STEP\n1 0x2FF0000 0 0 0 1 0 0 0 1 0 0 0 1 unit-box.dat')
        self.assertEqual(parse_model(p)[0]['step'],2)
        receipt=project(p,LIB,self.b/'direct.scene')
        self.assertEqual(receipt['parts'],1)

class PipelineTests(unittest.TestCase):
    def test_depth_transparency_and_ink_regressions(self):
        r=subprocess.run([sys.executable,str(ROOT/'tools/check_vector.py')],check=True,capture_output=True,text=True)
        report=json.loads(r.stdout);self.assertTrue(report['all_passed']);self.assertGreaterEqual(report['cases'],17)
    def test_deterministic_native_vector_export_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            b=Path(tmp)
            a=render(MODEL,LIB,b/'one',cache_dir=CACHE,width=300,height=260)
            render(MODEL,LIB,b/'two',cache_dir=CACHE,width=300,height=260)
            for name in ['model.svg','model.pdf']:self.assertEqual((b/'one'/name).read_bytes(),(b/'two'/name).read_bytes())
            root=ET.parse(b/'one/model.svg').getroot()
            self.assertFalse(any(n.tag.rsplit('}',1)[-1] in ('image','foreignObject') for n in root.iter()))
            self.assertEqual(a['pdf']['image_XObjects'],0)
            self.assertIn('python_version',a['execution'])
            self.assertEqual(len(a['execution']['package_source_sha256']),64)
            self.assertGreater(a['execution']['package_source_files'],30)
            self.assertEqual(set(a['execution']['native_binary_sha256']),{'vector','union'})
            self.assertTrue(all(len(v)==64 for v in a['execution']['native_binary_sha256'].values()))
            self.assertNotIn(str(ROOT),json.dumps(a['execution']))
            self.assertTrue((b/'one/model.pdf').read_bytes().startswith(b'%PDF-1.4'))
            with self.assertRaises(FileExistsError):render(MODEL,LIB,b/'one',cache_dir=CACHE)
    def test_cli_failure_does_not_leave_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'bad'
            r=subprocess.run([sys.executable,'-m','brick_blueprint','render',str(MODEL),'--library',str(LIB),'--output',str(target),'--width','0'],cwd=ROOT,capture_output=True,text=True)
            self.assertNotEqual(r.returncode,0);self.assertFalse(target.exists());self.assertIn('dimensions',r.stderr)
    def test_corrupt_library_zip_has_clear_cli_error_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            b=Path(tmp);bad=b/'bad.zip';bad.write_text('Not a ZIP archive')
            for action,input_file in [('render',MODEL),('tray',b/'tray.json')]:
                if action=='tray':input_file.write_text(json.dumps({'items':[{'model':str(MODEL)}]}))
                target=b/action
                r=subprocess.run([sys.executable,'-m','brick_blueprint',action,str(input_file),
                    '--library',str(bad),'--output',str(target)],cwd=ROOT,capture_output=True,text=True)
                self.assertEqual(r.returncode,1);self.assertIn('Render failed:',r.stderr)
                self.assertNotIn('Traceback',r.stderr);self.assertFalse(target.exists())

if __name__=='__main__':unittest.main()
