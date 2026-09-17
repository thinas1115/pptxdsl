"""体制図の階層DAG配置・入力検証・段階的収容を検証する。"""
from copy import deepcopy

from generate import BODY_BOTTOM, BODY_TOP, ContentArea
from layout_fit import FitError
from org_layout import OrgLayout, fit_org_layout
from validate_content import validate


def _org():
    return {
        "nodes": {
            "owner_a": {"name": "事業責任者", "sub": "投資判断",
                        "style": "primary"},
            "owner_b": {"name": "技術責任者", "sub": "技術判断",
                        "style": "primary"},
            "pm": {"name": "プログラムPM", "sub": "全体統括",
                   "style": "accent"},
            "advisor": {"name": "外部専門家", "sub": "助言",
                        "style": "external"},
            "design": {"name": "業務設計", "sub": "要件・運用",
                       "members": ["企画", "現場"]},
            "development": {"name": "開発", "sub": "実装・試験",
                            "members": ["アプリ", "基盤"]},
            "operation": {"name": "運用", "sub": "監視・改善"},
            "security": {"name": "セキュリティ", "sub": "審査・監査"},
        },
        "levels": [
            ["owner_a", "owner_b"],
            ["pm", "advisor"],
            ["design", "development"],
            ["operation", "security"],
        ],
        "edges": [
            {"from": "owner_a", "to": "pm"},
            {"from": "owner_b", "to": "pm"},
            {"from": "advisor", "to": "pm", "kind": "advice"},
            {"from": "pm", "to": "design"},
            {"from": "pm", "to": "development"},
            {"from": "owner_b", "to": "security"},
            {"from": "design", "to": "operation"},
            {"from": "development", "to": "operation"},
            {"from": "operation", "to": "security",
             "kind": "collaboration"},
        ],
    }


def _deck(org):
    return {
        "meta": {"title": "検証", "footer": "検証", "date": "2026年7月",
                 "author": "検証担当"},
        "slides": [{"type": "org", "kicker": "体制", "title": "推進体制",
                    "org": org}],
    }


def _overlap(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return (max(ax, bx) < min(ax + aw, bx + bw)
            and max(ay, by) < min(ay + ah, by + bh))


def _must_fail(fn, expected):
    try:
        fn()
    except FitError as exc:
        assert expected in str(exc), str(exc)
    else:
        raise AssertionError("過密入力を拒否しませんでした")


def main():
    org = _org()
    assert not validate(_deck(org))

    layout = OrgLayout(org, ContentArea())
    assert layout.fit_stage == "standard"
    assert layout.boxes["owner_a"][1] == layout.boxes["owner_b"][1]
    assert layout.boxes["owner_a"][2] <= 4.30
    assert layout.boxes["owner_b"][2] <= 4.30
    # 同じ連結成分の報告線は、階層間の横幹と子側接続点を共有する。
    assert layout.routes[0][1][1] == layout.routes[1][1][1]
    assert layout.routes[0][-1] == layout.routes[1][-1]
    assert layout.routes[3][0][0] == layout.routes[4][0][0]
    assert layout.routes[3][1][1] == layout.routes[4][1][1]
    # 同一階層で隣接する助言線は、階層間の幹へ迂回しない。
    assert len(layout.routes[2]) == 2
    pm_right = layout.boxes["pm"][0] + layout.boxes["pm"][2]
    assert layout.boxes["advisor"][0] - pm_right >= 0.59
    box_items = list(layout.boxes.items())
    for index, (_, box) in enumerate(box_items):
        for _, other in box_items[index + 1:]:
            assert not _overlap(box, other)
    for points in layout.routes:
        for start, end in zip(points[:-1], points[1:]):
            assert abs(start[0] - end[0]) <= 0.001 \
                or abs(start[1] - end[1]) <= 0.001

    assert fit_org_layout(org, 4.70).stage == "gap"
    assert fit_org_layout(org, 4.00).stage == "element"
    _must_fail(lambda: fit_org_layout(org, 3.00), "最小設定")
    labeled = deepcopy(org)
    labeled["edges"][2]["label"] = "助言"
    assert fit_org_layout(labeled, 4.70).values["gap_y"] >= 0.34

    old = _deck(org)
    old["slides"][0].pop("org")
    old["slides"][0].update(
        top={"name": "責任者", "sub": "判断"},
        pm={"name": "PM", "sub": "統括"}, teams=[],
        external={"name": "外部", "sub": "支援", "label": "助言"})
    assert any("旧org形式" in error
               for error in validate(old))

    invalid = deepcopy(_deck(org))
    invalid["slides"][0]["org"]["levels"][1].append("missing")
    errors = validate(invalid)
    assert any("未定義ノード" in error for error in errors)

    duplicate = deepcopy(_deck(org))
    duplicate["slides"][0]["org"]["levels"][1].append("owner_a")
    errors = validate(duplicate)
    assert any("複数の階層" in error for error in errors)

    reverse = deepcopy(_deck(org))
    reverse["slides"][0]["org"]["edges"].append(
        {"from": "operation", "to": "pm"})
    errors = validate(reverse)
    assert any("上位階層から下位階層" in error for error in errors)

    reporting_label = deepcopy(_deck(org))
    reporting_label["slides"][0]["org"]["edges"][0]["label"] = "承認"
    errors = validate(reporting_label)
    assert any("共有幹" in error for error in errors)

    dense = deepcopy(org)
    for node in dense["nodes"].values():
        node["members"] = ["担当A", "担当B"]
    dense["levels"] = [[f"node{i}"] for i in range(6)]
    dense["nodes"] = {
        f"node{i}": {"name": f"第{i + 1}階層", "sub": "担当",
                     "members": ["担当A", "担当B"]}
        for i in range(6)
    }
    dense["edges"] = [{"from": f"node{i}", "to": f"node{i + 1}"}
                      for i in range(5)]
    _must_fail(
        lambda: OrgLayout(
            dense, ContentArea(BODY_TOP, BODY_BOTTOM, False)),
        "最小設定",
    )

    print("org layout tests passed")


if __name__ == "__main__":
    main()
