"""4組み合わせ、逆順、lead、共通注記・脚注の複合レイアウトを生成する。"""

from copy import deepcopy
from pathlib import Path
import sys

from slidegen.generate_from_json import build_presentation
from slidegen.validate_content import validate
from tests.fixtures.gallery.split_patterns import SPLIT_SLIDES


def make_deck():
    normal = deepcopy(SPLIT_SLIDES)
    reverse = []
    lead = []
    for spec in SPLIT_SLIDES:
        mirrored = deepcopy(spec)
        mirrored["left"], mirrored["right"] = mirrored["right"], mirrored["left"]
        reverse.append(mirrored)
        described = deepcopy(spec)
        described["lead"] = "左右の異なる情報構造を、同じ本文領域で読み合わせます。"
        lead.append(described)
    annotated = deepcopy(SPLIT_SLIDES[1])
    annotated["note"] = "注記はスライド共通で一度だけ表示します。"
    annotated["footnote"] = {"label": "表示検証", "text": "この例はrendererの回帰確認にだけ使用します。"}
    return {"meta": {"title": "複合レイアウトの表示検証", "footer": "架空の構成と検証用の内容"},
            "slides": normal + reverse + lead + [annotated]}


def main(output):
    data = make_deck()
    errors = validate(data, allow_sample_content=True)
    if errors:
        raise ValueError("\n".join(errors))
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    build_presentation(data, allow_sample_content=True).save(destination)
    print(f"複合レイアウト: {destination}（{len(data['slides'])}ページ）")


if __name__ == "__main__":
    main(sys.argv[1])
