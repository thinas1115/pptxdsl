"""生成AIが作りがちな誤入力を公開content契約で拒否できるか検証する。"""
from copy import deepcopy

from validate_content import validate


def _deck(content_slide=None):
    slides = [
        {"type": "title", "title": "資料タイトル", "subtitle": "資料の目的"},
    ]
    if content_slide is not None:
        slides.append(content_slide)
    return {"meta": {"title": "資料タイトル"}, "slides": slides}


def _bullets():
    return {
        "type": "bullets", "kicker": "分類", "title": "要点",
        "bullets": [["本文A", None], ["本文B", None]],
    }


def _assert_error(deck, expected):
    errors = validate(deck)
    assert any(expected in error for error in errors), "\n".join(errors)


def main():
    assert not validate(_deck(_bullets()))

    ignored_bullet_value = _deck(_bullets())
    ignored_bullet_value["slides"][1]["bullets"][0][1] = "描画されない値"
    _assert_error(ignored_bullet_value, "text を持つオブジェクト")

    for style in ("numbered", "bullet", "checklist"):
        styled = _deck({
            "type": "bullets", "style": style,
            "kicker": "分類", "title": "要点",
            "bullets": [
                {"text": "本文A", **({"checked": True}
                                    if style == "checklist" else {})},
                {"text": "本文B"},
            ],
        })
        assert not validate(styled), "\n".join(validate(styled))

    invalid_style = _deck(_bullets())
    invalid_style["slides"][1]["style"] = "tasks"
    _assert_error(invalid_style, "numbered")

    invalid_checked = _deck({
        "type": "bullets", "style": "bullet",
        "kicker": "分類", "title": "要点",
        "bullets": [{"text": "本文A", "checked": True}],
    })
    _assert_error(invalid_checked, "style=checklist")

    invalid_plain_text = _deck({
        "type": "bullets", "style": "bullet",
        "kicker": "分類", "title": "要点",
        "bullets": ["本文A"],
    })
    _assert_error(invalid_plain_text, "text を持つオブジェクト")

    removed_hub = _deck({
        "type": "hub", "kicker": "関係図", "title": "関係者",
        "center": {"title": "中心"},
        "items": [{"title": "周辺"}],
    })
    _assert_error(removed_hub, "type=hub")

    legacy_cards = _deck({
        "type": "cards", "kicker": "比較", "title": "選択肢",
        "cards": [["見出しA", "本文A"], ["見出しB", "本文B"]],
    })
    _assert_error(legacy_cards, "heading / bodyを持つオブジェクト")

    no_cover = _deck(_bullets())
    no_cover["slides"].pop(0)
    assert not validate(no_cover)

    late_cover = _deck(_bullets())
    late_cover["slides"].reverse()
    assert not validate(late_cover)

    duplicate_cover = _deck(_bullets())
    duplicate_cover["slides"].append(deepcopy(duplicate_cover["slides"][0]))
    assert not validate(duplicate_cover)

    unknown_top = _deck(_bullets())
    unknown_top["layout"] = "wide"
    _assert_error(unknown_top, "未対応のトップレベルフィールド")

    organization_meta = _deck(_bullets())
    organization_meta["meta"]["organization"] = "組織名"
    assert not validate(organization_meta)

    unknown_meta = _deck(_bullets())
    unknown_meta["meta"]["company"] = "会社名"
    _assert_error(unknown_meta, "meta.company")

    unknown_slide = _deck(_bullets())
    unknown_slide["slides"][1]["caption"] = "説明"
    _assert_error(unknown_slide, "caption: 未対応")

    unresolved = _deck(_bullets())
    unresolved["slides"][1]["bullets"][0][0] = "TBD"
    _assert_error(unresolved, "未確定マーカー")

    process = {
        "type": "process", "kicker": "工程", "title": "処理手順",
        "steps": [
            {"name": "工程A", "desc": "説明A"},
            {"name": "工程B", "desc": "説明B", "actor": "担当区分"},
            {"name": "工程C", "desc": "説明C"},
        ],
    }
    assert not validate(_deck(process))

    process_attribute = deepcopy(process)
    process_attribute["steps"][1].pop("actor")
    process_attribute["steps"][1]["attribute"] = {
        "label": "OUTPUT", "value": "承認済み申請",
    }
    assert not validate(_deck(process_attribute))

    ambiguous_process = deepcopy(process_attribute)
    ambiguous_process["steps"][1]["actor"] = "担当区分"
    _assert_error(_deck(ambiguous_process), "actor と attribute を同時に指定")

    invalid_attribute = deepcopy(process)
    invalid_attribute["steps"][1].pop("actor")
    invalid_attribute["steps"][1]["attribute"] = {"label": "OUTPUT"}
    _assert_error(_deck(invalid_attribute), "attribute.value")

    legacy_table = _deck({
        "type": "table", "kicker": "表", "title": "一覧",
        "columns": ["列A", "列B"], "rows": [["値A", "値B"]],
        "col_widths": [5, 5],
    })
    _assert_error(legacy_table, "col_widths: 未対応")

    legacy_matrix = _deck({
        "type": "matrix", "kicker": "2軸", "title": "分布",
        "x_axis": "横軸", "y_axis": "縦軸", "target_label": "領域",
        "points": [{"name": "点A", "x": 0.5, "y": 0.5, "lx": 0.1}],
    })
    _assert_error(legacy_matrix, "points[0].lx")

    diagram = {
        "type": "diagram", "kicker": "構成図", "title": "接続関係",
        "diagram": {
            "cols": ["left", "right"], "rows": ["main"],
            "nodes": {
                "a": {"col": "left", "row": "main", "title": "ノードA",
                      "icon": "icons/fluent/desktop.png"},
                "b": {"col": "right", "row": "main", "title": "ノードB",
                      "icon": "icons/fluent/server.png"},
            },
            "containers": [], "channels": {},
            "edges": [{"from": "a", "to": "b", "label": "接続"}],
        },
    }
    assert not validate(_deck(diagram))

    invalid_diagram = _deck(deepcopy(diagram))
    invalid_diagram["slides"][1]["diagram"]["nodes"]["a"]["sub"] = 123
    invalid_diagram["slides"][1]["diagram"]["edges"][0].update(
        label_w=1.0, dash="solid", both="yes")
    errors = validate(invalid_diagram)
    for expected in ("nodes.a.sub", "label_w: 未対応", ".dash", ".both"):
        assert any(expected in error for error in errors), "\n".join(errors)

    print("OK: AI content contract accepts optional covers and rejects unsupported input")


if __name__ == "__main__":
    main()
