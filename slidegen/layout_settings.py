"""描画へ依存しない標準本文とジャンル固有の配置・可読性設定。単位はin/pt。"""

from dataclasses import dataclass
from typing import Protocol


class HeightArea(Protocol):
    @property
    def height(self) -> float: ...


class BodyArea(HeightArea, Protocol):
    @property
    def top(self) -> float: ...

    @property
    def bottom(self) -> float: ...


@dataclass(frozen=True)
class PageSettings:
    width: float = 13.333
    height: float = 7.5
    margin: float = 0.55
    body_top: float = 1.58
    body_bottom: float = 6.85

    @property
    def body_width(self) -> float:
        return self.width - 2 * self.margin


@dataclass(frozen=True)
class NetworkSettings:
    top_reserve: float = 0.46
    legend_gap: float = 0.12
    right_inset: float = 0.16
    lane_label_min_width: float = 1.46
    lane_label_max_width: float = 2.40
    lane_label_padding: float = 0.26
    lane_title_pt: float = 11.5
    lane_title_min_pt: float = 10.5
    lane_sub_pt: float = 8.5
    lane_sub_min_pt: float = 8.0
    node_title_min_pt: float = 8.5
    node_sub_min_pt: float = 7.5
    legend_pt: float = 9.5
    legend_row_height: float = 0.24


@dataclass(frozen=True)
class SwimlaneSettings:
    # 担当名のレールを含む広幅フレーム。標準本文marginへ寄せない。
    frame_x: float = 0.37
    frame_width: float = 12.59
    body_bottom: float = 6.48
    top_gap: float = 0.06
    stage_height: float = 0.37
    label_min_width: float = 1.27
    label_max_width: float = 1.85
    node_min_pt: float = 9.5
    stage_min_pt: float = 9.5
    lane_min_pt: float = 10.5


@dataclass(frozen=True)
class RoadmapSettings:
    # テーマ欄を独立させず、旧フレーム全体を時間軸に使う。
    label_x: float = 0.72
    grid_width: float = 11.87
    period_min_pt: float = 9.0
    track_min_pt: float = 10.0
    activity_min_pt: float = 9.0
    line_pt: float = 2.4


@dataclass(frozen=True)
class ProtocolSettings:
    rail_width: float = 1.42
    top_gap: float = 0.08
    legend_height: float = 0.36
    stage_min_pt: float = 9.0
    flow_min_pt: float = 10.5
    state_min_pt: float = 9.5
    detail_min_pt: float = 8.0


PAGE = PageSettings()
NETWORK = NetworkSettings()
SWIMLANE = SwimlaneSettings()
ROADMAP = RoadmapSettings()
PROTOCOL = ProtocolSettings()
