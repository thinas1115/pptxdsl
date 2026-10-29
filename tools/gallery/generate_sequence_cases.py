"""シーケンス図の疎・上限・自己処理・フェーズ名を実描画で確認する。"""
from copy import deepcopy
import json
from pathlib import Path
from slidegen.generate_from_json import build_presentation
import sys


from slidegen.validate_content import validate
from tests.fixtures.gallery.candidate_review_cases import REVIEW_DECK


def make_deck():
    slides = deepcopy([spec for spec in REVIEW_DECK["slides"]
                       if spec["type"] == "message_sequence"])
    root = Path(__file__).resolve().parents[2]
    vlan = json.loads((root / "examples/training/vlan/content.json").read_text(encoding="utf-8"))
    slides.extend(deepcopy([spec for spec in vlan["slides"]
                            if spec["type"] == "message_sequence"]))
    lead = deepcopy(slides[2])
    lead["lead"] = "最大件数でも、工程のまとまりと要求・応答・非同期の経路を別々に追います。"
    lead["phases"][0]["label"] = "申請受付と入力内容の確認"
    slides.append(lead)
    return {"meta": {"title": "シーケンス図の回帰検証", "footer": "フェーズ・自己処理・線の役割"},
            "slides": slides}


def main(output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    deck = make_deck()
    errors = validate(deck, allow_sample_content=True)
    if errors:
        raise ValueError("\n".join(errors))
    prs = build_presentation(deck, allow_sample_content=True)
    prs.save(output)
    print(f"シーケンス回帰デッキ: {output}（{len(deck['slides'])}ページ）")


if __name__ == "__main__":
    main(sys.argv[1])
