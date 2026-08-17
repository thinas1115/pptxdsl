"""レンダー済みギャラリーPNGからカテゴリー・type別の一覧画像を生成する。"""

from __future__ import annotations

import argparse
import os
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from content_patterns import PATTERN_DECK


CANVAS_WIDTH = 1920
BG = "#DCE8EE"
INK = "#10283A"
MUTED = "#536D7C"
ACCENT = "#07858B"
BORDER = "#9EB4C0"

MARGIN_X = 80
HEADER_Y = 34
CATEGORY_GAP = 78
ROW_GAP = 44
GROUP_GAP = 28
THUMB_GAP = 10
THUMB_W = 214
THUMB_H = round(THUMB_W * 9 / 16)
LABEL_H = 50

CATEGORY_ORDER = ("Common", "NW")
TYPE_ORDER = (
    "title",
    "bullets",
    "cards",
    "table",
    "two_column",
    "chart",
    "image",
    "process",
    "program_roadmap",
    "matrix",
    "org",
    "diagram",
    "scope_boundary",
    "decision_summary",
    "paired_comparison",
    "relationship_map",
    "swimlane_flow",
    "message_sequence",
    "concept",
    "config_lab",
    "knowledge_check",
    "nw_topology",
    "nw_protocol_flow",
    "nw_frame_anatomy",
)
TYPE_CATEGORIES = {
    "title": "Common",
    "bullets": "Common",
    "cards": "Common",
    "table": "Common",
    "two_column": "Common",
    "chart": "Common",
    "image": "Common",
    "process": "Common",
    "program_roadmap": "Common",
    "matrix": "Common",
    "org": "Common",
    "diagram": "Common",
    "scope_boundary": "Common",
    "decision_summary": "Common",
    "paired_comparison": "Common",
    "relationship_map": "Common",
    "swimlane_flow": "Common",
    "message_sequence": "Common",
    "concept": "Common",
    "config_lab": "Common",
    "knowledge_check": "Common",
    "nw_topology": "NW",
    "nw_protocol_flow": "NW",
    "nw_frame_anatomy": "NW",
}


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = (
        ("YuGothB.ttc", "YuGothR.ttc") if bold else ("YuGothR.ttc", "YuGothB.ttc")
    ) + (
        ("arialbd.ttf", "arial.ttf") if bold else ("arial.ttf", "arialbd.ttf")
    ) + (
        ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf")
        if bold
        else ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf")
    )
    roots = [Path(os.environ.get("WINDIR", "")) / "Fonts", Path("/usr/share/fonts/truetype/dejavu")]
    for name in names:
        for root in roots:
            candidate = root / name
            if candidate.is_file():
                return ImageFont.truetype(candidate, size=size)
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _gallery_groups() -> dict[str, list[int]]:
    groups: dict[str, list[int]] = defaultdict(list)
    for page, slide in enumerate(PATTERN_DECK["slides"], start=1):
        type_ = slide.get("type")
        if not isinstance(type_, str):
            raise ValueError(f"slides[{page}] has no string type")
        groups[type_].append(page)
    unknown = sorted(set(groups) - set(TYPE_CATEGORIES))
    if unknown:
        raise ValueError(f"Unclassified gallery type: {', '.join(unknown)}")
    missing_order = sorted(set(groups) - set(TYPE_ORDER))
    if missing_order:
        raise ValueError(f"TYPE_ORDER is missing: {', '.join(missing_order)}")
    return groups


def _label(type_: str, count: int) -> str:
    return f"{type_} x{count}" if count > 1 else type_


def _estimated_label_width(label: str) -> int:
    # Long snake_case type names are wider than a single thumbnail.
    return max(THUMB_W, len(label) * 17)


