"""工程表rendererの期間解決・レーン割当・収容計算。"""

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from slidegen.layout_fit import FitCandidate, FitError, FitResult, select_fit, stepped
from slidegen.layout_settings import BodyArea, ROADMAP

PROGRAM_ROADMAP_STEP = 0.25


@dataclass(frozen=True)
class ActivityPlacement:
    """時間軸上へ正規化し、自動レーンを割り当てた作業。"""

    index: int
    activity: Mapping[str, Any]
    start: float
    end: float
    lane: int


def _period_index(
    value: Any, periods: Sequence[str], *, end: bool = False, marker: bool = False
) -> float:
    if isinstance(value, bool):
        raise ValueError("真偽値は期間位置に指定できません")
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str) or value not in periods:
        raise ValueError(f"期間ラベル {value!r} が期間一覧にありません")
    index = periods.index(value)
    if marker:
        return index + 0.5
    return index + (1.0 if end else 0.0)


def resolve_span(item: Mapping[str, Any], periods: Sequence[str]) -> tuple[float, float]:
    """start/endを時間軸境界へ変換する。文字列のendは指定期間を含む。"""
    start = _period_index(item.get("start"), periods)
    end = _period_index(item.get("end"), periods, end=True)
    if not 0 <= start < end <= len(periods):
        raise ValueError(
            f"start={item.get('start')!r} / end={item.get('end')!r} は、"
            f"0 <= start < end <= {len(periods)} または期間ラベルで指定してください"
        )
    return start, end


def resolve_program_span(item: Mapping[str, Any], periods: Sequence[str]) -> tuple[float, float]:
    """program_roadmapの期間を1/4期間刻みの境界へ正規化する。"""
    start, end = resolve_span(item, periods)
    for field, position in (("start", start), ("end", end)):
        steps = position / PROGRAM_ROADMAP_STEP
        if abs(steps - round(steps)) > 1e-8:
            raise ValueError(f"{field}={item.get(field)!r} は0.25刻みの期間境界で指定してください")
    return start, end


def resolve_marker(value: Any, periods: Sequence[str]) -> float:
    """マイルストーン位置を解決する。文字列は該当期間の中央へ置く。"""
    at = _period_index(value, periods, marker=True)
    if not 0 <= at <= len(periods):
        raise ValueError(f"at={value!r} は0〜{len(periods)}または期間ラベルで指定してください")
    return at


def pack_activities(
    activities: Sequence[Mapping[str, Any]], periods: Sequence[str]
) -> tuple[list[ActivityPlacement], int]:
    """重なる作業を別レーンへ自動配置する区間彩色。"""
    normalized = []
    for index, activity in enumerate(activities):
        start, end = resolve_program_span(activity, periods)
        normalized.append((start, end, index, activity))
    normalized.sort(key=lambda item: (item[0], item[1], item[2]))

    lane_ends: list[float] = []
    placements = []
    for start, end, index, activity in normalized:
        lane = next(
            (i for i, lane_end in enumerate(lane_ends) if start >= lane_end),
            len(lane_ends),
        )
        if lane == len(lane_ends):
            lane_ends.append(end)
        else:
            lane_ends[lane] = end
        placements.append(ActivityPlacement(index, activity, start, end, lane))
    placements.sort(key=lambda item: item.index)
    return placements, len(lane_ends)


def centered_label_box(
    center: float,
    previous_center: float | None,
    following_center: float | None,
    outer_left: float,
    outer_right: float,
    max_width: float,
) -> tuple[float, float]:
    """隣接ラベルと重ねず、中心をバー中心に固定したラベル枠を返す。"""
    left_limit = outer_left if previous_center is None else (previous_center + center) / 2
    right_limit = outer_right if following_center is None else (center + following_center) / 2
    half_width = min(
        max_width / 2,
        center - left_limit,
        right_limit - center,
    )
    if half_width <= 0:
        raise ValueError("ラベルを中央配置できる幅がありません")
    return center - half_width, half_width * 2


def fit_program_roadmap(
    available: float, lane_counts: Sequence[int], *, has_note: bool = False
) -> FitResult:
    """テーマごとに異なるレーン数を自然高さで収容する。"""
    reserve = 0.30 if has_note else 0.0
    usable = available - reserve
    track_count = len(lane_counts)

    def used(values: Mapping[str, float]) -> float:
        rows = sum(2 * values["track_pad"] + count * values["lane_pitch"] for count in lane_counts)
        return (
            values["top_gap"]
            + values["header_h"]
            + rows
            + max(0, track_count - 1) * values["track_gap"]
        )

    candidates: list[FitCandidate] = []
    standard = {
        "top_gap": 0.16,
        "header_h": 0.44,
        "track_pad": 0.08,
        "track_gap": 0.03,
        "lane_pitch": 0.34,
        "period_pt": 10.0,
        "track_pt": 11.5,
        "activity_pt": 9.5,
    }
    candidates.append(("standard", standard, used(standard)))
    for lane_pitch in stepped(0.32, 0.30, 0.02):
        values = {
            "top_gap": 0.10,
            "header_h": 0.42,
            "track_pad": 0.06,
            "track_gap": 0.01,
            "lane_pitch": lane_pitch,
            "period_pt": 9.5,
            "track_pt": 11.0,
            "activity_pt": 9.0,
        }
        candidates.append(("gap", values, used(values)))
    for lane_pitch in stepped(0.28, 0.24, 0.02):
        ratio = (lane_pitch - 0.24) / 0.04
        values = {
            "top_gap": 0.08,
            "header_h": 0.40,
            "track_pad": 0.05,
            "track_gap": 0.01,
            "lane_pitch": lane_pitch,
            "period_pt": 8.0 + ratio,
            "track_pt": 9.5 + ratio,
            "activity_pt": 8.0 + 0.5 * ratio,
        }
        candidates.append(("element", values, used(values)))
    return select_fit(
        "program_roadmap",
        usable,
        candidates,
        guidance=("同時並行の作業を減らすか、テーマを複数スライドへ分割してください。"),
    )


