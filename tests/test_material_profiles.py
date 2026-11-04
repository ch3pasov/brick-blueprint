"""The implemented material policy must remain tied to its stated evidence."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from brick_blueprint.pipeline import render
from brick_blueprint.project import project
from brick_blueprint.style import load_style
from brick_blueprint.tray import render_tray

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT/'examples/library'
MODEL = ROOT/'examples/demo.ldr'


class MaterialProfileTests(unittest.TestCase):
    def test_generated_anchors_and_evidence_reproduce_from_research_data(self):
        spec=importlib.util.spec_from_file_location('build_style',ROOT/'tools/build_research_style.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        style,evidence=module.build()
        for name,value in [('default-style.json',style),('material-research.json',evidence)]:
            self.assertEqual((ROOT/'brick_blueprint'/name).read_bytes(),(json.dumps(value,indent=2)+'\n').encode())
        self.assertEqual(len(style['palette']),11)
        self.assertEqual(evidence['data_sha256'],hashlib.sha256((ROOT/'docs/THREE-FACE-SHADING.json').read_bytes()).hexdigest())

    def test_three_axis_colors_and_interpolation_are_separate(self):
        style=load_style();nominal=(100,100,100)
        self.assertEqual(style.face(72,nominal,(1,0,0),'body'),(105,105,105))
        self.assertEqual(style.face(72,nominal,(0,-1,0),'body'),(113,113,113))
        self.assertEqual(style.face(72,nominal,(0,0,1),'body'),(117,117,117))
        self.assertEqual(style.face(72,nominal,(.6,-.8,0),'body'),tuple([(.6*105+.8*113)/1.4]*3))
        receipt=style.receipt()
        self.assertEqual(receipt['usage'],{'axis_anchor':3,'interpolated_orientation':1})
        self.assertEqual([r['ldraw_color'] for r in receipt['bindings']],[72])
        self.assertNotIn(str(ROOT),json.dumps(receipt))

    def test_sand_yellow_and_brick_yellow_have_distinct_measured_anchors(self):
        # LEGO element4255416 is Sand Yellow138, LDraw Dark_Tan28.
        # Ordinary Tan19 is a separate, independently identified material.
        style=load_style()
        self.assertEqual(style.face(28,(137,125,98),(1,0,0),'body'),(141,124,99))
        self.assertEqual(style.face(19,(215,186,140),(1,0,0),'body'),(186,167,116))
        self.assertEqual(style.face(19,(215,186,140),(0,-1,0),'body'),(200.5,182.5,124))
        self.assertEqual(style.face(19,(215,186,140),(0,0,1),'body'),(207,187,131))
        binding=next(r for r in style.receipt()['bindings'] if r['ldraw_color']==28)
        self.assertEqual(binding['catalogue_element_association'],'4255416')
        tan=next(r for r in style.receipt()['bindings'] if r['ldraw_color']==19)
        self.assertEqual(tan['catalogue_element_association'],'4114306')
        validation=tan['geometry_transfer_validation']
        self.assertTrue(validation['all_nine_shifts_pass'])
        for prefix in ('data','control'):
            self.assertEqual(validation[prefix+'_sha256'],hashlib.sha256((ROOT/validation[prefix+'_file']).read_bytes()).hexdigest())

    def test_provisional_colors_and_transparent_tan_keep_nominal_fallback(self):
        style=load_style()
        for code,nominal in [(2,(0,133,43)),(322,(104,195,226))]:
            self.assertNotIn(str(code),style.data['palette'])
            self.assertEqual(style.face(code,nominal,(0,-1,0),'body'),nominal)
        self.assertEqual(style.face(19,(215,186,140),(1,0,0),'body',alpha=.5),(215,186,140))

    def test_unmeasured_and_transparent_colors_are_not_claimed_as_calibrated(self):
        style=load_style();nominal=(12,34,56)
        self.assertEqual(style.face(1,nominal,(0,-1,0),'body'),nominal)
        # A library may assign alpha even to a normally opaque nominal ID.
        self.assertEqual(style.face(4,nominal,(0,-1,0),'body',alpha=.5),nominal)
        self.assertEqual(style.face(4,nominal,(1,0,0),'stud_cylinder_wall',alpha=.5),(7,7,7))
        self.assertEqual(style.receipt()['usage'],{'nominal_fallback':1,'transparent_nominal_fallback':1,'legacy_unmeasured_stud_wall':1})
        with self.assertRaises(ValueError):style.face(4,nominal,(0,-1,0),'body',state='invalid',alpha=.5)

    def test_stud_reference_is_bounded_by_orientation_and_material_opacity(self):
        style=load_style();legacy=load_style(material_profile='legacy');nominal=(244,244,244)
        self.assertEqual(style.face(15,nominal,(1,0,0),'stud_cylinder_wall'),(16,16,16))
        self.assertEqual(legacy.face(15,nominal,(1,0,0),'stud_cylinder_wall'),(7,7,7))
        self.assertEqual(style.face(15,nominal,(1,0,0),'stud_cylinder_wall',alpha=.5),(7,7,7))
        self.assertEqual(style.face(15,nominal,(0,1,0),'sideways_stud_cylinder_wall'),(7,7,7))
        evidence=style.receipt()['stud_wall_reference']
        self.assertEqual(evidence['data_sha256'],hashlib.sha256((ROOT/evidence['data_file']).read_bytes()).hexdigest())
        self.assertEqual(style.receipt()['usage'],{'opaque_vertical_stud_reference':1,'legacy_unmeasured_stud_wall':2})

    def test_tampered_stud_reference_is_rejected(self):
        from brick_blueprint.style import Style
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'style.json';data=json.loads((ROOT/'brick_blueprint/default-style.json').read_text())
            data['stud_wall']['rgb']=[99,99,99];path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'stud-wall color'):Style(path,profile='research')

    def test_profile_and_custom_style_cannot_silently_override_one_another(self):
        with self.assertRaisesRegex(ValueError,'either'):load_style(ROOT/'brick_blueprint/default-style.json','research')
        with self.assertRaisesRegex(ValueError,'Unknown material'):load_style(material_profile='invented')
        custom=load_style(ROOT/'brick_blueprint/default-style.json')
        self.assertEqual(custom.receipt()['profile'],'custom')
        self.assertNotIn('research_profile',custom.receipt())

    def test_profile_changes_paint_without_changing_camera_or_geometry(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);paths=[base/'research.scene',base/'legacy.scene']
            a=project(MODEL,LIB,paths[0]);b=project(MODEL,LIB,paths[1],material_profile='legacy')
            self.assertEqual(a['camera'],b['camera']);self.assertEqual(a['dependencies'],b['dependencies'])
            self.assertNotEqual(a['scene_sha256'],b['scene_sha256'])
            rows=[p.read_text().splitlines() for p in paths];n=a['triangles']
            self.assertEqual(rows[0][0],rows[1][0])
            for x,y in zip(rows[0][1:n+1],rows[1][1:n+1]):
                x=x.split();y=y.split();self.assertEqual(x[:1]+x[4:],y[:1]+y[4:])
            self.assertEqual(rows[0][n+1:],rows[1][n+1:])

    def test_native_export_and_tray_preserve_material_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            one=render(MODEL,LIB,base/'one',cache_dir=ROOT/'.brickblueprint-cache')
            self.assertEqual(one['materials']['profile'],'research')
            self.assertEqual(one['pdf']['image_XObjects'],0)
            self.assertEqual(json.loads((base/'one/render.json').read_text())['materials'],one['materials'])
            manifest=base/'tray.json';manifest.write_text(json.dumps({'items':[{'model':str(MODEL)}]}))
            tray=render_tray(manifest,LIB,base/'tray',material_profile='legacy',cache_dir=ROOT/'.brickblueprint-cache')
            self.assertEqual(tray['items'][0]['materials']['profile'],'legacy')
            self.assertEqual(tray['items'][0]['style_sha256'],hashlib.sha256((ROOT/'brick_blueprint/legacy-style.json').read_bytes()).hexdigest())
            self.assertNotIn(str(ROOT),json.dumps(tray['items'][0]['materials']))

    def test_cli_rejects_conflicting_profiles_before_render(self):
        result=subprocess.run([sys.executable,'-m','brick_blueprint','render',str(MODEL),'--library',str(LIB),
            '--output','unused-test-output','--material-profile','legacy','--style',str(ROOT/'brick_blueprint/default-style.json')],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,2)
        self.assertIn('not allowed with argument',result.stderr)
        self.assertNotIn('Traceback',result.stderr)


if __name__=='__main__':unittest.main()
