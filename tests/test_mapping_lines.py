"""対応関係図の中央接続、局所交差処理と不要な下線の不在を確認する。"""
from copy import deepcopy
import math
import unittest

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Inches

from slidegen import generate
from slidegen.candidate_renderers import (
    _mapping_crossing_segments, _mapping_ports, s_mapping,
)
from tests.fixtures.gallery.content_patterns import PATTERN_DECK


class MappingLineTests(unittest.TestCase):
    def test_fan_out_and_fan_in_use_shared_centers(self):
        positions = {f'n{i}': i * .71 for i in range(6)}
        links = ([{'from': 'n0', 'to': f'n{i}'} for i in range(6)]
                 + [{'from': f'n{i}', 'to': 'n5'} for i in range(1, 6)])
        for link, (sy, ty) in zip(links, _mapping_ports(positions, positions, .58, links)):
            self.assertAlmostEqual(sy, positions[link['from']] + .29)
            self.assertAlmostEqual(ty, positions[link['to']] + .29)
            if link['from'] == link['to']:
                self.assertEqual(sy, ty)

    def test_shared_endpoints_are_not_masked(self):
        for endpoints in ([(1, 1), (1, 2)], [(1, 2), (2, 2)]):
            self.assertEqual(list(_mapping_crossing_segments(0, 3, endpoints, 1)), [])

    def test_unrelated_crossing_has_only_a_short_local_mask(self):
        segments = list(_mapping_crossing_segments(0, 3, [(1, 2), (2, 1)], 1))
        self.assertEqual(len(segments), 1)
        previous, (x1, y1, x2, y2) = segments[0]
        self.assertEqual(previous, 0)
        self.assertAlmostEqual((x1 + x2) / 2, 1.5)
        self.assertAlmostEqual((y1 + y2) / 2, 1.5)
        self.assertAlmostEqual(math.hypot(x2 - x1, y2 - y1), .09)

    def test_rendered_lines_match_boxes_and_no_partial_underlines(self):
        data = deepcopy(next(s for s in PATTERN_DECK['slides'] if s['type'] == 'relationship_map'))
        prs = Presentation()
        prs.slide_width, prs.slide_height = Inches(generate.SLIDE_W), Inches(generate.SLIDE_H)
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        s_mapping(slide, data, 1)
        shapes = {s.name: s for s in slide.shapes}
        for index, link in enumerate(data['links']):
            arrow = shapes[f'mapping:link:{index}']
            source = shapes[f"mapping:item:left:{link['from']}"]
            target = shapes[f"mapping:item:right:{link['to']}"]
            self.assertAlmostEqual(arrow.begin_y, source.top + source.height / 2, delta=2)
            self.assertAlmostEqual(arrow.end_y, target.top + target.height / 2, delta=2)
            self.assertEqual(arrow.begin_x, source.left + source.width)
            self.assertEqual(arrow.end_x, target.left)
        ports = [s for s in slide.shapes if s.name.startswith('mapping:port:')]
        self.assertEqual(len(ports), len(data['left_items']) + len(data['right_items']))
        for shape in slide.shapes:
            if shape.shape_type == MSO_SHAPE_TYPE.LINE:
                self.assertNotEqual(shape.line.color.rgb, generate.RULE)
        self.assertFalse(any(s.name.startswith('mapping:crossing-mask:') for s in slide.shapes))


if __name__ == '__main__':
    unittest.main()
