"""階層・ノード・関係だけから体制図を配置する専用レイアウタ。"""
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN

from diagrams import add_arrow, arrow_label
from diagrams3 import plain_line, route
from generate import (ACCENT, BODY_W, GRAY, LIGHT, MARGIN, NAVY,
                      RULE, SURFACE, TEXT, WHITE, ZEBRA, ContentArea, add_rect, add_text,
                      header, note_line)
from layout_fit import FitError, fit_text_or_raise, select_fit

FRAME_X = MARGIN + 0.10
FRAME_W = BODY_W - 0.20
MIN_NODE_W = 1.82
MAX_NODE_W = {1: 4.10, 2: 4.30, 3: 3.65, 4: 2.82, 5: 2.24}


def fit_org_layout(org, available):
    """体制図を標準→余白圧縮→箱縮小の順で収容する。"""
    nodes = org["nodes"]
    levels = org["levels"]
    has_edge_labels = any(edge.get("label") for edge in org.get("edges", []))
    has_members = [
        any(nodes[node_id].get("members") for node_id in level)
        for level in levels
    ]
    profiles = [
        ("standard", 0.08, 0.04, 0.34, 0.34, 0.84, 1.26,
         12.5, 9.5, 9.5),
        ("gap", 0.05, 0.03, 0.24, 0.24, 0.76, 1.14,
         12.5, 9.5, 9.5),
        ("element", 0.03, 0.02, 0.18, 0.20, 0.70, 1.06,
         11.5, 8.8, 8.8),
        ("element", 0.02, 0.02, 0.14, 0.18, 0.64, 1.00,
         10.5, 8.2, 8.2),
        ("element", 0.01, 0.01, 0.10, 0.16, 0.60, 0.94,
         9.5, 7.5, 7.5),
    ]
    candidates = []
    for (stage, top_gap, bottom_gap, gap_y, gap_x, plain_h, member_h,
         title_pt, sub_pt, members_pt) in profiles:
        # 関係ラベルの実測高さを、箱の縮小時も潰せない必須余白として残す。
        gap_y = max(gap_y, 0.34) if has_edge_labels else gap_y
        level_heights = [
            member_h if members else plain_h for members in has_members
        ]
        values = {
            "top_gap": top_gap,
            "bottom_gap": bottom_gap,
            "gap_y": gap_y,
            "gap_x": gap_x,
            "plain_h": plain_h,
            "member_h": member_h,
            "title_pt": title_pt,
            "sub_pt": sub_pt,
            "members_pt": members_pt,
            "level_heights": level_heights,
        }
        used = (top_gap + bottom_gap + sum(level_heights)
                + gap_y * max(0, len(levels) - 1))
        if used <= available:
            # 少ない階層を上端へ貼り付けず、余白の一部を上側と階層間へ戻す。
            surplus = available - used
            top_bonus = min(0.34, surplus * 0.28)
            remaining = surplus - top_bonus
            gap_count = max(0, len(levels) - 1)
            gap_bonus = min(
                0.28, remaining * 0.42 / gap_count) if gap_count else 0.0
            values["top_gap"] += top_bonus
            values["gap_y"] += gap_bonus
            used += top_bonus + gap_bonus * gap_count
        candidates.append((stage, values, used))
    return select_fit(
        "org", available, candidates,
        guidance=("階層を分割するか、メンバー記載を別スライドへ移してください。"),
    )


