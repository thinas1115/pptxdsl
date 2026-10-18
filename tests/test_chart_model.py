"""グラフの数値範囲・符号・ゼロ・表示形式の真値付き回帰。"""
from decimal import Decimal
import unittest

from slidegen.chart_model import axis_scale, finite_number, format_axis_value, format_value, range_values


class ChartModelTests(unittest.TestCase):
    def test_hundred_does_not_expand_to_two_hundred(self):
        scale = axis_scale([100])
        self.assertEqual((scale.minimum, scale.maximum), (0, 100))
        self.assertEqual(scale.ticks, (0, 20, 40, 60, 80, 100))

    def test_negative_mixed_zero_and_small_ranges(self):
        for values in ([-25, -10], [-25, 10], [0, 0], [0.001, 0.002], [1e300, -1e300]):
            scale = axis_scale(values)
            self.assertLess(scale.minimum, scale.maximum)
            self.assertIn(0, scale.ticks)
            self.assertLessEqual(len(scale.ticks), 8)
            for value in values:
                self.assertLessEqual(0, scale.ratio(value))
                self.assertLessEqual(scale.ratio(value), 1)
        self.assertEqual(axis_scale([-25]).ratio(-25), 0)

    def test_signed_stacks_do_not_cancel(self):
        extents = range_values([["A", [30, -10]], ["B", [-25, 20]]], stacked=True)
        self.assertEqual(extents, [30, -25, 20, -10])
        self.assertEqual(range_values([["A", [0, 0]]], stacked=True), [0, 0, 0, 0])

    def test_formats_do_not_infer_percent(self):
        for value, number_format, expected in (
            (25, None, "25"), (25, "0.0", "25.0"), (0.25, "0%", "25%"),
            (25, "0%", "2500%"), (-0.125, "0.0%", "-12.5%"),
            (1234.56, "#,##0.0", "1,234.6"), (2.55, "0.0", "2.6"),
            (-0.0001, "0.0", "0.0"), (0.000123, None, "0.000123"),
            (-0.0, None, "0"),
            (25, '0"%"', "25%"), (2.5, '0.0"件"', "2.5件"),
            (1e30, "0", "1" + "0" * 30),
        ):
            self.assertEqual(format_value(value, number_format), expected)
        for number_format in ("General", "0.00E+00", "", True, "0;[Red]-0"):
            with self.assertRaises(ValueError):
                format_value(1, number_format)

    def test_nonfinite_and_boolean_rejected(self):
        for value in (True, None, "1", float("inf"), float("nan")):
            self.assertFalse(finite_number(value))
            with self.assertRaises(ValueError):
                axis_scale([value])
        with self.assertRaises(ValueError):
            format_value(Decimal("Infinity"))

    def test_axis_uses_explicit_units_without_losing_tick_precision(self):
        self.assertEqual(format_axis_value(0.2, "0.0%"), "20%")
        self.assertEqual(format_axis_value(20, '0"%"'), "20%")
        self.assertEqual(format_axis_value(0.002, "0.0"), "0.002")
        self.assertEqual(format_axis_value(20, '0"件"'), "20件")
        self.assertEqual(format_axis_value(100), "100")


if __name__ == "__main__":
    unittest.main()
