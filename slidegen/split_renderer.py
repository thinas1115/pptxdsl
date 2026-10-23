"""共通ヘッダーの下で、領域対応した本文rendererを左右へ委譲する。"""

from typing import Any

from pptx.util import Emu

from slidegen import generate as g
from slidegen.chart_renderer import render_chart
from slidegen.diagram_layout import render_diagram
from slidegen.image_slide import render_image_body
from slidegen.layout_fit import FitError
from slidegen.split_layout import DrawingRegion, plan_split


def _bullets(slide: Any, spec: dict[str, Any], region: DrawingRegion) -> None:
    g.render_bullets_body(slide, spec, region, region=region)


def _cards(slide: Any, spec: dict[str, Any], region: DrawingRegion) -> None:
    g.render_cards_body(slide, spec, region, region=region)


def _table(slide: Any, spec: dict[str, Any], region: DrawingRegion) -> None:
    g.render_table_body(slide, spec, region, region=region)


def _image(slide: Any, spec: dict[str, Any], region: DrawingRegion) -> None:
    render_image_body(slide, spec, region, region=region)


def _diagram(slide: Any, spec: dict[str, Any], region: DrawingRegion) -> None:
    render_diagram(slide, spec["diagram"], content_area=region)


def _chart(slide: Any, spec: dict[str, Any], region: DrawingRegion) -> None:
    render_chart(slide, spec["chart"], region)


ADAPTERS = {
    "bullets": _bullets,
    "cards": _cards,
    "table": _table,
    "image": _image,
    "diagram": _diagram,
    "chart": _chart,
}


def s_split(slide: Any, spec: dict[str, Any], page: int) -> None:
    area = g.header(slide, spec["kicker"], spec["title"], spec.get("lead"))
    plan = plan_split(area, shifted=area.shifted, has_note=bool(spec.get("note")))
    for side, region in (("left", plan.left), ("right", plan.right)):
        child = spec[side]
        adapter = ADAPTERS.get(child["type"])
        if adapter is None:
            raise FitError(f"split.{side}: このtypeは半幅に対応していません")
        start = len(slide.shapes)
        try:
            adapter(slide, child, region)
            # 段階的収容後も領域をはみ出す描画は、切り取ったり隣へ逃がしたりしない。
            for shape in list(slide.shapes)[start:]:
                if (
                    shape.left.inches < region.left - 0.005
                    or Emu(shape.left + shape.width).inches > region.right + 0.005
                    or shape.top.inches < region.top - 0.005
                    or Emu(shape.top + shape.height).inches > region.bottom + 0.005
                ):
                    raise FitError(
                        "本文が子コンテンツの領域へ収まりません。項目数か文言を減らしてください。"
                    )
        except FitError as error:
            raise FitError(f"split.{side} ({child['type']}): {error}") from None
    if spec.get("note"):
        g.note_line(slide, spec["note"])
