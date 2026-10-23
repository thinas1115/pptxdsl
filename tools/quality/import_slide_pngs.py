"""PowerPointの手動PNG出力を検証し、原本を残してslide_連番へコピーする。"""
import argparse
from pathlib import Path
import re
import shutil
import tempfile
from zipfile import BadZipFile

from lxml.etree import LxmlError
from PIL import Image
from pptx import Presentation
from pptx.exc import PackageNotFoundError


def import_pngs(pptx: Path, source: Path, output: Path) -> int:
    if output.exists():
        raise ValueError("出力先が既に存在します。未使用のディレクトリを指定してください")
    count = len(Presentation(pptx).slides)
    if count < 1 or not source.is_dir():
        raise ValueError("PPTXのページとPNG入力ディレクトリを確認してください")
    pages = {}
    for path in source.iterdir():
        if path.suffix.lower() != ".png":
            continue
        match = re.search(r"([0-9]+)$", path.stem)
        if not match or path.is_symlink() or not path.is_file():
            raise ValueError("PNG名の末尾にスライド番号が必要です。専用の出力フォルダを指定してください")
        number = int(match[1])
        if number in pages:
            raise ValueError("PNGのスライド番号が重複しています")
        with Image.open(path) as image:
            if image.format != "PNG" or image.size != (1600, 900):
                raise ValueError("全ページをPNG・1600×900pxで書き出してください")
            image.verify()
        pages[number] = path
    if set(pages) != set(range(1, count + 1)):
        raise ValueError("PNGの枚数・連番がPPTXと一致しません。全スライドを書き出してください")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pptxdsl-png-", dir=output.parent) as temporary:
        staging = Path(temporary) / "pages"
        staging.mkdir()
        for number, path in sorted(pages.items()):
            shutil.copyfile(path, staging / f"slide_{number:02d}.png")
        if output.exists():
            raise ValueError("出力先が既に存在します。未使用のディレクトリを指定してください")
        staging.rename(output)
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pptx", type=Path)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        count = import_pngs(args.pptx, args.source, args.output)
    except (OSError, KeyError, BadZipFile, PackageNotFoundError, LxmlError, SyntaxError):
        raise SystemExit("NG: PPTX・PNGの読込または保存に失敗しました。形式と権限を確認してください") from None
    except ValueError as error:
        raise SystemExit(f"NG: {error}") from None
    print(f"PNGの枚数・連番・寸法を確認し、{count}ページをコピーしました。目視QAは別途必要です。")


if __name__ == "__main__":
    main()
