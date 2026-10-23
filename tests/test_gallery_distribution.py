"""生成物の追跡抑制と配布ギャラリーの検査失敗停止を確認する。"""
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from tools.distribution.build import ROOT, _build_gallery
from tools.gallery.build_gallery_overview import build
from tests.test_pptxdsl_skill import _broken_local_links


class GalleryDistributionTests(unittest.TestCase):
    def test_tracked_preview_is_small_and_pptx_is_generated(self):
        with Image.open(ROOT / "docs/pattern-gallery-by-type.png") as image:
            self.assertEqual(image.width, 960)
        self.assertLessEqual((ROOT / "docs/pattern-gallery-by-type.png").stat().st_size, 256 * 1024)
        result = subprocess.run(["git", "ls-files", "--", "examples/gallery/*.pptx"],
                                cwd=ROOT, capture_output=True, text=True, check=True)
        self.assertFalse(result.stdout.strip(), "生成済みギャラリーPPTXを再追跡しています")
        for relative in ("README.md", "AGENTS.md", "examples/gallery/README.md", "docs/gallery-distribution.md"):
            self.assertFalse(_broken_local_links(ROOT / relative), relative)

    def test_overview_supports_small_and_full_width(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new("RGB", (1600, 900), "white").save(root / "slide_01.png")
            with patch("tools.gallery.build_gallery_overview._gallery_groups", return_value={"image_compare": [1]}):
                for width in (960, 1920):
                    target = root / f"overview-{width}.png"
                    build(root, target, width=width)
                    with Image.open(target) as image:
                        self.assertEqual(image.width, width)
                        self.assertGreater(image.height, 0)

    def test_invalid_preview_width_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "invalid.png"
            for width in (0, 639, 1921):
                with self.subTest(width=width), self.assertRaisesRegex(ValueError, "640〜1920"):
                    build(Path(directory), target, width=width)
                self.assertFalse(target.exists())

    def test_generation_or_check_failure_leaves_no_distribution(self):
        for codes in ((1,), (0, 1)):
            with self.subTest(codes=codes), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                target = root / "gallery.pptx"
                outcomes = [subprocess.CompletedProcess([], code, "", "非公開の診断") for code in codes]
                with patch("tools.distribution.build.subprocess.run", side_effect=outcomes) as run:
                    with self.assertRaisesRegex(ValueError, "生成・機械検査に失敗"):
                        _build_gallery(target, ROOT)
                self.assertEqual(run.call_count, len(codes))
                self.assertFalse(target.exists())
                self.assertFalse(list(root.iterdir()))


if __name__ == "__main__":
    unittest.main()
