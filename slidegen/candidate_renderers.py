"""採用判断用に追加した業務スライドrenderer群。"""

from collections import defaultdict

from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches

from diagrams import add_arrow
from diagrams3 import plain_line, route
from generate import (
    ACCENT,
    BODY_W,
    CANVAS,
    GRAY,
    LIGHT,
    MARGIN,
    NAVY,
    RULE,
    TEXT,
    WHITE,
    ZEBRA,
    add_rect,
    add_text,
    header,
)
from layout_fit import FitError, fit_text_or_raise, select_fit, stepped


def _fit_rows(renderer, available, count, *, row_h, min_row_h, gap, min_gap,
              font, min_font, reserve=0.0):
    """余白、行高、文字の順に縮める共通収容処理。"""
    def used(values):
        return reserve + count * values["row_h"] + max(0, count - 1) * values["gap"]

    def candidates():
        yield "standard", {"row_h": row_h, "gap": gap, "font": font}, used(
            {"row_h": row_h, "gap": gap, "font": font})
        for current_gap in stepped(gap - 0.03, min_gap, 0.03):
            values = {"row_h": row_h, "gap": current_gap, "font": font}
            yield "gap", values, used(values)
        for current_h in stepped(row_h - 0.04, min_row_h, 0.04):
            values = {"row_h": current_h, "gap": min_gap, "font": font}
            yield "element", values, used(values)
        for current_font in stepped(font - 0.5, min_font, 0.5):
            values = {"row_h": min_row_h, "gap": min_gap, "font": current_font}
            yield "font", values, used(values)

    return select_fit(
        renderer,
        available,
        candidates(),
        guidance="項目を減らすか、文言を短くするか、複数スライドへ分割してください。",
    )


def _text_in_box(slide, renderer, field, x, y, w, h, text, max_pt, min_pt,
                 *, bold=False, color=TEXT, align=PP_ALIGN.LEFT,
                 anchor=MSO_ANCHOR.TOP, spacing=1.15, role=None):
    size, lines = fit_text_or_raise(
        renderer,
        field,
        text,
        w,
        h,
        max_pt,
        min_pt=min_pt,
        weight="bold" if bold else "regular",
        spacing=spacing,
        role=role,
    )
    return add_text(
        slide, x, y, w, h, "\n".join(lines), size,
        bold=bold, color=color, align=align, anchor=anchor, spacing=spacing,
    )


def _dot(slide, cx, cy, color=ACCENT, size=0.10):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.OVAL,
        Inches(cx - size / 2),
        Inches(cy - size / 2),
        Inches(size),
        Inches(size),
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    shape.shadow.inherit = False
    return shape


def _takeaway(slide, renderer, text, y, *, label="示唆"):
    add_rect(slide, MARGIN, y, BODY_W, 0.58, LIGHT)
    add_text(slide, MARGIN + 0.22, y + 0.15, 0.62, 0.24, label, 10.5,
             bold=True, color=ACCENT, align=PP_ALIGN.CENTER)
    _text_in_box(
        slide, renderer, "takeaway", MARGIN + 1.02, y + 0.11,
        BODY_W - 1.28, 0.34, text, 15, 11.5,
        bold=True, color=NAVY, anchor=MSO_ANCHOR.MIDDLE,
    )


