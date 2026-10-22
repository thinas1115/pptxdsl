"""初回coverageで未到達だった数値モデル・共通収容の拒否経路を検証する。"""
from decimal import Decimal
import unittest

from slidegen.chart_model import axis_scale, format_axis_value
from slidegen.layout_fit import FitError, fit_text_or_raise, fit_vertical_stacks, select_fit


class QualityFailurePathsTests(unittest.TestCase):
    def test_empty_fit_candidates(self):
        with self.assertRaisesRegex(ValueError, "候補がありません"):
            select_fit("test", 1, [], guidance="分割")

    def test_empty_vertical_stacks(self):
        for stacks in ([], [[]]):
            with self.assertRaisesRegex(ValueError, "空でないstack"):
                fit_vertical_stacks("test", 1, stacks, lambda item, size: size,
                                    standard_size=12, min_size=10, font_step=.5,
                                    standard_gap=.2, min_gap=.1, gap_step=.05,
                                    guidance="分割")

    def test_unacceptable_line_breaks_stop(self):
        with self.assertRaisesRegex(FitError, "自然な位置"):
            fit_text_or_raise("test", "label", "短い文字列", 5, 1, 12, min_pt=12,
                              line_validator=lambda lines: False)

    def test_axis_rejects_invalid_format_and_nonfinite_decimal(self):
        with self.assertRaisesRegex(ValueError, "未対応"):
            format_axis_value(1, "invalid")
        with self.assertRaisesRegex(ValueError, "有限"):
            axis_scale([Decimal("NaN")])
        with self.assertRaisesRegex(ValueError, "有限"):
            axis_scale([0, 1]).ratio(Decimal("Infinity"))


if __name__ == "__main__":
    unittest.main()
