"""Subnet名・CIDRの視認性を疎・上限・通常・lead付きで検証する。"""
from copy import deepcopy
from pathlib import Path
from slidegen.generate_from_json import build_presentation
import sys


from slidegen.validate_content import validate
from tests.fixtures.gallery.content_patterns import PATTERN_DECK
from tests.fixtures.gallery.content_lead_patterns import LEAD_PATTERN_DECK


def make_deck():
    sparse = {
        "type": "aws_vpc_layout", "kicker": "疎な構成", "title": "単一Subnetの構成",
        "vpc": {"label": "検証用VPC", "cidr": "10.0.0.0/16"},
        "azs": [{"id": "az-a", "label": "AZ-a", "subnets": [
            {"id": "sub-a", "label": "private subnet", "cidr": "10.0.1.0/24",
             "resources": [{"id": "node-a", "label": "処理関数", "icon": "icons/aws/lambda.png"}]}
        ]}]
    }
    dense = deepcopy(sparse)
    dense.update(title="3AZと9Subnetの構成", kicker="件数上限",
                 lead="Subnet名とCIDRは、境界線から分離した文字色で確認します。")
    dense["azs"] = [
        {"id": f"az-{az}", "label": f"AZ-{az + 1}", "subnets": [
            {"id": f"sub-{az}-{sub}", "label": f"private subnet {sub + 1}",
             "cidr": f"10.{az}.{sub}.0/24", "resources": [
                 {"id": f"node-{az}-{sub}", "label": f"処理関数 {az + 1}-{sub + 1}",
                  "icon": "icons/aws/lambda.png"}]}
            for sub in range(3)]}
        for az in range(3)]
    examples = [deepcopy(next(s for s in deck["slides"] if s["type"] == "aws_vpc_layout"))
                for deck in (PATTERN_DECK, LEAD_PATTERN_DECK)]
    return {"meta": {"title": "Subnet文字の回帰検証", "footer": "架空の構成による表示検証"},
            "slides": [sparse, dense, *examples]}


def main(output):
    deck = make_deck()
    errors = validate(deck, allow_sample_content=True)
    if errors:
        raise ValueError("\n".join(errors))
    prs = build_presentation(deck, allow_sample_content=True)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    prs.save(output)
    print(f"Subnet回帰デッキ: {output}（{len(deck['slides'])}ページ）")


if __name__ == "__main__":
    main(sys.argv[1])
