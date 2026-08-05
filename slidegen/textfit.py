"""日本語テキストの実測折り返し・自動フィットエンジン。

PowerPointに置く前にPillowで游ゴシックの実寸を測り、
「テキストボックスから溢れない」ことを生成時点で保証する。
"""
import os
import re
from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

if "WINDIR" not in os.environ:
    raise RuntimeError("游ゴシックの検出にはWindows環境が必要です")
FONT_DIR = Path(os.environ["WINDIR"]) / "Fonts"
FONT_PATHS = {
    "regular": str(FONT_DIR / "YuGothR.ttc"),
    "medium": str(FONT_DIR / "YuGothM.ttc"),
    "bold": str(FONT_DIR / "YuGothB.ttc"),
}

# pt -> px (96dpi)。PowerPoint実測はPillow計測より僅かに広く出ることが
# あるため安全係数を掛ける。
PT_TO_PX = 96 / 72
SAFETY = 1.08


@lru_cache(maxsize=64)
def _font(weight: str, size_pt: float) -> ImageFont.FreeTypeFont:
    px = max(4, round(size_pt * PT_TO_PX))
    return ImageFont.truetype(FONT_PATHS[weight], px, index=0)


def text_width_in(text: str, size_pt: float, weight: str = "regular") -> float:
    """文字列1行の幅をインチで返す(安全係数込み)。"""
    if not text:
        return 0.0
    f = _font(weight, size_pt)
    px = f.getlength(text)
    return px * SAFETY / 96.0


_BREAK_BEFORE = "、。，．）」』】”？！・：；"  # 行頭に来てはいけない文字
_BREAK_AFTER = "（「『【“"  # 行末に来てはいけない文字
_TEXT_TOKEN = re.compile(
    r"[0-9０-９]+(?:[.,，．〜～~\-–—/][0-9０-９]+)*"
    r"(?:秒|分|時間|日|週|か月|ヶ月|月|年|件|個|枚|回|人|台|社|選|円|万円|億円|%|％)?"
    r"|[A-Za-z0-9]+(?:[-./+_:][A-Za-z0-9]+)*"
    r"|[ァ-ヶー]+|[ｦ-ﾟ]+|[一-龯々〆ヵヶ]+|[ぁ-ゖ]+|\s+|.",
    re.DOTALL)
_LEADING_PARTICLES = "はがをにでへもの"


def _is_katakana(ch: str) -> bool:
    return "ァ" <= ch <= "ヶ" or ch == "ー" or "ｦ" <= ch <= "ﾟ"


def _is_japanese(ch: str) -> bool:
    return (_is_katakana(ch) or "ぁ" <= ch <= "ゖ"
            or "一" <= ch <= "龯" or ch == "々")


def title_lines_are_natural(lines: list[str]) -> bool:
    """前行の日本語から助詞だけが次行頭へ孤立していないか判定する。"""
    for previous, current in zip(lines, lines[1:]):
        if (previous and current and _is_japanese(previous[-1])
                and current[0] in _LEADING_PARTICLES):
            return False
    return True


def _wrap_role(text: str, width_in: float, size_pt: float, weight: str,
               *, min_last_ratio: float) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        wrapped = _wrap_one(para, width_in, size_pt, weight)
        if min_last_ratio > 0:
            wrapped = balance_last_line(
                wrapped, width_in, size_pt, weight,
                min_ratio=min_last_ratio)
        lines.extend(wrapped)
    return lines or [""]


def wrap_natural(text: str, width_in: float, size_pt: float,
                 weight: str = "regular") -> list[str]:
    """タイトル・見出し向け。短い最終行と助詞孤立を強く抑える。"""
    paragraphs = text.split("\n")
    # 見出しでは入力側の改行も絶対位置とはせず、短い末尾段落だけは
    # 直前段落へ戻して全体を再組版する。本文の段落区切りはwrap_bodyで維持する。
    if (len(paragraphs) >= 2
            and text_width_in(paragraphs[-1], size_pt, weight)
            < width_in * 0.28):
        paragraphs[-2:] = [paragraphs[-2] + paragraphs[-1]]
    lines: list[str] = []
    for paragraph in paragraphs:
        lines.extend(_wrap_one(paragraph, width_in, size_pt, weight))
    return balance_last_line(
        lines, width_in, size_pt, weight, min_ratio=0.28)


