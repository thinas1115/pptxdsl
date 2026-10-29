"""実測とPPTX指定で共有する日本語フォント契約。フォント自体は配布しない。"""
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from PIL import ImageFont


SUPPORTED_FAMILIES = ("Yu Gothic", "Noto Sans CJK JP", "Noto Sans JP")
# Pillow wheelのRAQM同梱有無で既定エンジンが変わるため、対応OSで共通のものを使う。
MEASUREMENT_LAYOUT = ImageFont.Layout.BASIC
_ENV_KEYS = tuple(f"PPTXDSL_FONT_{weight}{suffix}"
                  for weight in ("REGULAR", "BOLD", "MEDIUM", "CODE") for suffix in ("", "_INDEX")) + ("WINDIR",)


class FontConfigError(ValueError):
    """ファイルの絶対パスを含まない、利用者向け設定エラー。"""


@dataclass(frozen=True)
class FontFace:
    path: str
    index: int
    family: str
    style: str
    axes: tuple[float, ...] = ()


def _error(message):
    return FontConfigError(message + "。docs/font-contract.mdを確認し、対応するフォントとウェイトを指定してください。")


def _face(path, index, weight, families=SUPPORTED_FAMILIES):
    try:
        font = ImageFont.truetype(str(path), 32, index=index)
        family, style = font.getname()
        if family not in families:
            raise _error("未対応のフォントfamilyです")
        try:
            axes = font.get_variation_axes()
        except OSError:
            axes = []  # 可変フォント以外ではPillowがOSErrorを返す。
        values = ()
        expected = "Bold" if weight == "bold" else "Regular"
        if axes:
            # 対応するNoto可変フォントはWeight軸だけ。別軸の既定値を推測しない。
            if len(axes) != 1 or axes[0]["name"] != b"Weight":
                raise _error("未対応の可変フォント軸です")
            target = 700 if weight == "bold" else 400
            if not axes[0]["minimum"] <= target <= axes[0]["maximum"]:
                raise _error(f"可変フォントに{expected}のウェイトがありません")
            values = (target,)
            style = expected
        elif style != expected:
            raise _error(f"{expected}の指定が別のstyleへ置き換わっています")
        return FontFace(str(Path(path).resolve()), index, family, style, values)
    except FontConfigError:
        raise
    except (OSError, ValueError, TypeError):
        raise _error("フォントの読み込みまたはface indexの解決に失敗しました") from None


def _fontconfig_match(family, style):
    executable = shutil.which("fc-match")
    if not executable:
        return None
    try:
        result = subprocess.run(
            [executable, "-f", "%{file}\t%{index}\n", f"{family}:lang=ja:style={style}"],
            capture_output=True, text=True, errors="replace", timeout=10, check=False)
        if result.returncode:
            return None
        path, index = result.stdout.splitlines()[0].rsplit("\t", 1)
        # 上位16bitはFreeTypeのnamed instance。可変軸は本契約で明示選択する。
        return path, int(index) & 0xffff
    except (OSError, subprocess.TimeoutExpired, IndexError, ValueError):
        return None


def _configured(settings, weight):
    name = f"PPTXDSL_FONT_{weight.upper()}"
    value = settings[name]
    if not value:
        if settings[name + "_INDEX"]:
            raise _error(f"{name}_INDEXだけではフォントを選択できません")
        return None
    path = Path(value).expanduser()
    if not path.is_file():
        raise _error(f"{name}で指定したフォントが見つかりません")
    try:
        index = int(settings[name + "_INDEX"] or "0")
        if index < 0 or index > 0xffff:
            raise ValueError
    except ValueError:
        raise _error(f"{name}_INDEXは0以上65535以下の整数にしてください") from None
    return str(path), index


