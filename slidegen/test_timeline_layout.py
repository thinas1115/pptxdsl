"""工程表の期間解決・自動レーン・段階的収容を検証する。"""
from copy import deepcopy

from layout_fit import FitError
from timeline_layout import (centered_label_box, fit_program_roadmap,
                             pack_activities, resolve_marker,
                             resolve_program_span, resolve_span)
from validate_content import validate


def _must_fail(fn, expected):
    try:
        fn()
    except (FitError, ValueError) as exc:
        assert expected in str(exc), str(exc)
    else:
        raise AssertionError("過密または不正な入力を拒否しませんでした")


def main():
    periods = ["4月", "5月", "6月", "7月"]
    assert resolve_span({"start": 0, "end": 2}, periods) == (0.0, 2.0)
    assert resolve_span({"start": "5月", "end": "6月"}, periods) == (1.0, 3.0)
    assert resolve_program_span(
        {"start": 0.25, "end": 2.75}, periods) == (0.25, 2.75)
    _must_fail(
        lambda: resolve_program_span(
            {"start": 0.20, "end": 2.75}, periods),
        "0.25刻み",
    )
    assert resolve_marker("6月", periods) == 2.5
    _must_fail(
        lambda: resolve_span({"start": "4月", "end": "不明"}, periods),
        "期間一覧にありません",
    )

    placements, lane_count = pack_activities([
        {"label": "A", "start": "4月", "end": "6月"},
        {"label": "B", "start": "5月", "end": "7月"},
        {"label": "C", "start": "7月", "end": "7月"},
    ], periods)
    assert lane_count == 2
    assert [placement.lane for placement in placements] == [0, 1, 0]

    quarter_placements, quarter_lane_count = pack_activities([
        {"label": "A", "start": 0.25, "end": 1.25},
        {"label": "B", "start": 1.25, "end": 2.75},
    ], periods)
    assert quarter_lane_count == 1
    assert [(p.start, p.end) for p in quarter_placements] == [
        (0.25, 1.25), (1.25, 2.75)]

    label_x, label_w = centered_label_box(
        center=4.5, previous_center=None, following_center=5.25,
        outer_left=0.0, outer_right=12.0, max_width=1.45)
    assert abs((label_x + label_w / 2) - 4.5) < 1e-9
    assert abs(label_w - 0.75) < 1e-9

    assert fit_program_roadmap(5.27, [1, 2, 1]).stage == "standard"
    assert fit_program_roadmap(4.40, [2, 2, 4, 1, 1]).stage == "gap"
    assert fit_program_roadmap(4.80, [3, 3, 3, 3, 3]).stage == "element"
    _must_fail(
        lambda: fit_program_roadmap(5.27, [4, 4, 4, 4, 4, 4]),
        "最小設定",
    )

    deck = {
        "meta": {"title": "検証", "footer": "検証", "date": "2026年7月",
                 "author": "検証担当"},
        "slides": [{
            "type": "program_roadmap", "kicker": "検証", "title": "工程表",
            "periods": periods,
            "tracks": [{"name": "テーマ", "activities": [
                {"label": "作業", "start": "4月", "end": "6月"},
            ]}],
        }],
    }
    assert not validate(deck)
    invalid = deepcopy(deck)
    invalid["slides"][0]["tracks"][0]["activities"][0]["end"] = "不明"
    assert any("期間一覧にありません" in error
               for error in validate(invalid))
    invalid_quarter = deepcopy(deck)
    invalid_quarter["slides"][0]["tracks"][0]["activities"][0].update(
        start=0.2, end=1.0)
    assert any("0.25刻み" in error
               for error in validate(invalid_quarter))

    annotated = deepcopy(deck)
    annotated_track = annotated["slides"][0]["tracks"][0]
    annotated_track["goal"] = "判断に必要な材料を揃える"
    annotated_track["milestone"] = {"at": "5月", "label": "方針決定"}
    assert not validate(annotated)

    invalid_goal = deepcopy(annotated)
    invalid_goal["slides"][0]["tracks"][0]["goal"] = ""
    assert any("goal は空でない文字列" in error
               for error in validate(invalid_goal))

    invalid_milestone_step = deepcopy(annotated)
    invalid_milestone_step["slides"][0]["tracks"][0]["milestone"] = {
        "at": 0.2, "label": "方針決定"}
    assert any("0.25刻み" in error
               for error in validate(invalid_milestone_step))

    outside_milestone = deepcopy(annotated)
    outside_milestone["slides"][0]["tracks"][0]["milestone"] = {
        "at": "7月", "label": "範囲外"}
    assert any("同じテーマ内のいずれかの作業期間内" in error
               for error in validate(outside_milestone))

    print("timeline layout tests passed")


if __name__ == "__main__":
    main()
