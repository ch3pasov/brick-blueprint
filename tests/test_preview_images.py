"""Optional preview readers must reject another format hidden behind .png."""
from pathlib import Path
import importlib.util
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('preview_images',ROOT/'tools/preview_images.py')
previews=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(previews)


@unittest.skipUnless(importlib.util.find_spec('PIL'),'Optional Pillow not installed')
class PreviewImageTests(unittest.TestCase):
    def test_generated_png_pixels_are_preserved(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'preview.png'
            Image.new('RGB',(4,3),(13,75,200)).save(path)
            with previews.open_png(path) as actual:
                self.assertEqual(actual.format,'PNG')
                self.assertEqual(actual.size,(4,3))
                self.assertEqual(actual.convert('RGB').getpixel((2,1)),(13,75,200))

    def test_non_png_with_png_filename_is_rejected(self):
        from PIL import Image,UnidentifiedImageError
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'preview.png'
            Image.new('RGB',(4,3),(13,75,200)).save(path,format='JPEG')
            with self.assertRaises(UnidentifiedImageError):
                previews.open_png(path)


if __name__=='__main__':
    unittest.main()