def s_scope(slide, spec, page):
    """対象範囲・対象外・前提条件を2列で整理する。"""
    area = header(slide, spec["kicker"], spec["title"], spec.get("lead"))
    left_items, right_items = spec["in_scope"], spec["out_of_scope"]
    assumptions = spec.get("assumptions", [])
    assumptions_h = 0.82 if assumptions else 0.0
    body_top = area.top + 0.18
    body_bottom = area.bottom - assumptions_h - (0.12 if assumptions else 0.02)
    max_count = max(len(left_items), len(right_items))
    fitted = _fit_rows(
        "scope", body_bottom - body_top - 0.58, max_count,
        row_h=0.62, min_row_h=0.44, gap=0.12, min_gap=0.03,
        font=15.0, min_font=11.0,
    )
    values = fitted.values
    col_gap, col_w = 0.42, (BODY_W - 0.42) / 2

    def column(x, label, items, positive):
        color = ACCENT if positive else GRAY
        add_text(slide, x, body_top, col_w, 0.28, label, 14.5,
                 bold=True, color=color)
        plain_line(slide, x, body_top + 0.40, x + col_w, body_top + 0.40,
                   color=RULE, width=0.8)
        y = body_top + 0.58
        for index, item in enumerate(items):
            _dot(slide, x + 0.10, y + values["row_h"] / 2, color, 0.11)
            _text_in_box(
                slide, "scope", f"items[{index}]", x + 0.28, y,
                col_w - 0.34, values["row_h"], item,
                values["font"], 10.5, color=TEXT,
                anchor=MSO_ANCHOR.MIDDLE,
            )
            y += values["row_h"] + values["gap"]

    column(MARGIN + 0.10, spec.get("in_label", "対象"), left_items, True)
    column(MARGIN + 0.10 + col_w + col_gap,
           spec.get("out_label", "対象外"), right_items, False)
    if assumptions:
        y = area.bottom - 0.72
        add_rect(slide, MARGIN + 0.10, y, BODY_W - 0.20, 0.60, ZEBRA)
        add_text(slide, MARGIN + 0.30, y + 0.16, 0.82, 0.24, "前提条件", 10.5,
                 bold=True, color=NAVY)
        text = " / ".join(assumptions)
        _text_in_box(slide, "scope", "assumptions", MARGIN + 1.25, y + 0.10,
                     BODY_W - 1.58, 0.39, text, 11.5, 9.0,
                     color=TEXT, anchor=MSO_ANCHOR.MIDDLE, role="compact")


def s_summary(slide, spec, page):
    """少数の論点と結論を、箱を並べずに要約する。"""
    area = header(slide, spec["kicker"], spec["title"], spec.get("lead"))
    sections = spec["sections"]
    conclusion = spec.get("conclusion")
    conclusion_h = 0.72 if conclusion else 0.0
    top = area.top + 0.26
    available = area.bottom - top - conclusion_h - 0.18
    count = len(sections)
    if count <= 3:
        cols, rows = count, 1
    else:
        cols, rows = 2, 2
    gap_x, gap_y = 0.46, 0.28
    cell_w = (BODY_W - gap_x * (cols - 1)) / cols
    cell_h = (available - gap_y * (rows - 1)) / rows
    if cell_h < 1.22:
        raise FitError("summary: 結論を含む本文領域へ論点を配置できません。論点を減らしてください。")

    for index, section in enumerate(sections):
        row, col = divmod(index, cols)
        x = MARGIN + col * (cell_w + gap_x)
        y = top + row * (cell_h + gap_y)
        add_text(slide, x, y + 0.01, 0.40, 0.28, f"{index + 1:02d}", 11.5,
                 bold=True, color=ACCENT)
        _text_in_box(slide, "summary", f"sections[{index}].heading",
                     x + 0.55, y, cell_w - 0.55, 0.35,
                     section["heading"], 16.5, 12.0,
                     bold=True, color=NAVY)
        plain_line(slide, x + 0.55, y + 0.46, x + cell_w, y + 0.46,
                   color=RULE, width=0.8)
        _text_in_box(slide, "summary", f"sections[{index}].body",
                     x + 0.55, y + 0.60, cell_w - 0.58, cell_h - 0.68,
                     section["body"], 13.0, 10.0, color=TEXT, spacing=1.22)
    if conclusion:
        _takeaway(slide, "summary", conclusion, area.bottom - 0.62,
                  label=spec.get("conclusion_label", "結論"))


