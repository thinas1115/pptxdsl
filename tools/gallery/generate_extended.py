"""基本デッキに表現力検証スライドを加えた拡張サンプルを生成する。"""
import argparse
import json
from pathlib import Path

from slidegen import generate
from slidegen.generate_from_json import build_presentation
from tests.fixtures.gallery.content import DECK
from tests.fixtures.gallery.content_ext import EXTRA_SLIDES
from slidegen.org_layout import s_org
from slidegen.diagrams2 import s_matrix, s_process, s_program_roadmap
from slidegen.diagram_layout import render_diagram
from slidegen.candidate_renderers import (
    s_mapping, s_paired_comparison, s_scope, s_sequence, s_swimlane,
)


def s_diagram(slide, spec, page):
    """content.json と同じインライン仕様による図解スライド。"""
    area = generate.header(
        slide, spec["kicker"], spec["title"], spec.get("lead"))
    render_diagram(slide, spec["diagram"], note=spec.get("note"),
                   content_area=area if area.shifted else None)


RENDER_EXTENDED = dict(generate.RENDER,
                       org=s_org,
                       process=s_process, program_roadmap=s_program_roadmap,
                       matrix=s_matrix,
                       diagram=s_diagram,
                       scope_boundary=s_scope,
                       paired_comparison=s_paired_comparison, relationship_map=s_mapping,
                       swimlane_flow=s_swimlane, message_sequence=s_sequence)


def main(out_path, cover_footer_config=None):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        slides = DECK["slides"] + EXTRA_SLIDES
        fixture = json.loads(json.dumps({**DECK, "slides": slides}, ensure_ascii=False))
        prs = build_presentation(fixture, cover_footer_config,
                                 renderers=RENDER_EXTENDED, allow_sample_content=True)
    except ValueError as e:
        raise SystemExit(f"NG: 拡張ギャラリー: {e}") from None
    prs.save(out_path)
    print(f"saved: {out_path} ({len(slides)} slides)")


if __name__ == "__main__":
    default_out = Path(__file__).resolve().parents[2] / "out" / "sample_extended.pptx"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out_path", nargs="?", default=default_out)
    parser.add_argument("--cover-footer-config", metavar="PATH",
                        help="表紙・フッター設定JSON")
    args = parser.parse_args()
    main(args.out_path, args.cover_footer_config)
