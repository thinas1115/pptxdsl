"""生成画像・利用者素材を同梱コードの変更なしで利用する。"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
import tempfile
from threading import Barrier
import unittest

from PIL import Image

from slidegen.asset_paths import image_assets, resolve_image_path
from slidegen.generate_from_json import RENDER, build_presentation
from slidegen.validate_content import validate


def deck():
    return {"meta": {"title": "概念の説明"}, "slides": [
        {"type": "image", "kicker": "概念", "title": "待機領域のイメージ",
         "image": "generated/concept.png", "alt": "処理前の待機領域を示す模式図"}]}


class ExternalImageTests(unittest.TestCase):
    def test_embed_validate_and_reset_without_mutating_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "generated").mkdir()
            source = root / "generated/concept.png"
            Image.new("RGB", (1200, 600), "#dfeae7").save(source)
            content = deck()
            snapshot = deepcopy(content)
            self.assertTrue(validate(content))
            self.assertEqual(validate(content, asset_dir=root), [])
            prs = build_presentation(content, asset_dir=root)
            picture = next(s for s in prs.slides[0].shapes if s.name == "ContentImage")
            self.assertEqual(picture.image.blob, source.read_bytes())
            self.assertEqual(content, snapshot)
            self.assertTrue(validate(content))

    def test_boundary_and_exception_restoration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = resolve_image_path("images/pptxdsl-repository.png")
            with image_assets(root):
                self.assertEqual(resolve_image_path("images/pptxdsl-repository.png"), original)
                for path in ("../escape.png", "/escape.png", "C:/private.png", "C:private.png", "~/image.png", "concept.svg"):
                    with self.subTest(path=path), self.assertRaises(ValueError):
                        resolve_image_path(path)
            with self.assertRaises(RuntimeError):
                with image_assets(root):
                    raise RuntimeError("生成の中断")
            self.assertEqual(resolve_image_path("images/pptxdsl-repository.png"), original)
            with self.assertRaises(ValueError):
                build_presentation(deck(), asset_dir=root / "missing")

    def test_parallel_roots_and_nested_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            # OS固有の一時パス別名がない環境でも、同じ実体の別表記を通す。
            alias = Path(directory) / "alias"
            alias.mkdir()
            roots = [alias / ".." / name for name in ("a", "b")]
            for root, color in zip(roots, ("red", "blue")):
                (root / "generated").mkdir(parents=True)
                Image.new("RGB", (100, 100), color).save(root / "generated/concept.png")
            barrier = Barrier(2, timeout=20)

            def delayed(slide, spec, page):
                before = resolve_image_path(spec["image"])
                barrier.wait()
                RENDER["image"](slide, spec, page)
                self.assertEqual(resolve_image_path(spec["image"]), before)

            def build(root):
                prs = build_presentation(deck(), asset_dir=root, renderers={"image": delayed})
                return next(s.image.blob for s in prs.slides[0].shapes if s.name == "ContentImage")

            with ThreadPoolExecutor(max_workers=2) as pool:
                outputs = list(pool.map(build, roots))
            self.assertNotEqual(*outputs)
            with image_assets(roots[0]):
                build_presentation(deck(), asset_dir=roots[1])
                self.assertEqual(resolve_image_path("generated/concept.png"),
                                 (roots[0] / "generated/concept.png").resolve())


if __name__ == "__main__":
    unittest.main()
