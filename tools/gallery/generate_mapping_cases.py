"""一対多・多対多・長い項目名の対応線を検証する。"""
from copy import deepcopy
from pathlib import Path
from slidegen.generate_from_json import build_presentation
import sys


from slidegen.validate_content import validate
from tests.fixtures.gallery.content_patterns import PATTERN_DECK
from tests.fixtures.gallery.content_lead_patterns import LEAD_PATTERN_DECK


def make_deck():
    base = {"type": "relationship_map", "kicker": "対応線の検証", "title": "多対多の対応関係",
            "left_label": "確認事項", "right_label": "対応方法",
            "left_items": [{"id": f"l{i}", "text": f"確認事項{i + 1}"} for i in range(3)],
            "right_items": [{"id": f"r{i}", "text": f"対応方法{i + 1}"} for i in range(3)],
            "links": [{"from": f"l{i}", "to": f"r{j}", "emphasis": i == j}
                      for i in range(3) for j in range(3)]}
    fan_in = deepcopy(base)
    fan_in["title"] = "6項目から同じ項目への対応"
    fan_in["left_items"] = [{"id": f"l{i}", "text": f"確認事項{i + 1}"} for i in range(6)]
    fan_in["links"] = [{"from": f"l{i}", "to": "r1", "emphasis": i == 2} for i in range(6)]
    fan_out = deepcopy(fan_in)
    fan_out["title"] = "同じ項目から6項目への対応"
    fan_out["left_label"], fan_out["right_label"] = "対応方法", "確認事項"
    fan_out["left_items"], fan_out["right_items"] = fan_in["right_items"], fan_in["left_items"]
    fan_out["links"] = [{"from": link["to"], "to": link["from"], "emphasis": link["emphasis"]}
                        for link in fan_in["links"]]
    long = deepcopy(base)
    long["title"] = "長い確認事項と対応方法"
    long["lead"] = "線の交点と接続点を区別し、確認事項から対応方法まで1本ずつ追って確認します。"
    for index, item in enumerate(long["left_items"]):
        item["text"] = f"問い合わせ受付から記録の保存までの確認事項{index + 1}"
    for index, item in enumerate(long["right_items"]):
        item["text"] = f"担当区分と確認結果を共有するための対応方法{index + 1}"
    limit = deepcopy(fan_in)
    limit["title"] = "10本の関係線"
    limit["lead"] = "上限の関係線でも終端を分け、入力の対応と強調だけを保ちます。"
    limit["links"] += [{"from": f"l{i}", "to": "r2"} for i in range(4)]
    specs = [base, fan_in, fan_out, long, limit]
    for deck in (PATTERN_DECK, LEAD_PATTERN_DECK):
        specs.append(deepcopy(next(s for s in deck["slides"] if s["type"] == "relationship_map")))
    return {"meta": {"title": "対応関係の端点", "footer": "架空の確認事項による表示検証"}, "slides": specs}


def main(output):
    deck = make_deck()
    errors = validate(deck, allow_sample_content=True)
    if errors:
        raise ValueError("\n".join(errors))
    prs = build_presentation(deck, allow_sample_content=True)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    prs.save(output)
    print(f"対応関係の回帰デッキ: {output}（{len(deck['slides'])}ページ）")


if __name__ == "__main__":
    main(sys.argv[1])
