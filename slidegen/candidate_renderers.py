"""採用判断用に追加した業務スライドrenderer群。"""

from collections import defaultdict
from itertools import permutations

from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

from slidegen.asset_paths import resolve_icon_path
from slidegen import swimlane_layout as _swimlane_layout
from slidegen.layout_settings import SWIMLANE
from slidegen.diagrams import add_arrow
from slidegen.diagrams3 import plain_line, route
from slidegen.generate import (
    ACCENT,
    BODY_W,
    CANVAS,
    GRAY,
    LIGHT,
    MARGIN,
    NAVY,
    RULE,
    SURFACE,
    TEXT,
    WHITE,
    ZEBRA,
    add_rect,
    add_text,
    header,
)
from slidegen.layout_fit import FitError, fit_rows, fit_text_or_raise
from slidegen.quality_markers import (
    SEQUENCE_LIFELINE_PREFIX,
    SEQUENCE_MESSAGE_LABEL_PREFIX,
    SEQUENCE_SELF_ROUTE_PREFIX,
    SURFACE_ON_CANVAS_PREFIX,
)
from slidegen.textfit import text_width_in, wrap_compact


# 参照デザインから採取したswimlane本文用パレット。背景とヘッダーは全体テーマを使う。
SWIMLANE_ACCENT = RGBColor(0x10, 0x84, 0x90)
SWIMLANE_NAVY = RGBColor(0x0F, 0x2A, 0x46)
SWIMLANE_LIGHT = RGBColor(0xEA, 0xF0, 0xEF)
SWIMLANE_RULE = RGBColor(0x8F, 0x97, 0x9B)


def _flatten_shape(shape):
    """テーマ由来の影・光彩を外し、環境差のないフラットな図形にする。"""
    style = shape._element.find(qn("p:style"))
    if style is not None:
        shape._element.remove(style)
    shape.shadow.inherit = False
    return shape


def _flat_rect(slide, x, y, w, h, fill, *, line=None, round_=False):
    return _flatten_shape(
        add_rect(slide, x, y, w, h, fill, line=line, round_=round_))


def _fit_rows(renderer, available, count, *, row_h, min_row_h, gap, min_gap,
              font, min_font, reserve=0.0):
    return fit_rows(renderer, available, count, row_h=row_h, min_row_h=min_row_h,
                    gap=gap, min_gap=min_gap, font=font, min_font=min_font, reserve=reserve)



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
        bold=bold, color=color, align=align, anchor=anchor, spacing=spacing, role=role,
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
    return _flatten_shape(shape)


def _icon_medallion(slide, x, y, icon, *, size=0.46, muted=False):
    """Fluentアイコンを余白込みの円へ中央配置する。"""
    disk = slide.shapes.add_shape(
        MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(size), Inches(size))
    disk.fill.solid()
    disk.fill.fore_color.rgb = ZEBRA if muted else LIGHT
    disk.line.fill.background()
    _flatten_shape(disk)
    icon_path = resolve_icon_path(f"icons/fluent/{icon}.png")
    icon_size = size * 0.52
    slide.shapes.add_picture(
        str(icon_path), Inches(x + (size - icon_size) / 2),
        Inches(y + (size - icon_size) / 2), Inches(icon_size), Inches(icon_size))


