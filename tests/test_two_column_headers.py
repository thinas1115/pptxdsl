"""選択された2カラムの配色・配置と背景Configの保持を検証する。"""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches
from PIL import Image

from slidegen import generate
from slidegen.generation_context import bind_context, make_context
from slidegen.layout_fit import FitError


def spec():
    return {'type': 'two_column', 'kicker': '比較', 'title': '運用方式の比較',
            'left': {'label': '現状', 'heading': '導入前', 'bullets': ['担当者ごとに確認します。']},
            'right': {'label': '目標状態', 'heading': '導入後', 'bullets': ['共通の手順で確認します。']}}


def render(data):
    prs = Presentation()
    prs.slide_width = Inches(generate.SLIDE_W)
    prs.slide_height = Inches(generate.SLIDE_H)
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    generate.s_twocol(slide, data, 1)
    return slide


class TwoColumnHeaderTests(unittest.TestCase):
    def test_spacing_compression_precedes_font_shrink(self):
        data = spec()
        bullet = '比較する本文の説明を確認します。' * 4
        for side in ('left', 'right'):
            data[side]['bullets'] = [bullet] * 6
        text_w = (generate.BODY_W - .20 - 2 / 3) / 2 - .50
        height = max(.42, len(generate.wrap_text(bullet, text_w, 18))
                     * generate.line_height_in(18, 1.25) + .06)
        standard_used = 1.045 + 6 * height + 5 * .60
        actual_fit = generate.fit_vertical_stacks
        for expected, available in [('standard', standard_used + .01),
                                    ('gap', standard_used - .1),
                                    ('font', standard_used - 2.65)]:
            captured = []

            def capture(*args, **kwargs):
                result = actual_fit(*args, **kwargs)
                captured.append(result)
                return result

            with self.subTest(stage=expected), \
                    patch.object(generate, 'header', return_value=generate.ContentArea(
                        top=1, bottom=1 + available + .66)), \
                    patch.object(generate, 'fit_vertical_stacks', side_effect=capture):
                render(data)
                self.assertEqual(captured[0].stage, expected)
                self.assertGreaterEqual(captured[0].size, 11)

    def test_only_main_headings_and_reclaimed_space_with_and_without_lead(self):
        for lead in (None, '左右の状態を整理します。'):
            with self.subTest(lead=lead):
                data = spec()
                if lead:
                    data['lead'] = lead
                slide = render(data)
                texts = {s.text: s for s in slide.shapes if s.has_text_frame}
                area_top = generate.PAGE.content_top
                if lead:
                    area_top = (texts[lead].top + texts[lead].height) / Inches(1) + .14
                top = area_top + .50
                self.assertFalse({'現状', '目標状態', 'BEFORE', 'AFTER'} & texts.keys())
                for key, body in [('導入前', data['left']['bullets'][0]), ('導入後', data['right']['bullets'][0])]:
                    self.assertAlmostEqual(texts[key].top / Inches(1) - top, 0, places=5)
                    self.assertAlmostEqual(texts[body].top / Inches(1) - top, 1.045, places=5)
                    self.assertEqual(texts[key].text_frame.paragraphs[0].runs[0].font.size.pt, 21)
                    self.assertEqual(texts[body].text_frame.paragraphs[0].runs[0].font.size.pt, 18)
                    self.assertLess(texts[key].top + texts[key].height, texts[body].top)
                    self.assertLessEqual(texts[body].top + texts[body].height, Inches(generate.BODY_BOTTOM))

    def test_slide04_heading_rules_and_discreet_numbers_without_panels(self):
        data = spec()
        for side in ('left', 'right'):
            data[side]['bullets'] *= 3
        slide = render(data)
        # 見出し下の細い罫線だけを置き、帯・パネル・行ごとの線は置かない。
        rectangles = [s for s in slide.shapes
                      if (not s.has_text_frame or not s.text)
                      and s.width != Inches(generate.SLIDE_W)]
        self.assertEqual(len(rectangles), 2)
        for rule, color, heading in zip(rectangles, ('C9C6BE', '973F2B'), ('導入前', '導入後')):
            label = next(s for s in slide.shapes if s.has_text_frame and s.text == heading)
            self.assertEqual(rule.left, label.left)
            self.assertEqual(rule.width, label.width)
            self.assertAlmostEqual(rule.height / Inches(1), 1 / 96, places=5)
            self.assertAlmostEqual((rule.top - label.top) / Inches(1), 7 / 12, places=5)
            self.assertLess(label.top + label.height, rule.top)
            self.assertEqual(str(rule.fill.fore_color.rgb), color)
            self.assertNotIn('outerShdw', rule._element.xml)
        for heading, color in [('導入前', '666660'), ('導入後', '973F2B')]:
            shape = next(s for s in slide.shapes if s.has_text_frame and s.text == heading)
            self.assertEqual(str(shape.text_frame.paragraphs[0].runs[0].font.color.rgb), color)
        numbers = [s for s in slide.shapes if s.has_text_frame and s.text in {'01', '02', '03'}]
        self.assertEqual(len(numbers), 6)
        for number in numbers:
            self.assertEqual(number.text_frame.paragraphs[0].runs[0].font.size.pt, 13.5)
        for color in ('666660', '973F2B'):
            self.assertEqual(sum(str(s.text_frame.paragraphs[0].runs[0].font.color.rgb) == color
                                 for s in numbers), 3)

    def test_background_color_and_image_remain_config_owned(self):
        context = make_context({'meta': {}, 'slides': []})
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / 'background.png'
            Image.new('RGB', (32, 18), '#EFEFEF').save(image)
            for background_image in (None, image):
                config = replace(context.cover_footer, slide=replace(
                    context.cover_footer.slide, background_color=RGBColor.from_string('E9EEF2'),
                    background_image=background_image))
                with self.subTest(image=background_image is not None), \
                        bind_context(replace(context, cover_footer=config)):
                    slide = render(spec())
                    self.assertEqual(str(slide.shapes[0].fill.fore_color.rgb), 'E9EEF2')
                    images = [s for s in slide.shapes if s.name == generate.SLIDE_BACKGROUND_NAME]
                    self.assertEqual(len(images), int(background_image is not None))
                    # 背景画像も2カラムの色面で覆わない。
                    self.assertFalse(any(s.has_text_frame and not s.text
                                         and s.width != Inches(generate.SLIDE_W)
                                         and not s.name.startswith('two-column:heading-rule:')
                                         for s in slide.shapes))

    def test_legacy_labels_do_not_change_output_and_no_fallback_is_added(self):
        data = spec()
        without_labels = deepcopy(data)
        for side in ('left', 'right'):
            del without_labels[side]['label']
        self.assertEqual([s._element.xml for s in render(data).shapes],
                         [s._element.xml for s in render(without_labels).shapes])

    def test_body_uses_measured_breaks_instead_of_powerpoint_auto_wrap(self):
        data = spec()
        body = 'グラフや表の貼り付け後に、余白・フォント・禁則を手作業で直す'
        data['left']['bullets'] = [body]
        slide = render(data)
        shape = next(s for s in slide.shapes
                     if s.has_text_frame and s.text.replace('\n', '') == body)
        width = (generate.BODY_W - .20 - 2 / 3) / 2 - .50
        self.assertEqual(shape.text.split('\n'), generate.wrap_text(body, width, 18))
        self.assertFalse(shape.text_frame.word_wrap)

    def test_overfull_body_still_stops(self):
        data = spec()
        data['left']['bullets'] = ['長すぎる本文の収容限界を確認します。' * 100] * 6
        with self.assertRaises(FitError):
            render(data)


if __name__ == '__main__':
    unittest.main()
