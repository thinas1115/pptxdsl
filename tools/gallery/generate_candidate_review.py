"""候補rendererの疎・標準・上限入力をまとめた目視確認デッキを生成する。"""

import argparse
from pathlib import Path

from slidegen import generate
from slidegen.candidate_renderers import (
    s_mapping,
    s_paired_comparison,
    s_scope,
    s_sequence,
    s_swimlane,
)
from tests.fixtures.gallery.candidate_review_cases import REVIEW_DECK
from slidegen.generate_from_json import build_presentation


RENDER = {
    "scope_boundary": s_scope,
    "cards": generate.s_cards,
    "paired_comparison": s_paired_comparison,
    "relationship_map": s_mapping,
    "swimlane_flow": s_swimlane,
    "message_sequence": s_sequence,
}


def main(out_path):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        prs = build_presentation(REVIEW_DECK, renderers=RENDER, allow_sample_content=True)
    except ValueError as error:
        raise SystemExit(f"NG: 候補rendererレビュー: {error}") from None
    prs.save(out_path)
    print(f"saved: {out_path} ({len(REVIEW_DECK['slides'])} slides)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out_path", nargs="?", default="out/candidate_review.pptx")
    args = parser.parse_args()
    main(args.out_path)
