"""ネットワーク図の配置・配線計画。図形・Presentation・rendererに依存しない。"""

from dataclasses import dataclass
from typing import Any, Iterator, Mapping, Sequence

from slidegen.layout_fit import (
    FitCandidate,
    FitError,
    FitResult,
    fit_text_or_raise,
    select_fit,
    stepped,
)
from slidegen.layout_settings import BodyArea, HeightArea, NETWORK, PAGE
from slidegen.textfit import text_width_in


Spec = Mapping[str, Any]
Point = tuple[float, float]
LegendRows = list[list[tuple[str, str, float]]]
NETWORK_KIND_LABELS = {
    "access": "Access（単一セグメント）",
    "trunk": "Trunk（複数セグメント）",
    "routed": "L3転送",
    "control": "制御・確認",
    "broadcast": "ブロードキャスト",
    "blocked": "境界で停止",
}


def fit_network(
    area: HeightArea, lane_count: int, max_cell_nodes: int, legend_h: float = 0.24
) -> FitResult:
    available = area.height - NETWORK.top_reserve - NETWORK.legend_gap - legend_h

    def used(values: Mapping[str, float]) -> float:
        return lane_count * values["lane_h"] + max(0, lane_count - 1) * values["gap"]

    def candidates() -> Iterator[FitCandidate]:
        standard_lane = 1.62 if lane_count == 1 else 1.42 if lane_count == 2 else 1.32
        standard_icon = 0.48 if max_cell_nodes > 1 else 0.62 if lane_count == 1 else 0.56
        standard = {
            "lane_h": standard_lane,
            "gap": 0.10,
            "icon": standard_icon,
            "font": 9.5 if max_cell_nodes > 1 else 10.5,
        }
        yield "standard", standard, used(standard)
        for gap in stepped(0.07, 0.02, 0.025):
            values = dict(standard, gap=gap)
            yield "gap", values, used(values)
        min_lane = 0.90 if lane_count >= 3 else 1.02
        for lane_h in stepped(standard["lane_h"] - 0.05, min_lane, 0.05):
            values = {
                "lane_h": lane_h,
                "gap": 0.02,
                "icon": 0.44 if max_cell_nodes > 1 else 0.50,
                "font": 9.0 if max_cell_nodes > 1 else 10.0,
            }
            yield "element", values, used(values)
        values = {"lane_h": min_lane, "gap": 0.02, "icon": 0.44, "font": 9.0}
        yield "font", values, used(values)

    return select_fit(
        "nw_topology",
        available,
        candidates(),
        guidance="論理セグメントまたは機器数を減らし、複数スライドへ分割してください。",
    )


def network_legend(links: Sequence[Spec]) -> tuple[LegendRows, float]:
    kinds = list(dict.fromkeys(link.get("kind", "access") for link in links))
    if "trunk" in kinds:
        kinds.insert(0, "physical")
    rows: LegendRows = [[]]
    used = 0.0
    for kind in kinds:
        label = "物理リンク" if kind == "physical" else NETWORK_KIND_LABELS[kind]
        width = text_width_in(label, NETWORK.legend_pt) + 0.52
        if rows[-1] and used + 0.24 + width > PAGE.body_width - NETWORK.right_inset:
            rows.append([])
            used = 0.0
        rows[-1].append((kind, label, width))
        used += width + 0.24
    return rows, len(rows) * NETWORK.legend_row_height + (len(rows) - 1) * 0.10


def compact_lane_names(labels: Sequence[str]) -> str:
    parts = [label.split(maxsplit=1) for label in labels]
    if all(len(part) == 2 for part in parts):
        prefix = parts[0][0]
        if all(part[0] == prefix for part in parts[1:]):
            return f"{prefix} " + " / ".join(part[1] for part in parts)
    return " / ".join(labels)


@dataclass(frozen=True)
class NetworkGeometry:
    fitted: FitResult
    top: float
    lane_label_w: float
    col_gap: float
    lane_index: dict[str, int]
    col_index: dict[str, int]
    lane_centers: dict[str, float]
    col_centers: dict[str, float]
    positions: dict[str, Point]
    node_by_id: dict[str, Spec]
    placement_groups: dict[tuple[str, tuple[str, ...]], list[str]]

    def node_edge(self, node_id: str, toward_x: float, *, lane_id: str | None = None) -> Point:
        x, y = self.positions[node_id]
        node = self.node_by_id[node_id]
        if lane_id and lane_id in node["lanes"]:
            y = self.lane_centers[lane_id]
        icon_size = self.fitted.values["icon"]
        delta = icon_size / 2 + 0.07
        if len(node["lanes"]) > 1 and abs(y - self.positions[node_id][1]) > icon_size / 2:
            return x, y
        return (x + delta if toward_x > x else x - delta, y)


