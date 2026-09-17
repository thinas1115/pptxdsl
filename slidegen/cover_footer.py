"""表紙とフッターの設定・描画。

本文rendererから独立した範囲だけをユーザー設定可能にする。座標は公開せず、
設定JSONでは文言、表示項目、色、表紙背景画像だけを扱う。
"""
import json
import re
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from string import Formatter

from PIL import Image, UnidentifiedImageError
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

from layout_fit import fit_text_or_raise
from textfit import (
    line_height_in,
    text_width_in,
    title_lines_are_natural,
    wrap_text,
    wrap_title,
)


_HEX_COLOR = re.compile(r"^[0-9A-Fa-f]{6}$")
_TEMPLATE_FIELDS = {
    "title", "footer", "date", "organization", "author", "page", "total",
}
COVER_BACKGROUND_NAME = "Cover Background"
_DEFAULT_BACKGROUND_IMAGE = (
    Path(__file__).resolve().parent / "assets" / "cover" /
    "cover-background.png"
)
_COVER_KEYS = {
    "eyebrow", "show_date", "show_author", "show_rail", "rail",
    "background_image", "background_color", "title_color", "secondary_color",
}
_FOOTER_KEYS = {
    "text", "show_divider", "show_text", "show_page_number", "show_total",
    "text_color", "page_color", "divider_color",
}


@dataclass(frozen=True)
class RailItem:
    label: str
    value: str


@dataclass(frozen=True)
class CoverConfig:
    eyebrow: str
    show_date: bool
    show_author: bool
    show_rail: bool
    rail: tuple[RailItem, ...]
    background_image: Path | None
    background_color: RGBColor
    title_color: RGBColor
    secondary_color: RGBColor


@dataclass(frozen=True)
class FooterConfig:
    text: str
    show_divider: bool
    show_text: bool
    show_page_number: bool
    show_total: bool
    text_color: RGBColor
    page_color: RGBColor
    divider_color: RGBColor


@dataclass(frozen=True)
class CoverFooterConfig:
    cover: CoverConfig
    footer: FooterConfig


_DEFAULT_DATA = {
    "cover": {
        "eyebrow": "",
        "show_date": False,
        "show_author": False,
        "show_rail": True,
        "rail": [
            {"label": "DATE", "value": "{date}"},
            {"label": "ORGANIZATION", "value": "{organization}"},
            {"label": "AUTHOR", "value": "{author}"},
        ],
        "background_image": str(_DEFAULT_BACKGROUND_IMAGE),
        "background_color": "182C43",
        "title_color": "FFFFFC",
        "secondary_color": "DFEBE8",
    },
    "footer": {
        "text": "{footer}",
        "show_divider": True,
        "show_text": True,
        "show_page_number": True,
        "show_total": True,
        "text_color": "666E70",
        "page_color": "182C43",
        "divider_color": "D1CFC8",
    },
}


def _expect_bool(value, path):
    if not isinstance(value, bool):
        raise ValueError(f"{path} は true / false で指定してください")
    return value


def _expect_text(value, path, *, max_length):
    if not isinstance(value, str):
        raise ValueError(f"{path} は文字列で指定してください")
    if len(value) > max_length:
        raise ValueError(f"{path} は {max_length} 文字以内にしてください")
    return value


def _expect_color(value, path):
    if not isinstance(value, str) or not _HEX_COLOR.fullmatch(value):
        raise ValueError(f"{path} は6桁のHEX色(RRGGBB)で指定してください")
    return RGBColor.from_string(value.upper())


def _expect_optional_image(value, path, *, base_dir):
    if value is None:
        return None
    value = _expect_text(value, path, max_length=500).strip()
    if not value:
        raise ValueError(f"{path} は画像ファイルのパスまたは null にしてください")
    source = Path(value).expanduser()
    if not source.is_absolute():
        source = base_dir / source
    source = source.resolve()
    if source.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        raise ValueError(f"{path} はPNGまたはJPEGを指定してください: {value}")
    if not source.is_file():
        raise ValueError(f"{path} の画像が見つかりません: {value}")
    try:
        with Image.open(source) as image:
            image.verify()
    except (OSError, UnidentifiedImageError) as e:
        raise ValueError(f"{path} を画像として読み込めません: {value}") from e
    return source


