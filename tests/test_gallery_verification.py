"""The read-only gallery check must distinguish a new self-consistent forgery
from reproduction of the supplied reference, and reject unsafe inventories.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('verify_gallery',ROOT/'tools/verify_gallery.py')
verify=importlib.util.module_from_spec(spec);spec.loader.exec_module(verify)


def sha(data):return hashlib.sha256(data).hexdigest()
def data(value):return (json.dumps(value,indent=2)+'\n').encode()
def snapshot(folder):return {p.relative_to(folder).as_posix():sha(p.read_bytes()) for p in folder.rglob('*') if p.is_file()}


class GalleryVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.reference=self.root/'reference';self.output=self.root/'output'
        self.reference.mkdir();self.output.mkdir();(self.output/'kiosk').mkdir()
        self.svg=b'<svg xmlns="http://www.w3.org/2000/svg"/>'
        self.pdf=b'%PDF-1.4\nSynthetic checksum fixture; never presented as a real rendered PDF.\n'
        self.receipt=dict(model_sha256='model-input',model_structure={'expanded_parts':41},page_points=[760,600],
                          dependencies=[dict(file='ldraw/parts/example.dat',sha256='geometry-input')],
                          library_config=dict(file='ldraw/LDConfig.ldr',sha256='palette-input'),
                          execution=dict(package_source_sha256='package-input',python_version='3.12'),
                          pdf=dict(SVG_sha256=sha(self.svg),PDF_sha256=sha(self.pdf)))
        self.recipe=dict(scenes=['kiosk'],generator_sha256='generator-input',recipe_sha256='recipe-input',models={'kiosk.ldr':'model-input'},render_receipts={'kiosk':sha(data(self.receipt))})
        (self.reference/'kiosk-showcase.json').write_bytes(data(self.recipe))
        expected=dict(self.receipt,full_render_receipt_sha256=sha(data(self.receipt)))
        (self.reference/'kiosk.json').write_bytes(data(expected))
        self.save_actual()
        (self.output/'kiosk/model.svg').write_bytes(self.svg);(self.output/'kiosk/model.pdf').write_bytes(self.pdf)

    def save_actual(self):
        self.recipe['render_receipts']['kiosk']=sha(data(self.receipt))
        (self.output/'showcase.json').write_bytes(data(self.recipe))
        (self.output/'kiosk/render.json').write_bytes(data(self.receipt))

    def check(self):return verify.compare(showcase=self.output,reference=self.reference)

    def test_match_is_read_only_and_runtime_variation_is_reported(self):
        before=snapshot(self.root);self.assertEqual(self.check()['status'],'MATCH');self.assertEqual(before,snapshot(self.root))
        self.receipt['execution']['python_version']='3.13';self.save_actual()
        result=self.check();self.assertEqual(result['status'],'MATCH');self.assertEqual(len(result['runtime_notes']),1)
        # Root directory presentation is not a geometry revision.
        self.receipt['dependencies'][0]['file']='parts/example.dat'
        self.receipt['library_config']['file']='LDConfig.ldr';self.save_actual()
        self.assertEqual(self.check()['status'],'MATCH')

    def test_changed_artifact_fails_even_after_own_receipt_is_rehashed(self):
        changed=self.pdf+b'changed';(self.output/'kiosk/model.pdf').write_bytes(changed)
        result=self.check();self.assertEqual(result['status'],'MISMATCH')
        self.receipt['pdf']['PDF_sha256']=sha(changed);self.save_actual()
        result=self.check();self.assertEqual(result['status'],'MISMATCH')
        self.assertTrue(any(r['item'].endswith('model.pdf/reference') for r in result['differences']))
        self.assertFalse(any(r['item'].endswith('model.pdf/own-receipt') for r in result['differences']))

    def test_changed_palette_geometry_and_model_are_not_cleared_by_equal_vectors(self):
        self.receipt['library_config']['sha256']='changed-palette'
        self.receipt['dependencies'][0]['sha256']='changed-geometry'
        self.receipt['model_sha256']='changed-model';self.save_actual()
        result=self.check();self.assertEqual(result['status'],'MISMATCH')
        failed={r['item'] for r in result['differences']}
        self.assertIn('kiosk/DAT-and-palette',failed);self.assertIn('kiosk/model_sha256',failed)

    def test_unsafe_scene_inventory_and_symlink_escape_are_rejected(self):
        for names in (['../outside'],['kiosk','kiosk']):
            with self.subTest(names=names):
                recipe=dict(self.recipe,scenes=names);(self.output/'showcase.json').write_bytes(data(recipe))
                with self.assertRaises(ValueError):self.check()
        self.save_actual();(self.output/'kiosk/model.pdf').unlink()
        outside=self.root/'outside.pdf';outside.write_bytes(self.pdf)
        (self.output/'kiosk/model.pdf').symlink_to(outside)
        with self.assertRaises(ValueError):self.check()


if __name__=='__main__':unittest.main()