@dataclass(frozen=True)
class RoadmapActivity:
    placement: ActivityPlacement
    lane_top: float
    x1: float
    x2: float
    label_x: float
    label_width: float


@dataclass(frozen=True)
class RoadmapMilestone:
    x: float
    y: float
    label_x: float
    label_width: float


@dataclass(frozen=True)
class RoadmapPlan:
    fitted: FitResult
    grid_x: float
    period_width: float
    top: float
    grid_height: float
    row_heights: list[float]
    row_tops: list[float]
    bottom: float
    activities: list[list[RoadmapActivity]]
    milestones: list[RoadmapMilestone | None]


def plan_program_roadmap(spec: Mapping[str, Any], area: BodyArea) -> RoadmapPlan:
    """正規化・収容・全座標を確定する。図形やPPTXを生成しない。"""
    periods, tracks = spec["periods"], spec["tracks"]
    if not 3 <= len(periods) <= 12:
        raise FitError("program_roadmap: 期間は3〜12件までです。期間をまとめてください。")
    if not 1 <= len(tracks) <= 6:
        raise FitError("program_roadmap: テーマは1〜6件までです。複数スライドへ分割してください。")
    packed = [pack_activities(track["activities"], periods) for track in tracks]
    counts = [
        count + int(bool(track.get("milestone")))
        for track, (_placements, count) in zip(tracks, packed)
    ]
    fitted = fit_program_roadmap(area.height, counts, has_note=bool(spec.get("note")))
    values = fitted.values
    grid_x = ROADMAP.label_x + ROADMAP.track_width
    period_width = ROADMAP.grid_width / len(periods)
    top = area.top + values["top_gap"]
    row_heights = [2 * values["track_pad"] + count * values["lane_pitch"] for count in counts]
    grid_height = values["header_h"] + sum(row_heights) + values["track_gap"] * (len(tracks) - 1)
    row_tops = []
    cursor = top + values["header_h"]
    activities: list[list[RoadmapActivity]] = []
    milestones: list[RoadmapMilestone | None] = []
    for track, row_height, (placements, lane_count) in zip(tracks, row_heights, packed):
        row_top = cursor
        row_tops.append(row_top)
        cursor += row_height + values["track_gap"]
        neighbors: dict[int, tuple[ActivityPlacement | None, ActivityPlacement | None]] = {}
        for lane in range(lane_count):
            items = sorted(
                (item for item in placements if item.lane == lane),
                key=lambda item: (item.start, item.end),
            )
            for position, item in enumerate(items):
                neighbors[item.index] = (
                    items[position - 1] if position else None,
                    items[position + 1] if position + 1 < len(items) else None,
                )
        planned = []
        for placement in placements:
            lane_top = row_top + values["track_pad"] + placement.lane * values["lane_pitch"]
            x1 = grid_x + placement.start * period_width + 0.035
            x2 = grid_x + placement.end * period_width - 0.035
            previous, following = neighbors[placement.index]
            previous_center = (
                None
                if previous is None
                else (grid_x + (previous.start + previous.end) * period_width / 2)
            )
            following_center = (
                None
                if following is None
                else (grid_x + (following.start + following.end) * period_width / 2)
            )
            label_x, label_width = centered_label_box(
                (x1 + x2) / 2,
                previous_center,
                following_center,
                grid_x,
                grid_x + ROADMAP.grid_width,
                1.45,
            )
            planned.append(RoadmapActivity(placement, lane_top, x1, x2, label_x, label_width))
        activities.append(planned)
        milestone = track.get("milestone")
        if milestone:
            x = grid_x + resolve_marker(milestone["at"], periods) * period_width
            y = row_top + values["track_pad"] + lane_count * values["lane_pitch"] + 0.035
            width = min(1.45, max(0.78, period_width * 1.7))
            left = min(max(x - width / 2, grid_x), grid_x + ROADMAP.grid_width - width)
            milestones.append(RoadmapMilestone(x, y, left, width))
        else:
            milestones.append(None)
    return RoadmapPlan(
        fitted,
        grid_x,
        period_width,
        top,
        grid_height,
        row_heights,
        row_tops,
        cursor - values["track_gap"],
        activities,
        milestones,
    )
