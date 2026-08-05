"""renderer共通の段階的収容ポリシー。

レイアウト計算そのものは各rendererが持ち、このモジュールは候補選択、
テキスト実測、明示停止の契約だけを共有する。
"""
from dataclasses import dataclass
from typing import Iterable, Mapping

from textfit import (fit_font_size, line_height_in, text_width_in,
                     title_lines_are_natural, wrapper_for_role)


FIT_EPS = 0.01


class FitError(ValueError):
    """提出品質を保つ最小値でも領域へ収まらない場合のエラー。"""


@dataclass(frozen=True)
class FitResult:
    stage: str
    values: Mapping[str, float]
    used: float
    available: float


def stepped(start, minimum, step):
    """startからminimumまで、浮動小数誤差を抑えて降順生成する。"""
    value = start
    while value >= minimum - FIT_EPS:
        yield round(value, 4)
        value -= step


def select_fit(renderer, available, candidates: Iterable, *, guidance):
    """標準→圧縮→縮小の順に渡された候補から最初に収まるものを返す。"""
    last = None
    for stage, values, used in candidates:
        last = FitResult(stage, values, used, available)
        if used <= available + FIT_EPS:
            return last
    if last is None:
        raise ValueError("収容候補がありません")
    shortage = max(0.0, last.used - available)
    raise FitError(
        f"{renderer}: 最小設定でも縦方向に収まりません"
        f"(必要{last.used:.2f}in / 利用可能{available:.2f}in / "
        f"不足{shortage:.2f}in)。{guidance}"
    )


def ensure_within(renderer, used, available, *, guidance):
    """固定構図の使用量を検証し、超過時は不足量つきで停止する。"""
    return select_fit(
        renderer, available, [("standard", {}, used)], guidance=guidance)


def fit_text_or_raise(renderer, field, text, box_w, box_h, max_pt, *,
                      min_pt, weight="regular", spacing=1.3, pad_in=0.0,
                      wrapper=None, line_validator=None, role=None):
    """最小フォントでも入らない文字列を黙って描画せず停止する。"""
    role = role or ("natural" if weight in {"medium", "bold"} else "body")
    wrapper = wrapper or wrapper_for_role(role)
    if role == "natural" and line_validator is None:
        line_validator = title_lines_are_natural
    size, lines = fit_font_size(
        text, box_w, box_h, max_pt, min_pt=min_pt, weight=weight,
        spacing=spacing, pad_in=pad_in, wrapper=wrapper,
        line_validator=line_validator,
    )
    usable_w = box_w - pad_in * 2
    widest = max(
        (text_width_in(line, size, weight) for line in lines),
        default=0.0)
    if widest > usable_w + FIT_EPS:
        shortage = widest - usable_w
        raise FitError(
            f"{renderer}.{field}: 最小フォント{min_pt:g}ptでも語を分断せず"
            f"横方向に収まりません(必要{widest:.2f}in / "
            f"幅{usable_w:.2f}in / 不足{shortage:.2f}in)。"
            "文言を短くするか表示領域を見直してください。"
        )
    used = len(lines) * line_height_in(size, spacing) + pad_in * 2
    if used > box_h + FIT_EPS:
        shortage = used - box_h
        raise FitError(
            f"{renderer}.{field}: 最小フォント{min_pt:g}ptでも収まりません"
            f"(必要{used:.2f}in / 高さ{box_h:.2f}in / 不足{shortage:.2f}in)。"
            "文言を短くするか項目数を減らしてください。"
        )
    if line_validator is not None and not line_validator(lines):
        raise FitError(
            f"{renderer}.{field}: 最小フォント{min_pt:g}ptでも自然な位置で"
            "折り返せません。文言を短くしてください。"
        )
    return size, lines