@lru_cache(maxsize=8)
def _resolve(environment):
    settings = dict(zip(_ENV_KEYS, environment))
    regular = _configured(settings, "regular")
    bold = _configured(settings, "bold")
    medium = _configured(settings, "medium")
    if regular or bold:
        if not regular:
            raise _error("PPTXDSL_FONT_REGULARも指定してください")
        normal = _face(*regular, "regular")
        if not bold:
            if not normal.axes:
                raise _error("静的フォントにはPPTXDSL_FONT_BOLDも必要です")
            bold = regular
        heavy = _face(*bold, "bold")
    elif settings["WINDIR"]:
        base = Path(settings["WINDIR"]) / "Fonts"
        normal = _face(base / "YuGothR.ttc", 0, "regular")
        heavy = _face(base / "YuGothB.ttc", 0, "bold")
    else:
        normal = heavy = None
        for family in ("Noto Sans CJK JP", "Noto Sans JP"):
            matches = [_fontconfig_match(family, style) for style in ("Regular", "Bold")]
            if not all(matches):
                continue
            try:
                candidate = [_face(*match, weight) for match, weight in zip(matches, ("regular", "bold"))]
            except FontConfigError:
                continue
            if all(face.family == family for face in candidate):
                normal, heavy = candidate
                break
        if normal is None:
            raise _error("対応する日本語フォントを検出できません。fontconfigとNoto Sans CJK JPを導入してください")
    if normal.family != heavy.family:
        raise _error("RegularとBoldのfamilyが一致しません")
    if medium:
        try:
            matched = _face(*medium, "regular") == normal
        except FontConfigError:
            matched = False
        if not matched:
            raise _error("Mediumは通常書体の別名です。PPTXDSL_FONT_MEDIUMを外すかRegularと同じfaceを指定してください")
    return normal, heavy


def font_faces():
    """設定変更時は別キーで解決する。同一プロセスで古い書体を使い回さない。"""
    normal, heavy = _resolve(tuple(os.environ.get(key, "") for key in _ENV_KEYS))
    # PPTXのb属性が表現できるのは通常/太字のみ。500を測って400で描かない。
    return {"regular": normal, "medium": normal, "bold": heavy}


@lru_cache(maxsize=8)
def _code_face(environment):
    settings = dict(zip(_ENV_KEYS, environment))
    configured = _configured(settings, "code")
    families = ("Consolas", "Noto Sans Mono CJK JP")
    if configured:
        return _face(*configured, "regular", families)
    if settings["WINDIR"]:
        return _face(Path(settings["WINDIR"]) / "Fonts/consola.ttf", 0, "regular", families)
    match = _fontconfig_match("Noto Sans Mono CJK JP", "Regular")
    if not match:
        raise _error("コード用のNoto Sans Mono CJK JPを検出できません")
    return _face(*match, "regular", families)


def font_face(weight="regular"):
    if weight == "code":
        return _code_face(tuple(os.environ.get(key, "") for key in _ENV_KEYS))
    return font_faces()[weight]


def font_family(weight="regular"):
    return font_face(weight).family


@lru_cache(maxsize=64)
def load_font(face, px):
    try:
        font = ImageFont.truetype(face.path, px, index=face.index, layout_engine=MEASUREMENT_LAYOUT)
        if face.axes:
            font.set_variation_by_axes(list(face.axes))
        return font
    except (OSError, ValueError):
        raise _error("測定フォントを読み込めません") from None


def describe():
    """共有可能な診断情報。端末固有パスは出さず、同一ファイルをhashで確認する。"""
    result = {}
    for weight, face in font_faces().items():
        result[weight] = {
            "family": face.family, "style": face.style, "index": face.index,
            "axes": face.axes, "sha256": hashlib.sha256(Path(face.path).read_bytes()).hexdigest(),
        }
    return result


if __name__ == "__main__":
    try:
        print(json.dumps(describe(), ensure_ascii=False, indent=2))
    except FontConfigError as error:
        raise SystemExit(f"NG: フォント設定: {error}") from None
