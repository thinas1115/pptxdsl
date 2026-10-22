"""checkerの線分交差を解析解と境界条件で検証する。"""
from types import SimpleNamespace
import unittest

from pptx.enum.dml import MSO_FILL_TYPE

from slidegen.check_layout import has_solid_fill, seg_hits_rect


class GeometryTests(unittest.TestCase):
    def test_narrow_rect_between_old_sample_points(self):
        rect = (0.501, -0.1, 0.509, 0.1)
        self.assertTrue(seg_hits_rect((0, 0, 10, 0), rect, eps=0))
        self.assertTrue(seg_hits_rect((10, 0, 0, 0), rect, eps=0))

    def test_diagonal_vertical_and_contained_lines(self):
        rect = (1, 1, 2, 2)
        for segment in ((0, 0, 3, 3), (1.5, 0, 1.5, 3),
                        (1.2, 1.2, 1.8, 1.8), (3, 0, 0, 3)):
            with self.subTest(segment=segment):
                self.assertTrue(seg_hits_rect(segment, rect, eps=0))

    def test_tangent_border_and_trimmed_endpoints(self):
        rect = (1, 1, 2, 2)
        for segment in ((0, 1, 3, 1), (0, 2, 2, 0),
                        (0, 0, 1, 1), (0, 0, 0.1, 0.1),
                        (0, 0, 1.02, 1.02), (0, 0, 0, 0)):
            with self.subTest(segment=segment):
                self.assertFalse(seg_hits_rect(segment, rect, eps=0))

    def test_epsilon_erodes_rect(self):
        self.assertFalse(seg_hits_rect((0, 0, 10, 0), (1, -0.01, 2, 0.01), eps=0.02))

    def test_fill_uses_enum_and_does_not_swallow_failures(self):
        for kind, expected in ((MSO_FILL_TYPE.SOLID, True), (None, False),
                               (MSO_FILL_TYPE.BACKGROUND, False)):
            self.assertEqual(has_solid_fill(SimpleNamespace(fill=SimpleNamespace(type=kind))), expected)
        with self.assertRaises(AttributeError):
            has_solid_fill(object())


if __name__ == "__main__":
    unittest.main()
