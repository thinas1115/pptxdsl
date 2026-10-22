"""全非表紙パターンのlead対応検証ギャラリーを生成する。"""
import argparse
from pathlib import Path

from tests.fixtures.gallery.content_lead_patterns import LEAD_PATTERN_DECK
from slidegen.generate_from_json import RENDER, build_presentation


def main(out_path, cover_footer_config=None):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        prs = build_presentation(LEAD_PATTERN_DECK, cover_footer_config,
                                 renderers=RENDER, allow_sample_content=True)
    except ValueError as e:
        raise SystemExit(f"NG: leadギャラリー: {e}") from None
    prs.save(out_path)
    print(f"saved: {out_path} ({len(LEAD_PATTERN_DECK['slides'])} slides)")


if __name__ == "__main__":
    default_out = Path(__file__).resolve().parents[2] / "out" / "lead_gallery.pptx"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out_path", nargs="?", default=default_out)
    parser.add_argument("--cover-footer-config", metavar="PATH",
                        help="表紙・フッター設定JSON")
    args = parser.parse_args()
    main(args.out_path, args.cover_footer_config)
