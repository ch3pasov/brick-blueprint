"""Geometric invariants and evidence boundaries for the opt-in slope model."""
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest

from brick_blueprint.project import project
from brick_blueprint.style import load_style

ROOT = Path(__file__).resolve().parents[1]


class AngularMaterialTests(unittest.TestCase):
    def test_observed_slopes_replay_through_actual_style(self):
        spec = importlib.util.spec_from_file_location('angular_check', ROOT / 'tools/analyze_angular_material.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.analyze(ROOT)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['scores']['all']['candidate']['pass'], 77)

    def test_opt_in_keeps_axis_anchors_and_unmeasured_materials(self):
        base = load_style()
        angular = load_style(material_profile='research-angular')
        for color in map(int, base.data['palette']):
            for normal in [(1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, -1, 0), (0, 1, 0)]:
                self.assertEqual(base.face(color, (12, 34, 56), normal, 'body'), angular.face(color, (12, 34, 56), normal, 'body'))
        for color, feature, alpha in [(4, 'body', .5), (2, 'body', 1), (0, 'explicit_colour_surface', 1), (15, 'stud_cylinder_wall', 1), (15, 'sideways_stud_cylinder_wall', 1)]:
            self.assertEqual(base.face(color, (12, 34, 56), (.6, -.8, 0), feature, alpha=alpha), angular.face(color, (12, 34, 56), (.6, -.8, 0), feature, alpha=alpha))

    def test_continuity_and_normal_scaling_across_knots_axes_and_hemispheres(self):
        style = load_style(material_profile='research-angular')
        for code in (0, 4, 15, 71):
            for phi in (0, .001, 30, 89.999, 90, 120, 180):
                for theta in (0, 18, 26.56505117707799, 45, 73, 90):
                    p, t = math.radians(phi), math.radians(theta)
                    n = (math.sin(t) * math.cos(p), -math.cos(t), math.sin(t) * math.sin(p))
                    a = style.face(code, (0, 0, 0), n, 'body')
                    b = style.face(code, (0, 0, 0), tuple(7 * v for v in n), 'body')
                    self.assertLess(max(abs(x - y) for x, y in zip(a, b)), 1e-10)
                    for epsilon in (-1e-7, 1e-7):
                        u = t + epsilon
                        nearby = (math.sin(u) * math.cos(p), -math.cos(u), math.sin(u) * math.sin(p))
                        b = style.face(code, (0, 0, 0), nearby, 'body')
                        self.assertLess(max(abs(x - y) for x, y in zip(a, b)), .0001)

    def test_receipt_distinguishes_extrapolated_normals(self):
        s = load_style(material_profile='research-angular')
        for n in [(1, -1, 0), (1, -1, 1), (-1, -1, 0), (1, 1, 0)]:
            s.face(15, (255, 255, 255), n, 'body')
        receipt = s.receipt()
        for key in ('empirical_principal_slope', 'unmeasured_azimuth_blend', 'unmeasured_mirrored_direction', 'angular_lower_surface_fallback'):
            self.assertIn(key, receipt['usage'])
        self.assertIn('opt-in', receipt['interpolation_status'])
        self.assertNotIn(str(ROOT), json.dumps(receipt))

    def test_profile_changes_only_paint_in_projected_scene(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = project(ROOT / 'examples/demo.ldr', ROOT / 'examples/library', root / 'a.scene')
            b = project(ROOT / 'examples/demo.ldr', ROOT / 'examples/library', root / 'b.scene', material_profile='research-angular')
            self.assertEqual(a['camera'], b['camera'])
            self.assertEqual(a['dependencies'], b['dependencies'])
            aa, bb = [(root / name).read_text().splitlines() for name in ('a.scene', 'b.scene')]
            n = a['triangles']
            self.assertEqual(aa[0], bb[0])
            for x, y in zip(aa[1:n + 1], bb[1:n + 1]):
                x, y = x.split(), y.split()
                self.assertEqual(x[:1] + x[4:], y[:1] + y[4:])
            self.assertEqual(aa[n + 1:], bb[n + 1:])


if __name__ == '__main__':
    unittest.main()
