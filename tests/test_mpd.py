from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from brick_blueprint.ldraw import load_model,parse_model
from brick_blueprint.project import project
from brick_blueprint.pipeline import render

ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'examples/library'
I='1 0 0 0 1 0 0 0 1'
def line(color=4,x=0,y=0,z=0,m=I,ref='unit-box.dat'):
    return f'1 {color} {x} {y} {z} {m} {ref}\n'

class MPDTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.b=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def model(self,text,name='test.mpd'):
        p=self.b/name;p.write_text(text);return p
    def test_nested_rotation_reflection_color_and_root_step(self):
        p=self.model('0 FILE MAIN.ldr\n0 STEP\n'+line(4,10,20,30,'0 0 1 0 1 0 -1 0 0','SUB\\Arm.ldr')+
          '0 FILE sub/arm.ldr\n'+line(16,2,3,4,'-1 0 0 0 1 0 0 0 1','tip.ldr')+
          '0 FILE tip.ldr\n0 STEP\n0 STEP\n'+line(16,5,6,7)+line(2))
        parts,meta=load_model(p)
        # Independent hand composition: local(5,6,7)->(-3,9,11)->(21,29,33).
        self.assertEqual(parts[0]['xyz'],(21,29,33))
        self.assertEqual(parts[0]['matrix'],(0,0,1,0,1,0,1,0,0))
        self.assertEqual([p['ldraw_color'] for p in parts],[4,2])
        self.assertEqual([p['step'] for p in parts],[2,2])
        self.assertEqual(meta['used_submodels'],['main.ldr','sub/arm.ldr','tip.ldr'])
    def test_repeated_instances_are_not_cycles_or_extra_root_models(self):
        p=self.model('0 FILE main.ldr\n'+line(4,ref='two bricks.ldr')+line(2,50,ref='TWO BRICKS.LDR')+
          '0 FILE two bricks.ldr\n'+line(16)+line(16,20)+'0 FILE unused.ldr\n'+line(4,ref='unused.ldr'))
        parts,meta=load_model(p);self.assertEqual(len(parts),4)
        self.assertEqual([p['ldraw_color'] for p in parts],[4,4,2,2]);self.assertNotIn('unused.ldr',meta['used_submodels'])
    def test_cycle_missing_duplicates_and_unsafe_names(self):
        cases=[('0 FILE a.ldr\n'+line(ref='b.ldr')+'0 FILE b.ldr\n'+line(ref='a.ldr'),'cycle'),
          ('0 FILE a.ldr\n'+line(ref='missing.ldr'),'Missing model-local'),
          ('0 FILE a.ldr\n'+line()+'0 FILE A.LDR\n'+line(),'Duplicate'),
          ('0 FILE ../a.ldr\n'+line(),'Unsafe'),
          ('0 FILE a.ldr\n'+line(ref='../outside.ldr'),'Unsafe')]
        for text,error in cases:
            with self.subTest(error=error),self.assertRaisesRegex(ValueError,error):parse_model(self.model(text))
    def test_envelope_nofile_and_forward_references(self):
        p=self.model('An email wrapper\n0 comment\n0 FILE main.ldr\n'+line(ref='next.ldr')+
          '0 NOFILE\nIgnored signature\n'+line(ref='ignored.dat')+'0 FILE next.ldr\n'+line())
        self.assertEqual(len(parse_model(p)),1)
        with self.assertRaisesRegex(ValueError,'before first'):parse_model(self.model(line()+'0 FILE a.ldr\n'+line()))
    def test_unsupported_content_fails_explicitly(self):
        for text,error in [('0 FILE custom.dat\n'+line(),'embedded DAT'),
          ('0 FILE a.ldr\n3 4 0 0 0 1 0 0 1 1 0','type-1'),
          ('0 FILE a.ldr\n0 BFC INVERTNEXT\n'+line(),'INVERTNEXT'),
          ('0 FILE a.ldr\n0 !DATA image.png','Embedded data'),
          ('0 FILE a.ldr\n0 !TEXMAP START PLANAR','TEXMAP'),
          ('0 FILE a.ldr\n'+line(24),'color 24')]:
            with self.subTest(error=error),self.assertRaisesRegex(ValueError,error):parse_model(self.model(text))
    def test_expansion_depth_and_size_budgets(self):
        p=self.model('0 FILE a.ldr\n'+line(ref='b.ldr')+line(ref='b.ldr')+'0 FILE b.ldr\n'+line())
        for setting,value,error in [('MAX_MODEL_DEPTH',1,'depth'),('MAX_MODEL_EXPANSIONS',2,'expansion'),('MAX_MODEL_BYTES',10,'16 MiB'),('MAX_SUBMODELS',1,'Too many')]:
            with patch('brick_blueprint.ldraw.'+setting,value),self.assertRaisesRegex(ValueError,error):parse_model(p)
    def test_nonfinite_composed_transform_rejected(self):
        p=self.model('0 FILE a.ldr\n'+line(m='1e308 0 0 0 1 0 0 0 1',ref='b.ldr')+'0 FILE b.ldr\n'+line(x=1e308))
        with self.assertRaisesRegex(ValueError,'transform'):parse_model(p)
    def test_flat_equivalence_in_native_render(self):
        mpd=self.model('0 FILE main.ldr\n'+line(4,10,0,20,'0 0 1 0 1 0 -1 0 0','one.ldr')+
          line(2,-40,0,0,'-1 0 0 0 1 0 0 0 1','one.ldr')+'0 FILE one.ldr\n'+line(16,5,0,10))
        flat=self.model(line(4,20,0,15,'0 0 1 0 1 0 -1 0 0')+line(2,-45,0,10,'-1 0 0 0 1 0 0 0 1'),'flat.ldr')
        a=project(mpd,LIB,self.b/'a.scene');b=project(flat,LIB,self.b/'b.scene');self.assertEqual(a['scene_sha256'],b['scene_sha256'])
        for name,model in [('mpd',mpd),('flat',flat)]:render(model,LIB,self.b/name,cache_dir=ROOT/'.brickblueprint-cache',width=250,height=220)
        for ext in ['svg','pdf']:self.assertEqual((self.b/'mpd'/f'model.{ext}').read_bytes(),(self.b/'flat'/f'model.{ext}').read_bytes())

if __name__=='__main__':unittest.main()
