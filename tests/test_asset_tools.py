"""任意導入の素材変換依存でSVGから透過PNGを生成できることを確認する。"""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

from PIL import Image


class AssetToolTests(unittest.TestCase):
    def test_fluent_svg_conversion(self):
        ready = all(importlib.util.find_spec(module) for module in ("reportlab", "svglib", "rlPyCairo"))
        if not ready:
            if os.environ.get("PPTXDSL_ASSET_TOOLS_REQUIRED") == "1":
                self.fail("素材取得用依存が不足しています。requirements-dev.txtを導入してください。")
            self.skipTest("素材取得用依存は通常実行環境には不要。開発環境のCIで変換を検証する")
        from tools.assets.fetch_fluent_icons import PX, to_png

        svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M4 6h16v12H4z"/></svg>'
        with tempfile.TemporaryDirectory(prefix="pptxdsl-svg-") as temporary:
            output = Path(temporary) / "icon.png"
            to_png(svg, output)
            with Image.open(output) as image:
                self.assertEqual(image.size, (PX, PX))
                self.assertEqual(image.mode, "RGBA")
                self.assertEqual(image.getpixel((0, 0))[3], 0)
                self.assertEqual(image.getpixel((PX // 2, PX // 2))[3], 255)


if __name__ == "__main__":
    unittest.main()
