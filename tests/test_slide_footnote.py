"""旧補足入力はノートに保持し、スライドを占有しない。"""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pptx import Presentation

from slidegen import generate
from slidegen.check_layout import check
from slidegen.generate_from_json import RENDER, build_presentation
from slidegen.validate_content import validate
from tests.fixtures.gallery.content_patterns import PATTERN_DECK


class SlideFootnoteTests(unittest.TestCase):
    def test_all_types_keep_notes_without_reserving_space(self):
        specimens = {spec['type']: deepcopy(spec) for spec in PATTERN_DECK['slides']}
        self.assertEqual(set(specimens), set(RENDER))
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'notes.pptx'
            for kind, spec in specimens.items():
                with self.subTest(type=kind):
                    spec.pop('footnote', None)
                    deck = {'meta': {'title': '補足の互換検証'}, 'slides': [spec]}
                    plain = build_presentation(deck, allow_sample_content=True)
                    spec['footnote'] = {'label': '注意', 'text': '説明に必要な補足情報。'}
                    noted = build_presentation(deck, allow_sample_content=True)
                    geometry = lambda slide: [(s.name, s.left, s.top, s.width, s.height)
                                              for s in slide.shapes]
                    self.assertEqual(geometry(plain.slides[0]), geometry(noted.slides[0]))
                    self.assertFalse(any(s.name.startswith('slide-footnote:')
                                         for s in noted.slides[0].shapes))
                    noted.save(path)
                    reopened = Presentation(path)
                    self.assertIn('補足（注意）\n説明に必要な補足情報。',
                                  reopened.slides[0].notes_slide.notes_text_frame.text)
                    self.assertFalse(check(path))

    def test_existing_notes_are_preserved(self):
        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        slide.notes_slide.notes_text_frame.text = '既存の出典記録'
        generate.render_slide(lambda *_: None, slide,
                              {'type': 'bullets', 'footnote': {'text': '補足本文'}}, 1)
        self.assertEqual(slide.notes_slide.notes_text_frame.text,
                         '既存の出典記録\n補足\n補足本文')

    def test_invalid_legacy_notes_are_rejected(self):
        spec = deepcopy(next(s for s in PATTERN_DECK['slides'] if s['type'] == 'bullets'))
        for value in ('誤った形式', {}, {'text': ''}, {'text': '補足', 'label': ''},
                      {'text': '補足', 'x': 1}):
            with self.subTest(value=value):
                spec['footnote'] = value
                self.assertTrue(validate({'meta': {'title': '検証'}, 'slides': [spec]},
                                         allow_sample_content=True))


if __name__ == '__main__':
    unittest.main()
