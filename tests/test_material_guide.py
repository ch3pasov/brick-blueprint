import json
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from compose_material_guide import check_renderer_output, sample_faces


class MaterialGuideTests(unittest.TestCase):
    def test_alternate_vector_needs_its_own_receipt_and_the_reviewed_native_input(self):
        reference = dict(scene_sha256='scene', model_sha256='model', style_sha256='style',
                         line_width_points=.4, page_points=[300, 240],
                         execution={'package_source_sha256': 'package'},
                         pdf={'SVG_sha256': 'reference', 'image_XObjects': 0})
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            actual = dict(reference, pdf={'SVG_sha256': 'alternate', 'image_XObjects': 0})
            receipt = folder / 'render.json'
            receipt.write_text(json.dumps(actual))
            check_renderer_output(folder, 'alternate', reference, False)
            with self.assertRaisesRegex(ValueError, 'bytes'):
                check_renderer_output(folder, 'alternate', reference, True)
            with self.assertRaisesRegex(ValueError, 'own native render receipt'):
                check_renderer_output(folder, 'modified', reference, False)
            actual['scene_sha256'] = 'different camera'
            receipt.write_text(json.dumps(actual))
            with self.assertRaisesRegex(ValueError, 'scene_sha256'):
                check_renderer_output(folder, 'alternate', reference, False)

    def test_labels_follow_visible_face_paint_in_draw_order(self):
        paths = [ET.Element('path', d=d, fill=paint) for d, paint in [
            ('M0,0H600V480H0Z', '#0a0a0a'),
            ('M250,110H305V170H250Z', '#151515'),
            ('M350,260H420V350H350Z', '#202020')]]
        colors = {'left':[10]*3, 'top':[20.5]*3, 'right':[32]*3}
        sample_faces(paths, colors)
        with self.assertRaisesRegex(ValueError, 'Face paint'):
            sample_faces(list(reversed(paths)), colors)