def _validate_template(value, path, *, max_length):
    value = _expect_text(value, path, max_length=max_length)
    try:
        fields = [name for _, name, _, _ in Formatter().parse(value) if name]
    except ValueError as e:
        raise ValueError(f"{path} のプレースホルダーが不正です: {e}") from e
    for name in fields:
        if name not in _TEMPLATE_FIELDS:
            allowed = ", ".join(sorted(_TEMPLATE_FIELDS))
            raise ValueError(f"{path} の {{{name}}} は使用できません (使用可能: {allowed})")
    try:
        value.format(
            title="title", footer="footer", date="date",
            organization="organization", author="author", page=1, total=10,
        )
    except (KeyError, ValueError) as e:
        raise ValueError(f"{path} のプレースホルダー書式が不正です: {e}") from e
    return value


def _reject_unknown(data, allowed, path):
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise ValueError(f"{path} に未対応の項目があります: {', '.join(unknown)}")


def _merge_data(data):
    if not isinstance(data, dict):
        raise ValueError("設定JSONのトップレベルはオブジェクトにしてください")
    _reject_unknown(data, {"cover", "footer"}, "トップレベル")
    merged = {section: dict(values) for section, values in _DEFAULT_DATA.items()}
    for section in ("cover", "footer"):
        override = data.get(section, {})
        if not isinstance(override, dict):
            raise ValueError(f"{section} はオブジェクトにしてください")
        allowed = _COVER_KEYS if section == "cover" else _FOOTER_KEYS
        _reject_unknown(override, allowed, section)
        merged[section].update(override)
    return merged


def parse_cover_footer_config(data, *, base_dir=None):
    """設定dictを検証し、描画用の不変オブジェクトへ変換する。"""
    base_dir = Path.cwd() if base_dir is None else Path(base_dir)
    merged = _merge_data(data)
    cover = merged["cover"]
    footer = merged["footer"]

    rail_data = cover["rail"]
    if not isinstance(rail_data, list) or len(rail_data) > 3:
        raise ValueError("cover.rail は0〜3件の配列にしてください")
    rail = []
    for idx, item in enumerate(rail_data):
        path = f"cover.rail[{idx}]"
        if not isinstance(item, dict):
            raise ValueError(f"{path} はオブジェクトにしてください")
        _reject_unknown(item, {"label", "value"}, path)
        if set(item) != {"label", "value"}:
            raise ValueError(f"{path} には label と value が必要です")
        rail.append(RailItem(
            _validate_template(item["label"], f"{path}.label", max_length=18),
            _validate_template(item["value"], f"{path}.value", max_length=72),
        ))

    show_date = _expect_bool(cover["show_date"], "cover.show_date")
    show_author = _expect_bool(cover["show_author"], "cover.show_author")
    show_rail = _expect_bool(cover["show_rail"], "cover.show_rail")
    rail_labels = {item.label.strip().upper() for item in rail}
    if show_rail and show_date and "DATE" in rail_labels:
        raise ValueError(
            "cover.rail に DATE を表示する場合は cover.show_date を false "
            "にしてください")
    if show_rail and show_author and rail_labels & {"AUTHOR", "OWNER"}:
        raise ValueError(
            "cover.rail に AUTHOR / OWNER を表示する場合は "
            "cover.show_author を false "
            "にしてください")

    return CoverFooterConfig(
        cover=CoverConfig(
            eyebrow=_validate_template(
                cover["eyebrow"], "cover.eyebrow", max_length=48),
            show_date=show_date,
            show_author=show_author,
            show_rail=show_rail,
            rail=tuple(rail),
            background_image=_expect_optional_image(
                cover["background_image"], "cover.background_image",
                base_dir=base_dir),
            background_color=_expect_color(
                cover["background_color"], "cover.background_color"),
            title_color=_expect_color(cover["title_color"], "cover.title_color"),
            secondary_color=_expect_color(
                cover["secondary_color"], "cover.secondary_color"),
        ),
        footer=FooterConfig(
            text=_validate_template(footer["text"], "footer.text", max_length=100),
            show_divider=_expect_bool(
                footer["show_divider"], "footer.show_divider"),
            show_text=_expect_bool(footer["show_text"], "footer.show_text"),
            show_page_number=_expect_bool(
                footer["show_page_number"], "footer.show_page_number"),
            show_total=_expect_bool(footer["show_total"], "footer.show_total"),
            text_color=_expect_color(footer["text_color"], "footer.text_color"),
            page_color=_expect_color(footer["page_color"], "footer.page_color"),
            divider_color=_expect_color(
                footer["divider_color"], "footer.divider_color"),
        ),
    )


