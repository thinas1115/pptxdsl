"""共通フレームの余白、濃色lead、会社表記の位置を検証する。"""
import unittest

from pptx import Presentation
from pptx.util import Inches

from slidegen import generate
from slidegen.cover_footer import parse_cover_footer_config, render_footer
from slidegen.layout_settings import PAGE
from slidegen.layout_fit import FitError


def new_slide():
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(generate.SLIDE_W), Inches(generate.SLIDE_H)
    return prs.slides.add_slide(prs.slide_layouts[6])


class CleanSlideFrameTests(unittest.TestCase):
    def test_no_kicker_and_reclaimed_header_space(self):
        slide = new_slide()
        area = generate.header(slide, '表示しない分類', '資料の構成')
        self.assertFalse(any(getattr(s, 'text', '') == '表示しない分類' for s in slide.shapes))
        title = next(s for s in slide.shapes if s.name == 'slide-header:title')
        self.assertLess(title.top, Inches(.4))
        self.assertEqual(area.top, PAGE.content_top)
        self.assertGreaterEqual(Inches(area.top), title.top + title.height)
        self.assertTrue(area.shifted)
        self.assertAlmostEqual(area.map_y(generate.BODY_TOP), area.top)
        self.assertAlmostEqual(area.map_y(generate.BODY_BOTTOM), area.bottom)

    def test_lead_is_dark_and_has_explicit_line_height(self):
        slide = new_slide()
        area = generate.header(slide, '分類', '資料の構成', '説明に必要な本文を明瞭に表示します。')
        lead = next(s for s in slide.shapes if s.name == 'slide-header:lead')
        paragraph = lead.text_frame.paragraphs[0]
        self.assertEqual(paragraph.runs[0].font.color.rgb, generate.TEXT)
        self.assertEqual(paragraph.runs[0].font.size.pt, 18)
        self.assertAlmostEqual(paragraph.line_spacing.pt, 25.2)
        self.assertLessEqual(lead.top + lead.height, Inches(area.top))
        self.assertLess(area.top, 1.7)

    def test_two_line_lead_keeps_readable_size_and_overfull_lead_stops(self):
        slide = new_slide()
        area = generate.header(slide, '分類', '資料の構成',
                               '説明文の意味と読みやすさを確認します。\n資料全体で文字の大きさを揃えます。')
        lead = next(s for s in slide.shapes if s.name == 'slide-header:lead')
        self.assertEqual(len(lead.text_frame.paragraphs), 2)
        self.assertTrue(all(p.runs[0].font.size.pt == 18 for p in lead.text_frame.paragraphs))
        self.assertLessEqual(lead.top + lead.height, Inches(area.top))
        with self.assertRaises(FitError):
            generate.header(new_slide(), '分類', '資料の構成', '説明文が長すぎます。' * 200)

    def test_watermark_and_page_share_vertical_geometry_below_rule(self):
        for show_total in (False, True):
            with self.subTest(show_total=show_total):
                slide = new_slide()
                config = parse_cover_footer_config({'footer': {
                    'text': '© Example Company', 'show_divider': True, 'show_total': show_total}})
                render_footer(slide, 2, {}, 4, config,
                              add_text=generate.add_text, add_rect=generate.add_rect)
                self.assertEqual(len(slide.shapes), 3)
                shapes = {s.name: s for s in slide.shapes}
                watermark, page = shapes['slide-footer:watermark'], shapes['slide-footer:page']
                rule = shapes['slide-footer:rule']
                self.assertEqual((rule.left, rule.top, rule.width, rule.height),
                                 tuple(Inches(value) for value in (.72, 6.92, 11.9, .01)))
                self.assertLess(rule.top + rule.height, watermark.top)
                self.assertEqual((watermark.top, watermark.height), (page.top, page.height))
                self.assertEqual(watermark.text_frame.paragraphs[0].runs[0].font.size.pt, 11)
                self.assertFalse(watermark.text_frame.word_wrap)

    def test_rule_can_be_hidden_from_config(self):
        slide = new_slide()
        render_footer(slide, 1, {}, 4, parse_cover_footer_config({'footer': {'show_divider': False}}),
                      add_text=generate.add_text, add_rect=generate.add_rect)
        self.assertEqual([s.name for s in slide.shapes], ['slide-footer:page'])

    def test_two_line_title_and_lead_do_not_overlap_and_overfull_title_stops(self):
        slide = new_slide()
        area = generate.header(slide, '分類', '設計判断に必要な情報' * 7, '本文の読み方を確認します。')
        title = next(s for s in slide.shapes if s.name == 'slide-header:title')
        lead = next(s for s in slide.shapes if s.name == 'slide-header:lead')
        self.assertIn('\n', title.text)
        self.assertGreaterEqual(lead.top, title.top + title.height)
        self.assertGreaterEqual(Inches(area.top), lead.top + lead.height)
        self.assertGreaterEqual(title.text_frame.paragraphs[0].runs[0].font.size.pt, 16)
        with self.assertRaises(FitError):
            generate.header(new_slide(), '分類', '設計判断に必要な情報' * 200)

    def test_no_invented_company_text(self):
        slide = new_slide()
        render_footer(slide, 1, {'footer': '旧フッターの説明文'}, 4, parse_cover_footer_config({}),
                      add_text=generate.add_text, add_rect=generate.add_rect)
        self.assertEqual([s.name for s in slide.shapes], ['slide-footer:rule', 'slide-footer:page'])


if __name__ == '__main__':
    unittest.main()
