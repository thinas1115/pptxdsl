"""2カラムの見出し一本化と、その分だけ詰めた配置を検証する。"""
from copy import deepcopy
import unittest
from unittest.mock import patch

from pptx import Presentation
from pptx.util import Inches

from slidegen import generate
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
        height = max(.42, len(generate.wrap_text(bullet, 4.6, 14))
                     * generate.line_height_in(14, 1.18) + .06)
        standard_used = 1.28 + 6 * height + 5 * .18
        actual_fit = generate.fit_vertical_stacks
        for expected, available in [('standard', standard_used + .01),
                                    ('gap', standard_used - .1),
                                    ('font', standard_used - .45)]:
            captured = []

            def capture(*args, **kwargs):
                result = actual_fit(*args, **kwargs)
                captured.append(result)
                return result

            with self.subTest(stage=expected), \
                    patch.object(generate, 'header', return_value=generate.ContentArea(
                        top=1, bottom=1 + available + .42)), \
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
                panel = next(s for s in slide.shapes if abs(s.left - Inches(.76)) < 2)
                self.assertFalse({'現状', '目標状態', 'BEFORE', 'AFTER'} & texts.keys())
                for key, body in [('導入前', data['left']['bullets'][0]), ('導入後', data['right']['bullets'][0])]:
                    self.assertAlmostEqual((texts[key].top - panel.top) / Inches(1), .29, places=5)
                    self.assertAlmostEqual((texts[body].top - panel.top) / Inches(1), .99, places=5)
                    self.assertLess(texts[key].top + texts[key].height, texts[body].top)
                    self.assertLessEqual(texts[body].top + texts[body].height, panel.top + panel.height)

    def test_legacy_labels_do_not_change_output_and_no_fallback_is_added(self):
        data = spec()
        without_labels = deepcopy(data)
        for side in ('left', 'right'):
            del without_labels[side]['label']
        self.assertEqual([s._element.xml for s in render(data).shapes],
                         [s._element.xml for s in render(without_labels).shapes])

    def test_overfull_body_still_stops(self):
        data = spec()
        data['left']['bullets'] = ['長すぎる本文の収容限界を確認します。' * 100] * 6
        with self.assertRaises(FitError):
            render(data)


if __name__ == '__main__':
    unittest.main()
