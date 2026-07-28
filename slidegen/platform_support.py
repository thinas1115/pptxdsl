"""OS依存のフォント名とPillow実測ファイルを解決する。"""
from dataclasses import dataclass
import os
import platform
from pathlib import Path


@dataclass(frozen=True)
class FontConfig:
    family: str
    paths: dict[str, str]


def _custom_font_config(environ, path_exists):
    family = environ.get("PPTXDSL_FONT_FAMILY")
    regular = environ.get("PPTXDSL_FONT_REGULAR")
    if not family and not regular:
        return None
    if not family or not regular:
        raise RuntimeError(
            "フォントを上書きする場合はPPTXDSL_FONT_FAMILYと"
            "PPTXDSL_FONT_REGULARを両方指定してください。")
    paths = {
        "regular": regular,
        "medium": environ.get("PPTXDSL_FONT_MEDIUM", regular),
        "bold": environ.get("PPTXDSL_FONT_BOLD", regular),
    }
    if not all(path_exists(path) for path in paths.values()):
        raise RuntimeError(
            "環境変数で指定した日本語フォントを読み込めません。"
            "PPTXDSL_FONT_REGULAR/MEDIUM/BOLDを確認してください。")
    return FontConfig(family=family, paths=paths)


def _windows_profile(environ):
    windir = environ.get("WINDIR")
    if not windir:
        return None
    font_dir = Path(windir) / "Fonts"
    return FontConfig(
        family="Yu Gothic",
        paths={
            "regular": str(font_dir / "YuGothR.ttc"),
            "medium": str(font_dir / "YuGothM.ttc"),
            "bold": str(font_dir / "YuGothB.ttc"),
        },
    )


def _macos_profile():
    font_dir = Path("/System/Library/Fonts")
    return FontConfig(
        family="Hiragino Sans",
        paths={
            "regular": str(font_dir / "ヒラギノ角ゴシック W3.ttc"),
            "medium": str(font_dir / "ヒラギノ角ゴシック W3.ttc"),
            "bold": str(font_dir / "ヒラギノ角ゴシック W6.ttc"),
        },
    )


def resolve_font_config(system=None, environ=None, path_exists=None):
    """実行OSに対応するフォント設定を返し、曖昧な代替は行わない。"""
    system = system or platform.system()
    environ = environ or os.environ
    path_exists = path_exists or (lambda path: Path(path).is_file())

    custom = _custom_font_config(environ, path_exists)
    if custom:
        return custom

    profile = {
        "Windows": lambda: _windows_profile(environ),
        "Darwin": _macos_profile,
    }.get(system, lambda: None)()
    if profile and all(path_exists(path) for path in profile.paths.values()):
        return profile

    raise RuntimeError(
        "対応する日本語フォントを検出できません。Windowsでは游ゴシック、"
        "macOSではHiragino Sansを有効にしてください。別フォントを使う場合は"
        "PPTXDSL_FONT_FAMILYとPPTXDSL_FONT_REGULAR/MEDIUM/BOLDを"
        "環境変数で指定してください。")


FONT_CONFIG = resolve_font_config()
POWERPOINT_FONT_NAME = FONT_CONFIG.family
FONT_PATHS = FONT_CONFIG.paths
