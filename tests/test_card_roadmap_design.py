"""用途別カード、バー起点のテーマ、収容段階と最小値停止を検証する。"""

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pptx import Presentation
from pptx.util import Inches

from slidegen import generate
from slidegen.check_layout import check
from slidegen.layout_fit import FitError
from slidegen.layout_settings import ROADMAP
from slidegen.timeline_layout import plan_program_roadmap
from tools.gallery.generate_card_roadmap_cases import main, make_deck


class CardRoadmapDesignTests(unittest.TestCase):
    def test_sixteen_cases_pass_layout_and_styles_have_distinct_hierarchy(self):
        data = make_deck()
        self.assertEqual(len(data["slides"]), 16)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "cases.pptx"
            main(output)
            self.assertFalse(check(output))
            for slide, spec in zip(Presentation(output).slides, data["slides"]):
                if spec["type"] != "cards":
                    continue
                panels = [shape for shape in slide.shapes if shape.name.startswith("cards:editorial:panel:")]
                if spec["style"] == "editorial":
                    self.assertEqual(len(panels), len(spec["cards"]))
                    shapes = {shape.name: shape for shape in slide.shapes}
                    for index, panel in enumerate(panels):
                        for role, minimum in (("heading", 13), ("body", 11)):
                            shape = shapes[f"cards:editorial:{role}:{index}"]
                            self.assertGreater(shape.left, panel.left)
                            self.assertGreaterEqual(shape.top, panel.top)
                            self.assertLess(shape.left + shape.width, panel.left + panel.width)
                            self.assertLess(shape.top + shape.height, panel.top + panel.height)
                            self.assertGreaterEqual(shape.text_frame.paragraphs[0].runs[0].font.size.pt, minimum)
                    numbers = [shape.text for shape in slide.shapes if shape.has_text_frame
                               and generate.BODY_TOP < shape.top.inches < generate.BODY_BOTTOM]
                    self.assertFalse(set(numbers) & {f"{number:02d}" for number in range(1, 7)})
                else:
                    self.assertFalse(panels)
                    values = {card["value"] for card in spec["cards"]}
                    large_values = [shape for shape in slide.shapes if shape.has_text_frame and shape.text in values]
                    self.assertEqual(len(large_values), len(values))
                    self.assertTrue(all(shape.text_frame.paragraphs[0].runs[0].font.size.pt >= 22 for shape in large_values))

    def test_editorial_uses_gap_and_font_before_explicit_stop(self):
        spec = deepcopy(make_deck()["slides"][3])
        for card in spec["cards"]:
            card["body"] = "判断に必要な情報を確認し、対象と条件を明確にしてから次の作業へ進みます。"
        observed, stopped = set(), False
        original = generate.fit_vertical_stacks

        def capture(*args, **kwargs):
            fitted = original(*args, **kwargs)
            observed.add(fitted.stage)
            self.assertGreaterEqual(fitted.size, 11)
            return fitted

        for step in range(95):
            area = generate.ContentArea(1.58, 1.58 + 5.27 - step * .03)
            prs = Presentation()
            prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
            slide = prs.slides.add_slide(prs.slide_layouts[6])
            with patch.object(generate, "header", return_value=area), patch.object(generate, "fit_vertical_stacks", side_effect=capture):
                try:
                    generate.s_cards(slide, spec, 1)
                except FitError:
                    stopped = True
        self.assertEqual(observed, {"standard", "gap", "font"})
        self.assertTrue(stopped)

    def test_delayed_theme_starts_at_first_bar_and_goal_has_dedicated_lane(self):
        spec = {"periods": ["前期", "中期", "後期"], "tracks": [{
            "name": "試行", "goal": "結果の記録", "activities": [
                {"label": "受付", "start": 1, "end": 2},
                {"label": "照合", "start": 1.5, "end": 3},
            ]}]}
        plan = plan_program_roadmap(spec, generate.ContentArea(1.58, 6.85))
        theme = plan.themes[0]
        first, second = plan.activities[0]
        self.assertAlmostEqual(plan.grid_x, ROADMAP.label_x)
        self.assertAlmostEqual(theme.x, first.x1)
        self.assertGreater(theme.x, plan.grid_x)
        self.assertGreater(theme.goal_y, theme.y)
        self.assertGreater(second.lane_top, theme.goal_y)
        self.assertLess(plan.bottom, 6.85)
        with self.assertRaises(FitError):
            plan_program_roadmap(spec, generate.ContentArea(1.58, 2.0))

    def test_short_first_bar_gets_own_lane_without_losing_goal_or_milestone(self):
        spec = {"periods": [str(index) for index in range(12)], "tracks": [{
            "name": "短期作業", "goal": "結果の確認",
            "milestone": {"at": 6, "label": "完了"},
            "activities": [
                {"label": "半月作業", "start": 4.25, "end": 4.75},
                {"label": "後続作業", "start": 5, "end": 6},
            ]}]}
        original = deepcopy(spec)
        plan = plan_program_roadmap(spec, generate.ContentArea(1.58, 6.85))
        first, following = plan.activities[0]
        self.assertAlmostEqual(plan.themes[0].x, first.x1)
        self.assertGreater(following.lane_top, plan.themes[0].goal_y)
        self.assertGreater(plan.milestones[0].y, following.lane_top)
        self.assertLess(plan.bottom, 6.85)
        self.assertEqual(spec, original)
        with self.assertRaises(FitError):
            plan_program_roadmap(spec, generate.ContentArea(1.58, 2.5))


if __name__ == "__main__":
    unittest.main()
