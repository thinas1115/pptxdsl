"""工程表rendererの期間解決・レーン割当・収容計算。"""
from dataclasses import dataclass

from layout_fit import select_fit, stepped

PROGRAM_ROADMAP_STEP = 0.25


@dataclass(frozen=True)
class ActivityPlacement:
    """時間軸上へ正規化し、自動レーンを割り当てた作業。"""

    index: int
    activity: dict
    start: float
    end: float
    lane: int


def _period_index(value, periods, *, end=False, marker=False):
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


def resolve_span(item, periods):
    """start/endを時間軸境界へ変換する。文字列のendは指定期間を含む。"""
    start = _period_index(item.get("start"), periods)
    end = _period_index(item.get("end"), periods, end=True)
    if not 0 <= start < end <= len(periods):
        raise ValueError(
            f"start={item.get('start')!r} / end={item.get('end')!r} は、"
            f"0 <= start < end <= {len(periods)} または期間ラベルで指定してください"
        )
    return start, end


def resolve_program_span(item, periods):
    """program_roadmapの期間を1/4期間刻みの境界へ正規化する。"""
    start, end = resolve_span(item, periods)
    for field, position in (("start", start), ("end", end)):
        steps = position / PROGRAM_ROADMAP_STEP
        if abs(steps - round(steps)) > 1e-8:
            raise ValueError(
                f"{field}={item.get(field)!r} は0.25刻みの期間境界で"
                "指定してください"
            )
    return start, end


def resolve_marker(value, periods):
    """マイルストーン位置を解決する。文字列は該当期間の中央へ置く。"""
    at = _period_index(value, periods, marker=True)
    if not 0 <= at <= len(periods):
        raise ValueError(
            f"at={value!r} は0〜{len(periods)}または期間ラベルで指定してください"
        )
    return at


def pack_activities(activities, periods):
    """重なる作業を別レーンへ自動配置する区間彩色。"""
    normalized = []
    for index, activity in enumerate(activities):
        start, end = resolve_program_span(activity, periods)
        normalized.append((start, end, index, activity))
    normalized.sort(key=lambda item: (item[0], item[1], item[2]))

    lane_ends = []
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


def centered_label_box(center, previous_center, following_center,
                       outer_left, outer_right, max_width):
    """隣接ラベルと重ねず、中心をバー中心に固定したラベル枠を返す。"""
    left_limit = outer_left if previous_center is None else (
        previous_center + center) / 2
    right_limit = outer_right if following_center is None else (
        center + following_center) / 2
    half_width = min(
        max_width / 2,
        center - left_limit,
        right_limit - center,
    )
    if half_width <= 0:
        raise ValueError("ラベルを中央配置できる幅がありません")
    return center - half_width, half_width * 2


def fit_program_roadmap(available, lane_counts, *, has_note=False):
    """テーマごとに異なるレーン数を自然高さで収容する。"""
    reserve = 0.30 if has_note else 0.0
    usable = available - reserve
    track_count = len(lane_counts)

    def used(values):
        rows = sum(
            2 * values["track_pad"] + count * values["lane_pitch"]
            for count in lane_counts
        )
        return (values["top_gap"] + values["header_h"] + rows
                + max(0, track_count - 1) * values["track_gap"])

    candidates = []
    standard = {
        "top_gap": 0.16, "header_h": 0.44, "track_pad": 0.08,
        "track_gap": 0.03, "lane_pitch": 0.34, "period_pt": 10.0,
        "track_pt": 11.5, "activity_pt": 9.5,
    }
    candidates.append(("standard", standard, used(standard)))
    for lane_pitch in stepped(0.32, 0.30, 0.02):
        values = {
            "top_gap": 0.10, "header_h": 0.42, "track_pad": 0.06,
            "track_gap": 0.01, "lane_pitch": lane_pitch,
            "period_pt": 9.5, "track_pt": 11.0,
            "activity_pt": 9.0,
        }
        candidates.append(("gap", values, used(values)))
    for lane_pitch in stepped(0.28, 0.24, 0.02):
        ratio = (lane_pitch - 0.24) / 0.04
        values = {
            "top_gap": 0.08, "header_h": 0.40, "track_pad": 0.05,
            "track_gap": 0.01, "lane_pitch": lane_pitch,
            "period_pt": 8.0 + ratio, "track_pt": 9.5 + ratio,
            "activity_pt": 8.0 + 0.5 * ratio,
        }
        candidates.append(("element", values, used(values)))
    return select_fit(
        "program_roadmap", usable, candidates,
        guidance=("同時並行の作業を減らすか、テーマを複数スライドへ分割してください。"),
    )
