"""全非表紙パターンでlead指定を確認する検証デッキ。"""

import json

from content_patterns import PATTERN_DECK


LEADS = {
    "bullets": "結論を先に示し、その根拠を読み順に沿って確認します。",
    "cards": "4つの観点を比較し、意思決定に必要な差分を整理します。",
    "two_column": "導入前後を同じ観点で比較すると、改善の効果が明確になります。",
    "table": "候補ごとの適用範囲と制約を、同じ粒度で比較します。",
    "chart": "作成時間はすべての資料種別で短縮し、定型資料ほど効果が高くなりました。",
    "image": "画像を主役に据え、説明文は判断に必要な一文だけを添えます。",
    "process": "入力から提出までの責任分担を明確にし、品質確認を工程へ組み込みます。",
    "program_roadmap": "複数テーマの並行作業と実施時期を、同じ時間軸で確認します。",
    "matrix": "提出品質と再利用性の両面から、優先して整備する領域を判断します。",
    "org": "意思決定者と実行チームを分け、責任の所在を明確にします。",
    "diagram": "利用者からアプリケーション、データ保管までの主要な流れを示します。\n監視とバックアップを含む運用経路も同じ図で確認できます。",
    "scope_boundary": "実施する範囲と対象外を分け、合意が必要な前提条件を確認します。",
    "decision_summary": "背景から提案までの判断過程を短く整理し、結論へつなげます。",
    "paired_comparison": "左右を同じ評価軸で対応させ、方式ごとの優位点を判断します。",
    "relationship_map": "課題と施策の対応関係を示し、未対応や重複対応を確認します。",
    "swimlane_flow": "担当レーンと工程フェーズを重ね、引き継ぎ箇所を確認します。",
    "message_sequence": "送受信者とメッセージ順を分け、作業時系列を確認します。",
    "nw_concept": "用語の定義、判断に必要な要点、誤解しやすい境界を一続きで確認します。",
    "nw_topology": "物理機器と論理セグメントを重ね、リンクが運ぶ通信範囲を確認します。",
    "nw_protocol_flow": "同じフレームまたはパケットの情報が、処理段階ごとにどう変わるかを追跡します。",
    "nw_frame_anatomy": "フレーム内の各フィールドを分解し、追加情報の位置と役割を確認します。",
    "nw_config_lab": "設定例と確認観点を並べ、投入後に見るべき状態まで整理します。",
    "nw_knowledge_check": "設問と選択肢を同じ構造で示し、理解した理由まで確認します。",
}
SHORT_DIAGRAM_LEAD = "主要コンポーネントの役割とデータの流れを示します。"
METRICS_LEAD = "3つのKPIを比較し、改善効果と残る確認作業を整理します。"


def _slides():
    slides = []
    diagram_count = 0
    for source in PATTERN_DECK["slides"]:
        type_ = source["type"]
        if type_ == "title":
            continue
        spec = json.loads(json.dumps(source, ensure_ascii=False))
        if type_ == "diagram":
            spec["lead"] = LEADS[type_] if diagram_count == 0 else SHORT_DIAGRAM_LEAD
            diagram_count += 1
        elif type_ == "cards" and spec.get("style") == "metrics":
            spec["lead"] = METRICS_LEAD
        else:
            spec["lead"] = LEADS[type_]
        slides.append(spec)
    return slides


LEAD_PATTERN_DECK = {
    "meta": {
        "title": "lead対応検証ギャラリー",
        "footer": "lead対応検証ギャラリー",
        "date": "2026年7月",
        "author": "業務改善検討チーム",
    },
    "slides": _slides(),
}
