"""公開研修のネットワーク図だけを集め、背景・配線・凡例を回帰検証する。"""
import json
from pathlib import Path
from slidegen.generate_from_json import build_presentation
import sys


from slidegen.validate_content import validate


def make_deck():
    root = Path(__file__).resolve().parents[2]
    source = json.loads((root / "examples/training/vlan/content.json").read_text(encoding="utf-8"))
    return {"meta": {"title": "ネットワーク図の回帰検証", "footer": "配線・背景・凡例の確認"},
            "slides": [spec for spec in source["slides"] if spec["type"] == "nw_topology"]}


def main(output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    deck = make_deck()
    errors = validate(deck, allow_sample_content=True)
    if errors:
        raise ValueError("\n".join(errors))
    prs = build_presentation(deck, allow_sample_content=True)
    prs.save(output)
    print(f"ネットワーク回帰デッキ: {output}（{len(deck['slides'])}ページ）")


if __name__ == "__main__":
    main(sys.argv[1])
