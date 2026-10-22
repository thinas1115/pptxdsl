"""グラフ数値・表示・収容の実レンダリング用入力を作る開発ツール。"""
import json
from pathlib import Path
import sys


def make_deck():
    slides = []

    def add(kind, title, values, **options):
        slides.append({"type": "chart", "kicker": "グラフ回帰検証", "title": f"{kind}：{title}",
                       "chart": {"kind": kind, "categories": ["対象A", "対象B", "対象C"],
                                 "series": [["実績", values]], "show_values": True, **options}})

    for kind in ("bar", "column", "line", "stacked_bar", "stacked_column"):
        for title, values in (("通常の数値", [25, 50, 100]), ("負数だけの系列", [-25, -10, -5]),
                              ("正負とゼロの混在", [-25, 0, 50]), ("全項目のゼロ", [0, 0, 0])):
            add(kind, title, values)
    add("bar", "百分率の明示", [0.25, 0.5, 0.75], number_format="0.0%")
    add("column", "倍率なしの百分率接尾辞", [25, 50, 75], number_format='0"%"')
    add("line", "データラベルの非表示", [0.125, 0.25, 0.375], number_format="0.00", show_values=False)
    for count, title in ((4, "標準配置"), (5, "余白の圧縮"), (7, "文字要素の縮小")):
        slides.append({"type": "chart", "kicker": "段階的収容", "title": title,
                       "chart": {"kind": "bar", "categories": [f"項目{i + 1}" for i in range(count)],
                                 "series": [["実績", [10] * count], ["計画", [20] * count]], "show_values": False}})
    slides.append({"type": "chart", "kicker": "文字の収容", "title": "長いカテゴリ名と系列名",
                   "chart": {"kind": "bar", "categories": ["既存サービスの拡張案件", "新規サービスの導入案件"],
                             "series": [[name, [10, 20]] for name in (
                                 "東日本営業本部の法人営業担当における月次実績", "西日本営業本部の公共営業担当における月次実績")],
                             "show_values": False}})
    for kind in ("stacked_bar", "stacked_column"):
        slides.append({"type": "chart", "kicker": "正負別積み上げ", "title": f"{kind}：正負とゼロの内訳",
                       "chart": {"kind": kind, "categories": ["対象"], "show_values": True,
                                 "series": [[name, [value]] for name, value in zip(("系列A", "系列B", "系列C", "系列D"), (30, -25, 0, 10))]}})
    slides.append({"type": "chart", "kicker": "ゼロの内訳", "title": "4系列すべてのゼロ",
                   "chart": {"kind": "stacked_column", "categories": ["対象"], "show_values": True,
                             "series": [[f"系列{i + 1}", [0]] for i in range(4)]}})
    return {"meta": {"title": "グラフの回帰検証", "footer": "数値・表示形式・段階的収容の検証"}, "slides": slides}


if __name__ == "__main__":
    output = Path(sys.argv[1])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(make_deck(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"グラフ回帰入力: {output}")
