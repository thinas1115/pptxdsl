"""基本rendererの回帰サンプルデッキを生成する。"""
import argparse
import json
from pathlib import Path

from slidegen import generate
from tests.fixtures.gallery.content import DECK
from slidegen.generate_from_json import build_presentation


def main(out_path, cover_footer_config=None):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        # 古いPython fixtureのtupleだけをJSON配列へ変換して公開入力検証を通す。
        fixture = json.loads(json.dumps(DECK, ensure_ascii=False))
        prs = build_presentation(fixture, cover_footer_config, renderers=generate.RENDER,
                                 allow_sample_content=True)
    except ValueError as e:
        raise SystemExit(f"NG: 基本ギャラリー: {e}") from None
    prs.save(out_path)
    print(f"saved: {out_path} ({len(DECK['slides'])} slides)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out_path", nargs="?",
                        default=Path(__file__).resolve().parents[2] / "out" / "sample_basic.pptx")
    parser.add_argument("--cover-footer-config", metavar="PATH",
                        help="表紙・フッター設定JSON")
    args = parser.parse_args()
    main(args.out_path, args.cover_footer_config)