def _status_medallion(slide, x, y, mark, *, positive=True, size=0.42):
    disk = slide.shapes.add_shape(
        MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(size), Inches(size))
    disk.fill.solid()
    disk.fill.fore_color.rgb = ACCENT if positive else GRAY
    disk.line.fill.background()
    _flatten_shape(disk)
    add_text(slide, x, y - 0.01, size, size, mark, 16, bold=True, color=WHITE,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


def _number_medallion(slide, x, y, number, *, size=0.46):
    disk = slide.shapes.add_shape(
        MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(size), Inches(size))
    disk.fill.solid()
    disk.fill.fore_color.rgb = LIGHT
    disk.line.color.rgb = RULE
    _flatten_shape(disk)
    add_text(slide, x, y, size, size, f"{number:02d}", 9.5,
             bold=True, color=ACCENT, align=PP_ALIGN.CENTER,
             anchor=MSO_ANCHOR.MIDDLE)


def s_scope(slide, spec, page):
    """対象範囲と対象外を2列で整理する。"""
    area = header(slide, spec["kicker"], spec["title"], spec.get("lead"))
    left_items, right_items = spec["in_scope"], spec["out_of_scope"]
    body_top = area.top + 0.20
    body_bottom = area.bottom - 0.14
    max_count = max(len(left_items), len(right_items))
    sparse = max_count <= 2
    row_h = 1.04 if sparse else 0.58
    row_gap = 0.16 if sparse else 0.07
    font = 17.0 if sparse else 14.0
    fitted = _fit_rows(
        "scope_boundary", body_bottom - body_top - 0.82, max_count,
        row_h=row_h, min_row_h=0.44, gap=row_gap, min_gap=0.03,
        font=font, min_font=11.0,
    )
    values = fitted.values
    col_gap, col_w = 0.34, (BODY_W - 0.34) / 2
    content_h = max_count * values["row_h"] + max(0, max_count - 1) * values["gap"]
    panel_h = 0.70 + content_h
    if sparse:
        panel_h = max(panel_h, 2.22)
        body_top += max(0.0, body_bottom - body_top - panel_h) * 0.26

    def column(x, label, items, positive):
        color = ACCENT if positive else GRAY
        # 見出しだけが白く浮かないよう、外周を持つ一枚のパネルとして描く。
        _flat_rect(slide, x, body_top, col_w, panel_h, SURFACE, line=RULE)
        _flat_rect(slide, x, body_top, col_w, 0.62,
                   LIGHT if positive else ZEBRA)
        _status_medallion(slide, x + 0.20, body_top + 0.10,
                          "✓" if positive else "×", positive=positive)
        add_text(slide, x + 0.76, body_top + 0.16, col_w - 0.98, 0.28, label,
                 15.0, bold=True, color=NAVY, anchor=MSO_ANCHOR.MIDDLE)
        plain_line(slide, x, body_top + 0.62, x + col_w, body_top + 0.62,
                   color=RULE, width=0.8)
        y = body_top + 0.70 + max(0.0, panel_h - 0.70 - content_h) / 2
        for index, item in enumerate(items):
            marker = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE,
                Inches(x + 0.25), Inches(y + values["row_h"] / 2 - 0.035),
                Inches(0.07), Inches(0.07))
            marker.fill.solid()
            marker.fill.fore_color.rgb = color
            marker.line.fill.background()
            _flatten_shape(marker)
            _text_in_box(
                slide, "scope_boundary", f"items[{index}]", x + 0.48, y,
                col_w - 0.68, values["row_h"], item,
                values["font"], 10.5, color=TEXT,
                anchor=MSO_ANCHOR.MIDDLE,
            )
            if index < len(items) - 1:
                plain_line(slide, x + 0.48, y + values["row_h"],
                           x + col_w - 0.24, y + values["row_h"],
                           color=RULE, width=0.45)
            y += values["row_h"] + values["gap"]

    column(MARGIN, spec.get("in_label", "対象"), left_items, True)
    column(MARGIN + col_w + col_gap,
           spec.get("out_label", "対象外"), right_items, False)



def _paired_column_widths(rows, criterion_label="評価軸"):
    """評価軸は実測幅へ絞り、残りを左右本文へ等分する。入力に位置指定を持たせない。"""
    needed = max([text_width_in(row["criterion"], 11, "bold") for row in rows]
                 + [text_width_in(criterion_label, 10, "bold")]) + 0.12
    criterion_w = min(2.0, max(1.05, needed))
    body_w = (BODY_W - criterion_w - 0.40) / 2
    return body_w, criterion_w, body_w


