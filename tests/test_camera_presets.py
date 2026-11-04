"""Preset precedence, camera execution and shared tray distance."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from brick_blueprint.camera_presets import resolve_camera, all_camera_presets
from brick_blueprint import cli
from brick_blueprint.project import project
from brick_blueprint.tray import render_tray

ROOT = Path(__file__).resolve().parents[1]


class CameraPresetTests(unittest.TestCase):
    def test_list_is_independent_and_documents_selection(self):
        a = all_camera_presets()
        a['instruction']['settings']['field_of_view'] = 77
        self.assertEqual(resolve_camera('instruction')[0]['field_of_view'], 2)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            cli.main(['camera-presets'])
        self.assertIn('evidence', json.loads(out.getvalue())['instruction'])

    def test_precedence_and_invalid_combinations(self):
        settings, receipt = resolve_camera('instruction', elevation=28, field_of_view=4)
        self.assertEqual(settings['elevation'], 28)
        self.assertEqual(settings['field_of_view'], 4)
        self.assertEqual(receipt['overrides'], {'elevation': 28, 'field_of_view': 4})
        self.assertIsNone(resolve_camera('instruction', projection='orthographic')[0]['field_of_view'])
        with self.assertRaises(ValueError):
            resolve_camera('missing')
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, 'require perspective'):
                project(ROOT/'examples/demo.ldr', ROOT/'examples/library', Path(temp)/'s',
                        camera_preset='orthographic', field_of_view=2)

    def test_actual_preset_projection_equals_explicit_camera(self):
        with tempfile.TemporaryDirectory() as temp:
            t = Path(temp)
            for name, preset in all_camera_presets().items():
                with self.subTest(preset=name):
                    a = project(ROOT/'examples/demo.ldr', ROOT/'examples/library', t/'a', camera_preset=name)
                    b = project(ROOT/'examples/demo.ldr', ROOT/'examples/library', t/'b', **preset['settings'])
                    self.assertEqual((t/'a').read_bytes(), (t/'b').read_bytes())
                    self.assertEqual(a['camera']['preset']['name'], name)
                    self.assertEqual(a['points_per_ldu'], b['points_per_ldu'])
            a = project(ROOT/'examples/demo.ldr', ROOT/'examples/library', t/'a')
            b = project(ROOT/'examples/demo.ldr', ROOT/'examples/library', t/'b', camera_preset='presentation')
            self.assertEqual(a['scene_sha256'], b['scene_sha256'])
            self.assertNotIn('preset', a['camera'])

    def test_cli_leaves_preset_angles_unset_unless_explicit(self):
        report = {'parts': 1, 'pdf': {'PDF_bytes': 0}}
        with patch.object(cli, 'render', return_value=report) as fn, contextlib.redirect_stdout(io.StringIO()):
            cli.main(['render','fixture','--library','lib','--output','out',
                      '--camera-preset','instruction','--elevation','28'])
        self.assertEqual(fn.call_args.kwargs['camera_preset'], 'instruction')
        self.assertEqual(fn.call_args.kwargs['elevation'], 28)
        self.assertNotIn('azimuth', fn.call_args.kwargs)
        self.assertNotIn('projection', fn.call_args.kwargs)

    def test_tray_executes_preset_with_manifest_override(self):
        with tempfile.TemporaryDirectory() as temp:
            t=Path(temp)
            (t/'tray.json').write_text(json.dumps({'items': [
                {'model':str(ROOT/'examples/demo.ldr')},
                {'model':str(ROOT/'examples/demo.ldr'),'azimuth':70}]}))
            r=render_tray(t/'tray.json',ROOT/'examples/library',t/'out',camera_preset='instruction',
                          columns=2,width=400,height=220,cache_dir=ROOT/'.brickblueprint-cache')
            cams=[i['camera'] for i in r['items']]
            self.assertEqual([c['azimuth'] for c in cams],[35,70])
            self.assertEqual([c['field_of_view_vertical_degrees'] for c in cams],[2,2])
            self.assertEqual(cams[0]['distance_ldu'],cams[1]['distance_ldu'])
            self.assertEqual(cams[0]['preset']['overrides'],{})
            self.assertEqual(cams[1]['preset']['overrides'],{'azimuth':70})
            self.assertEqual(r['pdf']['image_XObjects'],0)


if __name__ == '__main__':
    unittest.main()
