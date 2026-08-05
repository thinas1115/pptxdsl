"""レンダー済みギャラリーPNGからTYPE別の一覧画像を生成する。"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


CANVAS_SIZE = (1920, 1080)
BG = "#DCE8EE"
INK = "#10283A"
MUTED = "#536D7C"
ACCENT = "#07858B"
BORDER = "#9EB4C0"


GROUPS = (
    ("title", (1,), 80, 170, 235),
    ("bullets ×3", (2, 3, 4), 345, 170, 235),
    ("cards ×2", (5, 6), 1100, 170, 235),
    ("table", (7,), 1610, 170, 235),
    ("chart ×3", (9, 10, 11), 80, 382, 235),
    ("image", (12,), 835, 382, 235),
    ("twocol", (8,), 1100, 382, 235),
    ("process ×2", (13, 14), 1365, 382, 235),
    ("program roadmap ×2", (15, 16), 80, 592, 235),
    ("matrix", (17,), 610, 592, 235),
    ("org", (18,), 875, 592, 235),
    ("diagram ×4", (19, 20, 21, 22), 475, 800, 235),
)


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


def _paste_thumbnail(canvas: Image.Image, source: Path, x: int, y: int, width: int) -> None:
    height = round(width * 9 / 16)
    with Image.open(source) as image:
        thumb = image.convert("RGB").resize((width, height), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((x - 2, y - 2, x + width + 1, y + height + 1), fill="#FFFFFF", outline=BORDER, width=2)
    canvas.paste(thumb, (x, y))


def build(png_dir: Path, output: Path) -> None:
    canvas = Image.new("RGB", CANVAS_SIZE, BG)
    draw = ImageDraw.Draw(canvas)
    title_font = _font(66, bold=True)
    count_font = _font(36, bold=True)
    small_font = _font(22)
    label_font = _font(29, bold=True)

    draw.text((80, 34), "pptxdsl", fill=INK, font=title_font)
    draw.line((370, 65, 370, 130), fill="#87A3B2", width=3)
    draw.text((410, 69), "12 TYPES  /  22 EXAMPLES", fill=ACCENT, font=count_font)
    draw.text((414, 119), "GROUPED BY TYPE", fill=MUTED, font=small_font)

    for label, pages, x, label_y, thumb_width in GROUPS:
        gap = 10
        group_width = len(pages) * thumb_width + (len(pages) - 1) * gap
        draw.text((x, label_y), label, fill="#294E63", font=label_font)
        draw.line((x, label_y + 42, x + group_width, label_y + 42), fill=ACCENT, width=4)
        thumb_y = label_y + 54
        for index, page in enumerate(pages):
            source = png_dir / f"slide_{page:02d}.png"
            if not source.is_file():
                raise FileNotFoundError(f"レンダー画像が見つかりません: {source}")
            _paste_thumbnail(canvas, source, x + index * (thumb_width + gap), thumb_y, thumb_width)

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
