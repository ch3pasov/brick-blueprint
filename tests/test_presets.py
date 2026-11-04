from pathlib import Path
import tempfile,unittest,xml.etree.ElementTree as ET
from brick_blueprint.presets import all_presets,get_preset
from brick_blueprint.pipeline import render
ROOT=Path(__file__).resolve().parents[1]
NS='{http://www.w3.org/2000/svg}'
class PresetTests(unittest.TestCase):
 def test_presets_have_evidence_and_distinct_semantic_roles(self):
  presets=all_presets();self.assertEqual(len(presets),15)
  self.assertNotEqual(presets['fortnite-lilac']['panels']['parts'],presets['fortnite-lilac']['panels']['subassembly'])
  self.assertIsNone(presets['starwars-foldout']['panels']['parts'])
  for p in presets.values():self.assertTrue(p['sources']);self.assertGreaterEqual(p['panel_radius_pt'],0)
 def test_unknown_preset(self):
  with self.assertRaisesRegex(ValueError,'Unknown preset'):get_preset('invented')
 def test_all_presets_render_round_panel_count_and_pdf(self):
  with tempfile.TemporaryDirectory() as tmp:
   for key,preset in all_presets().items():
    with self.subTest(preset=key):
     out=Path(tmp)/key;r=render(ROOT/'examples/demo.ldr',ROOT/'examples/library',out,preset=key,layout='callout',quantity=(2 if preset.get('show_quantity_labels',True) else 1),width=200,height=180,cache_dir=ROOT/'.brickblueprint-cache')
     root=ET.parse(out/'model.svg').getroot();rects=root.findall(NS+'rect');text=root.find(NS+'text')
     self.assertEqual(rects[0].get('fill'),preset['page_background'])
     panel=next(n for n in root if n.get('id')=='presentation-panel')
     self.assertEqual(panel.get('fill'),preset['panels'][preset['default_panel_role']])
     self.assertEqual(text.text if text is not None else None,'2x' if preset.get('show_quantity_labels',True) else None);self.assertEqual(r['pdf']['image_XObjects'],0)
 def test_unsupported_panel_role_fails_before_output(self):
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp)/'bad'
   with self.assertRaisesRegex(ValueError,'No measured'):render('unused','unused',out,preset='starwars-foldout',layout='callout',panel_role='parts')
   self.assertFalse(out.exists())
 def test_background_override_retains_panel_fill(self):
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp)/'custom';render(ROOT/'examples/demo.ldr',ROOT/'examples/library',out,preset='friends-aqua',layout='callout',background=(255,255,255),width=200,height=180,cache_dir=ROOT/'.brickblueprint-cache')
   rects=ET.parse(out/'model.svg').getroot().findall(NS+'rect')
   self.assertEqual(rects[0].get('fill'),'#FFFFFF');self.assertEqual(rects[1].get('fill'),'#BEE1E0')
 def test_count_must_be_positive(self):
  for count in (0,-1,1.5,True):
   with self.assertRaisesRegex(ValueError,'Quantity'):render('unused','unused','unused',quantity=count)
 def test_friends_subassembly_uses_purple_border_and_preserves_text_in_pdf(self):
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp)/'subassembly';receipt=render(ROOT/'examples/demo.ldr',ROOT/'examples/library',out,preset='friends-aqua',layout='callout',panel_role='subassembly',quantity=3,width=200,height=180,cache_dir=ROOT/'.brickblueprint-cache')
   panel=ET.parse(out/'model.svg').getroot().findall(NS+'rect')[1]
   self.assertEqual(panel.get('fill'),'#D2C5E2');self.assertEqual(panel.get('stroke'),'#4A2282')
   self.assertEqual(receipt['presentation']['panel_stroke_pt'],2)
   self.assertIn(b'/BaseFont /Helvetica-Bold',(out/'model.pdf').read_bytes())
 def test_slate_label_contrast_changes_with_panel_role(self):
  with tempfile.TemporaryDirectory() as tmp:
   for role,color in [('parts','#FFFFFF'),('subassembly','#303838')]:
    out=Path(tmp)/role
    render(ROOT/'examples/demo.ldr',ROOT/'examples/library',out,preset='botanicals-slate',layout='callout',panel_role=role,quantity=2,width=200,height=180,cache_dir=ROOT/'.brickblueprint-cache')
    root=ET.parse(out/'model.svg').getroot()
    self.assertEqual(root.find(NS+'text').get('fill'),color)
    self.assertEqual(root.findall(NS+'rect')[1].get('stroke'),color)
    pdf=(out/'model.pdf').read_bytes()
    self.assertIn(b'/BaseFont /Helvetica ',pdf)
    self.assertNotIn(b'/BaseFont /Helvetica-Bold',pdf)
 def test_green_subassembly_is_now_evidenced_by_11509(self):
  self.assertEqual(get_preset('botanicals-green')['panels']['subassembly'],'#FFF5CB')
 def test_no_count_preset_rejects_hidden_multiple(self):
  with self.assertRaisesRegex(ValueError,'one icon per piece'):
   render('unused','unused','unused',preset='classic-space',layout='callout',quantity=2)
if __name__=='__main__':unittest.main()
