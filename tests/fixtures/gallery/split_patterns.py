"""複合レイアウトの架空の表示例。新規資料の内容へ流用しない。"""


SPLIT_SLIDES = [
    {
        "type": "split", "kicker": "構成と判断材料", "title": "受付と記録の構成",
        "left": {"type": "diagram", "diagram": {
            "cols": ["入力", "記録"], "rows": ["受付", "保存"],
            "nodes": {
                "entry": {"col": "入力", "row": "受付", "title": "受付", "icon": "icons/fluent/app.png"},
                "process": {"col": "記録", "row": "受付", "title": "確認処理", "icon": "icons/fluent/server.png"},
                "store": {"col": "記録", "row": "保存", "title": "保存先", "icon": "icons/fluent/database.png"},
            },
            "containers": [{"name": "record", "label": "記録の範囲", "members": ["process", "store"]}],
            "edges": [{"from": "entry", "to": "process", "label": "受付内容"},
                      {"from": "process", "to": "store", "label": "記録"}],
        }},
        "right": {"type": "cards", "style": "editorial", "cards": [
            {"heading": "入力の範囲", "body": "受付内容と確認項目を分け、記録対象を明確にします。"},
            {"heading": "保存の条件", "body": "確認済みの内容だけを保存し、後から照合できるようにします。"},
        ]},
    },
    {
        "type": "split", "kicker": "画面と説明", "title": "公開リポジトリの確認点",
        "left": {"type": "image", "image": "images/pptxdsl-repository.png", "fit": "contain",
                 "alt": "公開されているpptxdslリポジトリの画面"},
        "right": {"type": "bullets", "style": "bullet", "bullets": [
            {"text": "セットアップと基本操作はREADMEから確認します。"},
            {"text": "入力構造とtypeの選択は、それぞれのガイドを参照します。"},
            {"text": "生成後は機械検査と実画像の目視を行います。"},
        ]},
    },
    {
        "type": "split", "kicker": "架空の数値による表示検証", "title": "工程別の確認項目",
        "left": {"type": "chart", "chart": {"kind": "column", "categories": ["準備", "確認", "提出"],
                 "series": [["検証用の架空値", [12, 20, 16]]], "show_values": True}},
        "right": {"type": "table", "columns": ["工程", "確認する内容"], "rows": [
            ["準備", "要件と情報源"], ["確認", "内容と配置"], ["提出", "編集用ファイル"],
        ]},
    },
    {
        "type": "split", "kicker": "要点と比較", "title": "確認手順と提出物",
        "left": {"type": "bullets", "style": "numbered", "bullets": [
            {"text": "資料の目的と情報源を確認します。"},
            {"text": "内容の確認後に配置と描画を検査します。"},
            {"text": "確認した範囲と未確認事項を記録します。"},
        ]},
        "right": {"type": "cards", "style": "editorial", "cards": [
            {"heading": "編集用", "body": "PPTXと内容データを渡し、後から修正できるようにします。"},
            {"heading": "確認用", "body": "PNGと検証結果を添え、実際の見え方を確認できます。"},
        ]},
    },
]
