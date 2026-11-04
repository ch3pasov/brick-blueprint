import math
from pathlib import Path
import tempfile
import unittest
from brick_blueprint.camera import PerspectiveCamera
from brick_blueprint.project import project
ROOT=Path(__file__).resolve().parents[1]

class CalibrationCameraTests(unittest.TestCase):
    def test_off_frame_optical_centre_matches_independent_pinhole(self):
        points=[(-5,-5,-5),(5,-5,-5),(0,5,5)]
        camera=PerspectiveCamera(points,(1,0,0),(0,1,0),(0,0,1),200,160,(0,0,200,160),
            field_of_view=math.degrees(2*math.atan(160/800)),camera_distance=1000,
            camera_target=(-750,550,0),principal_point=(-200,300))
        for x,y,z in points:
            got=camera.project((x,y,z))
            expected=(-200+400*(x+750)/(1000-z),300+400*(y-550)/(1000-z),1000*z/(1000-z))
            for a,b in zip(got,expected):self.assertAlmostEqual(a,b,places=10)
        self.assertEqual(camera.receipt()['principal_point_points'],(-200,300))
        expected_span=math.degrees(math.atan((160-300)/400)-math.atan(-300/400))
        self.assertAlmostEqual(camera.receipt()['vertical_page_span_degrees'],expected_span)
        self.assertNotAlmostEqual(camera.receipt()['vertical_page_span_degrees'],camera.field_of_view)

    def test_roll_rotates_image_axes_and_zero_preserves_scene_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);model=ROOT/'examples/demo.ldr';lib=ROOT/'examples/library'
            a=project(model,lib,d/'a.scene',width=300,height=240,scale=.4)
            b=project(model,lib,d/'b.scene',width=300,height=240,scale=.4,camera_roll=0)
            self.assertEqual((d/'a.scene').read_bytes(),(d/'b.scene').read_bytes())
            c=project(model,lib,d/'c.scene',width=300,height=240,scale=.4,camera_roll=20,
                      camera_target=a['camera']['target_ldu'])
            r=math.radians(20)
            for x,y,z in zip(c['camera']['right'],a['camera']['right'],a['camera']['down']):
                self.assertAlmostEqual(x,math.cos(r)*y+math.sin(r)*z,places=12)
            for x,y,z in zip(c['camera']['down'],a['camera']['right'],a['camera']['down']):
                self.assertAlmostEqual(x,-math.sin(r)*y+math.cos(r)*z,places=12)
            self.assertEqual(c['camera']['roll_degrees'],20)
            self.assertEqual(c['materials'],a['materials'])

    def test_invalid_or_cropped_calibration_fails(self):
        kwargs=dict(vertices=[(-1,-1,0),(1,-1,0),(0,1,0)],right=(1,0,0),down=(0,1,0),backward=(0,0,1),width=200,height=160,viewport=(0,0,200,160))
        for extra in [dict(principal_point=(0,0)),dict(principal_point=(float('nan'),0),camera_distance=100),dict(principal_point=(-1000,0),camera_distance=100)]:
            with self.assertRaises(ValueError):PerspectiveCamera(**kwargs,**extra)
        with tempfile.TemporaryDirectory() as d:
            for options in [dict(camera_roll=float('inf')),dict(camera_roll=181),dict(projection='orthographic',camera_roll=0),dict(projection='orthographic',principal_point=(0,0))]:
                with self.assertRaises(ValueError):project(ROOT/'examples/demo.ldr',ROOT/'examples/library',Path(d)/'bad.scene',**options)
