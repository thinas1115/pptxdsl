"""担当フローのセル配置・工程順・差戻し経路を、描画なしで計算する。"""

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Mapping

from slidegen.layout_fit import FitError, FitResult, fit_rows
from slidegen.layout_settings import BodyArea, SWIMLANE
from slidegen.textfit import text_width_in


Spec = Mapping[str, Any]
Point = tuple[float, float]
Rect = tuple[float, float, float, float]


def step_rects(spec: Spec, x0: float, y0: float, stage_w: float, lane_h: float) -> dict[str, Rect]:
    grouped: dict[tuple[str, str], list[Spec]] = defaultdict(list)
    lane_index = {lane["id"]: index for index, lane in enumerate(spec["lanes"])}
    stage_index = {stage["id"]: index for index, stage in enumerate(spec["stages"])}
    for step in spec["steps"]:
        grouped[(step["lane"], step["stage"])].append(step)
    rects = {}
    for (lane_id, stage_id), steps in grouped.items():
        cell_x = x0 + stage_index[stage_id] * stage_w
        cell_y = y0 + lane_index[lane_id] * lane_h
        gap = 0.10
        if len(spec["stages"]) <= 2:
            max_node_w = 2.36
        elif len(spec["stages"]) <= 3:
            max_node_w = 1.92
        else:
            max_node_w = min(2.20, stage_w - 0.28)
        available_w = stage_w - 0.28 - gap * (len(steps) - 1)
        widths = [
            min(max_node_w, max(0.88, text_width_in(step["name"], 10.5, "bold") + 0.36))
            for step in steps
        ]
        if sum(widths) > available_w:
            scale = available_w / sum(widths)
            widths = [width * scale for width in widths]
        total_w = sum(widths) + gap * (len(steps) - 1)
        cursor_x = cell_x + (stage_w - total_w) / 2
        node_h = min(0.62 if lane_h >= 1.20 else 0.50, lane_h - 0.24)
        for step, width in zip(steps, widths):
            rects[step["id"]] = (cursor_x, cell_y + (lane_h - node_h) / 2, width, node_h)
            cursor_x += width + gap
    return rects


@dataclass(frozen=True)
class SwimlanePlan:
    fitted: FitResult
    top: float
    lane_label_w: float
    stage_w: float
    lane_y0: float
    x0: float
    show_line_legend: bool
    rects: dict[str, Rect]
    paths: list[list[Point]]


def edge_path(
    edge: Spec,
    rects: Mapping[str, Rect],
    stage_index: Mapping[str, int],
    lane_index: Mapping[str, int],
    steps: Mapping[str, Spec],
    x0: float,
    lane_y0: float,
    stage_w: float,
    lane_h: float,
) -> list[Point]:
    sx, sy, sw, sh = rects[edge["from"]]
    tx, ty, tw, th = rects[edge["to"]]
    source_stage = stage_index[steps[edge["from"]]["stage"]]
    target_stage = stage_index[steps[edge["to"]]["stage"]]
    if target_stage > source_stage:
        start, end = (sx + sw, sy + sh / 2), (tx, ty + th / 2)
        if abs(start[1] - end[1]) < 0.02:
            return [start, end]
        boundary = x0 + target_stage * stage_w - 0.04
        return [start, (boundary, start[1]), (boundary, end[1]), end]
    if target_stage == source_stage:
        source_lane = lane_index[steps[edge["from"]]["lane"]]
        target_lane = lane_index[steps[edge["to"]]["lane"]]
        if source_lane == target_lane:
            left_to_right = tx > sx
            start = (sx + sw if left_to_right else sx, sy + sh / 2)
            end = (tx if left_to_right else tx + tw, ty + th / 2)
            return [start, end]
        if abs(target_lane - source_lane) == 1:
            downward = ty > sy
            start = (sx + sw / 2, sy + sh if downward else sy)
            end = (tx + tw / 2, ty if downward else ty + th)
            channel_y = (start[1] + end[1]) / 2
            return [start, (start[0], channel_y), (end[0], channel_y), end]
        upward = target_lane < source_lane
        channel_x = x0 + (source_stage + 1) * stage_w - 0.22
        start = (sx + sw, sy + sh / 2)
        target_x = tx + tw / 2
        target_y = ty + th if upward else ty
        approach_y = target_y + (0.10 if upward else -0.10)
        return [
            start,
            (channel_x, start[1]),
            (channel_x, approach_y),
            (target_x, approach_y),
            (target_x, target_y),
        ]
    channel_y = lane_y0 + len(lane_index) * lane_h + 0.10
    if channel_y > SWIMLANE.body_bottom - 0.08:
        raise FitError("swimlane: 差戻し線の配線領域が不足しています。工程を分割してください。")
    start = (sx + sw / 2, sy + sh)
    end = (tx + tw / 2, ty)
    source_channel = x0 + (source_stage + 1) * stage_w - 0.08
    target_channel = x0 + target_stage * stage_w + 0.08
    return [
        start,
        (start[0], start[1] + 0.035),
        (source_channel, start[1] + 0.035),
        (source_channel, channel_y),
        (target_channel, channel_y),
        (target_channel, end[1] - 0.035),
        (end[0], end[1] - 0.035),
        end,
    ]


def plan_swimlane(spec: Spec, area: BodyArea) -> SwimlanePlan:
    lanes, stages = spec["lanes"], spec["stages"]
    top = area.top + SWIMLANE.top_gap
    label_w = min(
        SWIMLANE.label_max_width,
        max(
            SWIMLANE.label_min_width,
            max(text_width_in(lane["label"], 13.0, "bold") + 0.22 for lane in lanes),
        ),
    )
    stage_index = {stage["id"]: index for index, stage in enumerate(stages)}
    steps = {step["id"]: step for step in spec["steps"]}
    has_feedback = any(
        stage_index[steps[edge["to"]]["stage"]] < stage_index[steps[edge["from"]]["stage"]]
        for edge in spec["edges"]
    )
    edge_kinds = {
        "feedback" if edge.get("kind") == "feedback" else "forward" for edge in spec["edges"]
    }
    fitted = fit_rows(
        "swimlane_flow",
        SWIMLANE.body_bottom - top - SWIMLANE.stage_height,
        len(lanes),
        row_h=1.34 if len(lanes) == 2 else 0.98 if len(lanes) == 3 else 0.95,
        min_row_h=0.62,
        gap=0.0,
        min_gap=0.0,
        font=11.5,
        min_font=9.0,
        reserve=0.30 if has_feedback else 0.0,
    )
    lane_h = fitted.values["row_h"]
    x0 = SWIMLANE.frame_x + label_w
    stage_w = (SWIMLANE.frame_width - label_w) / len(stages)
    lane_y0 = top + SWIMLANE.stage_height
    rects = step_rects(spec, x0, lane_y0, stage_w, lane_h)
    lane_index = {lane["id"]: index for index, lane in enumerate(lanes)}
    paths = [
        edge_path(edge, rects, stage_index, lane_index, steps, x0, lane_y0, stage_w, lane_h)
        for edge in spec["edges"]
    ]
    return SwimlanePlan(
        fitted, top, label_w, stage_w, lane_y0, x0, len(edge_kinds) > 1, rects, paths
    )
