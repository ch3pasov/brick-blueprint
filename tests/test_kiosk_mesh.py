"""Analytic solids qualify the optional example diagnostic, not a physical build."""
from pathlib import Path
import importlib.util
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('kiosk_mesh',ROOT/'tools/audit_kiosk_mesh.py')
mesh=importlib.util.module_from_spec(spec);spec.loader.exec_module(mesh)


def cube(center=(0,0,0),half=1,reverse=False):
    vertices=[(-1,-1,-1),(1,-1,-1),(1,-1,1),(-1,-1,1),
              (-1,1,-1),(1,1,-1),(1,1,1),(-1,1,1)]
    vertices=[tuple(c+half*v for c,v in zip(center,p)) for p in vertices]
    faces=[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]
    triangles=[]
    for face in faces:
        for indices in ((0,1,2),(0,2,3)):
            triangle=tuple(vertices[face[i]] for i in indices)
            triangles.append(triangle[::-1] if reverse else triangle)
    return triangles


class KioskMeshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binary,_=mesh.compile_scanner(ROOT/'.brickblueprint-cache')

    def test_disjoint_touching_and_overlapping_closed_solids(self):
        for center,expected in [((4,0,0),False),((2,0,0),False),((.5,0,0),True)]:
            result=mesh.scan_meshes([cube(),cube(center)],self.binary,pitch=.75,phase=0)
            with self.subTest(center=center):self.assertEqual(result['total_overlap']>0,expected)
        # Overlapping closed components in one owner have winding 2, not the
        # parity-0 classification that would hide a real inter-owner overlap.
        union=cube((-.5,0,0),half=2)+cube((.5,0,0),half=2)
        result=mesh.scan_meshes([union,cube(half=.5)],self.binary,pitch=.75,phase=1)
        self.assertGreater(result['total_overlap'],0)

    def test_oriented_cavity_is_empty_but_its_real_wall_overlap_is_detected(self):
        shell=cube(half=4)+cube(half=2,reverse=True)
        for phase in (0,1):
            empty=mesh.scan_meshes([shell,cube()],self.binary,pitch=.75,phase=phase)
            wall=mesh.scan_meshes([shell,cube((2.5,0,0))],self.binary,pitch=.75,phase=phase)
            self.assertGreater(empty['total_probes'],0)
            self.assertEqual(empty['total_overlap'],0)
            self.assertGreater(wall['total_overlap'],0)


if __name__=='__main__':unittest.main()
