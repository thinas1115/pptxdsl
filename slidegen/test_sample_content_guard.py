"""回帰検証用サンプルの文脈が通常入力へ混入しないことを検証する。"""
from copy import deepcopy

from content_lead_patterns import LEAD_PATTERN_DECK
from content_patterns import PATTERN_DECK
from content_stress_patterns import STRESS_PATTERN_DECK
from validate_content import validate


def _deck(title):
    return {
        "meta": {"title": "ネットワーク更改方針"},
        "slides": [{
            "type": "bullets",
            "kicker": "検討結果",
            "title": title,
            "bullets": [["資料要件から作成した結論", None]],
        }],
    }


def main():
    sample_title = "提出品質と再利用性から、整備優先度を決める"
    errors = validate(_deck(sample_title))
    assert any("回帰検証サンプルの文言" in error for error in errors), errors

    normalized_copy = "提出品質と再利用性から\n整備優先度を決める"
    errors = validate(_deck(normalized_copy))
    assert any("回帰検証サンプルの文言" in error for error in errors), errors

    errors = validate(_deck("拠点ネットワーク更改の判断基準を整理する"))
    assert any("名詞句または短い疑問形" in error for error in errors), errors
    assert not validate(_deck("拠点ネットワーク更改の判断基準"))
    assert not validate(_deck("資料作成"))

    for sample_deck in (
        PATTERN_DECK, LEAD_PATTERN_DECK, STRESS_PATTERN_DECK,
    ):
        errors = validate(deepcopy(sample_deck), allow_sample_content=True)
        assert not errors, "\n".join(errors)

    print("OK: 通常入力のサンプル流用を拒否し、回帰ギャラリーだけ許可")


if __name__ == "__main__":
    main()