def _layout(groups: dict[str, list[int]]) -> tuple[list[dict[str, object]], int]:
    placements: list[dict[str, object]] = []
    y = 176
    for category in CATEGORY_ORDER:
        placements.append({"kind": "category", "category": category, "x": MARGIN_X, "y": y})
        y += 58
        x = MARGIN_X
        row_height = LABEL_H + THUMB_H
        for type_ in TYPE_ORDER:
            pages = groups.get(type_)
            if not pages or TYPE_CATEGORIES[type_] != category:
                continue
            label = _label(type_, len(pages))
            thumbs_width = len(pages) * THUMB_W + (len(pages) - 1) * THUMB_GAP
            group_width = max(thumbs_width, _estimated_label_width(label))
            if x > MARGIN_X and x + group_width > CANVAS_WIDTH - MARGIN_X:
                x = MARGIN_X
                y += row_height + ROW_GAP
            placements.append({"kind": "group", "type": type_, "pages": pages, "x": x, "y": y})
            x += group_width + GROUP_GAP
        y += row_height + CATEGORY_GAP
    return placements, max(980, y)


def _paste_thumbnail(canvas: Image.Image, source: Path, x: int, y: int) -> None:
    with Image.open(source) as image:
        thumb = image.convert("RGB").resize((THUMB_W, THUMB_H), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((x - 2, y - 2, x + THUMB_W + 1, y + THUMB_H + 1), fill="#F8F7F1", outline=BORDER, width=2)
    canvas.paste(thumb, (x, y))


def build(png_dir: Path, output: Path) -> None:
    groups = _gallery_groups()
    placements, canvas_height = _layout(groups)
    canvas = Image.new("RGB", (CANVAS_WIDTH, canvas_height), BG)
    draw = ImageDraw.Draw(canvas)
    title_font = _font(66, bold=True)
    count_font = _font(36, bold=True)
    small_font = _font(22)
    category_font = _font(26, bold=True)
    label_font = _font(29, bold=True)

    type_count = len(groups)
    example_count = sum(len(pages) for pages in groups.values())
    draw.text((MARGIN_X, HEADER_Y), "pptxdsl", fill=INK, font=title_font)
    draw.line((370, HEADER_Y + 31, 370, HEADER_Y + 96), fill="#87A3B2", width=3)
    draw.text((410, HEADER_Y + 35), f"{type_count} TYPES  /  {example_count} EXAMPLES", fill=ACCENT, font=count_font)
    draw.text((414, HEADER_Y + 85), "GROUPED BY CATEGORY AND TYPE", fill=MUTED, font=small_font)

    for item in placements:
        if item["kind"] == "category":
            x = int(item["x"])
            y = int(item["y"])
            category = str(item["category"])
            label = "COMMON TYPES" if category == "Common" else "NW TYPES"
            draw.text((x, y), label, fill=INK, font=category_font)
            draw.line((x, y + 39, CANVAS_WIDTH - MARGIN_X, y + 39), fill="#87A3B2", width=2)
            continue

        x = int(item["x"])
        y = int(item["y"])
        type_ = str(item["type"])
        pages = list(item["pages"])  # type: ignore[arg-type]
        label = _label(type_, len(pages))
        thumbs_width = len(pages) * THUMB_W + (len(pages) - 1) * THUMB_GAP
        group_width = max(thumbs_width, _estimated_label_width(label))
        draw.text((x, y), label, fill="#294E63", font=label_font)
        draw.line((x, y + 42, x + group_width, y + 42), fill=ACCENT, width=4)
        thumb_y = y + 54
        thumb_x = x + max(0, (group_width - thumbs_width) // 2)
        for index, page in enumerate(pages):
            source = png_dir / f"slide_{int(page):02d}.png"
            if not source.is_file():
                raise FileNotFoundError(f"レンダー画像が見つかりません: {source}")
            _paste_thumbnail(canvas, source, thumb_x + index * (THUMB_W + THUMB_GAP), thumb_y)

    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("png_dir", type=Path, help="slide_01.png形式のレンダー画像ディレクトリ")
    parser.add_argument(
        "output",
        type=Path,
        nargs="?",
        default=Path("docs/pattern-gallery-by-type.png"),
        help="一覧画像の出力先",
    )
    args = parser.parse_args()
    build(args.png_dir, args.output)


if __name__ == "__main__":
    main()