class OrgLayout:
    """levelsを行、edgesを関係として階層DAGを配置・配線する。"""

    def __init__(self, org, content_area):
        self.org = org
        self.nodes = org["nodes"]
        self.levels = org["levels"]
        self.edges = org.get("edges", [])
        self.area = content_area
        self.level_of = {
            node_id: level_index
            for level_index, level in enumerate(self.levels)
            for node_id in level
        }
        self.fit = fit_org_layout(org, content_area.height)
        self.boxes = self._place_nodes()
        self.source_ports, self.target_ports = self._assign_ports()
        self.routes = self._route_edges()
        self._validate_routes()

    @property
    def fit_stage(self):
        return self.fit.stage

    def _place_nodes(self):
        values = self.fit.values
        boxes = {}
        cursor_y = self.area.top + values["top_gap"]
        for level_index, level in enumerate(self.levels):
            count = len(level)
            gap_x = values["gap_x"]
            has_same_level_edge = any(
                self.level_of[edge["from"]] == level_index
                and self.level_of[edge["to"]] == level_index
                for edge in self.edges
            )
            if has_same_level_edge:
                gap_x = max(gap_x, 0.60 if count == 2 else 0.50)
            available_node_w = (FRAME_W - gap_x * (count - 1)) / count
            if available_node_w < MIN_NODE_W:
                raise FitError(
                    f"org: 階層{level_index + 1}の{count}ノードを配置できません"
                    f"(箱幅{available_node_w:.2f}in / 最小{MIN_NODE_W:.2f}in)。"
                    "同じ階層を分割するかノード数を減らしてください。"
                )
            # 1〜2ノードの階層を横幅いっぱいに引き伸ばさない。
            node_w = min(available_node_w, MAX_NODE_W[count])
            total_w = node_w * count + gap_x * (count - 1)
            x0 = FRAME_X + (FRAME_W - total_w) / 2
            node_h = values["level_heights"][level_index]
            for index, node_id in enumerate(level):
                boxes[node_id] = (
                    x0 + index * (node_w + gap_x), cursor_y, node_w, node_h)
            cursor_y += node_h + values["gap_y"]
        return boxes

    def _assign_ports(self):
        """体制図の幹へ集約するため、各ノードの接続点を中央に統一する。"""
        source_ports = {
            edge_index: self.boxes[edge["from"]][0]
            + self.boxes[edge["from"]][2] / 2
            for edge_index, edge in enumerate(self.edges)
        }
        target_ports = {
            edge_index: self.boxes[edge["to"]][0]
            + self.boxes[edge["to"]][2] / 2
            for edge_index, edge in enumerate(self.edges)
        }
        return source_ports, target_ports

    def _reporting_components(self, edge_indexes):
        """同じ階層間でつながる親子群を、共有幹の単位へまとめる。"""
        remaining = set(edge_indexes)
        components = []
        while remaining:
            seed = remaining.pop()
            component_edges = {seed}
            component_nodes = {
                self.edges[seed]["from"], self.edges[seed]["to"],
            }
            changed = True
            while changed:
                changed = False
                for edge_index in list(remaining):
                    edge = self.edges[edge_index]
                    if edge["from"] in component_nodes or edge["to"] in component_nodes:
                        remaining.remove(edge_index)
                        component_edges.add(edge_index)
                        component_nodes.update((edge["from"], edge["to"]))
                        changed = True
            components.append(sorted(component_edges))
        return components

    def _route_edges(self):
        routed = []
        outer_index = 0
        frame_center = FRAME_X + FRAME_W / 2
        adjacent_groups = {}
        for edge_index, edge in enumerate(self.edges):
            source_level = self.level_of[edge["from"]]
            target_level = self.level_of[edge["to"]]
            if (edge.get("kind", "reporting") == "reporting"
                    and abs(target_level - source_level) == 1):
                key = tuple(sorted((source_level, target_level)))
                adjacent_groups.setdefault(key, []).append(edge_index)
        lane_fraction = {}
        for edge_indexes in adjacent_groups.values():
            components = self._reporting_components(edge_indexes)
            components.sort(key=lambda component: sum(
                self.source_ports[index] + self.target_ports[index]
                for index in component) / (2 * len(component)))
            count = len(components)
            for slot, component in enumerate(components):
                fraction = (0.50 if count == 1
                            else 0.38 + 0.24 * slot / (count - 1))
                for edge_index in component:
                    lane_fraction[edge_index] = fraction

        for edge_index, edge in enumerate(self.edges):
            source = self.boxes[edge["from"]]
            target = self.boxes[edge["to"]]
            source_level = self.level_of[edge["from"]]
            target_level = self.level_of[edge["to"]]
            sx, sy, sw, sh = source
            tx, ty, tw, th = target
            source_cx = self.source_ports[edge_index]
            target_cx = self.target_ports[edge_index]

            if source_level == target_level:
                left_id, right_id = sorted(
                    (edge["from"], edge["to"]),
                    key=lambda node_id: self.boxes[node_id][0])
                left_box = self.boxes[left_id]
                right_box = self.boxes[right_id]
                gap_left = left_box[0] + left_box[2]
                gap_right = right_box[0]
                has_between = any(
                    node_id not in {left_id, right_id}
                    and self.level_of[node_id] == source_level
                    and gap_left < box[0] + box[2] / 2 < gap_right
                    for node_id, box in self.boxes.items()
                )
                if not has_between:
                    mid_y = sy + sh / 2
                    line_left = gap_left + 0.06
                    line_right = gap_right - 0.06
                    if edge["from"] == left_id:
                        points = [(line_left, mid_y), (line_right, mid_y)]
                    else:
                        points = [(line_right, mid_y), (line_left, mid_y)]
                    routed.append(points)
                    continue
                bottom_space = self.area.bottom - (sy + sh)
                lane_below = (source_level == 0
                              or (source_level == len(self.levels) - 1
                                  and bottom_space >= 0.20))
                lane_offset = min(
                    self.fit.values["gap_y"] * 0.68,
                    max(0.10, bottom_space - 0.10),
                ) if lane_below else self.fit.values["gap_y"] * 0.32
                lane_y = ((sy + sh + lane_offset)
                          if lane_below
                          else sy - lane_offset)
                source_y = sy + sh if lane_below else sy
                target_y = ty + th if lane_below else ty
                points = [
                    (source_cx, source_y), (source_cx, lane_y),
                    (target_cx, lane_y), (target_cx, target_y),
                ]
            elif abs(target_level - source_level) == 1:
                downward = target_level > source_level
                source_y = sy + sh if downward else sy
                target_y = ty if downward else ty + th
                mid_y = source_y + (target_y - source_y) * lane_fraction[edge_index]
                points = [
                    (source_cx, source_y), (source_cx, mid_y),
                    (target_cx, mid_y), (target_cx, target_y),
                ]
            else:
                downward = target_level > source_level
                use_right = (source_cx + target_cx) / 2 >= frame_center
                channel_offset = 0.03 + (outer_index % 3) * 0.02
                channel_x = ((FRAME_X + FRAME_W + channel_offset)
                             if use_right
                             else FRAME_X - channel_offset)
                outer_index += 1
                source_y = sy + sh if downward else sy
                target_y = ty if downward else ty + th
                source_lane = source_y + (
                    self.fit.values["gap_y"] * 0.12 if downward else
                    -self.fit.values["gap_y"] * 0.12)
                target_lane = target_y + (
                    -self.fit.values["gap_y"] * 0.12 if downward else
                    self.fit.values["gap_y"] * 0.12)
                points = [
                    (source_cx, source_y), (source_cx, source_lane),
                    (channel_x, source_lane), (channel_x, target_lane),
                    (target_cx, target_lane), (target_cx, target_y),
                ]
            routed.append(points)
        return routed

    @staticmethod
    def _segment_hits_box(start, end, box):
        x1, y1 = start
        x2, y2 = end
        bx, by, bw, bh = box
        pad = 0.015
        if abs(x1 - x2) <= 0.001:
            return (bx + pad < x1 < bx + bw - pad
                    and max(min(y1, y2), by + pad)
                    < min(max(y1, y2), by + bh - pad))
        if abs(y1 - y2) <= 0.001:
            return (by + pad < y1 < by + bh - pad
                    and max(min(x1, x2), bx + pad)
                    < min(max(x1, x2), bx + bw - pad))
        return True

    def _validate_routes(self):
        for edge, points in zip(self.edges, self.routes):
            for start, end in zip(points[:-1], points[1:]):
                if abs(start[0] - end[0]) > 0.001 \
                        and abs(start[1] - end[1]) > 0.001:
                    raise FitError(
                        f"org: {edge['from']}→{edge['to']}の配線が直角ではありません")
                for node_id, box in self.boxes.items():
                    if node_id in {edge["from"], edge["to"]}:
                        continue
                    if self._segment_hits_box(start, end, box):
                        raise FitError(
                            f"org: {edge['from']}→{edge['to']}の配線が"
                            f"{node_id}を貫通します。levelsの階層を分けてください。"
                        )

    def _reporting_bus_groups(self):
        """複数の報告線を、親子間の共有幹として描く単位へまとめる。"""
        adjacent_groups = {}
        for edge_index, edge in enumerate(self.edges):
            source_level = self.level_of[edge["from"]]
            target_level = self.level_of[edge["to"]]
            if (edge.get("kind", "reporting") == "reporting"
                    and target_level - source_level == 1):
                adjacent_groups.setdefault(
                    (source_level, target_level), []).append(edge_index)
        groups = []
        for edge_indexes in adjacent_groups.values():
            groups.extend(
                component for component in self._reporting_components(edge_indexes)
                if len(component) > 1)
        return groups

    def _draw_reporting_bus(self, slide, edge_indexes):
        """親側スタブ、横幹、子側矢印を重複させずに描画する。"""
        edges = [self.edges[index] for index in edge_indexes]
        bus_y = self.routes[edge_indexes[0]][1][1]
        source_ids = list(dict.fromkeys(edge["from"] for edge in edges))
        target_ids = list(dict.fromkeys(edge["to"] for edge in edges))
        source_xs = [
            self.boxes[node_id][0] + self.boxes[node_id][2] / 2
            for node_id in source_ids
        ]
        target_xs = [
            self.boxes[node_id][0] + self.boxes[node_id][2] / 2
            for node_id in target_ids
        ]
        all_xs = source_xs + target_xs
        if max(all_xs) - min(all_xs) > 0.01:
            plain_line(slide, min(all_xs), bus_y, max(all_xs), bus_y,
                       width=1.10)
        for node_id, cx in zip(source_ids, source_xs):
            _x, y, _w, h = self.boxes[node_id]
            if abs(y + h - bus_y) > 0.01:
                plain_line(slide, cx, y + h, cx, bus_y, width=1.10)
        for node_id, cx in zip(target_ids, target_xs):
            _x, y, _w, _h = self.boxes[node_id]
            add_arrow(slide, cx, bus_y, cx, y, width=1.10)

    @staticmethod
    def _label_anchor(points):
        segments = list(zip(points[:-1], points[1:]))
        horizontal = [
            segment for segment in segments
            if abs(segment[0][1] - segment[1][1]) <= 0.001
        ]
        candidates = horizontal or segments
        start, end = max(
            candidates,
            key=lambda segment: abs(segment[1][0] - segment[0][0])
            + abs(segment[1][1] - segment[0][1]),
        )
        return ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)

    def _draw_node(self, slide, node_id):
        node = self.nodes[node_id]
        x, y, w, h = self.boxes[node_id]
        level_index = self.level_of[node_id]
        style = node.get("style", "primary" if level_index == 0 else "standard")
        palette = {
            "primary": (NAVY, NAVY, WHITE, LIGHT),
            "accent": (SURFACE, ACCENT, NAVY, GRAY),
            "standard": (SURFACE, RULE, NAVY, GRAY),
            "external": (ZEBRA, RULE, NAVY, GRAY),
        }
        fill, border, title_color, sub_color = palette[style]
        add_rect(slide, x, y, w, h, fill, line=border)

        members = node.get("members", [])
        sub = node.get("sub")
        title_h = 0.25 if h >= 0.70 else 0.22
        if not sub and not members:
            title_y = y + 0.08
            title_box_h = h - 0.16
            title_anchor = MSO_ANCHOR.MIDDLE
        else:
            title_y = y + 0.07
            title_box_h = title_h
            title_anchor = MSO_ANCHOR.TOP
        title_size, _ = fit_text_or_raise(
            "org", f"nodes.{node_id}.name", node["name"], w - 0.28,
            title_box_h, self.fit.values["title_pt"], min_pt=9.0,
            weight="bold", spacing=1.05)
        add_text(
            slide, x + 0.14, title_y, w - 0.28, title_box_h, node["name"],
            title_size, bold=True, color=title_color,
            align=PP_ALIGN.CENTER, anchor=title_anchor, spacing=1.05)

        member_top = y + h - 0.37 if members else y + h
        if sub:
            sub_y = title_y + title_h + 0.04
            sub_h = max(0.15, member_top - sub_y - 0.04)
            sub_size, _ = fit_text_or_raise(
                "org", f"nodes.{node_id}.sub", sub, w - 0.28, sub_h,
                self.fit.values["sub_pt"], min_pt=7.2, spacing=1.05)
            add_text(
                slide, x + 0.14, sub_y, w - 0.28, sub_h, sub, sub_size,
                color=sub_color, align=PP_ALIGN.CENTER,
                anchor=MSO_ANCHOR.MIDDLE, spacing=1.05)
        if members:
            separator = LIGHT if style == "primary" else RULE
            add_rect(slide, x + 0.16, member_top, w - 0.32, 0.01, separator)
            member_text = " / ".join(members)
            member_size, _ = fit_text_or_raise(
                "org", f"nodes.{node_id}.members", member_text,
                w - 0.30, 0.25, self.fit.values["members_pt"],
                min_pt=7.0, spacing=1.05)
            add_text(
                slide, x + 0.15, member_top + 0.07, w - 0.30, 0.24,
                member_text, member_size,
                color=LIGHT if style == "primary" else TEXT,
                align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE,
                spacing=1.05)

    def render(self, slide):
        reporting_groups = self._reporting_bus_groups()
        shared_reporting = {
            edge_index for group in reporting_groups for edge_index in group
        }
        direct_same_level = {
            edge_index for edge_index, (edge, points)
            in enumerate(zip(self.edges, self.routes))
            if self.level_of[edge["from"]] == self.level_of[edge["to"]]
            and len(points) == 2
        }
        for edge_indexes in reporting_groups:
            self._draw_reporting_bus(slide, edge_indexes)
        for edge_index, (edge, points) in enumerate(zip(self.edges, self.routes)):
            if edge_index in direct_same_level or edge_index in shared_reporting:
                continue
            kind = edge.get("kind", "reporting")
            dash = "dash" if kind != "reporting" else None
            route(slide, points, dash=dash, width=1.10,
                  both=kind == "collaboration")
        for level in self.levels:
            for node_id in level:
                self._draw_node(slide, node_id)
        for edge_index in sorted(direct_same_level):
            edge = self.edges[edge_index]
            points = self.routes[edge_index]
            kind = edge.get("kind", "reporting")
            if kind == "collaboration":
                center = ((points[0][0] + points[1][0]) / 2,
                          (points[0][1] + points[1][1]) / 2)
                route(slide, [center, points[0]], dash="dash", width=1.10)
                route(slide, [center, points[1]], dash="dash", width=1.10)
            else:
                route(slide, points, dash="dash", width=1.10)
        for edge_index, (edge, points) in enumerate(zip(self.edges, self.routes)):
            if edge.get("label"):
                cx, cy = self._label_anchor(points)
                if edge_index in direct_same_level:
                    cy -= 0.13
                arrow_label(slide, cx, cy, edge["label"], w=1.45, size=8.5)


def s_org(slide, spec, page):
    area = header(slide, spec["kicker"], spec["title"], spec.get("lead"))
    if spec.get("note") and area.shifted:
        area = ContentArea(area.top, area.bottom - 0.30, area.shifted)
    layout = OrgLayout(spec["org"], area)
    layout.render(slide)
    if spec.get("note"):
        note_line(slide, spec["note"])
    return layout
