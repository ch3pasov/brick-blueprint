import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from analyze_face_law_17 import check_replay


class FaceLawReplayTests(unittest.TestCase):
    def test_only_computed_float_results_get_roundoff_tolerance(self):
        def record(gain=1.08, observed=105., codes=(72, 14)):
            return {'rows': [observed], 'results': {'top': {'gain':gain, 'training_codes':list(codes)}}}

        check_replay(record(), record(gain=1.08 + 2e-14))
        for changed, field in [(record(gain=1.081), 'gain'), (record(gain=float('nan')), 'gain'),
                               (record(observed=105. + 2e-13), 'rows.0'),
                               (record(codes=(14, 72)), 'training_codes.0')]:
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, field):
                check_replay(record(), changed)
