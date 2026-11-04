"""Invalid custom styles must fail at the documented JSON boundary."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from brick_blueprint.instruction_style import validate_config

ROOT=Path(__file__).resolve().parents[1]
DEFAULT=json.loads((ROOT/'brick_blueprint/default-style.json').read_text())


class StyleInputTests(unittest.TestCase):
    def test_palette_container_and_material_keys_are_checked(self):
        for value in (None,[],42,'palette'):
            style=deepcopy(DEFAULT);style['palette']=value
            with self.subTest(value=value),self.assertRaisesRegex(ValueError,'palette must be an object'):
                validate_config(style)
        for key in (4,'four','\u0664'):
            style=deepcopy(DEFAULT);style['palette']={key:deepcopy(DEFAULT['palette']['4'])}
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'numeric nominal'):
                validate_config(style)

    def test_thresholds_scalars_and_confidence_cannot_fail_later_in_shading(self):
        changes=[(('edges','light_if_nominal_Y_below'),v) for v in ('45',None,True,float('nan'),float('inf'),-1,256)]
        changes += [(('edges','width_points'),True),(('page','count_font_points'),'13'),(('page','width_points'),False),
                    (('palette','4','confidence'),None),(('edges','confidence'),[]),(('family',),''),
                    (('schema_version',),True),(('fallback','normal_gains'),[True,1,1]),(('step_states','new','gain'),True)]
        for keys,value in changes:
            style=deepcopy(DEFAULT);target=style
            for key in keys[:-1]:target=target[key]
            target[keys[-1]]=value
            with self.subTest(keys=keys,value=value),self.assertRaises(ValueError):validate_config(style)

    def test_cli_reports_style_error_without_traceback_or_final_output(self):
        with tempfile.TemporaryDirectory() as temp:
            temp=Path(temp);config=temp/'invalid-style.json';out=temp/'render'
            for value in ([],None):
                style=deepcopy(DEFAULT);style['palette']=value;config.write_text(json.dumps(style))
                result=subprocess.run([sys.executable,'-m','brick_blueprint','render','examples/demo.ldr',
                    '--library','examples/library','--style',config,'--output',out,
                    '--cache-dir',ROOT/'.brickblueprint-cache'],cwd=ROOT,capture_output=True,text=True)
                self.assertEqual(result.returncode,1)
                self.assertIn('Material palette must be an object',result.stderr)
                self.assertNotIn('Traceback',result.stderr);self.assertFalse(out.exists())


if __name__=='__main__':unittest.main()
