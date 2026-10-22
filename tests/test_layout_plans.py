"""PPTXや図形を作らず配置、接続、収容段階、入力の非破壊性を確認する。"""
from copy import deepcopy
from dataclasses import dataclass
import unittest
from unittest.mock import patch

from slidegen.layout_fit import FitError, fit_rows, select_payload_fit
from slidegen.layout_settings import PAGE, ROADMAP, SWIMLANE
from slidegen.network_layout import plan_network
from slidegen.protocol_state_layout import plan_protocol_state_flow, protocol_candidates
from slidegen.swimlane_layout import edge_path, plan_swimlane
from slidegen.timeline_layout import plan_program_roadmap


@dataclass(frozen=True)
class Area:
    top: float = 1.58
    bottom: float = 6.85

    @property
    def height(self):
        return self.bottom - self.top


def network():
    return {
        "lanes": [{"id": "a", "label": "系統 A"}, {"id": "b", "label": "系統 B"}],
        "columns": [{"id": name} for name in ("c1", "c2", "c3")],
        "nodes": [{"id": "n1", "column": "c1", "lanes": ["a", "b"]},
                  {"id": "n2", "column": "c2", "lanes": ["a", "b"]},
                  {"id": "n3", "column": "c3", "lanes": ["a"]}],
        "links": [{"from": "n1", "to": "n2", "kind": "trunk", "lanes": ["a", "b"]},
                  {"from": "n1", "to": "n2", "kind": "broadcast", "lanes": ["a"]},
                  {"from": "n1", "to": "n3", "kind": "broadcast", "lanes": ["a"]},
                  {"from": "n3", "to": "n2", "kind": "blocked", "label": "停止"}],
    }


def swimlane():
    return {
        "lanes": [{"id": name, "label": name} for name in ("受付", "管理", "確認")],
        "stages": [{"id": name} for name in ("s1", "s2")],
        "steps": [{"id": "a", "lane": "受付", "stage": "s1", "name": "登録"},
                  {"id": "b", "lane": "確認", "stage": "s2", "name": "点検"}],
        "edges": [{"from": "a", "to": "b"}, {"from": "b", "to": "a", "kind": "feedback"}],
    }


def protocol():
    return {
        "stages": [{"id": name, "label": "接続先の状態と付加ヘッダの変化" * 2}
                   for name in ("a", "b", "c", "d", "e", "f")],
        "flows": [{"label": f"通信{index}", "states": [
            {"stage": name, "label": "値A" if name in "ab" else "値B", "detail": "処理の内容"}
            for name in reversed("abcdef")]} for index in range(2)],
    }


def roadmap():
    return {"periods": ["初期", "中期", "後期"], "tracks": [{
        "activities": [{"label": "計画", "start": 0, "end": 1},
                       {"label": "実施", "start": 1, "end": 2},
                       {"label": "点検", "start": .5, "end": 2.25}],
        "milestone": {"label": "完了", "at": 3},
    }]}