def s_paired_comparison(slide, spec, page):
    """同一観点で左右を比較し、対応関係を行単位で固定する。"""
    area = header(slide, spec["kicker"], spec["title"], spec.get("lead"))
    rows = spec["rows"]
    takeaway = spec.get("takeaway")
    top = area.top + 0.24
    takeaway_h = 0.72 if takeaway else 0.0
    fitted = _fit_rows(
        "paired_comparison", area.bottom - top - takeaway_h - 0.54,
        len(rows), row_h=0.68, min_row_h=0.46, gap=0.08, min_gap=0.02,
        font=13.5, min_font=10.0,
    )
    values = fitted.values
    left_x, left_w = MARGIN + 0.08, 5.10
    criterion_x, criterion_w = left_x + left_w + 0.18, 1.38
    right_x = criterion_x + criterion_w + 0.18
    right_w = MARGIN + BODY_W - 0.08 - right_x
    add_text(slide, left_x, top, left_w, 0.34, spec["left_label"], 15.5,
             bold=True, color=GRAY, align=PP_ALIGN.CENTER)
    add_text(slide, right_x, top, right_w, 0.34, spec["right_label"], 15.5,
             bold=True, color=ACCENT, align=PP_ALIGN.CENTER)
    add_text(slide, criterion_x, top + 0.02, criterion_w, 0.28,
             spec.get("criterion_label", "評価軸"), 10.0,
             bold=True, color=GRAY, align=PP_ALIGN.CENTER)
    plain_line(slide, left_x, top + 0.43, left_x + left_w, top + 0.43,
               color=RULE, width=0.9)
    plain_line(slide, right_x, top + 0.43, right_x + right_w, top + 0.43,
               color=ACCENT, width=1.1)
    y = top + 0.56
    rows_h = len(rows) * values["row_h"] + max(0, len(rows) - 1) * values["gap"]
    add_rect(slide, criterion_x, y, criterion_w, rows_h, ZEBRA)
    for index, row in enumerate(rows):
        fill = ZEBRA if index % 2 == 0 else CANVAS
        add_rect(slide, left_x, y, left_w, values["row_h"], fill)
        add_rect(slide, right_x, y, right_w, values["row_h"],
                 LIGHT if index % 2 == 0 else CANVAS)
        _text_in_box(slide, "paired_comparison", f"rows[{index}].left",
                     left_x + 0.20, y, left_w - 0.40, values["row_h"], row["left"],
                     values["font"], 9.5, anchor=MSO_ANCHOR.MIDDLE)
        _text_in_box(slide, "paired_comparison", f"rows[{index}].criterion",
                     criterion_x, y, criterion_w, values["row_h"], row["criterion"],
                     min(11.0, values["font"]), 8.5, bold=True, color=NAVY,
                     align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE,
                     role="compact")
        _text_in_box(slide, "paired_comparison", f"rows[{index}].right",
                     right_x + 0.20, y, right_w - 0.40, values["row_h"], row["right"],
                     values["font"], 9.5, anchor=MSO_ANCHOR.MIDDLE)
        y += values["row_h"] + values["gap"]
    if takeaway:
        _takeaway(slide, "paired_comparison", takeaway, area.bottom - 0.62)


