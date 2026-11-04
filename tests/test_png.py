import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from importlib.util import find_spec
from pathlib import Path
from unittest.mock import patch

from brick_blueprint.cli import main
from brick_blueprint.pipeline import render
from brick_blueprint.png import check_png_dpi

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / 'examples/demo.ldr'
LIB = ROOT / 'examples/library'


class PngTests(unittest.TestCase):
    def test_invalid_dpi_and_missing_extra(self):
        for value in (0, -1, 601, True, 2.5):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'DPI'):
                check_png_dpi(value)
        with patch('brick_blueprint.png.find_spec', return_value=None):
            check_png_dpi(None)
            with self.assertRaisesRegex(RuntimeError, 'install'):
                check_png_dpi(144)

    def test_failed_png_conversion_does_not_publish_partial_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'render'
            with patch('brick_blueprint.pipeline.check_png_dpi'), \
                 patch('brick_blueprint.pipeline.export_png', side_effect=OSError('PNG failed')), \
                 self.assertRaisesRegex(OSError, 'PNG failed'):
                render(MODEL, LIB, out, png_dpi=144, cache_dir=ROOT/'.brickblueprint-cache')
            self.assertFalse(out.exists())

    @unittest.skipUnless(find_spec('PIL') and find_spec('pypdfium2'), 'Optional PNG extra')
    def test_model_and_finished_tray_through_cli(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp/'piece.ldr').write_bytes(MODEL.read_bytes())
            manifest = tmp/'tray.json'
            manifest.write_text(json.dumps({'items':[{'model':'piece.ldr','quantity':2}]}))
            for action, source, options, dpi in [
                ('render', MODEL, ['--png'], 144),
                ('tray', manifest, ['--png-dpi','216','--png'], 216)
            ]:
                folder = tmp/action
                args = [action,str(source),'--library',str(LIB),'--output',str(folder),
                        '--width','160','--height','150','--cache-dir',str(ROOT/'.brickblueprint-cache')]
                with self.subTest(action=action), redirect_stdout(io.StringIO()):
                    main(args+options)
                    receipt = json.loads((folder/'render.json').read_bytes())
                    png = folder/'model.png'
                    self.assertEqual(receipt['png']['sha256'],hashlib.sha256(png.read_bytes()).hexdigest())
                    with Image.open(png) as image:
                        self.assertEqual(image.format,'PNG')
                        self.assertEqual(image.size,(160*dpi//72,150*dpi//72))
                        self.assertAlmostEqual(image.info['dpi'][0],dpi,places=1)
                        self.assertGreater(len(image.convert('RGB').getcolors(image.width*image.height)),3)
                    args[args.index(str(folder))] = str(tmp/(action+'-vectors'))
                    main(args)
                    control = tmp/(action+'-vectors')
                    self.assertFalse((control/'model.png').exists())
                    for file in ('model.svg','model.pdf'):
                        self.assertEqual((control/file).read_bytes(),(folder/file).read_bytes())