class LayoutPlanTests(unittest.TestCase):
    def test_no_shape_creation_and_no_input_mutation(self):
        for make_spec, planner in ((network, plan_network), (swimlane, plan_swimlane),
                                   (protocol, plan_protocol_state_flow), (roadmap, plan_program_roadmap)):
            spec = make_spec()
            original = deepcopy(spec)
            with self.subTest(planner=planner.__name__), patch("pptx.Presentation", side_effect=AssertionError("描画禁止")):
                result = planner(spec, Area())
                self.assertIsNotNone(result)
                self.assertEqual(spec, original)
                self.assertEqual(result, planner(spec, Area()))

    def test_network_trunk_broadcast_and_stop_have_explicit_paths(self):
        plan = plan_network(network(), Area())
        trunk, stopped = plan.links
        self.assertEqual(trunk.kind, "trunk")
        self.assertEqual([segment[2] for segment in trunk.trunk_lanes], ["a", "b"])
        self.assertIsNotNone(trunk.physical)
        self.assertEqual(len(plan.broadcasts), 1)
        self.assertEqual(len(plan.broadcasts[0].ends), 2)
        self.assertEqual(stopped.kind, "blocked")
        self.assertEqual(len(stopped.points), 3)
        self.assertIsNotNone(stopped.stop)
        self.assertLess(stopped.points[-1][1], stopped.stop[1])

    def test_network_rejects_three_devices_in_one_cell(self):
        spec = network()
        spec["nodes"] = [dict(spec["nodes"][0], id=f"n{index}") for index in range(3)]
        spec["links"] = []
        with self.assertRaisesRegex(FitError, "同じ列"):
            plan_network(spec, Area())

    def test_swimlane_feedback_keeps_dedicated_bottom_channel(self):
        plan = plan_swimlane(swimlane(), Area())
        self.assertTrue(plan.show_line_legend)
        self.assertEqual(len(plan.paths[0]), 4)
        self.assertEqual(len(plan.paths[1]), 8)
        self.assertLessEqual(max(y for _x, y in plan.paths[1]), SWIMLANE.body_bottom - .08)
        for x, y, width, height in plan.rects.values():
            self.assertGreaterEqual(x, plan.x0)
            self.assertGreaterEqual(y, plan.lane_y0)
            self.assertGreater(width, 0)
            self.assertGreater(height, 0)
        with self.assertRaises(FitError):
            plan_swimlane(swimlane(), Area(top=6.0))

    def test_swimlane_same_cell_adjacent_and_nonadjacent_lane_routes(self):
        rects = {"a": (2., 2., 1., .5), "b": (4., 2., 1., .5)}
        steps = {"a": {"stage": "s", "lane": "a"}, "b": {"stage": "s", "lane": "a"}}
        args = ({"from": "a", "to": "b"}, rects, {"s": 0}, {"a": 0, "b": 1, "c": 2}, steps, 1., 1., 5., 1.)
        self.assertEqual(edge_path(*args), [(3., 2.25), (4., 2.25)])
        steps["b"]["lane"] = "b"
        rects["b"] = (4., 3., 1., .5)
        self.assertEqual(len(edge_path(*args)), 4)
        steps["b"]["lane"] = "c"
        rects["b"] = (4., 4., 1., .5)
        self.assertEqual(len(edge_path(*args)), 5)

    def test_protocol_sorts_states_and_detects_value_not_detail_changes(self):
        plan = plan_protocol_state_flow(protocol(), Area())
        self.assertEqual([state["stage"] for state in plan.rows[0].states], list("abcdef"))
        self.assertEqual(plan.rows[0].changed, {"c"})
        self.assertLess(plan.rows[0].top, plan.rows[1].top)
        self.assertAlmostEqual(plan.rows[-1].top + plan.rows[-1].height, plan.rows_bottom)
        self.assertEqual(len(plan.fitted.values["row_heights"]), 2)
        with self.assertRaises(FitError):
            plan_protocol_state_flow(protocol(), Area(bottom=2.))

    def test_protocol_uses_all_fit_stages_before_explicit_stop(self):
        spec = protocol()
        candidates = list(protocol_candidates(spec["stages"], spec["flows"]))
        observed = set()
        for _stage, _values, used in candidates:
            area = Area(bottom=Area().top + used + .08 + .36 - .009)
            observed.add(plan_protocol_state_flow(spec, area).fitted.stage)
        self.assertEqual(observed, {"standard", "gap", "icon", "font"})

    def test_roadmap_packs_overlaps_and_keeps_markers_in_grid(self):
        plan = plan_program_roadmap(roadmap(), Area())
        self.assertEqual([item.placement.lane for item in plan.activities[0]], [0, 0, 1])
        self.assertEqual(plan.row_tops, [plan.top + plan.fitted.values["header_h"]])
        marker = plan.milestones[0]
        self.assertAlmostEqual(marker.x, plan.grid_x + ROADMAP.grid_width)
        self.assertLessEqual(marker.label_x + marker.label_width, plan.grid_x + ROADMAP.grid_width)
        for activity in plan.activities[0]:
            self.assertAlmostEqual(activity.label_x + activity.label_width / 2,
                                   (activity.x1 + activity.x2) / 2)
        with self.assertRaises(FitError):
            plan_program_roadmap(roadmap(), Area(bottom=1.8))
        for key, value in (("periods", ["a", "b"]), ("tracks", [])):
            spec = roadmap()
            spec[key] = value
            with self.assertRaises(FitError):
                plan_program_roadmap(spec, Area())

    def test_row_fit_stages_and_typed_payload_selection(self):
        def fit(height):
            return fit_rows("試験", height, 2, row_h=1., min_row_h=.65,
                            gap=.2, min_gap=.05, font=12., min_font=10.)
        self.assertEqual([fit(h).stage for h in (2.5, 2.15, 1.5, 1.35)],
                         ["standard", "gap", "element", "font"])
        with self.assertRaises(FitError):
            fit(1.3)
        first, second = {"rows": [2., 3.]}, {"rows": [1., 2.]}
        result = select_payload_fit("試験", 3., [("standard", first, 5.), ("gap", second, 3.)], guidance="分割")
        self.assertIs(result.values, second)
        self.assertEqual((result.stage, result.used, result.available), ("gap", 3., 3.))
        with self.assertRaises(ValueError):
            select_payload_fit("試験", 3., [], guidance="分割")
        with self.assertRaises(FitError):
            select_payload_fit("試験", 2., [("gap", second, 3.)], guidance="分割")

    def test_settings_keep_distinct_existing_profiles(self):
        self.assertEqual(PAGE.margin, .55)
        self.assertEqual(PAGE.body_width, 13.333 - 2 * .55)
        self.assertEqual(SWIMLANE.frame_width, 12.59)
        self.assertAlmostEqual(ROADMAP.track_width + ROADMAP.grid_width, 11.87)


if __name__ == "__main__":
    unittest.main()
