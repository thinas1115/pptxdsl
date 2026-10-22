"""構成図の入力契約。節別に型・参照を検証し、配置可能性はエンジンへ渡す。"""

from typing import Any, Mapping, Protocol, TypeGuard

from slidegen.asset_paths import resolve_icon_path
from slidegen.aws_icon_policy import icon_policy_error


class DiagramValidation(Protocol):
    @property
    def spec(self) -> Mapping[str, Any]: ...

    def err(self, message: str) -> None: ...

    def allow_keys(self, value: Mapping[str, Any], allowed: set[str], path: str) -> None: ...


def _is_str(value: Any) -> TypeGuard[str]:
    return isinstance(value, str) and bool(value.strip())


_EDGE_SIDES = {"left", "right", "top", "bottom"}
_CHANNEL_KINDS = {"left_of_col", "right_of_col", "above_row", "below_row", "outside_container"}


def validate_diagram(s: DiagramValidation) -> None:
    d = s.spec.get("diagram")
    if not isinstance(d, dict):
        s.err(
            '"diagram" (cols/rows/nodes/edges を持つオブジェクト) が必要です。'
            "座標は書かない(グリッド仕様のみ)"
        )
        return
    s.allow_keys(d, {"cols", "rows", "nodes", "containers", "channels", "edges"}, "diagram")
    if "spec" in s.spec or "spec" in d:
        s.err(
            '"spec" (サンプル図の名前参照) は使えません。diagram の中に'
            "グリッド仕様をインラインで書いてください"
        )
    if "area" in d:
        s.err("diagram.area は指定できません。描画領域は行数からエンジンが自動計算します")
    cols, rows = _validate_axes(s, d)
    nodes = _validate_nodes(s, d, cols, rows)
    if nodes is None:
        return
    names = _validate_containers(s, d, nodes)
    channels = _validate_channels(s, d, cols, rows, nodes, names)
    _validate_edges(s, d, rows, nodes, names, channels)


def _validate_axes(s: DiagramValidation, d: Mapping[str, Any]) -> tuple[list[Any], list[Any]]:
    cols, rows = d.get("cols"), d.get("rows")
    for key, v in (("cols", cols), ("rows", rows)):
        if not (isinstance(v, list) and v and all(_is_str(c) for c in v)):
            s.err(f"diagram.{key} は文字列の配列 (1件以上) が必要です")
        elif len(set(v)) != len(v):
            s.err(f"diagram.{key} は重複しない名前にしてください")
    return (cols if isinstance(cols, list) else [], rows if isinstance(rows, list) else [])


def _validate_nodes(
    s: DiagramValidation, d: Mapping[str, Any], cols: list[Any], rows: list[Any]
) -> Mapping[str, Any] | None:
    nodes = d.get("nodes")
    if not (isinstance(nodes, dict) and nodes):
        s.err("diagram.nodes (ノード名 → {col, row, title} のオブジェクト) が必要です")
        return None
    for name, n in nodes.items():
        if not isinstance(n, dict):
            s.err(f"nodes.{name} はオブジェクトにしてください")
            continue
        s.allow_keys(n, {"col", "row", "title", "sub", "icon", "service"}, f"diagram.nodes.{name}")
        if not _is_str(n.get("title")):
            s.err(f"nodes.{name}.title (文字列) が必要です")
        if "sub" in n and not _is_str(n["sub"]):
            s.err(f"nodes.{name}.sub は空でない文字列にしてください")
        if "service" in n and not _is_str(n["service"]):
            s.err(f"nodes.{name}.service は空でないAWSサービス識別名にしてください")
        if isinstance(cols, list) and n.get("col") not in cols:
            s.err(f"nodes.{name}.col={n.get('col')!r} が diagram.cols にありません")
        if isinstance(rows, list) and n.get("row") not in rows:
            s.err(f"nodes.{name}.row={n.get('row')!r} が diagram.rows にありません")
        if not _is_str(n.get("icon")):
            s.err(
                f"nodes.{name}.icon は必須です。CONTENT_SCHEMA.md の"
                f"Fluent/AWSアイコン一覧から選んでください"
            )
        else:
            try:
                icon_path = resolve_icon_path(n["icon"])
            except ValueError:
                s.err(f"nodes.{name}.icon は slidegen/assets/ 内の相対パスにしてください")
            else:
                if not icon_path.is_file():
                    s.err(
                        f"nodes.{name}.icon={n['icon']!r} が assets/ にありません。"
                        f"Fluent一覧は fetch_fluent_icons.py --list で確認してください"
                    )
                if _is_str(n.get("title")) and ("service" not in n or _is_str(n["service"])):
                    try:
                        policy_error = icon_policy_error(n["title"], n["icon"], n.get("service"))
                    except ValueError as error:
                        s.err(f"nodes.{name}.service: {error}")
                    else:
                        if policy_error:
                            s.err(f"nodes.{name}.icon: {policy_error}")
    return nodes