def s_paired_comparison(slide, spec, page):
    """同一観点で左右を比較し、対応関係を行単位で固定する。"""
    area = header(slide, spec["kicker"], spec["title"], spec.get("lead"))
    rows = spec["rows"]
    top = area.top + 0.20
    sparse = len(rows) <= 2
    row_h = 0.88 if sparse else 0.68
    row_gap = 0.0
    font = 15.0 if sparse else 13.5
    fitted = _fit_rows(
        "paired_comparison", area.bottom - top - 0.70,
        len(rows), row_h=row_h, min_row_h=0.46, gap=row_gap, min_gap=0.0,
        font=font, min_font=10.0,
    )
    values = fitted.values
    rows_h = len(rows) * values["row_h"] + max(0, len(rows) - 1) * values["gap"]
    block_h = 0.70 + rows_h
    top += max(0.0, area.bottom - top - block_h) * 0.34
    left_w, criterion_w, right_w = _paired_column_widths(rows, spec.get("criterion_label", "評価軸"))
    left_x = MARGIN
    criterion_x = left_x + left_w + 0.20
    right_x = criterion_x + criterion_w + 0.20
    _flat_rect(slide, left_x, top, left_w, 0.56, NAVY, round_=True)
    _flat_rect(slide, right_x, top, right_w, 0.56, ACCENT, round_=True)
    add_text(slide, left_x + 0.18, top, left_w - 0.36, 0.56,
             spec["left_label"], 15.5, bold=True, color=WHITE,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    add_text(slide, right_x + 0.18, top, right_w - 0.36, 0.56,
             spec["right_label"], 15.5, bold=True, color=WHITE,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    add_text(slide, criterion_x, top + 0.13, criterion_w, 0.28,
             spec.get("criterion_label", "評価軸"), 10.0,
             bold=True, color=GRAY, align=PP_ALIGN.CENTER,
             anchor=MSO_ANCHOR.MIDDLE)
    _flat_rect(slide, left_x, top + 0.64, left_w, rows_h, ZEBRA)
    _flat_rect(slide, right_x, top + 0.64, right_w, rows_h, LIGHT)
    row_positions = [
        top + 0.64 + index * (values["row_h"] + values["gap"])
        for index in range(len(rows))
    ]

    # 接続線を先に描き、評価軸と接続点を必ず前面へ重ねる。
    for index, y in enumerate(row_positions):
        if index > 0:
            plain_line(slide, left_x + 0.18, y,
                       left_x + left_w - 0.18, y, color=RULE, width=0.55)
            plain_line(slide, right_x + 0.18, y,
                       right_x + right_w - 0.18, y, color=RULE, width=0.55)
        cy = y + values["row_h"] / 2
        plain_line(slide, left_x + left_w, cy, criterion_x, cy,
                   color=GRAY, width=1.25)
        plain_line(slide, criterion_x + criterion_w, cy, right_x, cy,
                   color=ACCENT, width=1.25)

    for index, (row, y) in enumerate(zip(rows, row_positions)):
        cy = y + values["row_h"] / 2
        left_box = _text_in_box(slide, "paired_comparison", f"rows[{index}].left",
                     left_x + 0.20, y, left_w - 0.40, values["row_h"], row["left"],
                     values["font"], 9.5, anchor=MSO_ANCHOR.MIDDLE)
        left_box.name = f"paired:left:{index}"
        _flat_rect(slide, criterion_x + 0.06, y + 0.12,
                   criterion_w - 0.12, values["row_h"] - 0.24, SURFACE)
        criterion_box = _text_in_box(slide, "paired_comparison", f"rows[{index}].criterion",
                     criterion_x + 0.06, y + 0.12,
                     criterion_w - 0.12, values["row_h"] - 0.24, row["criterion"],
                     min(11.0, values["font"]), 8.5, bold=True, color=NAVY,
                     align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE,
                     role="compact")
        criterion_box.name = f"paired:criterion:{index}"
        right_box = _text_in_box(slide, "paired_comparison", f"rows[{index}].right",
                     right_x + 0.20, y, right_w - 0.40, values["row_h"], row["right"],
                     values["font"], 9.5, anchor=MSO_ANCHOR.MIDDLE)
        right_box.name = f"paired:right:{index}"

    # 接続点は線より後に追加し、線端を明確な円として見せる。
    for y in row_positions:
        cy = y + values["row_h"] / 2
        _dot(slide, left_x + left_w, cy, GRAY, 0.10)
        _dot(slide, right_x, cy, ACCENT, 0.10)
def _mapping_items_by_min_crossings(left_items, right_items, links):
    """関係を変えずに左右項目を並べ替え、直接結線の交差数を最小化する。"""
    left_ids = [item["id"] for item in left_items]
    right_ids = [item["id"] for item in right_items]
    original_left = {item_id: index for index, item_id in enumerate(left_ids)}
    original_right = {item_id: index for index, item_id in enumerate(right_ids)}
    pairs = [(link["from"], link["to"]) for link in links]
    best = None
    for left_order in permutations(left_ids):
        left_rank = {item_id: index for index, item_id in enumerate(left_order)}
        for right_order in permutations(right_ids):
            right_rank = {item_id: index for index, item_id in enumerate(right_order)}
            crossings = sum(
                (left_rank[source_a] - left_rank[source_b])
                * (right_rank[target_a] - right_rank[target_b]) < 0
                for index, (source_a, target_a) in enumerate(pairs)
                for source_b, target_b in pairs[index + 1:]
            )
            displacement = sum(
                abs(index - original_left[item_id])
                for index, item_id in enumerate(left_order)
            ) + sum(
                abs(index - original_right[item_id])
                for index, item_id in enumerate(right_order)
            )
            score = (crossings, displacement, left_order, right_order)
            if best is None or score < best:
                best = score
                if crossings == 0 and displacement == 0:
                    break
        if best[:2] == (0, 0):
            break
    left_by_id = {item["id"]: item for item in left_items}
    right_by_id = {item["id"]: item for item in right_items}
    return (
        [left_by_id[item_id] for item_id in best[2]],
        [right_by_id[item_id] for item_id in best[3]],
        best[0],
    )


def _mapping_ports(left_y, right_y, row_h, links):
    """相手側の並び順に端点を分散し、同じ項目への複数線を識別する。"""
    ports = [{}, {}]
    for side, (own, other, key, other_key) in enumerate((
            (left_y, right_y, "from", "to"),
            (right_y, left_y, "to", "from"))):
        grouped = defaultdict(list)
        for index, link in enumerate(links):
            grouped[link[key]].append(index)
        for item_id, indices in grouped.items():
            indices.sort(key=lambda index: (other[links[index][other_key]], index))
            span = min(0.42, row_h - 0.20) if len(indices) > 1 else 0.0
            if len(indices) > 1 and span / (len(indices) - 1) < 0.055:
                raise FitError("relationship_map: 接続端点の間隔を確保できません。"
                               "関係線を減らすか、複数スライドへ分割してください。")
            for rank, index in enumerate(indices):
                ports[side][index] = own[item_id] + row_h / 2 + (
                    -span / 2 + rank * span / (len(indices) - 1)
                    if len(indices) > 1 else 0.0)
    return [(ports[0][index], ports[1][index]) for index in range(len(links))]


def s_mapping(slide, spec, page):
    """左右の項目間に一対多・多対多の対応線を描く。"""
    area = header(slide, spec["kicker"], spec["title"], spec.get("lead"))
    left_items, right_items = spec["left_items"], spec["right_items"]
    links = spec["links"]
    left_items, right_items, _crossings = _mapping_items_by_min_crossings(
        left_items, right_items, links)
    top = area.top + 0.22
    body_bottom = area.bottom - 0.10
    max_count = max(len(left_items), len(right_items))
    sparse = max_count <= 2
    fitted = _fit_rows(
        "relationship_map", body_bottom - top - 0.52, max_count,
        row_h=0.82 if sparse else 0.58,
        min_row_h=0.58 if sparse else 0.42,
        gap=0.22 if sparse else 0.13,
        min_gap=0.12 if sparse else 0.04,
        font=15.0 if sparse else 13.5, min_font=10.0,
    )
    values = fitted.values
    left_x, left_w = MARGIN + 0.16, 4.60
    right_x = MARGIN + BODY_W - left_w - 0.16
    right_w = left_w
    header_h = 0.48
    for x, width, label, text_x in (
        (left_x, left_w, spec["left_label"], left_x + 0.52),
        (right_x, right_w, spec["right_label"], right_x + 0.18),
    ):
        add_text(slide, text_x, top, width - 0.70, header_h, label, 14.0,
                 bold=True, color=NAVY, anchor=MSO_ANCHOR.MIDDLE)
        plain_line(slide, x, top + header_h, x + width, top + header_h,
                   color=ACCENT, width=1.1)
    start_y = top + header_h + 0.08

    def positions(items):
        return {
            item["id"]: start_y + i * (values["row_h"] + values["gap"])
            for i, item in enumerate(items)
        }

    left_y, right_y = positions(left_items), positions(right_items)
    def draw_items(items, y_by_id, x, width, side):
        for index, item in enumerate(items):
            y = y_by_id[item["id"]]
            box = _flat_rect(slide, x, y, width, values["row_h"],
                             ZEBRA if side == "left" else LIGHT)
            box.name = f"mapping:item:{side}:{item['id']}"
            marker_x = x + 0.25 if side == "left" else x + width - 0.25
            _dot(slide, marker_x, y + values["row_h"] / 2, ACCENT, 0.25)
            add_text(slide, marker_x - 0.12, y + values["row_h"] / 2 - 0.12,
                     0.24, 0.24, f"{index + 1}", 8.5, bold=True, color=WHITE,
                     align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
            text_x = x + 0.52 if side == "left" else x + 0.18
            text_w = width - 0.70
            try:
                text = _text_in_box(slide, "relationship_map", f"{side}_items[{index}].text",
                             text_x, y, text_w, values["row_h"], item["text"],
                             values["font"], 9.5, bold=True, color=NAVY,
                             anchor=MSO_ANCHOR.MIDDLE)
            except FitError as error:
                raise FitError(f"{error} 関係を論点ごとに分割してください。") from None
            text.name = f"mapping:text:{side}:{item['id']}"
            if index < len(items) - 1:
                plain_line(slide, text_x, y + values["row_h"],
                           x + width - 0.18 if side == "left" else marker_x - 0.34,
                           y + values["row_h"], color=RULE, width=0.45)

    gap_left = left_x + left_w
    gap_right = right_x
    endpoints = _mapping_ports(left_y, right_y, values["row_h"], links)
    # 参考スライドと同じく、項目間を直接追えることを優先する。線を先に描き、
    # 項目と端点を前面へ置くことで、交差があっても接続元と接続先を見失いにくくする。
    for index, (link, (sy, ty)) in enumerate(zip(links, endpoints)):
        color = ACCENT if link.get("emphasis") else GRAY
        width = 1.4 if link.get("emphasis") else 1.0
        # 後から描く線の下へ背景色の縁を置き、交点で線が連結して見える
        # 誤読を防ぐ。端点は項目描画後に置き直す。
        mask = plain_line(slide, gap_left, sy, gap_right, ty,
                          color=CANVAS, width=3.6)
        mask.name = f"mapping:crossing-mask:{index}"
        arrow = add_arrow(slide, gap_left, sy, gap_right, ty,
                          color=color, width=width)
        arrow.name = f"mapping:link:{index}"
    draw_items(left_items, left_y, left_x, left_w, "left")
    draw_items(right_items, right_y, right_x, right_w, "right")
    for index, (link, (sy, ty)) in enumerate(zip(links, endpoints)):
        color = ACCENT if link.get("emphasis") else GRAY
        for side, x, y in (("left", gap_left, sy), ("right", gap_right, ty)):
            dot = _dot(slide, x, y, color, 0.06)
            dot.name = f"mapping:port:{side}:{index}"
def _swimlane_step_rects(spec, x0, y0, stage_w, lane_h):
    return _swimlane_layout.step_rects(spec, x0, y0, stage_w, lane_h)



def _circled_step_number(index):
    """工程順を視線の入口にする。20件超は通常数字へ安全にフォールバックする。"""
    return chr(0x2460 + index) if 0 <= index < 20 else f"{index + 1}."


def _swimlane_step_label(step, index):
    number = step.get("number", index + 1)
    if number is None:
        return step["name"]
    return f"{_circled_step_number(number - 1)} {step['name']}"


def _swimlane_header(slide, spec):
    """全type共通のヘッダー階層を使い、本文開始位置を返す。"""
    return header(slide, spec["kicker"], spec["title"], spec.get("lead"))


def _swimlane_label(slide, field, x, y, w, h, text, max_pt, min_pt):
    """標準文字で2行へ折り返してから縮小し、最小値でも入らなければ停止する。"""
    try:
        size, lines = fit_text_or_raise(
            "swimlane_flow", field, text, w, h - 0.04, max_pt,
            min_pt=min_pt, weight="bold", spacing=1.10, wrapper=wrap_compact,
            line_validator=lambda candidate: len(candidate) <= 2,
            role="compact")
    except FitError as error:
        raise FitError(f"{error} 担当・工程を複数スライドへ分割してください。") from None
    return add_text(slide, x, y, w, h, "\n".join(lines), size,
                    bold=True, color=SWIMLANE_NAVY, align=PP_ALIGN.CENTER,
                    anchor=MSO_ANCHOR.MIDDLE, spacing=1.10, wrap=False)


def s_swimlane(slide, spec, page):
    """計画済みのセル・経路を、背景→接続→工程の順で描く。"""
    area = _swimlane_header(slide, spec)
    plan = _swimlane_layout.plan_swimlane(spec, area)
    _draw_swimlane_frame(slide, spec, plan)
    _draw_swimlane_edges(slide, spec, plan)
    _draw_swimlane_steps(slide, spec, plan)


def _draw_swimlane_frame(slide, spec, plan):
    lanes, stages = spec["lanes"], spec["stages"]
    frame_x, frame_w = SWIMLANE.frame_x, SWIMLANE.frame_width
    top, stage_h = plan.top, SWIMLANE.stage_height
    lane_label_w, stage_w = plan.lane_label_w, plan.stage_w
    lane_h, lane_y0, x0 = plan.fitted.values["row_h"], plan.lane_y0, plan.x0
    show_line_legend = plan.show_line_legend
    for index, stage in enumerate(stages):
        x = x0 + index * stage_w
        shape = slide.shapes.add_shape(
            MSO_SHAPE.CHEVRON, Inches(x), Inches(top),
            Inches(stage_w + (0.04 if index < len(stages) - 1 else 0)),
            Inches(stage_h))
        shape.fill.solid()
        shape.fill.fore_color.rgb = CANVAS
        shape.line.color.rgb = SWIMLANE_RULE
        shape.line.width = Pt(0.85)
        shape.name = (
            f"{SURFACE_ON_CANVAS_PREFIX}swimlane-stage:{stage['id']}")
        _flatten_shape(shape)
        caption = _swimlane_label(slide, f"stages[{index}].label",
                                 x + 0.14, top + 0.025, stage_w - 0.28, 0.32,
                                 stage["label"], 10.5, SWIMLANE.stage_min_pt)
        caption.name = f"swimlane:stage-label:{stage['id']}"
    if show_line_legend:
        legend_x = frame_x + 0.08
        add_text(slide, legend_x, top + 0.01, 0.28, 0.18,
                 "凡例", 7.5, bold=True, color=GRAY,
                 anchor=MSO_ANCHOR.MIDDLE)
        add_arrow(slide, legend_x + 0.36, top + 0.13,
                  legend_x + 0.62, top + 0.13, color=SWIMLANE_ACCENT, width=1.15)
        add_text(slide, legend_x + 0.68, top + 0.04, 0.42, 0.18,
                 "順方向", 7.0, color=SWIMLANE_NAVY,
                 anchor=MSO_ANCHOR.MIDDLE)
        add_arrow(slide, legend_x + 0.36, top + 0.31,
                  legend_x + 0.62, top + 0.31, color=SWIMLANE_ACCENT, width=1.15,
                  dash="dash")
        add_text(slide, legend_x + 0.68, top + 0.22, 0.42, 0.18,
                 "差戻し", 7.0, color=SWIMLANE_NAVY,
                 anchor=MSO_ANCHOR.MIDDLE)
    for index, lane in enumerate(lanes):
        y = lane_y0 + index * lane_h
        label_bg = _flat_rect(slide, frame_x, y, lane_label_w, lane_h, SWIMLANE_LIGHT)
        label_bg.name = f"swimlane:lane-background:label:{lane['id']}"
        canvas_bg = _flat_rect(slide, x0, y, frame_w - lane_label_w, lane_h, CANVAS)
        canvas_bg.name = f"swimlane:lane-background:canvas:{lane['id']}"
        lane_text_w = lane_label_w - 0.22
        label = _swimlane_label(slide, f"lanes[{index}].label",
                               frame_x + 0.12, y, lane_text_w, lane_h,
                               lane["label"], 13.0, SWIMLANE.lane_min_pt)
        label.name = f"swimlane:lane-label:{lane['id']}"
    # 後続レーンの背景で前レーンの下罫線が隠れないよう、境界は全背景の後に描く。
    for index, lane in enumerate(lanes):
        y = lane_y0 + (index + 1) * lane_h
        boundary = plain_line(slide, frame_x, y, frame_x + frame_w, y,
                              color=SWIMLANE_RULE, width=0.8)
        boundary.name = f"swimlane:lane-boundary:{lane['id']}"
    # レーン背景が矢羽根の下辺を覆うため、工程帯の境界を最後に引き直す。
    plain_line(slide, x0, lane_y0, frame_x + frame_w, lane_y0,
               color=SWIMLANE_RULE, width=0.85)
    plain_line(slide, x0, lane_y0, x0, lane_y0 + len(lanes) * lane_h,
               color=SWIMLANE_RULE, width=0.8)
    for index in range(1, len(stages)):
        x = x0 + index * stage_w
        plain_line(slide, x, lane_y0, x, lane_y0 + len(lanes) * lane_h,
                   color=SWIMLANE_RULE, width=0.55)


def _draw_swimlane_edges(slide, spec, plan):
    for edge_index, (edge, points) in enumerate(zip(spec["edges"], plan.paths)):
        before_route = len(slide.shapes)
        route(slide, points,
              dash="dash" if edge.get("kind") == "feedback" else None,
              width=1.10, color=SWIMLANE_ACCENT)
        for part, shape in enumerate(list(slide.shapes)[before_route:]):
            shape.name = f"swimlane:edge:{edge_index}:{part}"


def _draw_swimlane_steps(slide, spec, plan):
    rects, fitted = plan.rects, plan.fitted
    for index, step in enumerate(spec["steps"]):
        x, y, w, h = rects[step["id"]]
        box = _flat_rect(slide, x, y, w, h,
                   SWIMLANE_LIGHT if step.get("style") == "accent"
                   else SURFACE,
                   line=SWIMLANE_ACCENT)
        box.name = f"swimlane:step:{step['id']}"
        display_name = _swimlane_step_label(step, index)
        label = _swimlane_label(slide, f"steps[{index}].name",
                               x + 0.06, y, w - 0.12, h, display_name,
                               max(SWIMLANE.node_min_pt, min(11.5, fitted.values["font"])), SWIMLANE.node_min_pt)
        label.name = f"swimlane:step-label:{step['id']}"

def s_sequence(slide, spec, page):
    """参加者間のメッセージを上から下へ時系列表示する。"""
    area = header(slide, spec["kicker"], spec["title"], spec.get("lead"))
    participants, messages = spec["participants"], spec["messages"]
    phases = spec.get("phases", [])
    kinds = {message.get("kind", "request") for message in messages}
    show_legend = len(kinds) > 1
    legend_h = 0.16 if show_legend else 0.0
    top = area.top + 0.16
    header_h = 0.46
    message_top = top + header_h + 0.14
    available = area.bottom - message_top - legend_h - 0.12
    sparse = len(messages) <= 4
    fitted = _fit_rows(
        "message_sequence", available, len(messages),
        row_h=0.78 if sparse else 0.42,
        min_row_h=0.56 if sparse else 0.29,
        gap=0.34 if sparse else 0.12,
        min_gap=0.16 if sparse else 0.02,
        font=13.5 if sparse else 10.5, min_font=8.0,
    )
    sequence_center = MARGIN + BODY_W / 2
    half_span = (4.18 if len(participants) <= 3
                 else min(4.45, 2.80 + 0.55 * (len(participants) - 2)))
    participant_x0 = sequence_center - half_span
    participant_x1 = sequence_center + half_span
    used_h = (len(messages) * fitted.values["row_h"]
              + max(0, len(messages) - 1) * fitted.values["gap"])
    message_top += max(0.0, available - used_h) * 0.28
    xs = [participant_x0 + i * (participant_x1 - participant_x0) / (len(participants) - 1)
          for i in range(len(participants))]
    x_by_id = {participant["id"]: x for participant, x in zip(participants, xs)}
    message_y = {
        message["id"]: message_top + i * (fitted.values["row_h"] + fitted.values["gap"])
        for i, message in enumerate(messages)
    }
    index_by_id = {message["id"]: index for index, message in enumerate(messages)}
    message_fill = {message["id"]: CANVAS for message in messages}
    lifeline_bottom = message_y[messages[-1]["id"]] + fitted.values["row_h"] + 0.08
    for phase_index, phase in enumerate(phases):
        start_index = index_by_id[phase["from"]]
        end_index = index_by_id[phase["to"]]
        start_center = (message_y[messages[start_index]["id"]]
                        + fitted.values["row_h"] / 2)
        # ラベル上端をフェーズ境界にし、直前フェーズの背景が文字へ重ならないようにする。
        y1 = start_center - 0.28
        if end_index + 1 < len(messages):
            next_center = (message_y[messages[end_index + 1]["id"]]
                           + fitted.values["row_h"] / 2)
            y2 = next_center - 0.29
        else:
            y2 = lifeline_bottom
        # 左端ライフラインより手前をフェーズ名専用のレールにする。
        # 矢印上のラベル背景へ重ねず、参加者の中心位置・メッセージ行高も保つ。
        phase_x = participant_x0 - 1.50
        phase_w = participant_x1 - phase_x + 0.48
        phase_fill = LIGHT if phase_index % 2 == 0 else ZEBRA
        _flat_rect(slide, phase_x, y1, phase_w, y2 - y1,
                   phase_fill)
        for message in messages[start_index:end_index + 1]:
            message_fill[message["id"]] = phase_fill
        phase_h = min(0.56, y2 - y1 - 0.08)
        phase_size, phase_lines = fit_text_or_raise(
            "message_sequence", f"phases[{phase_index}].label", phase["label"],
            1.20, phase_h, 10.5, min_pt=9.5,
            weight="bold", spacing=1.05, role="compact")
        phase_box = add_text(
            slide, phase_x + 0.12, y1 + 0.04, 1.20, phase_h,
            "\n".join(phase_lines), phase_size, bold=True, color=ACCENT,
            align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
            spacing=1.05, role="compact", wrap=False)
        phase_box.name = f"sequence-phase-label:{phase_index}"
        phase_box.fill.solid()
        phase_box.fill.fore_color.rgb = LIGHT if phase_index % 2 == 0 else ZEBRA
    for index, (participant, x) in enumerate(zip(participants, xs)):
        box_w = min(2.08 if sparse else 1.74,
                    (participant_x1 - participant_x0) / len(participants) * 0.88)
        _text_in_box(slide, "message_sequence", f"participants[{index}].label",
                     x - box_w / 2 + 0.08, top, box_w - 0.16, header_h,
                     participant["label"], 12.5 if sparse else 11.0, 8.5,
                     bold=True, color=NAVY,
                     align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE,
                     role="compact")
        plain_line(slide, x - box_w / 2 + 0.08, top + header_h,
                   x + box_w / 2 - 0.08, top + header_h,
                   color=RULE, width=0.8)
        lifeline = plain_line(slide, x, top + header_h, x, lifeline_bottom,
                              color=RULE, width=0.60)
        lifeline.name = f"{SEQUENCE_LIFELINE_PREFIX}{participant['id']}"
    for index, message in enumerate(messages):
        y = message_y[message["id"]] + fitted.values["row_h"] / 2
        sx, tx = x_by_id[message["from"]], x_by_id[message["to"]]
        kind = message.get("kind", "request")
        message_color = ACCENT if kind == "async" else GRAY if kind == "return" else NAVY
        if sx == tx:
            loop_w, loop_h = 0.54, max(0.26, fitted.values["row_h"] * 0.76)
            dash = "dash" if message.get("kind") == "return" else None
            # 自己処理は割り当て行の上側で完結させ、次行のラベル領域を侵食しない。
            route_top = y - loop_h
            route_bottom = y
            route_right = sx + loop_w
            outgoing = plain_line(
                slide, sx, route_top, route_right, route_top,
                color=message_color, width=1.25)
            turn = plain_line(
                slide, route_right, route_top, route_right, route_bottom,
                color=message_color, width=1.25)
            returned = add_arrow(
                slide, route_right, route_bottom, sx, route_bottom,
                color=message_color, width=1.25)
            self_route = (outgoing, turn, returned)
            for segment, role in zip(self_route, ("out", "turn", "return")):
                segment.name = f"{SEQUENCE_SELF_ROUTE_PREFIX}{message['id']}:{role}"
                if dash:
                    segment.line.dash_style = MSO_LINE_DASH_STYLE.DASH
            # ラベルをループ外へ置き、自己処理を示す3辺を背景マスクで隠さない。
            label_w = 1.10
            label_left = route_right + 0.10
            label_x = label_left + label_w / 2
        else:
            arrow = add_arrow(slide, sx, y, tx, y,
                              color=message_color, width=1.25)
            if kind == "return":
                # 公開APIでsolidFill→prstDashの順序を守る。逆順では
                # PowerPointが明示色を無視してテーマ色の青へ戻す場合がある。
                arrow.line.dash_style = MSO_LINE_DASH_STYLE.DASH
            arrow.name = f"sequence-message-line:{message['id']}"
            label_x, label_w = (sx + tx) / 2, min(1.72, abs(tx - sx) - 0.10)
        label_y = y - 0.27
        label_size, lines = fit_text_or_raise(
            "message_sequence", f"messages[{index}].label", message["label"],
            label_w, 0.24, fitted.values["font"], min_pt=7.5,
            weight="bold", spacing=1.0, role="compact")
        tb = add_text(slide, label_x - label_w / 2, label_y, label_w, 0.24,
                      "\n".join(lines), label_size, bold=True, color=NAVY,
                      align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE,
                      spacing=1.0, role="compact")
        tb.fill.solid()
        tb.fill.fore_color.rgb = message_fill[message["id"]]
        tb.name = f"{SEQUENCE_MESSAGE_LABEL_PREFIX}{message['id']}"
    if show_legend:
        legend_y = area.bottom - 0.17
        legend_x = MARGIN + 0.10
        add_text(slide, legend_x, legend_y, 0.38, 0.18, "凡例", 7.5,
                 bold=True, color=GRAY, anchor=MSO_ANCHOR.MIDDLE)
        entries = [("要求", NAVY, None), ("応答", GRAY, "dash")]
        if "async" in kinds:
            entries.append(("非同期", ACCENT, None))
        for index, (label, color, dash) in enumerate(entries):
            x = legend_x + 0.48 + index * 1.05
            legend_line = add_arrow(slide, x, legend_y + 0.09, x + 0.28, legend_y + 0.09,
                                    color=color, width=1.0)
            if dash:
                legend_line.line.dash_style = MSO_LINE_DASH_STYLE.DASH
            add_text(slide, x + 0.34, legend_y, 0.56, 0.18, label, 7.5,
                     color=TEXT, anchor=MSO_ANCHOR.MIDDLE)
