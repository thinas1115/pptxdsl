"""本文背景・表紙・フッターをまとめた設定JSONの雛形を作る。"""
import argparse
import json
import os
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from slidegen.cover_footer import parse_cover_footer_config


def create_template(path, *, background_color="F7F5EF", background_image=None,
                    cover_background_image=None, footer_text="{footer}"):
    destination = Path(path)
    if destination.exists():
        raise ValueError("設定ファイルは既にあります。既存設定を編集するか別の出力名を指定してください")
    base = destination.parent.resolve()

    def relative(source):
        if source is None:
            return None
        try:
            return Path(os.path.relpath(Path(source).resolve(), base)).as_posix()
        except ValueError:
            raise ValueError("背景画像と設定JSONは同じドライブへ配置してください") from None

    data = {
        "slide": {"background_color": background_color, "background_image": relative(background_image)},
        "cover": {"background_image": relative(cover_background_image),
                  "background_color": "182C43", "title_color": "FFFFFC", "secondary_color": "DFEBE8"},
        "footer": {"text": footer_text, "text_color": "666E70", "page_color": "182C43",
                   "divider_color": "D1CFC8"},
    }
    parse_cover_footer_config(data, base_dir=base)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="新規の設定JSON（既存ファイルは上書きしない）")
    parser.add_argument("--background-color", default="F7F5EF", help="本文背景の6桁HEX色")
    parser.add_argument("--background-image", type=Path, help="文字なしの本文背景PNG/JPEG")
    parser.add_argument("--cover-background-image", type=Path, help="文字なしの表紙背景PNG/JPEG")
    parser.add_argument("--footer-text", default="{footer}", help="フッター文字または{footer}等の参照")
    args = parser.parse_args()
    try:
        path = create_template(args.output, background_color=args.background_color,
                               background_image=args.background_image,
                               cover_background_image=args.cover_background_image,
                               footer_text=args.footer_text)
    except (OSError, ValueError) as error:
        message = str(error) if isinstance(error, ValueError) else "設定を書き込めません。保存先の権限を確認してください"
        raise SystemExit(f"NG: {message}") from None
    print(f"設定を作成しました: {path.name}")


if __name__ == "__main__":
    main()
