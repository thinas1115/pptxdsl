"""左右50:50の本文領域。PPTX、座標入力、rendererのグローバル変更に依存しない。"""

from dataclasses import dataclass
import math

from slidegen.layout_fit import FitError
from slidegen.layout_settings import BodyArea, PAGE


@dataclass(frozen=True)
class DrawingRegion:
    left: float
    top: float
    width: float
    bottom: float
    shifted: bool = False

    def __post_init__(self) -> None:
        if (
            not all(
                math.isfinite(value) for value in (self.left, self.top, self.width, self.bottom)
            )
            or self.width <= 0
            or self.bottom <= self.top
        ):
            raise FitError("split: 子コンテンツの描画領域が不足しています")

    @property
    def right(self) -> float:
        return self.left + self.width

    @property
    def height(self) -> float:
        return self.bottom - self.top


@dataclass(frozen=True)
class SplitPlan:
    left: DrawingRegion
    right: DrawingRegion
    gutter: float


def plan_split(area: BodyArea, *, shifted: bool = False, has_note: bool = False) -> SplitPlan:
    gutter = 0.46
    width = (PAGE.body_width - gutter) / 2
    top = area.top + 0.08
    bottom = area.bottom - (0.30 if has_note else 0)
    left = DrawingRegion(PAGE.margin, top, width, bottom, shifted)
    right = DrawingRegion(PAGE.margin + width + gutter, top, width, bottom, shifted)
    return SplitPlan(left, right, gutter)