def wrap_body(text: str, width_in: float, size_pt: float,
              weight: str = "regular") -> list[str]:
    """lead・本文向け。読みやすさを保ちつつ過剰な行移動を避ける。"""
    return _wrap_role(
        text, width_in, size_pt, weight, min_last_ratio=0.18)


def wrap_compact(text: str, width_in: float, size_pt: float,
                 weight: str = "regular") -> list[str]:
    """表セル・線ラベル向け。最終行補正を行わず、領域利用を優先する。"""
    return _wrap_role(
        text, width_in, size_pt, weight, min_last_ratio=0.0)


def wrapper_for_role(role: str):
    """文章の役割に対応する折り返し関数を返す。"""
    wrappers = {
        "natural": wrap_natural,
        "body": wrap_body,
        "compact": wrap_compact,
    }
    try:
        return wrappers[role]
    except KeyError as error:
        raise ValueError(f"未対応の文章役割です: {role}") from error


def wrap_text(text: str, width_in: float, size_pt: float,
              weight: str = "regular") -> list[str]:
    """後方互換の本文折り返し。新規コードは文章役割を明示する。"""
    return wrap_body(text, width_in, size_pt, weight)


def balance_last_line(lines: list[str], width_in: float, size_pt: float,
                      weight: str = "regular",
                      min_ratio: float = 0.28) -> list[str]:
    """極端に短い最終行へ直前行の末尾を移し、タイトルの孤立語を防ぐ。"""
    if len(lines) < 2 or not lines[-1].strip():
        return list(lines)
    if text_width_in(lines[-1], size_pt, weight) >= width_in * min_ratio:
        return list(lines)

    result = list(lines)
    joined = result[-2] + result[-1]
    original_split = len(result[-2])
    token_boundaries = set()
    position = 0
    for token in _natural_tokens(joined):
        position += len(token)
        token_boundaries.add(position)
    for split in range(original_split - 1, 0, -1):
        if split not in token_boundaries:
            continue
        left = joined[:split].rstrip()
        right = joined[split:].lstrip()
        if not left or not right:
            continue
        # 英単語・識別子・連続カタカナの途中では分割しない。
        before = joined[split - 1]
        after = joined[split]
        if before.isascii() and after.isascii() \
                and before.isalnum() and after.isalnum():
            continue
        if _is_katakana(before) and _is_katakana(after):
            continue
        if right[0] in _BREAK_BEFORE or left[-1] in _BREAK_AFTER:
            continue
        right_w = text_width_in(right, size_pt, weight)
        if (right_w >= width_in * min_ratio
                and right_w <= width_in
                and text_width_in(left, size_pt, weight) <= width_in):
            result[-2:] = [left, right]
            return result
    return result


def wrap_title(text: str, width_in: float, size_pt: float,
               weight: str = "regular") -> list[str]:
    """英単語・カタカナ語を分断せず、短い最終行も補正する。"""
    return wrap_natural(text, width_in, size_pt, weight)


def _natural_tokens(para: str) -> list[str]:
    """日本語の意味単位を壊しにくい折り返しトークンを作る。"""
    result: list[str] = []
    for token in _TEXT_TOKEN.findall(para):
        if not token:
            continue
        # 助詞・活用語尾は直前語へ付け、次行頭へ孤立させない。
        if (result and all("ぁ" <= ch <= "ゖ" for ch in token)
                and not result[-1].isspace()):
            result[-1] += token
            continue
        # 句読点や閉じ括弧も直前語と同じトークンにする。
        if result and token[0] in _BREAK_BEFORE and not result[-1].isspace():
            result[-1] += token
            continue
        # 開き括弧は直後の語と離さない。
        if result and result[-1] and result[-1][-1] in _BREAK_AFTER:
            result[-1] += token
            continue
        result.append(token)
    return result


def _is_protected_token(token: str) -> bool:
    """英単語・識別子・数値単位・連続カタカナを語中分割から守る。"""
    core = token.strip().strip(_BREAK_BEFORE + _BREAK_AFTER)
    if not core:
        return False
    if any(ch.isascii() and ch.isalpha() for ch in core):
        return True
    if all(_is_katakana(ch) for ch in core):
        return True
    return core[0].isdigit() or "０" <= core[0] <= "９"


