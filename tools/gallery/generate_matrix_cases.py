"""点とラベルの対応を、近接点・長名・端・疎・通常/leadで検証する。"""
from copy import deepcopy
from pathlib import Path
from slidegen.generate_from_json import build_presentation
import sys


from slidegen.validate_content import validate
from tests.fixtures.gallery.content_patterns import PATTERN_DECK
from tests.fixtures.gallery.content_lead_patterns import LEAD_PATTERN_DECK


def make_deck():
    base = {"type": "matrix", "kicker": "点と名称の配置", "title": "近接点の比較",
            "x_axis": "再利用性 →", "y_axis": "↑ 品質", "target_label": "検証領域",
            "points": [{"name": name, "x": x, "y": y} for name, x, y in (
                ("方式A", .44, .52), ("方式B", .49, .52),
                ("方式C", .54, .58), ("方式D", .49, .66))]}
    long = deepcopy(base)
    long["title"] = "長い名称と点の対応"
    long["lead"] = "点の座標は変えず、文字枠を実測し、横へ避けた名称は短い線で対応を示します。"
    long["points"] = [{"name": name, "x": x, "y": y} for name, x, y in (
        ("受付記録の再利用方式", .22, .75), ("担当者への通知方式", .48, .68),
        ("申請内容の照合方式", .52, .48), ("複数窓口の統合方式", .75, .38))]
    edges = deepcopy(base)
    edges["title"] = "領域端と最大8点"
    edges["points"] = [{"name": f"対象{i + 1}", "x": x, "y": y} for i, (x, y) in enumerate(
        ((.03, .15), (.03, .50), (.03, .85), (.30, .18), (.70, .82), (.97, .15), (.97, .50), (.97, .85)))]
    sparse = deepcopy(base)
    sparse["title"] = "単一点と名称"
    sparse["points"] = [{"name": "単独の確認対象", "x": .40, "y": .55}]
    specs = [base, long, edges, sparse]
    for deck in (PATTERN_DECK, LEAD_PATTERN_DECK):
        specs.append(deepcopy(next(s for s in deck["slides"] if s["type"] == "matrix")))
    return {"meta": {"title": "点ラベルの回帰検証", "footer": "架空の位置づけによる表示検証"}, "slides": specs}


def main(output):
    deck = make_deck()
    errors = validate(deck, allow_sample_content=True)
    if errors:
        raise ValueError("\n".join(errors))
    prs = build_presentation(deck, allow_sample_content=True)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    prs.save(output)
    print(f"点ラベルの回帰デッキ: {output}（{len(deck['slides'])}ページ）")


if __name__ == "__main__":
    main(sys.argv[1])