def network_geometry(spec: Spec, area: BodyArea, legend_h: float) -> NetworkGeometry:
    lanes, columns, nodes = spec["lanes"], spec["columns"], spec["nodes"]
    lane_index = {lane["id"]: index for index, lane in enumerate(lanes)}
    groups: dict[tuple[str, tuple[str, ...]], list[str]] = {}
    for node in nodes:
        ordered = tuple(sorted(node["lanes"], key=lambda lane: lane_index[lane]))
        groups.setdefault((node["column"], ordered), []).append(node["id"])
    max_cell_nodes = max(len(group) for group in groups.values())
    if max_cell_nodes > 2:
        raise FitError(
            "network.nodes: 同じ列・論理セグメントに3件以上の機器は配置できません。"
            "列を追加するか、複数スライドへ分割してください。"
        )
    fitted = fit_network(area, len(lanes), max_cell_nodes, legend_h)
    lane_h, gap = fitted.values["lane_h"], fitted.values["gap"]
    top = area.top + NETWORK.top_reserve
    used_h = len(lanes) * lane_h + max(0, len(lanes) - 1) * gap
    top += max(0.0, (fitted.available - used_h) * 0.12)
    label_w = max(
        NETWORK.lane_label_min_width,
        min(
            NETWORK.lane_label_max_width,
            max(
                max(
                    text_width_in(lane["label"], NETWORK.lane_title_pt, "bold"),
                    text_width_in(lane.get("sub", ""), NETWORK.lane_sub_pt),
                )
                + NETWORK.lane_label_padding
                for lane in lanes
            ),
        ),
    )
    x0 = PAGE.margin + label_w
    x1 = PAGE.margin + PAGE.body_width - NETWORK.right_inset
    col_gap = (x1 - x0) / len(columns)
    lane_centers = {
        lane["id"]: top + i * (lane_h + gap) + lane_h / 2 for i, lane in enumerate(lanes)
    }
    col_centers = {column["id"]: x0 + (i + 0.5) * col_gap for i, column in enumerate(columns)}
    col_index = {column["id"]: index for index, column in enumerate(columns)}
    offsets: dict[str, float] = {}
    for group in groups.values():
        if len(group) == 1:
            offsets[group[0]] = 0.0
        else:
            spacing = min(0.72, col_gap * 0.42)
            offsets[group[0]] = -spacing / 2
            offsets[group[1]] = spacing / 2
    positions = {
        node["id"]: (
            col_centers[node["column"]] + offsets[node["id"]],
            sum(lane_centers[lane] for lane in node["lanes"]) / len(node["lanes"]),
        )
        for node in nodes
    }
    return NetworkGeometry(
        fitted,
        top,
        label_w,
        col_gap,
        lane_index,
        col_index,
        lane_centers,
        col_centers,
        positions,
        {n["id"]: n for n in nodes},
        groups,
    )


@dataclass(frozen=True)
class NetworkLabel:
    text: str
    x: float
    y: float
    width: float
    size: float = 8.5
    trunk: bool = False


@dataclass(frozen=True)
class BroadcastRoute:
    start: Point
    ends: list[Point]
    channel_y: float
    bus_end_x: float
    label: NetworkLabel | None


@dataclass(frozen=True)
class NetworkLink:
    index: int
    kind: str
    start: Point
    end: Point
    color: str
    points: list[Point]
    label: NetworkLabel | None = None
    physical: tuple[Point, Point] | None = None
    trunk_lanes: tuple[tuple[Point, Point, str], ...] = ()
    stop: Point | None = None


@dataclass(frozen=True)
class NetworkPlan:
    geometry: NetworkGeometry
    legend_rows: LegendRows
    legend_h: float
    broadcasts: list[BroadcastRoute]
    links: list[NetworkLink]


def broadcast_routes(
    links: Sequence[Spec], geometry: NetworkGeometry
) -> tuple[list[BroadcastRoute], set[int]]:
    groups: dict[tuple[str, str | None], list[tuple[int, Spec]]] = {}
    for index, link in enumerate(links):
        if link.get("kind") == "broadcast":
            lane_ids = link.get("lanes", [])
            groups.setdefault((link["from"], lane_ids[0] if lane_ids else None), []).append(
                (index, link)
            )
    routes: list[BroadcastRoute] = []
    grouped: set[int] = set()
    for (source_id, lane_id), group in groups.items():
        if len(group) < 2:
            continue
        targets = [link["to"] for _, link in group]
        source_x, source_y = geometry.positions[source_id]
        target_xs = [geometry.positions[target][0] for target in targets]
        start = geometry.node_edge(source_id, sum(target_xs) / len(target_xs), lane_id=lane_id)
        ends = [geometry.node_edge(target, source_x, lane_id=lane_id) for target in targets]
        channel_y = source_y - geometry.fitted.values["lane_h"] * 0.30
        bus_end_x = max(end[0] for end in ends)
        labels = [link["label"] for _, link in group if link.get("label")]
        label = (
            NetworkLabel(
                labels[0],
                (start[0] + bus_end_x) / 2,
                channel_y - 0.16,
                min(1.70, max(0.90, bus_end_x - start[0] - 0.10)),
            )
            if labels
            else None
        )
        routes.append(BroadcastRoute(start, ends, channel_y, bus_end_x, label))
        grouped.update(index for index, _ in group)
    return routes, grouped


