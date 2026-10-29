"""本文背景・表紙・フッターをひとつの設定で変更する。"""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import tempfile
import unittest

from PIL import Image, ImageDraw

from slidegen.check_layout import check
from slidegen.cover_footer import SLIDE_BACKGROUND_NAME, parse_cover_footer_config
from slidegen.generate_from_json import build_presentation
from slidegen.template_config import create_template
from slidegen import generate


def deck():
    return {"meta": {"title": "運用会議", "footer": "社内確認用"}, "slides": [
        {"type": "title", "title": "運用会議", "subtitle": "実施条件の確認"},
        {"type": "section_divider", "kicker": "第1章", "title": "確認項目"},
        {"type": "bullets", "kicker": "条件", "title": "適用範囲",
         "bullets": [{"text": "対象部門と担当範囲を確認します。"}]}]}


class TemplateConfigTests(unittest.TestCase):
    def test_defaults_and_legacy_config_match(self):
        default = build_presentation(deck())
        legacy = build_presentation(deck(), parse_cover_footer_config({"footer": {"text": "{footer}"}}))
        self.assertEqual([s._element.xml for s in default.slides], [s._element.xml for s in legacy.slides])

    def test_create_and_apply_all_sections_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            body = Image.new("RGB", (1600, 900), "white")
            ImageDraw.Draw(body).rectangle((1450, 10, 1570, 40), fill="#0d7870")
            body.save(root / "body.png")
            Image.new("RGB", (1600, 900), "#182c43").save(root / "cover.png")
            output = root / "config/template.json"
            create_template(output, background_color="FFFFFF", background_image=root / "body.png",
                            cover_background_image=root / "cover.png", footer_text="検証用 / {footer}")
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["slide"]["background_image"], "../body.png")
            self.assertEqual(data["cover"]["background_image"], "../cover.png")
            original = output.read_bytes()
            with self.assertRaises(ValueError):
                create_template(output)
            self.assertEqual(output.read_bytes(), original)
            prs = build_presentation(deck(), output)
            for slide in list(prs.slides)[1:]:
                self.assertEqual(str(slide.shapes[0].fill.fore_color.rgb), "FFFFFF")
                background = next(s for s in slide.shapes if s.name == SLIDE_BACKGROUND_NAME)
                self.assertEqual(background.image.blob, (root / "body.png").read_bytes())
                self.assertIn("検証用 / 社内確認用", "\n".join(s.text for s in slide.shapes if s.has_text_frame))
            destination = root / "template.pptx"
            prs.save(destination)
            self.assertEqual(check(destination), [])
            if os.environ.get("PPTXDSL_TEMPLATE_QA_OUT"):
                output = Path(os.environ["PPTXDSL_TEMPLATE_QA_OUT"])
                output.parent.mkdir(parents=True, exist_ok=True)
                prs.save(output)

    def test_invalid_settings_leave_no_file(self):
        for data in ({"slide": {"background_color": "red"}}, {"slide": {"font": 20}},
                     {"slide": {"background_image": "/private/image.png"}},
                     {"slide": {"background_image": "C:private.png"}}, {"slide": []}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                parse_cover_footer_config(data)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "config.json"
            with self.assertRaises(ValueError):
                create_template(output, background_color="wrong")
            self.assertFalse(output.exists())

    def test_parallel_backgrounds_are_isolated(self):
        def build(color):
            config = parse_cover_footer_config({"slide": {"background_color": color}})
            prs = build_presentation(deck(), config)
            return str(prs.slides[2].shapes[0].fill.fore_color.rgb)
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(list(pool.map(build, ("FFFFFF", "F0F8FF"))), ["FFFFFF", "F0F8FF"])
        self.assertEqual(str(build_presentation(deck()).slides[2].shapes[0].fill.fore_color.rgb), "F7F5EF")

    def test_canvas_masks_follow_the_background_not_the_text_color(self):
        def renderer(slide, spec, page):
            generate.header(slide, spec["kicker"], spec["title"])
            mask = generate.add_rect(slide, 1, 3, 2, 0.5, generate.CANVAS)
            mask.name = "mask"
        config = parse_cover_footer_config({"slide": {"background_color": "FFFFFF"}})
        prs = build_presentation(deck(), config, renderers={**generate.RENDER, "bullets": renderer})
        mask = next(s for s in prs.slides[2].shapes if s.name == "mask")
        self.assertEqual(str(mask.fill.fore_color.rgb), "FFFFFF")
        self.assertEqual(str(generate.CANVAS), "F7F5EF")


if __name__ == "__main__":
    unittest.main()
