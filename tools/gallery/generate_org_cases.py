"""名称のみ・役割・長い役割・メンバー・多階層の体制図を実描画で検証する。"""
from copy import deepcopy
from pathlib import Path
from slidegen.generate_from_json import build_presentation
import sys


from slidegen.validate_content import validate
from tests.fixtures.gallery.content_patterns import PATTERN_DECK
from tests.fixtures.gallery.content_lead_patterns import LEAD_PATTERN_DECK


def make_deck():
    existing = deepcopy(next(s for s in PATTERN_DECK["slides"] if s["type"] == "org"))
    names = deepcopy(existing)
    names["title"] = "名称のみの推進体制"
    for node in names["org"]["nodes"].values():
        node.pop("sub", None)
        node.pop("members", None)
    roles = deepcopy(existing)
    roles["title"] = "役割付きの推進体制"
    long = deepcopy(existing)
    long["title"] = "長い役割説明の体制"
    long["org"]["nodes"]["business_team"]["sub"] = "受付手順の整備と問い合わせ対応を担当"
    long["org"]["nodes"]["application_team"]["sub"] = "実装と試験結果の照合を担当"
    members = deepcopy(existing)
    members["title"] = "役割と担当区分の体制"
    members["lead"] = "名称・役割・担当区分を分けて表示します。値は架空の組織による表示検証用です。"
    for node_id in ("business_team", "application_team", "platform_team", "operation_team"):
        members["org"]["nodes"][node_id]["members"] = ["担当A", "担当B"]
    sparse = {"type": "org", "kicker": "少数ノード", "title": "単一の責任主体",
              "org": {"nodes": {"owner": {"name": "試行責任者", "sub": "試行範囲と完了条件を確認"}},
                      "levels": [["owner"]], "edges": []}}
    deep = {"type": "org", "kicker": "多階層", "title": "階層と短い役割の体制",
            "lead": "階層を圧縮する場合も、役割の文字下限を維持します。",
            "org": {"nodes": {f"n{i}": {"name": f"担当階層{i + 1}", "sub": "判断と連絡"} for i in range(5)},
                    "levels": [[f"n{i}"] for i in range(5)],
                    "edges": [{"from": f"n{i}", "to": f"n{i + 1}"} for i in range(4)]}}
    lead = deepcopy(next(s for s in LEAD_PATTERN_DECK["slides"] if s["type"] == "org"))
    return {"meta": {"title": "体制図の役割説明", "footer": "架空の組織による表示検証"},
            "slides": [names, roles, long, members, sparse, deep, lead]}


def main(output):
    deck = make_deck()
    errors = validate(deck, allow_sample_content=True)
    if errors:
        raise ValueError("\n".join(errors))
    prs = build_presentation(deck, allow_sample_content=True)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    prs.save(output)
    print(f"体制図の回帰デッキ: {output}（{len(deck['slides'])}ページ）")


if __name__ == "__main__":
    main(sys.argv[1])
