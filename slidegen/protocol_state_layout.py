"""パケット状態図の収容・段階列・行位置・値変化を、描画せず計画する。"""

from dataclasses import dataclass
from typing import Any, Iterator, Mapping, Sequence, TypedDict

from slidegen.layout_fit import PayloadFitResult, select_payload_fit, stepped
from slidegen.layout_settings import BodyArea, HeightArea, PAGE, PROTOCOL
from slidegen.textfit import line_height_in, wrap_compact


Spec = Mapping[str, Any]


class ProtocolStyle(TypedDict):
    stage_gap: float
    row_gap: float
    icon_size: float
    stage_font: float
    flow_font: float
    flow_sub_font: float
    state_font: float
    detail_font: float


class ProtocolValues(ProtocolStyle):
    stage_w: float
    header_h: float
    row_heights: list[float]


def measure_protocol(
    values: ProtocolStyle, stages: Sequence[Spec], flows: Sequence[Spec]
) -> tuple[ProtocolValues, float]:
    rail_w = PROTOCOL.rail_width
    stage_w = (PAGE.body_width - rail_w - (len(stages) - 1) * values["stage_gap"]) / len(stages)
    text_w = stage_w - 0.18
    header_lines = max(
        len(wrap_compact(stage["label"], text_w, values["stage_font"], "bold")) for stage in stages
    )
    header_h = max(
        values["icon_size"] + 0.08 + header_lines * line_height_in(values["stage_font"], 1.0), 0.62
    )
    row_heights = []
    for flow in flows:
        label_lines = wrap_compact(flow["label"], rail_w - 0.20, values["flow_font"], "bold")
        sub_lines = (
            wrap_compact(flow["sub"], rail_w - 0.20, values["flow_sub_font"], "regular")
            if flow.get("sub")
            else []
        )
        rail_text_h = (
            0.20
            + len(label_lines) * line_height_in(values["flow_font"], 1.0)
            + (
                0.04 + len(sub_lines) * line_height_in(values["flow_sub_font"], 1.0)
                if sub_lines
                else 0.0
            )
            + 0.14
        )
        state_heights = []
        for state in flow["states"]:
            title_lines = wrap_compact(state["label"], text_w, values["state_font"], "bold")
            detail_lines = (
                wrap_compact(state.get("detail", ""), text_w, values["detail_font"], "regular")
                if state.get("detail")
                else []
            )
            text_h = len(title_lines) * line_height_in(values["state_font"], 1.0) + (
                0.05 + len(detail_lines) * line_height_in(values["detail_font"], 1.0)
                if detail_lines
                else 0.0
            )
            state_heights.append(0.42 + text_h)
        row_heights.append(max(0.98, rail_text_h, max(state_heights) + 0.18))
    total = header_h + 0.18 + sum(row_heights) + max(0, len(flows) - 1) * values["row_gap"] + 0.06
    result: ProtocolValues = {
        **values,
        "stage_w": stage_w,
        "header_h": header_h,
        "row_heights": row_heights,
    }
    return result, total


def protocol_candidates(
    stages: Sequence[Spec], flows: Sequence[Spec]
) -> Iterator[tuple[str, ProtocolValues, float]]:
    standard: ProtocolStyle = {
        "stage_gap": 0.18,
        "row_gap": 0.16,
        "icon_size": 0.34,
        "stage_font": 10.5,
        "flow_font": 12.5,
        "flow_sub_font": 9.0,
        "state_font": 11.0,
        "detail_font": 9.0,
    }
    values, used = measure_protocol(standard, stages, flows)
    yield "standard", values, used
    for row_gap in stepped(0.12, 0.06, 0.03):
        compact: ProtocolStyle = {**standard, "row_gap": row_gap, "stage_gap": 0.12}
        values, used = measure_protocol(compact, stages, flows)
        yield "gap", values, used
    for icon_size in stepped(0.32, 0.26, 0.02):
        compact = {**standard, "row_gap": 0.06, "stage_gap": 0.10, "icon_size": icon_size}
        values, used = measure_protocol(compact, stages, flows)
        yield "icon", values, used
    for state_font in stepped(10.5, PROTOCOL.state_min_pt, 0.5):
        compact = {
            "stage_gap": 0.10,
            "row_gap": 0.06,
            "icon_size": 0.26,
            "stage_font": 9.5,
            "flow_font": max(11.0, state_font + 1.0),
            "flow_sub_font": PROTOCOL.detail_min_pt,
            "state_font": state_font,
            "detail_font": max(PROTOCOL.detail_min_pt, state_font - 2.0),
        }
        values, used = measure_protocol(compact, stages, flows)
        yield "font", values, used


def fit_protocol_state_flow(
    area: HeightArea, stages: Sequence[Spec], flows: Sequence[Spec]
) -> PayloadFitResult[ProtocolValues]:
    return select_payload_fit(
        "nw_protocol_flow",
        area.height - PROTOCOL.top_gap - PROTOCOL.legend_height,
        protocol_candidates(stages, flows),
        guidance=(
            "段階を6件以内、トラックを3件以内に絞り、各状態の説明を短くするか、"
            "複数ページへ分割してください。"
        ),
    )


def changed_stages(stages: Sequence[Spec], states: Sequence[Spec]) -> set[str]:
    """表示値・付加情報だけを位置順で比較し、理由や装飾差は含めない。"""
    by_stage = {state["stage"]: state for state in states}
    previous = None
    changed = set()
    for stage in stages:
        state = by_stage[stage["id"]]
        value = (state["label"], state.get("encapsulation"))
        if previous is not None and value != previous:
            changed.add(stage["id"])
        previous = value
    return changed


@dataclass(frozen=True)
class ProtocolRow:
    top: float
    height: float
    states: list[Spec]
    changed: set[str]


@dataclass(frozen=True)
class ProtocolPlan:
    fitted: PayloadFitResult[ProtocolValues]
    stage_centers: dict[str, float]
    top: float
    rows_top: float
    rows_bottom: float
    rows: list[ProtocolRow]


def plan_protocol_state_flow(spec: Spec, area: BodyArea) -> ProtocolPlan:
    stages, flows = spec["stages"], spec["flows"]
    fitted = fit_protocol_state_flow(area, stages, flows)
    values = fitted.values
    stage_x0 = PAGE.margin + PROTOCOL.rail_width
    stage_w = values["stage_w"]
    centers = {
        stage["id"]: stage_x0 + index * (stage_w + values["stage_gap"]) + stage_w / 2
        for index, stage in enumerate(stages)
    }
    top = area.top + PROTOCOL.top_gap + PROTOCOL.legend_height
    rows_top = top + values["header_h"] + 0.18
    rows_bottom = rows_top + sum(values["row_heights"]) + max(0, len(flows) - 1) * values["row_gap"]
    stage_index = {stage["id"]: index for index, stage in enumerate(stages)}
    rows = []
    row_y = rows_top
    for index, flow in enumerate(flows):
        states = sorted(flow["states"], key=lambda state: stage_index[state["stage"]])
        row_h = values["row_heights"][index]
        rows.append(ProtocolRow(row_y, row_h, states, changed_stages(stages, states)))
        row_y += row_h + values["row_gap"]
    return ProtocolPlan(fitted, centers, top, rows_top, rows_bottom, rows)
