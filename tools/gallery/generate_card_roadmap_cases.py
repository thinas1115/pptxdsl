"""用途別カード9枚と工程表7枚を、同じ品質ゲートで比較する。"""

from copy import deepcopy
from pathlib import Path
import sys

from slidegen.generate_from_json import build_presentation
from slidegen.validate_content import validate
from tools.gallery.generate_roadmap_cases import make_deck as roadmap_deck


def make_deck():
    topics = (
        ("資料要件", "対象読者と目的、説明範囲を先に決めます。"),
        ("情報源", "文言と数値は利用者が指定した情報源から確認します。"),
        ("情報構造", "独立項目の比較と時系列の説明を使い分けます。"),
        ("描画確認", "画像と実データを使い、内容と配置を確かめます。"),
        ("修正範囲", "検出した問題を直し、関連する出力を再検査します。"),
        ("提出物", "編集できるファイルと検証結果を一緒に渡します。"),
    )
    slides = []
    for count in (2, 3, 4, 6):
        slides.append({
            "type": "cards", "style": "editorial", "kicker": "独立項目の整理",
            "title": f"説明カード{count}項目",
            "cards": [{"heading": heading, "body": body} for heading, body in topics[:count]],
        })
    for count in (2, 3, 6):
        slides.append({
            "type": "cards", "style": "metrics", "kicker": "架空の数値による表示検証",
            "title": f"指標カード{count}項目",
            "cards": [{"heading": f"確認指標{index + 1}", "value": f"{(index + 1) * 12}%",
                       "body": "これは表示検証用の架空の数値です。", "emphasis": index == 0}
                      for index in range(count)],
        })
    editorial_lead = deepcopy(slides[3])
    editorial_lead.update(title="説明付きの項目整理", lead="独立した論点のまとまりを保ち、見出しと本文を読み分けます。")
    slides.append(editorial_lead)
    metrics_lead = deepcopy(slides[6])
    metrics_lead.update(title="説明付きの指標一覧", lead="指標名、値、補足の階層を使い、説明カードと区別します。")
    slides.append(metrics_lead)
    slides.extend(roadmap_deck()["slides"])
    return {"meta": {"title": "カードと工程表の表示検証", "footer": "回帰検証専用・架空の内容"}, "slides": slides}


def main(output):
    data = make_deck()
    errors = validate(data, allow_sample_content=True)
    if errors:
        raise ValueError("\n".join(errors))
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    build_presentation(data, allow_sample_content=True).save(destination)
    print(f"カードと工程表: {destination}（{len(data['slides'])}ページ）")


if __name__ == "__main__":
    main(sys.argv[1])
