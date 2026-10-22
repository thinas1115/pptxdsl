"""生成単位の読み取り専用状態。スレッド・入れ子の生成間で共有しない。"""
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Mapping

from pptx.dml.color import RGBColor

from slidegen.cover_footer import CoverFooterConfig, load_cover_footer_config
from slidegen.layout_settings import PAGE


@dataclass(frozen=True)
class Theme:
    """標準テーマの不変値。JSONへ座標やフォント値を公開しない。"""
    NAVY: RGBColor = RGBColor(0x18, 0x2C, 0x43)
    ACCENT: RGBColor = RGBColor(0x0D, 0x78, 0x70)
    CORAL: RGBColor = RGBColor(0xC7, 0x58, 0x3E)
    LIGHT: RGBColor = RGBColor(0xDF, 0xEB, 0xE8)
    TEXT: RGBColor = RGBColor(0x20, 0x27, 0x29)
    GRAY: RGBColor = RGBColor(0x66, 0x6E, 0x70)
    DONE_TEXT: RGBColor = RGBColor(0x56, 0x60, 0x62)
    WHITE: RGBColor = RGBColor(0xFF, 0xFF, 0xFC)
    SURFACE: RGBColor = RGBColor(0xFA, 0xF9, 0xF5)
    ZEBRA: RGBColor = RGBColor(0xEC, 0xEA, 0xE4)
    CANVAS: RGBColor = RGBColor(0xF7, 0xF5, 0xEF)
    RULE: RGBColor = RGBColor(0xD1, 0xCF, 0xC8)
    SLIDE_W: float = PAGE.width
    SLIDE_H: float = PAGE.height
    MARGIN: float = PAGE.margin
    BODY_TOP: float = PAGE.body_top
    BODY_BOTTOM: float = PAGE.body_bottom


STANDARD_THEME = Theme()


@dataclass(frozen=True)
class GenerationContext:
    metadata: Mapping
    slide_count: int
    cover_footer: CoverFooterConfig
    theme: Theme = STANDARD_THEME
    content_bottom: float = STANDARD_THEME.BODY_BOTTOM

    def __post_init__(self):
        if self.theme != STANDARD_THEME:
            raise ValueError("任意テーマの差し替えは未対応です。標準テーマを使用してください")
        object.__setattr__(self, "metadata", MappingProxyType(deepcopy(dict(self.metadata))))

    def with_bottom(self, bottom):
        return replace(self, content_bottom=bottom)


def make_context(deck, cover_footer_config=None):
    config = (cover_footer_config if isinstance(cover_footer_config, CoverFooterConfig)
              else load_cover_footer_config(cover_footer_config))
    return GenerationContext(deck["meta"], len(deck["slides"]), config)


_EMPTY_CONTEXT = make_context({"meta": {}, "slides": []})
_CURRENT = ContextVar("pptxdsl_generation_context", default=_EMPTY_CONTEXT)


def current_context():
    return _CURRENT.get()


@contextmanager
def bind_context(context):
    """同期rendererの境界だけで使用し、正常・異常終了とも必ず元へ戻す。"""
    token = _CURRENT.set(context)
    try:
        yield context
    finally:
        _CURRENT.reset(token)
