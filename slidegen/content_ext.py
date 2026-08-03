"""基本サンプル9枚の後ろに追加する表現力検証スライド定義。"""

from copy import deepcopy

from diagram_specs import AWS_MULTIAZ_EXAMPLE, AWS_SIMPLE_EXAMPLE

EXTRA_SLIDES = [
    {
        "type": "process",
        "kicker": "運用フロー",
        "title": "資料作成は5ステップ。LLMは構成と文言、レイアウトはコードが保証する",
        "steps": [
            {"name": "構成案作成", "desc": "調査データ・実績を渡し、スライド構成と文言をLLMに起案させる。", "actor": "Claude"},
            {"name": "構造化", "desc": "構成をcontent.json(スライド種別+文言)に変換し、内容をレビューする。", "actor": "Claude + 人間"},
            {"name": "自動生成", "desc": "パイプラインがテンプレート準拠のPPTXを決定論的に生成する。", "actor": "コード"},
            {"name": "実機検査", "desc": "PowerPointでPNG化し、溢れ・重なり・禁則を確認する。", "actor": "コード + 人間"},
            {"name": "提出", "desc": "指摘があればcontent.jsonを直して再生成。手動修正はしない。", "actor": "人間"},
        ],
        "emph": [4],
    },
    {
        "type": "diagram",
        "diagram": deepcopy(AWS_SIMPLE_EXAMPLE),
        "kicker": "参考: システム構成(表現力検証)",
        "title": "全社展開時はAWS上にAPI化し、Bedrock経由で構成JSONを生成する",
        "note": "図は簡略化。実装時はIAM・ネットワーク設計を別途詳細化する。",
    },
    {
        "type": "org",
        "kicker": "推進体制",
        "title": "責任者から各チームまで、指揮系統を明確にする",
        "org": {
            "nodes": {
                "project_owner": {"name": "プロジェクト責任者", "sub": "方針・予算",
                                  "style": "primary"},
                "system_owner": {"name": "システム責任者", "sub": "システム方針",
                                 "style": "primary"},
                "pm": {"name": "プロジェクトマネージャー", "sub": "計画・課題・品質管理",
                       "style": "accent"},
                "business": {"name": "業務チーム", "sub": "業務要件・受入"},
                "application": {"name": "開発チーム", "sub": "設計・開発・試験"},
                "platform": {"name": "基盤チーム", "sub": "基盤・ネットワーク"},
                "operation": {"name": "移行・運用チーム", "sub": "移行・運用設計"},
            },
            "levels": [
                ["project_owner", "system_owner"],
                ["pm"],
                ["business", "application", "platform", "operation"],
            ],
            "edges": [
                {"from": "project_owner", "to": "pm"},
                {"from": "system_owner", "to": "pm"},
                {"from": "pm", "to": "business"},
                {"from": "pm", "to": "application"},
                {"from": "pm", "to": "platform"},
                {"from": "pm", "to": "operation"},
            ],
        },
    },
    {
        "type": "diagram",
        "diagram": deepcopy(AWS_MULTIAZ_EXAMPLE),
        "kicker": "参考: 本番構成(高密度検証)",
        "title": "本番はマルチAZ冗長構成。CloudFront配信とRDS同期まで含めて表現できるか検証",
    },
    {
        "type": "roadmap",
        "kicker": "導入ロードマップ",
        "title": "2026年下期はパイロット→展開→定着化の3フェーズで進める",
        "months": ["7月", "8月", "9月", "10月", "11月", "12月"],
        "phases": [
            {"name": "Phase 1  パイロット", "goal": "週次レポートで実測", "bar": "2部門・手直し時間の実測", "start": 0, "end": 2},
            {"name": "Phase 2  横展開", "goal": "対象資料の拡大", "bar": "5部門・テンプレ3種に拡大", "start": 2, "end": 4.5},
            {"name": "Phase 3  定着化", "goal": "標準業務フロー化", "bar": "規程反映・研修・効果報告", "start": 4.5, "end": 6},
        ],
        "milestones": [
            {"at": 2, "row": 0, "label": "効果判定"},
            {"at": 4.5, "row": 1, "label": "展開判定"},
            {"at": 6, "row": 2, "label": "経営報告"},
        ],
    },
    {
        "type": "matrix",
        "kicker": "ポジショニング",
        "title": "「テンプレート準拠 × 無修正提出」の両立は自前パイプラインのみが到達",
        "x_axis": "テンプレート準拠度 →",
        "y_axis": "↑ 無修正提出への近さ",
        "target_label": "目標領域",
        "points": [
            {"name": "NotebookLM", "x": 0.12, "y": 0.30},
            {"name": "Gamma", "x": 0.27, "y": 0.52},
            {"name": "イルシル", "x": 0.5, "y": 0.42},
            {"name": "Copilot", "x": 0.82, "y": 0.34},
            {"name": "Claude PPTX Skill", "x": 0.68, "y": 0.62},
            {"name": "自前パイプライン", "x": 0.87, "y": 0.86, "emph": True},
        ],
        "note": "位置づけは本調査の定性評価。無修正提出=生成後の手直しがどれだけ不要か。",
    },
]
