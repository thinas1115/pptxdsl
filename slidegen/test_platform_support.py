"""OS別フォント解決を実ファイルへ依存せず検証する。"""
from platform_support import resolve_font_config


def _all_exist(_path):
    return True


windows = resolve_font_config(
    system="Windows", environ={"WINDIR": "virtual-windows"},
    path_exists=_all_exist)
assert windows.family == "Yu Gothic"
assert windows.paths["regular"].endswith("YuGothR.ttc")
assert windows.paths["bold"].endswith("YuGothB.ttc")

macos = resolve_font_config(
    system="Darwin", environ={}, path_exists=_all_exist)
assert macos.family == "Hiragino Sans"
assert macos.paths["regular"].endswith("W3.ttc")
assert macos.paths["bold"].endswith("W6.ttc")

custom = resolve_font_config(
    system="Darwin",
    environ={
        "PPTXDSL_FONT_FAMILY": "Example Sans",
        "PPTXDSL_FONT_REGULAR": "fonts/example-regular.ttf",
        "PPTXDSL_FONT_BOLD": "fonts/example-bold.ttf",
    },
    path_exists=_all_exist)
assert custom.family == "Example Sans"
assert custom.paths["medium"] == "fonts/example-regular.ttf"

try:
    resolve_font_config(
        system="Linux", environ={}, path_exists=lambda _path: False)
except RuntimeError as error:
    assert "対応する日本語フォントを検出できません" in str(error)
    assert "PPTXDSL_FONT_FAMILY" in str(error)
else:
    raise AssertionError("未対応OSでフォント解決エラーになりませんでした")

print("platform support tests passed")
