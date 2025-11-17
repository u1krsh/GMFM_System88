import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from gmfm_app.scoring.engine import calculate_gmfm66, calculate_gmfm88
from gmfm_app.scoring.constants import GMFM66_ITEMS, GMFM88_ITEMS


class TestScoring(unittest.TestCase):
    def test_gmfm66_all_max_scores(self):
        raw = {iid: 3 for ids in GMFM66_ITEMS.values() for iid in ids}
        result = calculate_gmfm66(raw)
        self.assertEqual(result["total_percent"], 100.0)
        for d in result["domains"].values():
            self.assertEqual(d["percent"], 100.0)

    def test_gmfm66_zero_scores(self):
        raw = {iid: 0 for ids in GMFM66_ITEMS.values() for iid in ids}
        result = calculate_gmfm66(raw)
        self.assertEqual(result["total_percent"], 0.0)
        for d in result["domains"].values():
            self.assertEqual(d["percent"], 0.0)

    def test_gmfm88_partial_scores(self):
        raw = {ids[0]: 1 for ids in GMFM88_ITEMS.values() if ids}
        result = calculate_gmfm88(raw)
        self.assertGreaterEqual(result["total_percent"], 0.0)
        self.assertLessEqual(result["total_percent"], 100.0)
        for d in result["domains"].values():
            self.assertGreaterEqual(d["percent"], 0.0)


if __name__ == "__main__":
    unittest.main()