def s_mapping(slide, spec, page):
    """左右の項目間に一対多・多対多の対応線を描く。"""
    area = header(slide, spec["kicker"], spec["title"], spec.get("lead"))
    left_items, right_items = spec["left_items"], spec["right_items"]
    links = spec["links"]
    takeaway = spec.get("takeaway")
    top = area.top + 0.22
    takeaway_h = 0.72 if takeaway else 0.0
    body_bottom = area.bottom - takeaway_h - 0.10
    max_count = max(len(left_items), len(right_items))
    fitted = _fit_rows(
        "mapping", body_bottom - top - 0.52, max_count,
        row_h=0.58, min_row_h=0.42, gap=0.13, min_gap=0.04,
        font=13.5, min_font=10.0,
    )
    values = fitted.values
    left_x, item_w = MARGIN + 0.16, 4.45
    right_x = MARGIN + BODY_W - item_w - 0.16
    add_text(slide, left_x, top, item_w, 0.30, spec["left_label"], 14.5,
             bold=True, color=NAVY)
    add_text(slide, right_x, top, item_w, 0.30, spec["right_label"], 14.5,
             bold=True, color=NAVY)
    start_y = top + 0.48

    def positions(items):
        total = len(items) * values["row_h"] + max(0, len(items) - 1) * values["gap"]
        extra = max(0.0, body_bottom - start_y - total)
        return {
            item["id"]: start_y + extra * 0.35 + i * (values["row_h"] + values["gap"])
            for i, item in enumerate(items)
        }

    left_y, right_y = positions(left_items), positions(right_items)
    # 対応線を先に描き、項目と端点を前面へ置く。多対多では直交線の
    # 交差が分岐に見えるため、端点間を直接結んで対応関係を保つ。
    gap_left = left_x + item_w
    gap_right = right_x
    endpoint_colors = {}
    for link in links:
        sy = left_y[link["from"]] + values["row_h"] / 2
        ty = right_y[link["to"]] + values["row_h"] / 2
        color = ACCENT if link.get("emphasis") else GRAY
        width = 1.4 if link.get("emphasis") else 1.0
        add_arrow(slide, gap_left, sy, gap_right, ty, color=color, width=width)
        endpoint_colors[("left", link["from"])] = color
        endpoint_colors[("right", link["to"])] = color

    def draw_items(items, y_by_id, x, side):
        for index, item in enumerate(items):
            y = y_by_id[item["id"]]
            add_rect(slide, x, y, item_w, values["row_h"], WHITE, line=RULE)
            marker_x = x + 0.25 if side == "left" else x + item_w - 0.25
            _dot(slide, marker_x, y + values["row_h"] / 2, ACCENT, 0.25)
            add_text(slide, marker_x - 0.12, y + values["row_h"] / 2 - 0.12,
                     0.24, 0.24, f"{index + 1}", 8.5, bold=True, color=WHITE,
                     align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
            text_x = x + 0.48 if side == "left" else x + 0.18
            text_w = item_w - 0.66
            _text_in_box(slide, "mapping", f"{side}_items[{index}].text",
                         text_x, y, text_w, values["row_h"], item["text"],
                         values["font"], 9.5, bold=True, color=NAVY,
                         anchor=MSO_ANCHOR.MIDDLE)

    draw_items(left_items, left_y, left_x, "left")
    draw_items(right_items, right_y, right_x, "right")
    for item in left_items:
        color = endpoint_colors.get(("left", item["id"]), GRAY)
        _dot(slide, gap_left, left_y[item["id"]] + values["row_h"] / 2,
             color, 0.08)
    for item in right_items:
        color = endpoint_colors.get(("right", item["id"]), GRAY)
        _dot(slide, gap_right, right_y[item["id"]] + values["row_h"] / 2,
             color, 0.08)
    if takeaway:
        _takeaway(slide, "mapping", takeaway, area.bottom - 0.62)


def _swimlane_step_rects(spec, x0, y0, stage_w, lane_h):
    grouped = defaultdict(list)
    lane_index = {lane["id"]: index for index, lane in enumerate(spec["lanes"])}
    stage_index = {stage["id"]: index for index, stage in enumerate(spec["stages"])}
    for step in spec["steps"]:
        grouped[(step["lane"], step["stage"])].append(step)
    rects = {}
    for (lane_id, stage_id), steps in grouped.items():
        cell_x = x0 + stage_index[stage_id] * stage_w
        cell_y = y0 + lane_index[lane_id] * lane_h
        gap = 0.08
        width = min(1.72, (stage_w - 0.22 - gap * (len(steps) - 1)) / len(steps))
        total_w = len(steps) * width + gap * (len(steps) - 1)
        start_x = cell_x + (stage_w - total_w) / 2
        node_h = min(0.56, lane_h - 0.20)
        for index, step in enumerate(steps):
            rects[step["id"]] = (
                start_x + index * (width + gap),
                cell_y + (lane_h - node_h) / 2,
                width,
                node_h,
            )
    return rects


def s_swimlane(slide, spec, page):
    """担当レーンと工程フェーズを持つ業務フローを描く。"""
    area = header(slide, spec["kicker"], spec["title"], spec.get("lead"))
    lanes, stages = spec["lanes"], spec["stages"]
    takeaway = spec.get("takeaway")
    takeaway_h = 0.72 if takeaway else 0.0
    top = area.top + 0.12
    stage_h, lane_label_w = 0.48, 1.48
    stage_index = {stage["id"]: index for index, stage in enumerate(stages)}
    step_by_id = {step["id"]: step for step in spec["steps"]}
    has_feedback = any(
        stage_index[step_by_id[edge["to"]]["stage"]]
        < stage_index[step_by_id[edge["from"]]["stage"]]
        for edge in spec["edges"]
    )
    feedback_h = 0.30 if has_feedback else 0.0
    available_h = area.bottom - top - stage_h - takeaway_h - 0.12
    fitted = _fit_rows(
        "swimlane", available_h, len(lanes),
        row_h=0.86, min_row_h=0.62, gap=0.0, min_gap=0.0,
        font=11.5, min_font=9.0, reserve=feedback_h,
    )
    lane_h = fitted.values["row_h"]
    x0 = MARGIN + lane_label_w
    stage_w = (BODY_W - lane_label_w) / len(stages)
    lane_y0 = top + stage_h
    for index, stage in enumerate(stages):
        x = x0 + index * stage_w
        add_text(slide, x + 0.08, top + 0.10, stage_w - 0.16, 0.26,
                 stage["label"], 11.5, bold=True, color=NAVY,
                 align=PP_ALIGN.CENTER)
        if index:
            plain_line(slide, x, top, x, lane_y0 + len(lanes) * lane_h,
                       color=RULE, width=0.65)
    rects = _swimlane_step_rects(spec, x0, lane_y0, stage_w, lane_h)
    lane_index = {lane["id"]: index for index, lane in enumerate(lanes)}
    for index, lane in enumerate(lanes):
        y = lane_y0 + index * lane_h
        add_rect(slide, MARGIN, y, BODY_W, lane_h,
                 ZEBRA if index % 2 == 0 else CANVAS)
        _text_in_box(slide, "swimlane", f"lanes[{index}].label",
                     MARGIN + 0.12, y, lane_label_w - 0.22, lane_h,
                     lane["label"], 13.0, 10.0, bold=True, color=NAVY,
                     anchor=MSO_ANCHOR.MIDDLE)
        plain_line(slide, MARGIN, y + lane_h, MARGIN + BODY_W, y + lane_h,
                   color=RULE, width=0.65)
    for edge in spec["edges"]:
        sx, sy, sw, sh = rects[edge["from"]]
        tx, ty, tw, th = rects[edge["to"]]
        source_stage = stage_index[step_by_id[edge["from"]]["stage"]]
        target_stage = stage_index[step_by_id[edge["to"]]["stage"]]
        if target_stage > source_stage:
            start, end = (sx + sw, sy + sh / 2), (tx, ty + th / 2)
            if abs(start[1] - end[1]) < 0.02:
                points = [start, end]
            else:
                boundary = x0 + target_stage * stage_w
                points = [start, (boundary, start[1]), (boundary, end[1]), end]
        elif target_stage == source_stage:
            source_lane = lane_index[step_by_id[edge["from"]]["lane"]]
            target_lane = lane_index[step_by_id[edge["to"]]["lane"]]
            if source_lane == target_lane:
                left_to_right = tx > sx
                start = (sx + sw if left_to_right else sx, sy + sh / 2)
                end = (tx if left_to_right else tx + tw, ty + th / 2)
                points = [start, end]
            elif abs(target_lane - source_lane) == 1:
                downward = ty > sy
                start = (sx + sw / 2, sy + sh if downward else sy)
                end = (tx + tw / 2, ty if downward else ty + th)
                points = [start, end]
            else:
                # 中間レーンのノードを貫通しないよう工程セル右端を通し、
                # 対象ノードの上下辺へ最後の短い縦線で接続する。
                upward = target_lane < source_lane
                channel_x = x0 + (source_stage + 1) * stage_w - 0.22
                start = (sx + sw, sy + sh / 2)
                target_x = tx + tw / 2
                target_y = ty + th if upward else ty
                approach_y = target_y + (0.10 if upward else -0.10)
                points = [start, (channel_x, start[1]),
                          (channel_x, approach_y),
                          (target_x, approach_y), (target_x, target_y)]
        else:
            channel_y = lane_y0 + len(lanes) * lane_h + 0.10
            if channel_y > area.bottom - takeaway_h - 0.08:
                raise FitError("swimlane: 差戻し線の配線領域が不足しています。工程を分割してください。")
            start = (sx + sw / 2, sy + sh)
            end = (tx + tw / 2, ty + th)
            points = [start, (start[0], channel_y), (end[0], channel_y), end]
        route(slide, points,
              dash="dash" if edge.get("kind") == "feedback" else None,
              width=1.15)
    for index, step in enumerate(spec["steps"]):
        x, y, w, h = rects[step["id"]]
        add_rect(slide, x, y, w, h,
                 LIGHT if step.get("style") == "accent" else WHITE,
                 line=ACCENT if step.get("style") == "accent" else RULE)
        _text_in_box(slide, "swimlane", f"steps[{index}].name",
                     x + 0.10, y, w - 0.20, h, step["name"],
                     fitted.values["font"], 8.5, bold=True, color=NAVY,
                     align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE,
                     role="compact")
    if takeaway:
        _takeaway(slide, "swimlane", takeaway, area.bottom - 0.62)


def s_sequence(slide, spec, page):
    """参加者間のメッセージを上から下へ時系列表示する。"""
    area = header(slide, spec["kicker"], spec["title"], spec.get("lead"))
    participants, messages = spec["participants"], spec["messages"]
    phases = spec.get("phases", [])
    takeaway = spec.get("takeaway")
    takeaway_h = 0.72 if takeaway else 0.0
    top = area.top + 0.16
    header_h = 0.46
    message_top = top + header_h + 0.24
    available = area.bottom - message_top - takeaway_h - 0.12
    fitted = _fit_rows(
        "sequence", available, len(messages),
        row_h=0.42, min_row_h=0.30, gap=0.12, min_gap=0.02,
        font=10.5, min_font=8.0,
    )
    participant_x0, participant_x1 = 3.05, 12.25
    xs = [participant_x0 + i * (participant_x1 - participant_x0) / (len(participants) - 1)
          for i in range(len(participants))]
    x_by_id = {participant["id"]: x for participant, x in zip(participants, xs)}
    message_y = {
        message["id"]: message_top + i * (fitted.values["row_h"] + fitted.values["gap"])
        for i, message in enumerate(messages)
    }
    index_by_id = {message["id"]: index for index, message in enumerate(messages)}
    lifeline_bottom = message_y[messages[-1]["id"]] + fitted.values["row_h"] + 0.08
    for phase in phases:
        start_index = index_by_id[phase["from"]]
        y1 = message_y[messages[start_index]["id"]] - fitted.values["gap"] / 2
        plain_line(slide, MARGIN + 1.52, y1, MARGIN + BODY_W - 0.12, y1,
                   color=RULE, width=0.7)
        phase_box = add_text(slide, MARGIN + 0.60, y1 - 0.12, 0.82, 0.24,
                             phase["label"], 8.5, bold=True, color=ACCENT,
                             align=PP_ALIGN.RIGHT,
                             anchor=MSO_ANCHOR.MIDDLE)
        phase_box.fill.solid()
        phase_box.fill.fore_color.rgb = CANVAS
    for index, (participant, x) in enumerate(zip(participants, xs)):
        box_w = min(1.74, (participant_x1 - participant_x0) / len(participants) * 0.88)
        _text_in_box(slide, "sequence", f"participants[{index}].label",
                     x - box_w / 2 + 0.08, top, box_w - 0.16, header_h,
                     participant["label"], 11.0, 8.5, bold=True, color=NAVY,
                     align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE,
                     role="compact")
        plain_line(slide, x - box_w / 2, top + header_h,
                   x + box_w / 2, top + header_h, color=RULE, width=0.8)
        plain_line(slide, x, top + header_h, x, lifeline_bottom,
                   color=GRAY, width=0.75, dash="dash")
    for index, message in enumerate(messages):
        y = message_y[message["id"]] + fitted.values["row_h"] / 2
        sx, tx = x_by_id[message["from"]], x_by_id[message["to"]]
        add_text(slide, MARGIN + 0.18, y - 0.12, 0.38, 0.24,
                 f"{index + 1:02d}", 9.5, bold=True, color=ACCENT,
                 align=PP_ALIGN.RIGHT)
        if sx == tx:
            loop_w, loop_h = 0.46, max(0.22, fitted.values["row_h"] * 0.72)
            points = [(sx, y - loop_h / 2), (sx + loop_w, y - loop_h / 2),
                      (sx + loop_w, y + loop_h / 2), (sx, y + loop_h / 2)]
            route(slide, points,
                  dash="dash" if message.get("kind") == "return" else None,
                  width=1.0)
            label_x, label_w = sx + 0.10, 1.20
        else:
            add_arrow(slide, sx, y, tx, y, width=1.05,
                      dash="dash" if message.get("kind") == "return" else None)
            label_x, label_w = (sx + tx) / 2, min(1.72, abs(tx - sx) - 0.10)
        label_y = y - 0.27
        label_size, lines = fit_text_or_raise(
            "sequence", f"messages[{index}].label", message["label"],
            label_w, 0.24, fitted.values["font"], min_pt=7.5,
            weight="bold", spacing=1.0, role="compact")
        tb = add_text(slide, label_x - label_w / 2, label_y, label_w, 0.24,
                      "\n".join(lines), label_size, bold=True, color=NAVY,
                      align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE,
                      spacing=1.0)
        tb.fill.solid()
        tb.fill.fore_color.rgb = CANVAS
    if takeaway:
        _takeaway(slide, "sequence", takeaway, area.bottom - 0.62)
