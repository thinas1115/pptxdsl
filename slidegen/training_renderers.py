"""技術研修で使う概念説明、ネットワーク、プロトコル、実習renderer。"""

import math

from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

from slidegen.asset_paths import resolve_icon_path
from slidegen import network_layout as _network_layout
from slidegen import protocol_state_layout as _protocol_layout
from slidegen.layout_settings import NETWORK, PROTOCOL
from slidegen.diagrams import add_arrow, arrow_label, set_line_dash
from slidegen.generate import (
    ACCENT,
    BODY_W,
    CANVAS,
    CORAL,
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
from slidegen.layout_fit import FitError, fit_text_or_raise, select_fit, stepped
from slidegen.textfit import line_height_in, text_width_in, wrap_text


_LANE_PALETTE = (
    (RGBColor(0xD9, 0xEB, 0xE8), ACCENT),
    (RGBColor(0xE4, 0xE9, 0xEE), NAVY),
    (RGBColor(0xF1, 0xE3, 0xDF), CORAL),
    (RGBColor(0xEA, 0xE8, 0xE2), GRAY),
)
_FIELD_FILLS = {
    "standard": (SURFACE, NAVY),
    "muted": (ZEBRA, GRAY),
    "highlight": (LIGHT, ACCENT),
    "alert": (RGBColor(0xF1, 0xE3, 0xDF), CORAL),
}


def _fit_concept(area, definition, points):
    left_w = 5.45
    right_w = BODY_W - left_w - 0.72
    available = area.height - 0.34 - 0.08

    def used(values):
        definition_h = len(wrap_text(
            definition, left_w - 0.10, values["definition_font"], "regular"
        )) * line_height_in(values["definition_font"], 1.18)
        left_h = 0.96 + definition_h
        right_h = 0.0
        for point in points:
            label_h = len(wrap_text(
                point["label"], right_w, values["label_font"], "bold"
            )) * line_height_in(values["label_font"], 1.08)
            text_h = len(wrap_text(
                point["text"], right_w, values["body_font"], "regular"
            )) * line_height_in(values["body_font"], 1.14)
            right_h += label_h + text_h + values["inside_gap"]
        right_h += max(0, len(points) - 1) * values["row_gap"]
        return max(left_h, right_h)

    def candidates():
        standard = {
            "definition_font": 18.5, "label_font": 13.0,
            "body_font": 15.0, "inside_gap": 0.12, "row_gap": 0.28,
        }
        yield "standard", standard, used(standard)
        for row_gap in stepped(0.22, 0.08, 0.035):
            values = dict(standard, row_gap=row_gap)
            yield "gap", values, used(values)
        for body_font in stepped(14.5, 12.5, 0.5):
            values = {
                "definition_font": max(17.0, body_font + 4.5),
                "label_font": max(11.5, body_font - 2.0),
                "body_font": body_font,
                "inside_gap": 0.08,
                "row_gap": 0.08,
            }
            yield "font", values, used(values)

    return select_fit(
        "concept", available, candidates(),
        guidance="要点を4件以内へ絞るか、定義と説明を短くしてください。",
    )


def s_concept(slide, spec, page):
    """技術用語を定義し、理解に必要な観点を並べる。"""
    area = header(slide, spec["kicker"], spec["title"], spec.get("lead"))
    points = spec["points"]
    fitted = _fit_concept(area, spec["definition"], points)
    values = fitted.values

    top = area.top + 0.34
    left_w = 5.45
    divider_x = MARGIN + left_w + 0.34
    right_x = divider_x + 0.38
    right_w = MARGIN + BODY_W - right_x
    content_bottom = area.bottom - 0.10

    term_x = MARGIN + 0.04
    term_w = left_w - 0.10
    definition_x = MARGIN + 0.04
    definition_w = left_w - 0.10
    if spec.get("icon"):
        icon_path = resolve_icon_path(spec["icon"])
        icon_size = 0.60
        slide.shapes.add_picture(
            str(icon_path), Inches(MARGIN + 0.04), Inches(top + 0.06),
            Inches(icon_size), Inches(icon_size),
        )
        term_x += 0.84
        term_w -= 0.84
    term_size, term_lines = fit_text_or_raise(
        "concept", "term", spec["term"], term_w, 0.72, 30.0,
        min_pt=23.5, weight="bold", spacing=1.0, role="natural",
    )
    add_text(
        slide, term_x, top, term_w, 0.72, "\n".join(term_lines), term_size,
        bold=True, color=NAVY, anchor=MSO_ANCHOR.MIDDLE, spacing=1.0,
    )

    definition_y = top + 0.96
    definition_h = content_bottom - definition_y
    definition_size, definition_lines = fit_text_or_raise(
        "concept", "definition", spec["definition"], definition_w,
        definition_h, values["definition_font"], min_pt=16.5,
        spacing=1.18, role="natural",
    )
    add_text(
        slide, definition_x, definition_y, definition_w, definition_h,
        "\n".join(definition_lines), definition_size, color=TEXT,
        spacing=1.18,
    )

    add_rect(slide, divider_x, top, 0.01, content_bottom - top, RULE)
    row_h = (content_bottom - top) / len(points)
    for index, point in enumerate(points):
        y = top + index * row_h
        label_size, label_lines = fit_text_or_raise(
            "concept", f"points[{index}].label", point["label"],
            right_w, 0.34, values["label_font"], min_pt=11.5,
            weight="bold", spacing=1.08, role="compact",
        )
        label_h = len(label_lines) * line_height_in(label_size, 1.08) + 0.02
        add_text(
            slide, right_x, y + 0.03, right_w, label_h,
            "\n".join(label_lines), label_size, bold=True, color=ACCENT,
            spacing=1.08, role="compact",
        )
        body_y = y + label_h + values["inside_gap"]
        body_size, body_lines = fit_text_or_raise(
            "concept", f"points[{index}].text", point["text"],
            right_w, row_h - (body_y - y) - 0.08, values["body_font"],
            min_pt=12.5, spacing=1.14, role="body",
        )
        add_text(
            slide, right_x, body_y, right_w, row_h - (body_y - y) - 0.08,
            "\n".join(body_lines), body_size, color=TEXT, spacing=1.14,
        )
        if index < len(points) - 1:
            add_rect(slide, right_x, y + row_h - 0.02, right_w, 0.008, RULE)


def _set_connector_arrow(connector, *, both=False, dash=None):
    ln = connector.line._get_or_add_ln()
    for tag, enabled in (("a:headEnd", both), ("a:tailEnd", True)):
        if enabled:
            ln.append(ln.makeelement(
                qn(tag), {"type": "triangle", "w": "med", "len": "med"}))
    set_line_dash(connector, dash)


def _plain_connector(slide, x1, y1, x2, y2, color, *, width=1.6,
                     arrow=False, dash=None):
    conn = slide.shapes.add_connector(
        MSO_CONNECTOR.STRAIGHT,
        Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    conn.line.color.rgb = color
    conn.line.width = Pt(width)
    conn.shadow.inherit = False
    if arrow:
        _set_connector_arrow(conn, dash=dash)
    elif dash:
        set_line_dash(conn, dash)
    return conn


def _route_colored(slide, points, color, *, width=1.6, dash=None):
    for start, end in zip(points[:-2], points[1:-1]):
        _plain_connector(slide, *start, *end, color, width=width, dash=dash)
    add_arrow(slide, *points[-2], *points[-1], color=color,
              width=width, dash=dash)


def _compact_lane_names(labels):
    return _network_layout.compact_lane_names(labels)



def _fit_network(area, lane_count, max_cell_nodes, legend_h=0.24):
    return _network_layout.fit_network(area, lane_count, max_cell_nodes, legend_h)



def _node_label(slide, x, y, width, text, font, *, sub=None, fill=CANVAS):
    title_size, title_lines = fit_text_or_raise(
        "nw_topology", "node.label", text, width - 0.08, 0.35, font,
        min_pt=NETWORK.node_title_min_pt, weight="bold", spacing=1.05, role="compact")
    rendered = "\n".join(title_lines)
    title_w = min(width, max(text_width_in(line, title_size, "bold") for line in title_lines) + 0.08)
    title_h = len(title_lines) * line_height_in(title_size, 1.05) + 0.02
    box = add_text(
        slide, x - title_w / 2, y, title_w, title_h, rendered, title_size,
        bold=True, color=NAVY, align=PP_ALIGN.CENTER,
        anchor=MSO_ANCHOR.MIDDLE, spacing=1.05, wrap=False, role="compact")
    box.name = "network-node:label"
    box.fill.solid()
    box.fill.fore_color.rgb = fill
    if sub:
        sub_size, sub_lines = fit_text_or_raise(
            "nw_topology", "node.sub", sub, width - 0.08, 0.28, font - 1.5,
            min_pt=NETWORK.node_sub_min_pt, spacing=1.0, role="compact")
        sub_h = len(sub_lines) * line_height_in(sub_size, 1.0) + 0.01
        sub_w = min(width, max(text_width_in(line, sub_size) for line in sub_lines) + 0.08)
        sub_box = add_text(
            slide, x - sub_w / 2, y + title_h + 0.01, sub_w, sub_h,
            "\n".join(sub_lines), sub_size, color=GRAY,
            align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, spacing=1.0, wrap=False, role="compact")
        sub_box.name = "network-node:sub"
        sub_box.fill.solid()
        sub_box.fill.fore_color.rgb = fill




def _network_legend(links):
    return _network_layout.network_legend(links)



def s_network(slide, spec, page):
    """配置・配線計画を作り、背景→接続→機器→凡例の順で描く。"""
    area = header(slide, spec["kicker"], spec["title"], spec.get("lead"))
    plan = _network_layout.plan_network(spec, area)
    _draw_network_lanes(slide, spec, plan)
    _draw_network_ports(slide, spec, plan)
    _draw_network_links(slide, plan)
    _draw_network_nodes(slide, spec, plan)
    _draw_network_legend(slide, plan, area.bottom - plan.legend_h)


def _draw_network_lanes(slide, spec, plan):
    geometry = plan.geometry
    lane_h, gap = geometry.fitted.values["lane_h"], geometry.fitted.values["gap"]
    for index, lane in enumerate(spec["lanes"]):
        y = geometry.top + index * (lane_h + gap)
        fill, color = _LANE_PALETTE[index]
        background = add_rect(slide, MARGIN, y, BODY_W, lane_h, fill)
        background.name = f"layout-background:network-lane:{lane['id']}"
        label_w = geometry.lane_label_w - NETWORK.lane_label_padding
        label_size, label_lines = fit_text_or_raise(
            "nw_topology", "lane.label", lane["label"], label_w, 0.30,
            NETWORK.lane_title_pt, min_pt=NETWORK.lane_title_min_pt,
            weight="bold", spacing=1.0, role="compact")
        add_text(slide, MARGIN + 0.16, y + 0.16, label_w, 0.30,
                 "\n".join(label_lines), label_size, bold=True, color=color,
                 anchor=MSO_ANCHOR.MIDDLE, spacing=1.0, wrap=False, role="compact")
        if lane.get("sub"):
            sub_h = lane_h - 0.49 - 0.08
            sub_size, sub_lines = fit_text_or_raise(
                "nw_topology", "lane.sub", lane["sub"], label_w, sub_h,
                NETWORK.lane_sub_pt, min_pt=NETWORK.lane_sub_min_pt, spacing=1.0, role="compact")
            box = add_text(slide, MARGIN + 0.16, y + 0.49, label_w, sub_h,
                           "\n".join(sub_lines), sub_size, color=GRAY,
                           spacing=1.0, wrap=False, role="compact")
            box.name = f"network-lane:sub:{lane['id']}"
    for column in spec["columns"]:
        if column.get("label"):
            add_text(slide, geometry.col_centers[column["id"]] - geometry.col_gap / 2,
                     geometry.top - 0.33, geometry.col_gap, 0.22, column["label"], 9,
                     bold=True, color=GRAY, align=PP_ALIGN.CENTER)


def _draw_network_ports(slide, spec, plan):
    geometry = plan.geometry
    icon_size = geometry.fitted.values["icon"]
    for node in spec["nodes"]:
        if len(node["lanes"]) <= 1:
            continue
        x, node_y = geometry.positions[node["id"]]
        ordered = sorted(node["lanes"], key=geometry.lane_index.get)
        rail_top, rail_bottom = geometry.lane_centers[ordered[0]], geometry.lane_centers[ordered[-1]]
        clearance = icon_size / 2 + 0.09
        if rail_top < node_y - clearance:
            _plain_connector(slide, x, rail_top, x, node_y - clearance, RULE, width=2.0)
        if node_y + clearance < rail_bottom:
            _plain_connector(slide, x, node_y + clearance, x, rail_bottom, RULE, width=2.0)
        for lane_id in ordered:
            port = slide.shapes.add_shape(MSO_SHAPE.OVAL,
                Inches(x - 0.045), Inches(geometry.lane_centers[lane_id] - 0.045),
                Inches(0.09), Inches(0.09))
            port.fill.solid()
            port.fill.fore_color.rgb = NAVY
            port.line.fill.background()
            port.shadow.inherit = False


def _draw_network_label(slide, label):
    if label is None:
        return
    if not label.trunk:
        arrow_label(slide, label.x, label.y, label.text, w=label.width, size=label.size)
        return
    box = add_text(slide, label.x, label.y, label.width, 0.34, label.text,
                   label.size, bold=True, color=NAVY, align=PP_ALIGN.CENTER,
                   anchor=MSO_ANCHOR.MIDDLE, spacing=1.0, wrap=False, role="compact")
    box.name = "network-link:trunk-label"
    box.fill.solid()
    box.fill.fore_color.rgb = CANVAS


def _draw_network_links(slide, plan):
    geometry = plan.geometry
    for route in plan.broadcasts:
        _plain_connector(slide, route.start[0], route.start[1], route.start[0], route.channel_y,
                         CORAL, width=2.2)
        _plain_connector(slide, route.start[0], route.channel_y, route.bus_end_x, route.channel_y,
                         CORAL, width=2.2)
        for end in route.ends:
            add_arrow(slide, end[0], route.channel_y, end[0], end[1], color=CORAL, width=2.2)
        _draw_network_label(slide, route.label)
    for link in plan.links:
        if link.physical is not None:
            physical = _plain_connector(slide, *link.physical[0], *link.physical[1], GRAY, width=1.5)
            physical.name = f"network-link:physical:{link.index}"
            for start, end, lane in link.trunk_lanes:
                _plain_connector(slide, *start, *end, _LANE_PALETTE[geometry.lane_index[lane]][1], width=2.0)
            _draw_network_label(slide, link.label)
            continue
        color = (_LANE_PALETTE[geometry.lane_index[link.color[5:]]][1]
                 if link.color.startswith("lane:") else
                 CORAL if link.color == "coral" else NAVY if link.color == "navy" else GRAY)
        if link.stop is not None:
            for start, end in zip(link.points, link.points[1:]):
                _plain_connector(slide, *start, *end, CORAL, width=1.8, dash="dash")
            middle_x, boundary_y = link.stop
            add_text(slide, middle_x - 0.19, boundary_y - 0.17, 0.38, 0.34,
                     "×", 18, bold=True, color=CORAL, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        elif len(link.points) == 2:
            add_arrow(slide, *link.start, *link.end, color=color,
                      width=2.2 if link.kind == "broadcast" else 1.6,
                      dash="dash" if link.kind == "control" else None)
        else:
            _route_colored(slide, link.points, color,
                           width=2.2 if link.kind == "broadcast" else 1.6,
                           dash="dash" if link.kind == "control" else None)
        _draw_network_label(slide, link.label)


def _draw_network_nodes(slide, spec, plan):
    geometry = plan.geometry
    icon_size, font = geometry.fitted.values["icon"], geometry.fitted.values["font"]
    for node in spec["nodes"]:
        x, y = geometry.positions[node["id"]]
        node_fill = (_LANE_PALETTE[geometry.lane_index[node["lanes"][0]]][0]
                     if len(node["lanes"]) == 1 else CANVAS)
        halo = slide.shapes.add_shape(MSO_SHAPE.OVAL,
            Inches(x - icon_size / 2 - 0.06), Inches(y - icon_size / 2 - 0.06),
            Inches(icon_size + 0.12), Inches(icon_size + 0.12))
        halo.fill.solid()
        halo.fill.fore_color.rgb = node_fill
        halo.line.fill.background()
        halo.shadow.inherit = False
        icon_path = resolve_icon_path(node["icon"])
        slide.shapes.add_picture(str(icon_path), Inches(x - icon_size / 2), Inches(y - icon_size / 2),
                                Inches(icon_size), Inches(icon_size))
        group_size = len(geometry.placement_groups[(node["column"],
            tuple(sorted(node["lanes"], key=geometry.lane_index.get)))])
        label_width = min(1.68, geometry.col_gap * (0.44 if group_size > 1 else 0.92))
        _node_label(slide, x, y + icon_size / 2 + 0.08, label_width, node["label"], font,
                    sub=node.get("sub"), fill=node_fill)


def _draw_network_legend(slide, plan, legend_y):
    for row_index, row in enumerate(plan.legend_rows):
        x = MARGIN + 0.08
        y = legend_y + row_index * 0.34
        for kind, label, width in row:
            color = (CORAL if kind in {"broadcast", "blocked"} else
                     ACCENT if kind in {"access", "trunk"} else GRAY if kind == "physical" else NAVY)
            if kind == "trunk":
                for dy, line_color in ((0.05, ACCENT), (0.13, NAVY)):
                    _plain_connector(slide, x, y + dy, x + 0.28, y + dy, line_color, width=2.0)
            else:
                _plain_connector(slide, x, y + 0.09, x + 0.28, y + 0.09, color,
                                 width=2.2 if kind == "broadcast" else 1.5,
                                 arrow=kind in {"access", "routed", "broadcast"},
                                 dash="dash" if kind in {"control", "blocked"} else None)
            box = add_text(slide, x + 0.36, y, width - 0.36, NETWORK.legend_row_height,
                           label, NETWORK.legend_pt, color=TEXT, spacing=1.0, wrap=False, role="compact")
            box.name = f"network-legend:{kind}"
            x += width + 0.24



_PROTOCOL_APPEARANCES = {
    "plain": "通常の値",
    "encapsulated": "タグ・ヘッダー付加",
    "internal": "装置内部処理",
    "alert": "異常・要確認",
}


def _protocol_changed_stages(stages, states):
    return _protocol_layout.changed_stages(stages, states)



def _fit_protocol_state_flow(area, stages, flows):
    return _protocol_layout.fit_protocol_state_flow(area, stages, flows)



def _protocol_state_marker(
        slide, cx, y, width, appearance, encapsulation=None):
    marker_w = min(1.02, width * 0.72)
    marker_h = 0.20
    x = cx - marker_w / 2
    if appearance == "internal":
        marker = add_rect(slide, x, y + 0.08, marker_w, 0.04, NAVY)
        marker.name = "protocol-state-flow:marker:internal"
        return marker_w
    fill = RGBColor(0xF9, 0xF8, 0xF4)
    line = CORAL if appearance == "alert" else NAVY
    marker = add_rect(slide, x, y, marker_w, marker_h, fill, line=line)
    marker.name = f"protocol-state-flow:marker:{appearance}"
    if appearance == "encapsulated":
        tag_w = min(
            marker_w * 0.48,
            max(0.20, text_width_in(encapsulation, 6.5, "bold") + 0.10),
        )
        tag = add_rect(slide, x, y, tag_w, marker_h, NAVY)
        tag.name = "protocol-state-flow:marker:encapsulated:tag"
        label_size, label_lines = fit_text_or_raise(
            "nw_protocol_flow", "state.encapsulation", encapsulation,
            tag_w - 0.04, marker_h - 0.02, 6.5, min_pt=5.5,
            weight="bold", spacing=1.0, role="compact",
        )
        add_text(
            slide, x + 0.02, y + 0.01, tag_w - 0.04, marker_h - 0.02,
            "\n".join(label_lines), label_size,
            bold=True, color=WHITE, align=PP_ALIGN.CENTER,
            anchor=MSO_ANCHOR.MIDDLE, spacing=1.0, role="compact",
        )
    return marker_w


def _protocol_legend(slide, states, top):
    used = {state.get("appearance", "plain") for state in states}
    x = MARGIN
    for appearance, label in _PROTOCOL_APPEARANCES.items():
        if appearance not in used:
            continue
        start = len(slide.shapes)
        _protocol_state_marker(slide, x + 0.21, top, 0.42 / 0.72,
                               appearance, "＋")
        for shape in list(slide.shapes)[start:]:
            shape.name = "protocol-state-flow:legend:" + shape.name
        width = text_width_in(label, 9.0) + 0.04
        box = add_text(slide, x + 0.54, top, width, 0.22, label, 9.0,
                       color=TEXT, spacing=1.0, wrap=False, role="compact")
        box.name = f"protocol-state-flow:legend:{appearance}"
        x += 0.54 + width + 0.26
    label = "下線：直前から値・付加情報が変化"
    width = BODY_W - (x - MARGIN)
    size, lines = fit_text_or_raise(
        "nw_protocol_flow", "legend", label, width, 0.24, 9.0,
        min_pt=9.0, spacing=1.0, role="compact")
    box = add_text(slide, x, top, width, 0.24, "\n".join(lines), size,
                   color=CORAL, spacing=1.0, wrap=False, role="compact")
    box.name = "protocol-state-flow:legend:change"


def s_protocol_state_flow(slide, spec, page):
    """収容・状態順・変化点を計画し、凡例→段階→状態行を描く。"""
    area = header(slide, spec["kicker"], spec["title"], spec.get("lead"))
    plan = _protocol_layout.plan_protocol_state_flow(spec, area)
    _protocol_legend(slide, [state for flow in spec["flows"] for state in flow["states"]], area.top + 0.02)
    _draw_protocol_stages(slide, spec["stages"], plan)
    for flow_index, flow in enumerate(spec["flows"]):
        _draw_protocol_track(slide, flow_index, flow, plan)


def _draw_protocol_stages(slide, stages, plan):
    values, stage_centers = plan.fitted.values, plan.stage_centers
    stage_w, top = values["stage_w"], plan.top
    rows_top, rows_bottom = plan.rows_top, plan.rows_bottom
    for stage in stages:
        cx = stage_centers[stage["id"]]
        if stage.get("role") == "link":
            background = add_rect(
                slide, cx - stage_w / 2 - 0.03, rows_top - 0.08,
                stage_w + 0.06, rows_bottom - rows_top + 0.16,
                RGBColor(0xEA, 0xF0, 0xEF),
            )
            background.name = (
                f"layout-background:protocol-state-flow:stage:{stage['id']}"
            )
        icon_path = resolve_icon_path(stage["icon"])
        icon_size = values["icon_size"]
        slide.shapes.add_picture(
            str(icon_path), Inches(cx - icon_size / 2), Inches(top),
            Inches(icon_size), Inches(icon_size),
        )
        label_size, label_lines = fit_text_or_raise(
            "nw_protocol_flow", "stage.label", stage["label"],
            stage_w - 0.12, values["header_h"] - icon_size - 0.05,
            values["stage_font"], min_pt=PROTOCOL.stage_min_pt, weight="bold",
            spacing=1.0, role="compact",
        )
        add_text(
            slide, cx - stage_w / 2 + 0.06, top + icon_size + 0.06,
            stage_w - 0.12, values["header_h"] - icon_size - 0.04,
            "\n".join(label_lines), label_size, bold=True, color=NAVY,
            align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.TOP, spacing=1.0, role="compact",
        )



def _draw_protocol_track(slide, flow_index, flow, plan):
    values, stage_centers = plan.fitted.values, plan.stage_centers
    stage_w, rail_w = values["stage_w"], PROTOCOL.rail_width
    row_y, row_h = plan.rows[flow_index].top, plan.rows[flow_index].height
    fill, color = _LANE_PALETTE[flow_index % len(_LANE_PALETTE)]
    background = add_rect(slide, MARGIN, row_y, BODY_W, row_h, fill)
    background.name = (
        f"layout-background:protocol-state-flow:track:{flow_index}"
    )
    flow_label_size, flow_label_lines = fit_text_or_raise(
        "nw_protocol_flow", "flow.label", flow["label"],
        rail_w - 0.20, row_h - 0.32,
        values["flow_font"], min_pt=PROTOCOL.flow_min_pt, weight="bold",
        spacing=1.0, role="compact",
    )
    flow_label_h = (
        len(flow_label_lines) * line_height_in(flow_label_size, 1.0) + 0.02
    )
    add_text(
        slide, MARGIN + 0.10, row_y + 0.20,
        rail_w - 0.20, flow_label_h,
        "\n".join(flow_label_lines), flow_label_size,
        bold=True, color=color, spacing=1.0, role="compact",
    )
    if flow.get("sub"):
        flow_sub_y = row_y + 0.20 + flow_label_h + 0.04
        sub_size, sub_lines = fit_text_or_raise(
            "nw_protocol_flow", "flow.sub", flow["sub"],
            rail_w - 0.20, row_y + row_h - flow_sub_y - 0.10,
            values["flow_sub_font"], min_pt=PROTOCOL.detail_min_pt,
            spacing=1.0, role="compact",
        )
        add_text(
            slide, MARGIN + 0.10, flow_sub_y,
            rail_w - 0.20, row_y + row_h - flow_sub_y - 0.10,
            "\n".join(sub_lines), sub_size, color=GRAY, spacing=1.0, role="compact",
        )

    states = plan.rows[flow_index].states
    changed_stages = plan.rows[flow_index].changed
    marker_y = row_y + 0.18
    arrow_y = marker_y + 0.10
    marker_widths = {}
    for state in states:
        marker_widths[state["stage"]] = min(1.02, stage_w * 0.72)
    for left, right in zip(states, states[1:]):
        left_cx = stage_centers[left["stage"]]
        right_cx = stage_centers[right["stage"]]
        add_arrow(
            slide,
            left_cx + marker_widths[left["stage"]] / 2 + 0.04,
            arrow_y,
            right_cx - marker_widths[right["stage"]] / 2 - 0.04,
            arrow_y,
            color=color, width=1.6,
        )

    for state in states:
        cx = stage_centers[state["stage"]]
        _protocol_state_marker(
            slide, cx, marker_y, stage_w,
            state.get("appearance", "plain"),
            state.get("encapsulation"),
        )
        text_w = stage_w - 0.18
        title_size, title_lines = fit_text_or_raise(
            "nw_protocol_flow", "state.label", state["label"],
            text_w, row_h - 0.48, values["state_font"],
            min_pt=PROTOCOL.state_min_pt, weight="bold", spacing=1.0, role="compact",
        )
        title_y = marker_y + 0.30
        title_h = len(title_lines) * line_height_in(title_size, 1.0) + 0.03
        changed = state["stage"] in changed_stages
        value_box = add_text(
            slide, cx - text_w / 2, title_y, text_w, title_h,
            "\n".join(title_lines), title_size, bold=True,
            color=CORAL if changed else NAVY,
            align=PP_ALIGN.CENTER, spacing=1.0, role="compact",
        )
        value_box.name = (
            f"protocol-state-flow:value:{'changed' if changed else 'unchanged'}:"
            f"{flow_index}:{state['stage']}"
        )
        if changed:
            for paragraph in value_box.text_frame.paragraphs:
                for run in paragraph.runs:
                    run.font.underline = True
        if state.get("detail"):
            detail_y = title_y + title_h + 0.03
            detail_h = row_y + row_h - detail_y - 0.10
            detail_size, detail_lines = fit_text_or_raise(
                "nw_protocol_flow", "state.detail", state["detail"],
                text_w, detail_h, values["detail_font"],
                min_pt=PROTOCOL.detail_min_pt, spacing=1.0, role="compact",
            )
            add_text(
                slide, cx - text_w / 2, detail_y, text_w, detail_h,
                "\n".join(detail_lines), detail_size, color=GRAY,
                align=PP_ALIGN.CENTER, spacing=1.0, role="compact",
            )



_PROTOCOL_ANNOTATION_GAP = 0.14


def _fit_protocol(area, frames):
    available = area.height
    annotation_rows = [math.ceil(len(frame.get("annotations", [])) / 4) for frame in frames]

    def used(values):
        frame_block = (len(frames) * values["frame_h"]
                       + max(0, len(frames) - 1) * values["gap"])
        annotation_block = sum(
            _PROTOCOL_ANNOTATION_GAP + rows * values["annotation_row_h"]
            for rows in annotation_rows if rows
        )
        return 0.30 + frame_block + annotation_block + 0.08

    def candidates():
        for gap in stepped(0.28, 0.12, 0.04):
            values = {"frame_h": 0.92, "gap": gap,
                      "annotation_row_h": 0.66, "annotation_text_h": 0.48,
                      "font": 10.5, "annotation_font": 10.5}
            yield "standard" if gap == 0.28 else "gap", values, used(values)
        for frame_h in stepped(0.86, 0.70, 0.04):
            values = {"frame_h": frame_h, "gap": 0.12,
                      "annotation_row_h": 0.58, "annotation_text_h": 0.42,
                      "font": 9.5, "annotation_font": 9.5}
            yield "element", values, used(values)
        values = {"frame_h": 0.68, "gap": 0.10,
                  "annotation_row_h": 0.54, "annotation_text_h": 0.40,
                  "font": 8.5, "annotation_font": 8.5}
        yield "font", values, used(values)

    return select_fit(
        "nw_frame_anatomy", available, candidates(),
        guidance="フレーム数・フィールド数・注釈数を減らして分割してください。")


def s_protocol_anatomy(slide, spec, page):
    """フレームやパケットのフィールド構造を比較する。"""
    area = header(slide, spec["kicker"], spec["title"], spec.get("lead"))
    frames = spec["frames"]
    annotations = [
        (frame_index, annotation)
        for frame_index, frame in enumerate(frames)
        for annotation in frame.get("annotations", [])
    ]
    fitted = _fit_protocol(area, frames)
    values = fitted.values
    frame_h, gap, font = values["frame_h"], values["gap"], values["font"]
    label_w = 1.25
    frame_totals = [
        sum(field["bits"] for field in frame["fields"])
        for frame in frames
    ]
    min_total = min(frame_totals)
    max_total = max(frame_totals)
    compare_lengths = len(frames) > 1 and min_total != max_total
    length_label_w = 0.78 if compare_lengths else 0.0
    bar_x = MARGIN + label_w
    bar_w = BODY_W - label_w - length_label_w
    top = area.top + 0.30
    scale_note = add_text(
        slide, MARGIN, area.top + 0.02, BODY_W, 0.22,
        "幅はbit数に比例しない概念図", 9.0, color=TEXT,
        spacing=1.0, wrap=False, role="compact")
    scale_note.name = "protocol-anatomy:scale-note"

    minimum_by_bits = {}
    for frame in frames:
        for field in frame["fields"]:
            minimum = max(
                0.34,
                text_width_in(field["name"], font, "bold") + 0.24,
            )
            minimum_by_bits[field["bits"]] = max(
                minimum_by_bits.get(field["bits"], 0.0), minimum)

    def frame_width(frame, scale):
        return sum(
            max(minimum_by_bits[field["bits"]],
                scale * math.sqrt(field["bits"]))
            for field in frame["fields"]
        )

    minimum_required = max(frame_width(frame, 0.0) for frame in frames)
    if minimum_required > bar_w:
        raise FitError(
            "nw_frame_anatomy.fields: フィールド名の最小幅だけで描画領域を"
            "超えます。フィールド数を減らすか名称を短くしてください。")

    low, high = 0.0, bar_w
    for _ in range(40):
        mid = (low + high) / 2
        if max(frame_width(frame, mid) for frame in frames) <= bar_w:
            low = mid
        else:
            high = mid
    width_by_bits = {
        bits: max(minimum, low * math.sqrt(bits))
        for bits, minimum in minimum_by_bits.items()
    }

    field_centers = {}
    field_names = {}
    frame_ys = []
    cursor_y = top
    for frame in frames:
        frame_ys.append(cursor_y)
        cursor_y += frame_h + gap
        if frame.get("annotations"):
            cursor_y += (_PROTOCOL_ANNOTATION_GAP
                         + math.ceil(len(frame["annotations"]) / 4) * values["annotation_row_h"])
    for frame_index, frame in enumerate(frames):
        y = frame_ys[frame_index]
        add_text(slide, MARGIN + 0.02, y + 0.20, label_w - 0.18, 0.30,
                 frame["label"], 11, bold=True, color=NAVY,
                 anchor=MSO_ANCHOR.MIDDLE)
        frame_bar_w = sum(
            width_by_bits[field["bits"]] for field in frame["fields"])
        x = bar_x
        for field_index, field in enumerate(frame["fields"]):
            width = width_by_bits[field["bits"]]
            fill, color = _FIELD_FILLS[field.get("role", "standard")]
            add_rect(slide, x, y, width, frame_h, fill, line=RULE)
            name_size, name_lines = fit_text_or_raise(
                "nw_frame_anatomy", f"frames[{frame_index}].fields[{field_index}].name",
                field["name"], width - 0.10, frame_h * 0.52, font,
                min_pt=7.5, weight="bold", spacing=1.0, role="compact")
            add_text(slide, x + 0.05, y + 0.12, width - 0.10, frame_h * 0.48,
                     "\n".join(name_lines), name_size, bold=True, color=color,
                     align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, spacing=1.0, role="compact")
            add_text(slide, x + 0.04, y + frame_h - 0.25, width - 0.08, 0.16,
                     field.get("size_label", f"{field['bits']} bit"),
                     max(7.0, font - 2), color=GRAY,
                     align=PP_ALIGN.CENTER)
            field_centers[(frame_index, field["id"])] = (x + width / 2, y + frame_h)
            field_names[(frame_index, field["id"])] = field["name"]
            x += width

        if compare_lengths:
            delta = frame_totals[frame_index] - min_total
            if delta == 0:
                length_label = "基準"
            elif delta % 8 == 0:
                length_label = f"+{delta // 8} byte"
            else:
                length_label = f"+{delta} bit"
            add_text(slide, bar_x + frame_bar_w + 0.08, y + 0.33,
                     length_label_w - 0.10, 0.22, length_label,
                     max(7.5, font - 1.5), bold=delta > 0,
                     color=ACCENT if delta > 0 else GRAY,
                     anchor=MSO_ANCHOR.MIDDLE)

    if annotations:
        next_index = {}
        for frame_index, annotation in annotations:
            index = next_index.get(frame_index, 0)
            next_index[frame_index] = index + 1
            columns = min(4, len(frames[frame_index]["annotations"]))
            annotation_w = (BODY_W - 0.22 * (columns - 1)) / columns
            col = index % columns
            row = index // columns
            x = MARGIN + col * (annotation_w + 0.22)
            y = (frame_ys[frame_index] + frame_h + _PROTOCOL_ANNOTATION_GAP
                 + row * values["annotation_row_h"])
            source_x, source_y = field_centers[(frame_index, annotation["field"])]
            target_x = x + 0.20
            target_y = y - 0.06
            connector = _plain_connector(slide, source_x, source_y + 0.02,
                                         target_x, target_y, GRAY, width=1.1)
            connector.name = f"protocol-anatomy:annotation:{frame_index}:{annotation['field']}"
            annotation_label = field_names[(frame_index, annotation["field"])]
            annotation_label_w = min(
                annotation_w * 0.42,
                max(0.42, text_width_in(annotation_label, 8.5, "bold") + 0.08),
            )
            label_size, label_lines = fit_text_or_raise(
                "nw_frame_anatomy", "annotation.field", annotation_label,
                annotation_label_w, values["annotation_text_h"], 8.5,
                min_pt=8.5, weight="bold", spacing=1.08, role="compact")
            add_text(slide, x, y, annotation_label_w, values["annotation_text_h"],
                     "\n".join(label_lines), label_size,
                     bold=True, color=ACCENT, spacing=1.08, wrap=False, role="compact")
            fit_size, lines = fit_text_or_raise(
                "nw_frame_anatomy", "annotation", annotation["text"],
                annotation_w - annotation_label_w - 0.06,
                values["annotation_text_h"], values["annotation_font"],
                min_pt=8.0,
                spacing=1.08, role="compact")
            add_text(slide, x + annotation_label_w + 0.06, y,
                     annotation_w - annotation_label_w - 0.06,
                     values["annotation_text_h"],
                     "\n".join(lines), fit_size, color=TEXT, spacing=1.08, wrap=False, role="compact")

def _fit_code_text(code, width, height):
    from slidegen.font_config import font_family
    if font_family("code") == "Consolas" and not code.isascii():
        raise FitError(
            "config_lab.code: ConsolasではASCIIのコードだけを扱います。"
            "日本語コメントは本文へ移すか、PPTXDSL_FONT_CODEでNoto Sans Mono CJK JPを指定してください。")
    for size in stepped(13.0, 9.5, 0.5):
        widest = max(text_width_in(line or " ", size, "code") for line in code.splitlines())
        used_h = max(1, len(code.splitlines())) * line_height_in(size, 1.18)
        if widest <= width and used_h <= height:
            return size
    raise FitError(
        "config_lab.code: 最小フォントでも折り返さずに収まりません。"
        "コマンドを短くするか、実習を複数スライドへ分割してください。")


def _apply_code_font(textbox):
    from slidegen.font_config import font_family
    family = font_family("code")
    for paragraph in textbox.text_frame.paragraphs:
        for run in paragraph.runs:
            run.font.name = family
            r_pr = run._r.get_or_add_rPr()
            for tag in ("a:ea", "a:cs"):
                element = r_pr.find(qn(tag))
                if element is None:
                    element = r_pr.makeelement(qn(tag), {})
                    r_pr.append(element)
                element.set("typeface", family)


def s_code_lab(slide, spec, page):
    """設定例と確認結果を、折り返さないコードと要点で示す。"""
    area = header(slide, spec["kicker"], spec["title"], spec.get("lead"))
    sections = spec["sections"]
    checks = spec["checks"]
    top = area.top + 0.30
    bottom = area.bottom - 0.15
    panel_h = bottom - top
    left_w = 7.55
    right_x = MARGIN + left_w + 0.42
    right_w = BODY_W - left_w - 0.42
    add_rect(slide, MARGIN, top, left_w, panel_h, NAVY)
    section_gap = 0.20
    section_h = (panel_h - section_gap * (len(sections) - 1)) / len(sections)
    for index, section in enumerate(sections):
        y = top + index * (section_h + section_gap)
        add_text(slide, MARGIN + 0.28, y + 0.20, left_w - 0.56, 0.22,
                 section["label"], 10, bold=True, color=RGBColor(0x8F, 0xD4, 0xCC))
        code_y = y + 0.55
        code_h = section_h - 0.72
        size = _fit_code_text(section["code"], left_w - 0.56, code_h)
        code_box = add_text(
            slide, MARGIN + 0.28, code_y, left_w - 0.56, code_h,
            section["code"], size, color=WHITE, spacing=1.18, wrap=False, role="compact")
        _apply_code_font(code_box)

    add_text(slide, right_x, top + 0.02, right_w, 0.32,
             spec.get("check_label", "確認ポイント"), 13.5,
             bold=True, color=NAVY)
    rule_y = top + 0.47
    add_rect(slide, right_x, rule_y, right_w, 0.01, RULE)
    available = panel_h - 0.66
    row_h = available / len(checks)
    if row_h < 0.58:
        raise FitError("config_lab.checks: 確認項目が多すぎます。5件以内へ絞ってください。")
    for index, check in enumerate(checks):
        y = top + 0.62 + index * row_h
        add_text(slide, right_x, y + 0.02, 0.34, 0.24,
                 f"{index + 1:02d}", 9.5, bold=True, color=ACCENT)
        size, lines = fit_text_or_raise(
            "config_lab", f"checks[{index}]", check,
            right_w - 0.44, row_h - 0.10, 12.5, min_pt=9.5,
            spacing=1.13, role="body")
        add_text(slide, right_x + 0.44, y, right_w - 0.44, row_h - 0.08,
                 "\n".join(lines), size, color=TEXT, spacing=1.13)
        if index < len(checks) - 1:
            add_rect(slide, right_x + 0.44, y + row_h - 0.04,
                     right_w - 0.44, 0.008, RULE)

def _layout_options(question, size, mode, width, columns=None):
    option_size = size - 1.5
    columns = columns or len(question["options"])
    column_w = (width - .18 * (columns - 1)) / columns
    # 設問をまたいでA/B/Cの列位置を共有する。正答の太字も先に測り、
    # 問題・解答モードや収容時の縮小で横並び/縦並びが変わらないようにする。
    horizontal = all(
        "\n" not in option and text_width_in(
            f"{chr(65 + i)}. {option}", 13.5,
            "bold" if i == question["answer"] else "regular") + .12 <= column_w
        for i, option in enumerate(question["options"]))
    item_width = column_w if horizontal else width
    items = []
    for option_index, option in enumerate(question["options"]):
        correct = option_index == question["answer"]
        weight = "bold" if mode == "answers" and correct else "regular"
        option_text = f"{chr(65 + option_index)}. {option}"
        _, lines = fit_text_or_raise(
            "knowledge_check", f"options[{option_index}]", option_text,
            item_width - .12, 5.0, option_size, min_pt=option_size,
            weight=weight, spacing=1.08, role="compact")
        item_height = max(
            0.28, len(lines) * line_height_in(option_size, 1.08) + 0.02
        )
        items.append({
            "index": option_index,
            "text": "\n".join(lines),
            "width": item_width,
            "height": item_height,
        })
    rows = [items] if horizontal else [[item] for item in items]
    height = sum(max(item["height"] for item in row) for row in rows)
    height += max(0, len(rows) - 1) * 0.05
    return rows, height


def _fit_questions(area, questions, mode):
    available = area.height - 0.36
    columns = max(len(question["options"]) for question in questions)

    def measure(size, gap):
        heights = []
        for question in questions:
            question_h = len(wrap_text(question["question"], 10.25, size, "bold")) \
                * line_height_in(size, 1.12)
            _option_rows, option_h = _layout_options(
                question, size, mode, 10.85, columns)
            explanation_h = 0.0
            if mode == "answers":
                explanation_h = len(wrap_text(
                    question["explanation"], 9.55, size - 2.0)) \
                    * line_height_in(size - 2.0, 1.10) + 0.10
            heights.append(max(0.76, question_h + option_h + explanation_h + 0.20))
        return heights, sum(heights) + max(0, len(heights) - 1) * gap

    def candidates():
        profiles = [("standard" if gap == .24 else "gap", 15.0, gap)
                    for gap in stepped(.24, .10, .035)]
        profiles += [("font", size, .10) for size in stepped(14.5, 11.5, .5)]
        generated, width_error = False, None
        for stage, size, gap in profiles:
            try:
                _heights, used = measure(size, gap)
            except FitError as error:
                width_error = error
                continue
            generated = True
            yield stage, {"size": size, "gap": gap}, used
        if not generated and width_error:
            raise FitError(f"{width_error} 設問を分割してください。") from None

    fitted = select_fit(
        "knowledge_check", available, candidates(),
        guidance="設問を分割するか、選択肢と解説を短くしてください。")
    heights, _used = measure(fitted.values["size"], fitted.values["gap"])
    return fitted, heights


def s_knowledge_check(slide, spec, page):
    """設問用と解答・解説用を同じ構造から描き分ける。"""
    area = header(slide, spec["kicker"], spec["title"], spec.get("lead"))
    questions = spec["questions"]
    mode = spec["mode"]
    columns = max(len(question["options"]) for question in questions)
    fitted, heights = _fit_questions(area, questions, mode)
    size, gap = fitted.values["size"], fitted.values["gap"]
    top = area.top + 0.22
    used = sum(heights) + gap * max(0, len(heights) - 1)
    top += max(0, (area.height - 0.30 - used) * 0.12)

    for index, (question, row_h) in enumerate(zip(questions, heights)):
        marker_color = ACCENT if mode == "answers" else NAVY
        marker = slide.shapes.add_shape(
            MSO_SHAPE.OVAL, Inches(MARGIN + 0.02), Inches(top + 0.02),
            Inches(0.42), Inches(0.42))
        marker.fill.solid()
        marker.fill.fore_color.rgb = marker_color
        marker.line.fill.background()
        marker.shadow.inherit = False
        add_text(slide, MARGIN + 0.02, top + 0.02, 0.42, 0.42,
                 f"{index + 1:02d}", 10, bold=True, color=WHITE,
                 align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        x = MARGIN + 0.68
        question_size, question_lines = fit_text_or_raise(
            "knowledge_check", f"questions[{index}].question",
            question["question"], 10.85, 0.56, size,
            min_pt=11.5, weight="bold", spacing=1.12, role="natural")
        q_h = len(question_lines) * line_height_in(question_size, 1.12)
        question_box = add_text(slide, x, top, 10.85, q_h + 0.04,
                 "\n".join(question_lines), question_size,
                 bold=True, color=NAVY, spacing=1.12, wrap=False)
        question_box.name = f"knowledge:question:{index}"
        option_y = top + q_h + 0.10
        option_rows, option_h = _layout_options(
            question, size, mode, 10.85, columns)
        for row in option_rows:
            option_x = x
            option_row_h = max(item["height"] for item in row)
            for item in row:
                correct = item["index"] == question["answer"]
                option_color = ACCENT if mode == "answers" and correct else GRAY
                option_box = add_text(
                    slide, option_x, option_y, item["width"], item["height"],
                    item["text"], size - 1.5,
                    bold=mode == "answers" and correct,
                    color=option_color, spacing=1.08, role="compact", wrap=False,
                )
                option_box.name = f"knowledge:option:{index}:{item['index']}"
                option_x += item["width"] + 0.18
            option_y += option_row_h + 0.05
        if mode == "answers":
            explanation_y = top + q_h + 0.10 + option_h + 0.10
            add_text(slide, x, explanation_y, 0.58, 0.22,
                     "解説", 9.5, bold=True, color=ACCENT)
            exp_size, exp_lines = fit_text_or_raise(
                "knowledge_check", f"questions[{index}].explanation",
                question["explanation"], 9.90, row_h - (explanation_y - top),
                size - 2.0, min_pt=9.5, spacing=1.10, role="body")
            explanation_box = add_text(slide, x + 0.68, explanation_y, 9.90,
                     row_h - (explanation_y - top), "\n".join(exp_lines),
                     exp_size, color=TEXT, spacing=1.10, wrap=False)
            explanation_box.name = f"knowledge:explanation:{index}"
        if index < len(questions) - 1:
            add_rect(slide, x, top + row_h + gap / 2,
                     BODY_W - 0.72, 0.008, RULE)
        top += row_h + gap