def _split_if_allowed(token: str, width_in: float, size_pt: float,
                      weight: str) -> list[str]:
    if _is_protected_token(token):
        return [token]
    return _wrap_chars(token, width_in, size_pt, weight)


def _wrap_tokens(para: str, width_in: float, size_pt: float,
                 weight: str) -> list[str]:
    if not para:
        return [""]
    lines = []
    cur = ""
    for token in _natural_tokens(para):
        candidate = cur + token
        if text_width_in(candidate, size_pt, weight) <= width_in or not cur:
            cur = candidate
            if text_width_in(cur, size_pt, weight) <= width_in:
                continue
            split_token = _split_if_allowed(
                cur, width_in, size_pt, weight)
            lines.extend(split_token[:-1])
            cur = split_token[-1]
            continue
        if token.isspace():
            lines.append(cur.rstrip())
            cur = ""
            continue
        if len(token) == 1 and token in _BREAK_BEFORE:
            cur += token
            lines.append(cur.rstrip())
            cur = ""
            continue
        if cur and cur[-1] in _BREAK_AFTER:
            opener = cur[-1]
            lines.append(cur[:-1].rstrip())
            cur = opener + token.lstrip()
        else:
            lines.append(cur.rstrip())
            cur = token.lstrip()
        if text_width_in(cur, size_pt, weight) > width_in:
            split_token = _split_if_allowed(
                cur, width_in, size_pt, weight)
            lines.extend(split_token[:-1])
            cur = split_token[-1]
    if cur:
        lines.append(cur.rstrip())
    return [line for line in lines if line != ""] or [""]


def _wrap_one(para: str, width_in: float, size_pt: float, weight: str) -> list[str]:
    return _wrap_tokens(para, width_in, size_pt, weight)


def _wrap_chars(para: str, width_in: float, size_pt: float,
                weight: str) -> list[str]:
    """単一トークンが領域より長い場合だけ文字単位へフォールバックする。"""
    if not para:
        return [""]
    lines = []
    cur = ""
    for ch in para:
        if text_width_in(cur + ch, size_pt, weight) <= width_in or not cur:
            cur += ch
            continue
        # 禁則: 句読点等は前の行に食い込ませる
        if ch in _BREAK_BEFORE:
            cur += ch
            lines.append(cur)
            cur = ""
        elif cur and cur[-1] in _BREAK_AFTER:
            lines.append(cur[:-1])
            cur = cur[-1] + ch
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def line_height_in(size_pt: float, spacing: float = 1.3) -> float:
    """1行の高さ(インチ)。PowerPointの行送り(倍率spacing)相当。"""
    return size_pt * spacing / 72.0


def fit_font_size(text: str, box_w_in: float, box_h_in: float,
                  max_pt: float, min_pt: float = 10.0,
                  weight: str = "regular", spacing: float = 1.3,
                  pad_in: float = 0.0, wrapper=None,
                  line_validator=None) -> tuple[float, list[str]]:
    """ボックス(幅x高さ)に収まる最大フォントサイズと折り返し結果を返す。

    min_ptまで縮めても入らない場合はmin_ptの結果を返す(呼び出し側で
    行数超過を検知してコンテンツを削る判断をする)。
    """
    w = box_w_in - pad_in * 2
    h = box_h_in - pad_in * 2
    wrapper = wrapper or wrap_text
    size = max_pt
    while size >= min_pt:
        lines = wrapper(text, w, size, weight)
        if (all(text_width_in(line, size, weight) <= w + 0.01
                for line in lines)
                and len(lines) * line_height_in(size, spacing) <= h
                and (line_validator is None or line_validator(lines))):
            return size, lines
        size -= 0.5
    return min_pt, wrapper(text, w, min_pt, weight)


def fits(text: str, box_w_in: float, box_h_in: float, size_pt: float,
         weight: str = "regular", spacing: float = 1.3,
         pad_in: float = 0.0) -> bool:
    """指定サイズで収まるかの判定。"""
    w = box_w_in - pad_in * 2
    lines = wrap_text(text, w, size_pt, weight)
    return (
        all(text_width_in(line, size_pt, weight) <= w + 0.01
            for line in lines)
        and len(lines) * line_height_in(size_pt, spacing)
        <= box_h_in - pad_in * 2
    )
