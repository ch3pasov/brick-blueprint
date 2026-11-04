import json,tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
from brick_blueprint.tray import render_tray
ROOT=Path(__file__).resolve().parents[1];NS='{http://www.w3.org/2000/svg}'
class TrayTests(unittest.TestCase):
 def fixture(self,tmp):
  T=Path(tmp)
  for name,size in [('small',10),('large',30)]:
   (T/(name+'.ldr')).write_text(f'0 test box\n1 4 0 0 0 {size} 0 0 0 10 0 0 0 10 unit-box.dat\n')
  m=T/'tray.json';m.write_text(json.dumps({'items':[{'model':'small.ldr','quantity':3},{'model':'large.ldr','quantity':1}]}));return m
 def render(self,m,out,**kwargs):return render_tray(m,ROOT/'examples/library',out,cache_dir=ROOT/'.brickblueprint-cache',columns=2,width=300,height=180,**kwargs)
 def test_shared_physical_scale_and_quantities(self):
  with tempfile.TemporaryDirectory() as tmp:
   m=self.fixture(tmp);out=Path(tmp)/'out';r=self.render(m,out,preset='ninjago-peach')
   self.assertEqual(r['items'][0]['points_per_ldu'],r['items'][1]['points_per_ldu'])
   root=ET.parse(out/'model.svg').getroot();self.assertEqual([x.text for x in root.findall(NS+'text')],['3x','1x'])
   ids=[n.get('id') for n in root.iter() if n.get('id')];self.assertEqual(len(ids),len(set(ids)))
   self.assertEqual(r['pdf']['image_XObjects'],0)
   self.assertEqual((r['item_count'],r['rendered_parts'],r['represented_parts']),(2,2,4))
 def test_no_overwrite(self):
  with tempfile.TemporaryDirectory() as tmp:
   m=self.fixture(tmp);out=Path(tmp)/'out';out.mkdir();(out/'keep').write_text('unchanged')
   with self.assertRaises(FileExistsError):self.render(m,out)
   self.assertEqual((out/'keep').read_text(),'unchanged')
 def test_slate_tray_uses_readable_white_quantities(self):
  with tempfile.TemporaryDirectory() as tmp:
   m=self.fixture(tmp);out=Path(tmp)/'out';self.render(m,out,preset='botanicals-slate')
   root=ET.parse(out/'model.svg').getroot()
   self.assertEqual([t.get('fill') for t in root.findall(NS+'text')],['#FFFFFF','#FFFFFF'])
   self.assertEqual([t.text for t in root.findall(NS+'text')],['3x','1x'])
 def test_default_columns_work_for_single_item(self):
  with tempfile.TemporaryDirectory() as tmp:
   m=self.fixture(tmp);m.write_text(json.dumps({'items':[{'model':'small.ldr','quantity':2}]}))
   r=render_tray(m,ROOT/'examples/library',Path(tmp)/'out',width=180,height=160,cache_dir=ROOT/'.brickblueprint-cache')
   self.assertEqual(r['columns'],1);self.assertEqual(r['rows'],1)
 def test_explicit_oversized_scale_rejected_atomically(self):
  with tempfile.TemporaryDirectory() as tmp:
   m=self.fixture(tmp);out=Path(tmp)/'out'
   with self.assertRaisesRegex(ValueError,'does not fit'):self.render(m,out,scale=100)
   self.assertFalse(out.exists())
 def test_malformed_item_and_unknown_role(self):
  with tempfile.TemporaryDirectory() as tmp:
   m=self.fixture(tmp);out=Path(tmp)/'out'
   with self.assertRaisesRegex(ValueError,'no measured parts'):self.render(m,out,preset='starwars-foldout')
   m.write_text(json.dumps({'items':[{'model':'small.ldr','quantity':False},{'model':'large.ldr'}]}))
   with self.assertRaisesRegex(ValueError,'Quantity'):self.render(m,out)
 def test_bad_item_camera_values_fail_before_output(self):
  with tempfile.TemporaryDirectory() as tmp:
   m=self.fixture(tmp);out=Path(tmp)/'out'
   for value in ('35',None,True,float('nan'),float('inf')):
    for name in ('azimuth','elevation'):
     m.write_text(json.dumps({'items':[{'model':'small.ldr',name:value}]}))
     with self.subTest(name=name,value=value),self.assertRaisesRegex(ValueError,'finite numbers'):
      self.render(m,out)
     self.assertFalse(out.exists())
 def test_transparent_forms_have_unique_references(self):
  with tempfile.TemporaryDirectory() as tmp:
   m=self.fixture(tmp);T=Path(tmp)
   for name in ['small','large']:
    p=T/(name+'.ldr');p.write_text(p.read_text().replace('1 4 ','1 47 '))
   out=T/'out';self.render(m,out);root=ET.parse(out/'model.svg').getroot();ids={n.get('id') for n in root.iter() if n.get('id')}
   refs=[n.get('{http://www.w3.org/1999/xlink}href')[1:] for n in root.iter() if n.get('{http://www.w3.org/1999/xlink}href')]
   self.assertTrue(refs);self.assertTrue(all(r in ids for r in refs))
 def test_no_count_tray_requires_explicit_repeated_icons(self):
  with tempfile.TemporaryDirectory() as tmp:
   m=self.fixture(tmp);out=Path(tmp)/'out'
   with self.assertRaisesRegex(ValueError,'one icon per piece'):self.render(m,out,preset='classic-space')
   self.assertFalse(out.exists())
   m.write_text(json.dumps({'items':[{'model':'small.ldr'},{'model':'small.ldr'}]}))
   r=self.render(m,out,preset='classic-space')
   self.assertEqual(len(r['items']),2)
   self.assertTrue(all(t.text is None for t in ET.parse(out/'model.svg').getroot().findall(NS+'text')))
if __name__=='__main__':unittest.main()
