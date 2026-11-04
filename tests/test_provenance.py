"""Receipts identify the palette bytes consumed, as well as DAT geometry."""
from pathlib import Path
import hashlib
import json
import shutil
import tempfile
import unittest
import zipfile
from brick_blueprint.ldraw import Library
from brick_blueprint.project import project
from brick_blueprint.pipeline import render
from brick_blueprint.tray import render_tray

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT/'examples/library'
MODEL = ROOT/'examples/demo.ldr'


class ProvenanceTests(unittest.TestCase):
    def test_directory_and_prefixed_zip_record_same_consumed_palette(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            library = base/'library'
            shutil.copytree(LIB, library)
            path = library/'LDConfig.ldr'
            data = path.read_bytes()+b'0 Author: Test Fixture\n0 !LICENSE Test-only notice\n'
            path.write_bytes(data)
            archive = base/'library.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                for item in library.rglob('*'):
                    if item.is_file():
                        z.write(item, 'ldraw/'+item.relative_to(library).as_posix())
            for source, name in [(library, 'LDConfig.ldr'), (archive, 'ldraw/LDConfig.ldr')]:
                with self.subTest(source=source), Library(source) as lib:
                    self.assertEqual(lib.config_receipt['file'], name)
                    self.assertEqual(lib.config_receipt['sha256'], hashlib.sha256(data).hexdigest())
                    self.assertEqual(lib.config_receipt['authors'], ['Author: Test Fixture'])
                    self.assertEqual(lib.config_receipt['licenses'], ['Test-only notice'])
                    # The receipt describes the snapshot already parsed, not a later reread.
                    if source == library:
                        path.write_bytes(b'changed after constructor')
                        self.assertEqual(lib.config_receipt['sha256'], hashlib.sha256(data).hexdigest())
                        path.write_bytes(data)

    def test_palette_only_change_is_visible_with_unchanged_dat_dependencies(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            library = base/'library'
            shutil.copytree(LIB, library)
            first = project(MODEL, library, base/'before.scene')
            config = library/'LDConfig.ldr'
            config.write_bytes(config.read_bytes().replace(b'ALPHA 128', b'ALPHA 64'))
            second = project(MODEL, library, base/'after.scene')
            self.assertEqual(first['dependencies'], second['dependencies'])
            self.assertEqual(first['model_sha256'], second['model_sha256'])
            self.assertNotEqual(first['scene_sha256'], second['scene_sha256'])
            self.assertNotEqual(first['library_config']['sha256'], second['library_config']['sha256'])
            self.assertEqual(second['library_config']['sha256'], hashlib.sha256(config.read_bytes()).hexdigest())

    def test_pipeline_and_tray_persist_palette_provenance_without_input_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            expected = hashlib.sha256((LIB/'LDConfig.ldr').read_bytes()).hexdigest()
            one = render(MODEL, LIB, base/'one', cache_dir=ROOT/'.brickblueprint-cache')
            self.assertEqual(one['library_config']['sha256'], expected)
            self.assertEqual(json.loads((base/'one/render.json').read_text())['library_config'], one['library_config'])
            model = base/'item.ldr'
            model.write_text('1 4 0 0 0 10 0 0 0 10 0 0 0 10 unit-box.dat\n')
            manifest = base/'tray.json'
            manifest.write_text(json.dumps({'items': [{'model': 'item.ldr'}]}))
            tray = render_tray(manifest, LIB, base/'tray', cache_dir=ROOT/'.brickblueprint-cache')
            self.assertEqual(tray['items'][0]['library_config']['sha256'], expected)
            self.assertNotIn(str(LIB), (base/'tray/render.json').read_text())


if __name__ == '__main__':
    unittest.main()
