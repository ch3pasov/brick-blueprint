from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from compose_lighthouse_plate import GRID, expand, integer_path


class IntegerPlateTests(unittest.TestCase):
    def test_subpaths_and_repeated_vertices_survive_exactly(self):
        # Tiny hole, repeated vertex and relative move after a closed contour.
        source = 'M0,0h2v2h-2z m1,1 l.001,0 0,-.001 0,0z'
        encoded, count = integer_path(source)
        expected = [tuple([op]+[v*GRID for v in coords]) for op,*coords in expand(source)]
        self.assertEqual(count,len(expected))
        self.assertEqual(expand(encoded),expected)

    def test_geometry_outside_the_native_grid_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'finer precision'):
            integer_path('M0,0L.00001,0Z')