def trunk_link(
    index: int, link: Spec, geometry: NetworkGeometry, lanes: Sequence[Spec]
) -> NetworkLink:
    source_x, source_y = geometry.positions[link["from"]]
    target_x, target_y = geometry.positions[link["to"]]
    lane_by_id = {lane["id"]: lane for lane in lanes}
    active = link.get("lanes", []) or list(lane_by_id)
    physical = (
        geometry.node_edge(link["from"], target_x),
        geometry.node_edge(link["to"], source_x),
    )
    segments = tuple(
        (
            geometry.node_edge(link["from"], target_x, lane_id=lane),
            geometry.node_edge(link["to"], source_x, lane_id=lane),
            lane,
        )
        for lane in active
    )
    start, end, _ = segments[-1]
    text = f"{link.get('label', 'Trunk')}\n{compact_lane_names([lane_by_id[lane]['label'] for lane in active])}"
    label_w = min(2.20, max(0.80, abs(end[0] - start[0]) - 0.12))
    size, lines = fit_text_or_raise(
        "nw_topology",
        "link.trunk.label",
        text,
        label_w - 0.12,
        0.34,
        8.5,
        min_pt=7.0,
        weight="bold",
        spacing=1.0,
        role="compact",
    )
    label_w = min(label_w, max(text_width_in(line, size, "bold") for line in lines) + 0.12)
    label = NetworkLabel(
        "\n".join(lines),
        (source_x + target_x) / 2 - label_w / 2,
        min(source_y, target_y) - 0.42,
        label_w,
        size,
        trunk=True,
    )
    return NetworkLink(index, "trunk", start, end, "gray", [], label, physical, segments)


def ordinary_link(index: int, link: Spec, geometry: NetworkGeometry) -> NetworkLink:
    source_x, _ = geometry.positions[link["from"]]
    target_x, _ = geometry.positions[link["to"]]
    kind = link.get("kind", "access")
    lane_ids = link.get("lanes", [])
    lane_id = lane_ids[0] if lane_ids else None
    color = (
        "coral"
        if kind == "broadcast"
        else f"lane:{lane_id}"
        if lane_id in geometry.lane_index
        else "navy"
        if kind == "routed"
        else "gray"
    )
    start = geometry.node_edge(link["from"], target_x, lane_id=lane_id)
    end = geometry.node_edge(link["to"], source_x, lane_id=lane_id)
    label = None
    if kind == "blocked":
        boundary_y = (start[1] + end[1]) / 2
        stop_y = boundary_y - 0.08 if end[1] > start[1] else boundary_y + 0.08
        middle_x = (start[0] + end[0]) / 2
        points = [start, (middle_x, start[1]), (middle_x, stop_y)]
        if link.get("label"):
            label = NetworkLabel(link["label"], middle_x + 0.78, boundary_y - 0.14, 1.48)
        return NetworkLink(
            index, kind, start, end, "coral", points, label, stop=(middle_x, boundary_y)
        )
    source_col = geometry.col_index[geometry.node_by_id[link["from"]]["column"]]
    target_col = geometry.col_index[geometry.node_by_id[link["to"]]["column"]]
    if kind == "broadcast" and abs(source_col - target_col) > 1 and abs(start[1] - end[1]) <= 0.02:
        channel_y = start[1] - geometry.fitted.values["lane_h"] * 0.30
        points = [start, (start[0], channel_y), (end[0], channel_y), end]
    elif abs(start[1] - end[1]) <= 0.02:
        points = [start, end]
    else:
        middle_x = (start[0] + end[0]) / 2
        points = [start, (middle_x, start[1]), (middle_x, end[1]), end]
    if link.get("label"):
        label = NetworkLabel(
            link["label"],
            (start[0] + end[0]) / 2,
            (start[1] + end[1]) / 2 - 0.16,
            min(1.4, geometry.col_gap * 0.88),
        )
    return NetworkLink(index, kind, start, end, color, points, label)


def plan_network(spec: Spec, area: BodyArea) -> NetworkPlan:
    legend, legend_h = network_legend(spec["links"])
    geometry = network_geometry(spec, area, legend_h)
    broadcasts, grouped = broadcast_routes(spec["links"], geometry)
    links = [
        trunk_link(i, link, geometry, spec["lanes"])
        if link.get("kind") == "trunk"
        else ordinary_link(i, link, geometry)
        for i, link in enumerate(spec["links"])
        if i not in grouped
    ]
    return NetworkPlan(geometry, legend, legend_h, broadcasts, links)
