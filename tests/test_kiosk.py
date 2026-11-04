from collections import Counter
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from brick_blueprint.ldraw import load_model

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('generate_kiosk',ROOT/'examples/generate_kiosk.py')
generator=importlib.util.module_from_spec(spec);spec.loader.exec_module(generator)


class KioskTests(unittest.TestCase):
    def test_generator_recreates_exact_editable_examples_and_bom(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/'kiosk'
            receipt=generator.write(dest)
            expected=ROOT/'examples/kiosk'
            files={p.relative_to(dest) for p in dest.rglob('*') if p.is_file()}
            self.assertEqual(files,{p.relative_to(expected) for p in expected.rglob('*') if p.is_file()})
            for name in files:self.assertEqual((dest/name).read_bytes(),(expected/name).read_bytes(),str(name))
            self.assertEqual(receipt['parts'],41)
            tray=json.loads((dest/'bom-tray.json').read_text())
            parts,metadata=load_model(dest/'kiosk.ldr')
            inventory=Counter((p['part'],p['ldraw_color']) for p in parts)
            counted=Counter()
            for item in tray['items']:
                specimen,_=load_model(dest/item['model'])
                self.assertEqual(len(specimen),1)
                p=specimen[0];counted[(p['part'],p['ldraw_color'])]+=item['quantity']
            self.assertEqual(inventory,counted)
            with self.assertRaises(FileExistsError):generator.write(dest)

    def test_flat_and_repeated_mpd_have_same_geometry_colors_and_root_steps(self):
        flat,_=load_model(ROOT/'examples/kiosk/kiosk.ldr')
        mpd,meta=load_model(ROOT/'examples/kiosk/kiosk.mpd')
        def physical(p):return p['part'],p['ldraw_color'],tuple(p['xyz']),tuple(p['matrix']),p['step']
        self.assertEqual(Counter(map(physical,flat)),Counter(map(physical,mpd)))
        self.assertEqual(len(flat),41)
        self.assertEqual({p['step'] for p in flat},set(range(1,9)))
        self.assertEqual(meta['declared_submodels'],9)


if __name__=='__main__':unittest.main()
