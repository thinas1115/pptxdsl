"""image_compare rendererのパス・段階的収容・schemaを検証する。"""
from copy import deepcopy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Inches, Pt

from slidegen import generate
from slidegen.image_slide import (
    COMPARE_PICTURE_NAME, fit_image_compare_layout, s_image_compare,
)
from slidegen.layout_fit import FitError
from slidegen.validate_content import validate
from slidegen import image_slide
from slidegen.check_layout import check


def _slide():
    prs = Presentation()
    prs.slide_width = Inches(generate.SLIDE_W)
    prs.slide_height = Inches(generate.SLIDE_H)
    return prs.slides.add_slide(prs.slide_layouts[6])


def _must_fail(fn, expected):
    try:
        fn()
    except FitError as exc:
        assert expected in str(exc), str(exc)
    else:
        raise AssertionError("過密入力を拒否しませんでした")


def main():
    spec = {
        "type": "image_compare", "kicker": "比較", "title": "画像比較",
        "left": {"image": "images/pptxdsl-repository.png", "label": "変更前"},
        "right": {"image": "cover/cover-background.png", "label": "変更後"},
        "fit": "cover", "shadow": True,
    }
    deck = {
        "meta": {"title": "検証", "footer": "検証", "date": "2026年7月",
                 "author": "検証担当"},
        "slides": [spec],
    }
    assert not validate(deck)

    slide = _slide()
    s_image_compare(slide, spec, 1)
    pictures = [shape for shape in slide.shapes
                if shape.shape_type == MSO_SHAPE_TYPE.PICTURE]
    assert len(pictures) == 2
    assert all(p.name == COMPARE_PICTURE_NAME for p in pictures)
    left_pic, right_pic = sorted(pictures, key=lambda p: p.left)
    assert left_pic.left < right_pic.left
    # cover指定なので、縦横比に応じてどちらかの軸をトリミングしている。
    assert (left_pic.crop_top > 0 or left_pic.crop_left > 0)
    assert (right_pic.crop_top > 0 or right_pic.crop_left > 0)

    texts = {shape.text_frame.text for shape in slide.shapes
             if shape.has_text_frame}
    assert {"変更前", "変更後"} <= texts

    contain_spec = dict(spec, fit="contain")
    contain_slide = _slide()
    s_image_compare(contain_slide, contain_spec, 1)
    contain_pictures = [shape for shape in contain_slide.shapes
                         if shape.shape_type == MSO_SHAPE_TYPE.PICTURE]
    assert all(p.crop_left == p.crop_right == 0
               and p.crop_top == p.crop_bottom == 0
               for p in contain_pictures)

    default_label_spec = deepcopy(spec)
    del default_label_spec["left"]["label"]
    del default_label_spec["right"]["label"]
    default_slide = _slide()
    s_image_compare(default_slide, default_label_spec, 1)
    default_texts = {shape.text_frame.text for shape in default_slide.shapes
                      if shape.has_text_frame}
    assert {"BEFORE", "AFTER"} <= default_texts

    assert fit_image_compare_layout(5.27).stage == "standard"
    assert fit_image_compare_layout(3.60).stage == "gap"
    assert fit_image_compare_layout(3.20).stage == "element"
    _must_fail(lambda: fit_image_compare_layout(2.30), "最小設定")

    invalid = deepcopy(deck)
    del invalid["slides"][0]["right"]
    assert any('"right"' in error for error in validate(invalid))

    invalid = deepcopy(deck)
    invalid["slides"][0]["left"]["image"] = "images/missing.png"
    assert any("left.image" in error and "assets/にありません" in error
               for error in validate(invalid))

    invalid = deepcopy(deck)
    invalid["slides"][0]["right"]["image"] = "../../outside.png"
    assert any("assets内" in error for error in validate(invalid))

    invalid = deepcopy(deck)
    invalid["slides"][0]["fit"] = "stretch"
    assert any("contain" in error for error in validate(invalid))

    invalid = deepcopy(deck)
    invalid["slides"][0]["shadow"] = "yes"
    assert any("true または false" in error for error in validate(invalid))

    invalid = deepcopy(deck)
    invalid["slides"][0]["left"]["caption"] = "説明"
    assert any("left" in error and "caption" in error for error in validate(invalid))

    print("image_compare slide tests passed")