def load_cover_footer_config(path=None):
    """設定JSONを読み込む。pathが未指定なら標準設定を返す。"""
    if path is None:
        return parse_cover_footer_config({})
    source = Path(path)
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise ValueError(f"設定ファイルが見つかりません: {source}") from e
    except json.JSONDecodeError as e:
        raise ValueError(
            f"設定JSONが不正です: {source} ({e.lineno}行{e.colno}列)") from e
    except UnicodeDecodeError as e:
        raise ValueError(f"設定JSONはUTF-8で保存してください: {source}") from e
    return parse_cover_footer_config(data, base_dir=source.parent.resolve())


def _format(value, meta, *, page, total):
    return value.format(
        title=meta.get("title", ""), footer=meta.get("footer", ""),
        date=meta.get("date", ""),
        organization=meta.get("organization", ""),
        author=meta.get("author", ""),
        page=page, total=total,
    )


def _single_line_size(text, width, size, min_size, *, field, weight="regular"):
    def fits_single_line(candidate_size):
        lines = wrap_text(text, width, candidate_size, weight)
        return (
            len(lines) == 1
            and text_width_in(lines[0], candidate_size, weight) <= width + 0.01
        )

    while not fits_single_line(size) and size > min_size:
        size -= 0.5
    if not fits_single_line(size):
        raise ValueError(f"{field} の展開後の文字列が長すぎます: {text}")
    return size


def _rail_value_layout(text, *, field, max_lines):
    """右欄の値を指定行数内へ収め、描画用の文字サイズ・行・高さを返す。"""
    spacing = 1.08
    size = 13.5
    while size >= 9.0 - 0.01:
        lines = wrap_text(text, 2.35, size, "bold")
        if len(lines) <= max_lines:
            height = max(
                0.30,
                len(lines) * line_height_in(size, spacing) + 0.04,
            )
            return size, lines, height
        size -= 0.5
    raise ValueError(
        f"{field} の展開後の文字列が{max_lines}行以内に収まりません: {text}")


def _add_cover_background_image(slide, source):
    """画像比率を維持し、中央を基準にスライド全面へトリミングする。"""
    with Image.open(source) as image:
        image_width, image_height = image.size
    slide_width, slide_height = 13.333, 7.5
    image_ratio = image_width / image_height
    slide_ratio = slide_width / slide_height
    picture = slide.shapes.add_picture(
        str(source), Inches(0), Inches(0),
        width=Inches(slide_width), height=Inches(slide_height),
    )
    picture.name = COVER_BACKGROUND_NAME
    if image_ratio > slide_ratio:
        crop = (1 - slide_ratio / image_ratio) / 2
        picture.crop_left = picture.crop_right = crop
    elif image_ratio < slide_ratio:
        crop = (1 - image_ratio / slide_ratio) / 2
        picture.crop_top = picture.crop_bottom = crop
    return picture