def _validate_containers(
    s: DiagramValidation, d: Mapping[str, Any], nodes: Mapping[str, Any]
) -> set[str]:
    cont_names: set[str] = set()
    containers = d.get("containers", [])
    if not isinstance(containers, list):
        s.err("diagram.containers は配列にしてください")
        containers = []
    for i, c in enumerate(containers):
        if not (
            isinstance(c, dict)
            and _is_str(c.get("name"))
            and _is_str(c.get("label"))
            and isinstance(c.get("members"), list)
        ):
            s.err(f"containers[{i}] には name / label (文字列) と members (配列) が必要です")
            continue
        s.allow_keys(c, {"name", "label", "members", "color", "dash"}, f"diagram.containers[{i}]")
        if not c["members"] or not all(_is_str(member) for member in c["members"]):
            s.err(f"containers[{i}].members は1件以上の参照文字列にしてください")
        if c.get("color", "line") not in ("line", "navy", "accent"):
            s.err(f"containers[{i}].color は line / navy / accent にしてください")
        if "dash" in c and c["dash"] != "dash":
            s.err(f'containers[{i}].dash は "dash" にしてください')
        for key in ("pad", "pad_x"):
            if key in c:
                s.err(
                    f"containers[{i}].{key} は指定できません。余白は入れ子構造と"
                    "行数からエンジンが自動計算します"
                )
        cont_names.add(c["name"])
    for i, c in enumerate(containers):
        if not isinstance(c, dict) or not isinstance(c.get("members"), list):
            continue
        for m in c["members"]:
            ref_ok = (
                m[1:] in cont_names
                if isinstance(m, str) and m.startswith("@")
                else isinstance(m, str) and m in nodes
            )
            if not ref_ok:
                s.err(f"containers[{i}].members の {m!r} が nodes / @コンテナ名 に見つかりません")
    return cont_names


def _validate_channels(
    s: DiagramValidation,
    d: Mapping[str, Any],
    cols: list[Any],
    rows: list[Any],
    nodes: Mapping[str, Any],
    cont_names: set[str],
) -> Mapping[str, Any]:
    channels = d.get("channels", {})
    if not isinstance(channels, dict):
        s.err("diagram.channels はオブジェクトにしてください")
        channels = {}
    for name, ch in channels.items():
        if not _is_str(name):
            s.err("diagram.channels のキーは空でない文字列にしてください")
        if not (
            isinstance(ch, list)
            and len(ch) == 2
            and isinstance(ch[0], str)
            and ch[0] in _CHANNEL_KINDS
        ):
            s.err(
                f"channels.{name} は [種類, 基準] の2要素配列にしてください "
                f"(種類: {', '.join(sorted(_CHANNEL_KINDS))})"
            )
            continue
        kind, ref = ch
        if kind in {"left_of_col", "right_of_col"} and ref not in (cols or []):
            s.err(f"channels.{name} の基準 {ref!r} が diagram.cols にありません")
        elif kind in {"above_row", "below_row"} and ref not in (rows or []):
            s.err(f"channels.{name} の基準 {ref!r} が diagram.rows にありません")
        elif kind == "outside_container":
            valid_ref = (
                isinstance(ref, list)
                and len(ref) == 2
                and isinstance(ref[1], str)
                and ref[1] in {"left", "right", "top", "bottom", "top_inside"}
                and (
                    (_is_str(ref[0]) and ref[0] in cont_names)
                    or (
                        isinstance(ref[0], list)
                        and ref[0]
                        and all(isinstance(node, str) and node in nodes for node in ref[0])
                    )
                )
            )
            if not valid_ref:
                s.err(
                    f"channels.{name} のoutside_container基準は "
                    "[コンテナ名またはノード名配列, 辺] にしてください"
                )
    return channels


def _validate_edges(
    s: DiagramValidation,
    d: Mapping[str, Any],
    rows: list[Any],
    nodes: Mapping[str, Any],
    cont_names: set[str],
    channels: Mapping[str, Any],
) -> None:
    edges = d.get("edges")
    if not (isinstance(edges, list) and edges):
        s.err("diagram.edges ({from, to} の配列、1件以上) が必要です")
        return
    for i, e in enumerate(edges):
        if not isinstance(e, dict):
            s.err(f"edges[{i}] はオブジェクトにしてください")
            continue
        s.allow_keys(
            e,
            {
                "from",
                "to",
                "label",
                "exit",
                "enter",
                "via",
                "dash",
                "both",
                "from_row",
            },
            f"diagram.edges[{i}]",
        )
        for key in ("from", "to"):
            v = e.get(key)
            ref_ok = (
                v[1:] in cont_names
                if isinstance(v, str) and v.startswith("@")
                else isinstance(v, str) and v in nodes
            )
            if not ref_ok:
                s.err(f"edges[{i}].{key}={v!r} が nodes / @コンテナ名 に見つかりません")
        for key in ("exit", "enter"):
            if key in e and (not isinstance(e[key], str) or e[key] not in _EDGE_SIDES):
                s.err(
                    f"edges[{i}].{key} は {', '.join(sorted(_EDGE_SIDES))} のいずれかにしてください"
                )
        if "label" in e and not _is_str(e["label"]):
            s.err(f"edges[{i}].label は空でない文字列にしてください")
        if "dash" in e and e["dash"] != "dash":
            s.err(f'edges[{i}].dash は "dash" にしてください')
        if "both" in e and not isinstance(e["both"], bool):
            s.err(f"edges[{i}].both は真偽値にしてください")
        via = e.get("via", [])
        if not (isinstance(via, list) and all(_is_str(v) for v in via)):
            s.err(f"edges[{i}].via はチャネル名の配列にしてください")
            via = []
        for v in via:
            if v not in channels:
                s.err(f"edges[{i}].via の {v!r} が diagram.channels にありません")
        source = e.get("from")
        if isinstance(source, str) and source.startswith("@"):
            if e.get("from_row") not in (rows or []):
                s.err(
                    f"edges[{i}].from_row はコンテナ始点の接続行として"
                    "diagram.rowsから指定してください"
                )
        elif "from_row" in e:
            s.err(f"edges[{i}].from_row はfromが@コンテナ名の場合だけ指定できます")