class CompareQualityTests(unittest.TestCase):
    def test_label_rule_clearance_survives_all_fit_stages(self):
        """1〜3行と圧縮時も、保存された固定行送り・罫線・画像の間隔を照合する。"""
        prs = Presentation()
        prs.slide_width = Inches(generate.SLIDE_W)
        prs.slide_height = Inches(generate.SLIDE_H)
        for count in (1, 2, 3):
            labels = ("\n".join(("変更前の受付一覧", "対応状況と担当者の確認", "表示条件の比較")[:count]), "変更後")
            for stage, available in (("standard", 5.27),
                                     ("gap", 3.148 + count * 20.8 / 72),
                                     ("element", 2.368 + count * 17.6 / 72)):
                with self.subTest(lines=count, stage=stage):
                    fitted = fit_image_compare_layout(available, labels)
                    self.assertEqual(fitted.stage, stage)
                    v = fitted.values
                    self.assertAlmostEqual(v["marker_h"], count * v["line_pitch"] / 72)
                    if stage == "element":
                        self.assertEqual(v["label_size"], 11)
                    spec = {"type": "image_compare", "kicker": "比較", "title": "画像比較",
                            "left": {"image": "images/pptxdsl-repository.png", "label": labels[0]},
                            "right": {"image": "images/pptxdsl-repository.png", "label": labels[1]}}
                    slide = prs.slides.add_slide(prs.slide_layouts[6])
                    area = generate.ContentArea(bottom=generate.BODY_TOP + available)
                    with patch.object(image_slide, "header", return_value=area):
                        s_image_compare(slide, spec, 1)
                    shapes = {s.name: s for s in slide.shapes}
                    pictures = [s for s in slide.shapes if s.name == COMPARE_PICTURE_NAME]
                    self.assertEqual(pictures[0].top, pictures[1].top)
                    for i, picture in enumerate(pictures):
                        label = shapes[f"image-compare:label:{i}"]
                        rule = shapes[f"image-compare:rule:{i}"]
                        self.assertGreaterEqual(rule.top - label.top - label.height,
                                                Inches(0.08) - 2)
                        self.assertGreaterEqual(picture.top - rule.top - rule.height,
                                                Inches(v["mid_gap"]) - 2)
                        self.assertLessEqual(picture.top + picture.height,
                                             Inches(area.bottom - v["bottom_pad"]) + 2)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "labels.pptx"
            prs.save(path)
            saved = Presentation(path)
            for slide in saved.slides:
                for shape in slide.shapes:
                    if shape.name.startswith("image-compare:label:"):
                        for paragraph in shape.text_frame.paragraphs:
                            size = paragraph.runs[0].font.size.pt
                            self.assertEqual(paragraph.line_spacing, Pt(size * 1.6))
                            self.assertEqual(paragraph.space_before, Pt(0))
                            self.assertEqual(paragraph.space_after, Pt(0))
        with self.assertRaises(FitError):
            fit_image_compare_layout(2.368 + 3 * 17.6 / 72 - 0.02,
                                     ("確認前\n確認中\n確認後", "変更後"))
        if os.environ.get("PPTXDSL_COMPARE_LABEL_QA_OUT"):
            destination = Path(os.environ["PPTXDSL_COMPARE_LABEL_QA_OUT"])
            destination.parent.mkdir(parents=True, exist_ok=True)
            prs.save(destination)

    def test_automatic_wrap_uses_the_same_fixed_line_pitch(self):
        text = "変更前の受付一覧と対応状況および担当者ごとの処理状況の確認" * 2
        fitted = fit_image_compare_layout(5.27, (text, "変更後"))
        lines = image_slide._comparison_label_lines(text, fitted.values["label_size"])
        self.assertIn(len(lines), (2, 3))
        self.assertAlmostEqual(fitted.values["marker_h"], len(lines) * 20.8 / 72)

    def test_long_labels_are_measured_and_dense_labels_stop(self):
        labels = ("変更前の画面\n表示条件を選択する前", "変更後")
        fitted = fit_image_compare_layout(5.27, labels)
        self.assertGreater(fitted.values["marker_h"], 0.4)
        with self.assertRaises(FitError):
            fit_image_compare_layout(5.27, ("非常に長い見出し" * 100, "変更後"))
        with self.assertRaises(FitError):
            fit_image_compare_layout(5.27, ("X" * 200, "変更後"))

    def test_aspect_ratios_labels_and_footnote(self):
        prs = Presentation()
        prs.slide_width = Inches(generate.SLIDE_W)
        prs.slide_height = Inches(generate.SLIDE_H)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # 自前の格子素材で端の欠落・変形を検出する。既存画像の加工はしない。
            for name, size in (("wide", (1200, 600)), ("portrait", (500, 1000))):
                image = Image.new("RGB", size, "#dfeae7")
                draw = ImageDraw.Draw(image)
                draw.rectangle((2, 2, size[0] - 3, size[1] - 3), outline="#0d7870", width=10)
                for x in range(100, size[0], 100):
                    draw.line((x, 0, x, size[1]), fill="#718d92", width=2)
                for y in range(100, size[1], 100):
                    draw.line((0, y, size[0], y), fill="#718d92", width=2)
                image.save(root / (name + ".png"))
            for index, (left, right, fit, decorated) in enumerate((
                ("wide", "wide", "contain", False),
                ("portrait", "portrait", "contain", False),
                ("wide", "portrait", "contain", False),
                ("portrait", "wide", "cover", False),
                ("wide", "wide", "contain", True),
                ("wide", "portrait", "cover", True),
            ), 1):
                slide = prs.slides.add_slide(prs.slide_layouts[6])
                spec = {"type": "image_compare", "kicker": "画像比較の回帰検証", "title": "画像比率とラベル",
                        "left": {"image": left, "label": "変更前\n比較対象の基準"},
                        "right": {"image": right, "label": "変更後"},
                        "fit": fit, "shadow": decorated}
                if decorated:
                    spec.update(lead="画像端の表示と左右の上端を確認します。",
                                footnote={"text": "画像比較の検証用格子です。"})
                with patch.object(image_slide, "resolve_image_path", side_effect=lambda p: root / (p + ".png")):
                    generate.render_slide(s_image_compare, slide, spec, index)
                pictures = [s for s in slide.shapes if s.name == COMPARE_PICTURE_NAME]
                self.assertEqual(len(pictures), 2)
                self.assertEqual(pictures[0].top, pictures[1].top)
                for picture, key in zip(pictures, (left, right)):
                    self.assertLessEqual((picture.top + picture.height) / 914400, generate.BODY_BOTTOM)
                    if fit == "contain":
                        expected = 2 if key == "wide" else 0.5
                        self.assertAlmostEqual(picture.width / picture.height, expected, places=4)
                        self.assertEqual(picture.crop_left + picture.crop_top + picture.crop_right + picture.crop_bottom, 0)
                if left == "portrait" and fit == "contain" and not decorated:
                    self.assertGreater(pictures[0].height / 914400, 4)
                labels = [s for s in slide.shapes if s.name.startswith("image-compare:label:")]
                self.assertEqual(labels[0].height, labels[1].height)
                self.assertFalse(labels[0].text_frame.word_wrap)
                self.assertEqual(labels[0].text_frame.text, "変更前\n比較対象の基準")
            output = root / "compare.pptx"
            prs.save(output)
            self.assertEqual(check(output), [])
            if os.environ.get("PPTXDSL_COMPARE_QA_OUT"):
                destination = Path(os.environ["PPTXDSL_COMPARE_QA_OUT"])
                destination.parent.mkdir(parents=True, exist_ok=True)
                prs.save(destination)


if __name__ == "__main__":
    main()
    unittest.main()