def render_cover(slide, spec, meta, total, config, *, add_text, add_rect):
    """固定レイアウト内で、設定済みの表紙要素を描画する。"""
    cover = config.cover
    add_rect(slide, 0, 0, 13.333, 7.5, cover.background_color)
    if cover.background_image is not None:
        _add_cover_background_image(slide, cover.background_image)
    if cover.eyebrow:
        eyebrow = _format(cover.eyebrow, meta, page=1, total=total)
        eyebrow_size = _single_line_size(
            eyebrow, 3.2, 10, 8, field="cover.eyebrow", weight="bold")
        add_text(slide, 0.9, 0.68, 3.2, 0.3, eyebrow, eyebrow_size,
                 bold=True, color=cover.secondary_color, wrap=False)
    if cover.show_date and meta.get("date"):
        date_size, _ = fit_text_or_raise(
            "cover", "date", meta["date"], 2.62, 0.3, 10,
            min_pt=8, spacing=1.1)
        add_text(slide, 9.78, 0.68, 2.62, 0.3, meta["date"], date_size,
                 color=cover.secondary_color, align=PP_ALIGN.RIGHT)

    rail_items = []
    if cover.show_rail:
        for idx, item in enumerate(cover.rail):
            label = _format(item.label, meta, page=1, total=total)
            value = _format(item.value, meta, page=1, total=total)
            if not label.strip() or not value.strip():
                continue
            label_size = _single_line_size(
                label, 2.25, 8.8, 7,
                field=f"cover.rail[{idx}].label", weight="bold")
            max_lines = 3 if label.strip().upper() in {
                "ORG", "ORGANIZATION", "AUTHOR", "OWNER"
            } else 1
            value_size, value_lines, value_h = _rail_value_layout(
                value, field=f"cover.rail[{idx}].value",
                max_lines=max_lines)
            rail_items.append((
                label, label_size, value_lines, value_size, value_h,
            ))

    has_rail = bool(rail_items)
    title_w = 8.05 if has_rail else 11.45
    subtitle_w = 8.0 if has_rail else 11.35
    title_size, title_lines = fit_text_or_raise(
        "cover", "title", spec["title"], title_w, 2.15, 42,
        min_pt=34, weight="bold", spacing=1.08, wrapper=wrap_title,
        line_validator=title_lines_are_natural)
    title_h = max(1.0, len(title_lines) * line_height_in(title_size, 1.08) + 0.1)
    add_text(slide, 0.9, 1.72, title_w, title_h, "\n".join(title_lines), title_size,
             bold=True, color=cover.title_color, spacing=1.08)

    subtitle_y = min(4.72, 1.72 + title_h + 0.38)
    subtitle_size, subtitle_lines = fit_text_or_raise(
        "cover", "subtitle", spec["subtitle"], subtitle_w, 0.8, 17.5,
        min_pt=15, spacing=1.2)
    add_text(slide, 0.94, subtitle_y, subtitle_w, 0.8, "\n".join(subtitle_lines),
             subtitle_size, color=cover.secondary_color, spacing=1.2)

    if rail_items:
        item_heights = [0.34 + item[4] for item in rail_items]
        if len(rail_items) > 1:
            item_gap = min(
                0.55,
                max(0.30, (3.45 - sum(item_heights))
                    / (len(rail_items) - 1)),
            )
        else:
            item_gap = 0.0
        block_h = sum(item_heights) + item_gap * (len(rail_items) - 1)
        rail_height = 0.14 + block_h + 0.18
        add_rect(slide, 9.45, 1.68, 0.012, rail_height, cover.secondary_color)
        y = 1.82
        for idx, item in enumerate(rail_items):
            label, label_size, value_lines, value_size, value_h = item
            add_text(slide, 9.82, y, 2.25, 0.25, label, label_size,
                     bold=True, color=cover.secondary_color,
                     wrap=False)
            add_text(slide, 9.82, y + 0.34, 2.35, value_h,
                     "\n".join(value_lines), value_size, bold=True,
                     color=cover.title_color, spacing=1.08, wrap=False)
            y += item_heights[idx] + item_gap

    if cover.show_author and meta.get("author"):
        author_size, _ = fit_text_or_raise(
            "cover", "author", meta["author"], 4.8, 0.3, 10.5,
            min_pt=8.5, weight="bold", spacing=1.1)
        add_text(slide, 0.9, 6.5, 4.8, 0.3, meta["author"], author_size,
                 bold=True, color=cover.title_color)


def render_footer(slide, page, meta, total, config, *, add_text, add_rect):
    """本文領域を変えずに、設定済みのフッターだけを描画する。"""
    footer = config.footer
    digits = max(2, len(str(total)))
    if footer.show_divider:
        add_rect(slide, 0.72, 6.92, 11.9, 0.01, footer.divider_color)
    if footer.show_text:
        footer_text = _format(footer.text, meta, page=page, total=total)
        if footer_text.strip():
            default_text = footer.text == _DEFAULT_DATA["footer"]["text"]
            footer_size = 8.2
            if not default_text:
                footer_size = _single_line_size(
                    footer_text, 7.8, 8.2, 6.5, field="footer.text")
            add_text(slide, 0.72, 7.01, 7.8, 0.25,
                     footer_text, footer_size, color=footer.text_color,
                     anchor=MSO_ANCHOR.MIDDLE, wrap=default_text)
    if footer.show_page_number:
        if footer.show_total:
            page_text = f"{page:0{digits}d}"
            total_text = f" / {total:0{digits}d}"
            marker = add_text(
                slide, 11.38, 6.98, 1.24, 0.28,
                page_text + total_text, 8.2, color=footer.text_color,
                align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE, wrap=False)
            if marker is not None:
                paragraph = marker.text_frame.paragraphs[0]
                page_run = paragraph.runs[0]
                total_style = deepcopy(page_run._r.get_or_add_rPr())
                page_run.text = page_text
                page_run.font.size = Pt(11)
                page_run.font.bold = True
                page_run.font.color.rgb = footer.page_color
                total_run = paragraph.add_run()
                default_style = total_run._r.get_or_add_rPr()
                total_run._r.remove(default_style)
                total_run._r.insert(0, total_style)
                total_run.text = total_text
        else:
            add_text(slide, 11.78, 6.98, 0.84, 0.28,
                     f"{page:0{digits}d}", 11, bold=True,
                     color=footer.page_color, align=PP_ALIGN.RIGHT)
