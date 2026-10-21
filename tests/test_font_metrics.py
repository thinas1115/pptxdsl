"""幅校正が数値超過・文字欠落・代替書体を見逃さないことを確認する。"""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.quality.font_metrics import compare, pdf_fonts


class FontMetricTests(unittest.TestCase):
    def test_width_excess_and_missing_text_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = root / "expected.json"
            observed = root / "observed.json"
            case = {"id": "metric", "page": 1, "top_pt": 10, "bottom_pt": 50, "text": "日本語", "pillow_width_pt": 30}
            expected.write_text(json.dumps({"fonts": {}, "cases": [case]}), encoding="utf-8")
            observed.write_text('[{"id":"metric","width_pt":32}]', encoding="utf-8")
            self.assertLess(compare(expected, observed, "powerpoint")["max_ratio"], 1.08)
            observed.write_text('[{"id":"metric","width_pt":33}]', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "安全係数"):
                compare(expected, observed, "powerpoint")
            # 字面の上端がセルより上でも、中心がセル内にある行は対象にする。
            observed.write_text('<doc><page><word xMin="10" xMax="40" yMin="7" yMax="25">日本語</word></page></doc>', encoding="utf-8")
            self.assertEqual(compare(expected, observed, "poppler")["max_ratio"], 1)
            observed.write_text('<doc><page><word xMin="10" xMax="40" yMin="7" yMax="25">欠落</word></page></doc>', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "文字列"):
                compare(expected, observed, "poppler")

    def test_pdf_substitution_is_rejected(self):
        def fonts(name):
            return subprocess.CompletedProcess([], 0, f"name type\n---- ----\nAAAAAA+{name} TrueType\n")
        with patch("tools.quality.font_metrics.subprocess.run", return_value=fonts("NotoSansCJKjp-Regular")):
            self.assertTrue(pdf_fonts(Path("deck.pdf"), "Noto Sans CJK JP"))
        with patch("tools.quality.font_metrics.subprocess.run", return_value=fonts("LiberationSans")):
            with self.assertRaisesRegex(ValueError, "代替"):
                pdf_fonts(Path("deck.pdf"), "Noto Sans JP")


if __name__ == "__main__":
    unittest.main()
