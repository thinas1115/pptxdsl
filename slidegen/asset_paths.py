"""同梱画像資産の配置と互換パス解決。"""
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path, PureWindowsPath


ASSET_DIR = Path(__file__).parent / "assets"
ICON_DIR = ASSET_DIR / "icons"
AWS_ICON_DIR = ICON_DIR / "aws"
FLUENT_ICON_DIR = ICON_DIR / "fluent"
IMAGE_DIR = ASSET_DIR / "images"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
_IMAGE_ROOT = ContextVar("pptxdsl_image_root", default=None)


@contextmanager
def image_assets(directory=None):
    """利用者の素材ルートを生成・検証の呼出し内だけで使用する。"""
    root = Path(directory).resolve() if directory is not None else None
    if root is not None and not root.is_dir():
        raise ValueError("画像素材ディレクトリがありません。--asset-dirを確認してください")
    token = _IMAGE_ROOT.set(root)
    try:
        yield
    finally:
        _IMAGE_ROOT.reset(token)


def resolve_icon_path(icon: str) -> Path:
    """アイコン指定をassets配下の実ファイルパスへ変換する。

    正規表記は ``icons/aws/...`` / ``icons/fluent/...``。既存content.jsonとの
    互換性のため、AWSの裸ファイル名と旧 ``fluent/...`` も受け付ける。
    """
    raw = Path(icon)
    if raw.is_absolute() or not raw.parts:
        raise ValueError("アイコンはslidegen/assets内の相対パスで指定してください")

    if raw.parts[0] == "fluent":
        candidate = FLUENT_ICON_DIR.joinpath(*raw.parts[1:])
    elif raw.parts[0] == "aws":
        candidate = AWS_ICON_DIR.joinpath(*raw.parts[1:])
    elif len(raw.parts) == 1:
        candidate = AWS_ICON_DIR / raw
    else:
        candidate = ASSET_DIR / raw

    resolved = candidate.resolve()
    try:
        resolved.relative_to(ASSET_DIR.resolve())
    except ValueError as exc:
        raise ValueError(
            "アイコンはslidegen/assets内の相対パスで指定してください"
        ) from exc
    return resolved


def resolve_image_path(image: str) -> Path:
    """利用者素材、同梱assetsの順でPNG/JPEGを解決する。"""
    raw = Path(image)
    if (raw.is_absolute() or not raw.parts or PureWindowsPath(image).drive
            or PureWindowsPath(image).root or image.startswith("~")):
        raise ValueError("画像はslidegen/assets内の相対パスで指定してください")
    external = _IMAGE_ROOT.get()
    if external is not None:
        candidate = (external / raw).resolve()
        try:
            candidate.relative_to(external)
        except ValueError as exc:
            raise ValueError("画像は素材ディレクトリ内の相対パスで指定してください") from exc
        if candidate.suffix.lower() not in IMAGE_EXTENSIONS:
            raise ValueError("画像形式はPNGまたはJPEGを指定してください")
        if candidate.is_file():
            return candidate
    candidate = (ASSET_DIR / raw).resolve()
    try:
        candidate.relative_to(ASSET_DIR.resolve())
    except ValueError as exc:
        raise ValueError(
            "画像はslidegen/assets内の相対パスで指定してください"
        ) from exc
    if candidate.suffix.lower() not in IMAGE_EXTENSIONS:
        raise ValueError("画像形式はPNGまたはJPEGを指定してください")
    return candidate
