"""構成図の参照・素材の意味検証。構造検証に合格した入力だけを受け取る。"""

from typing import Any, Mapping, Protocol

from slidegen.asset_paths import resolve_icon_path
from slidegen.aws_icon_policy import icon_policy_error


class DiagramValidation(Protocol):
    @property
    def spec(self) -> Mapping[str, Any]: ...

    def err(self, message: str) -> None: ...


def validate_diagram(s: DiagramValidation) -> None:
    d = s.spec["diagram"]
    cols, rows, nodes = d["cols"], d["rows"], d["nodes"]
    for name, node in nodes.items():
        for key, values in (("col", cols), ("row", rows)):
            if node[key] not in values:
                s.err(f"nodes.{name}.{key} が diagram.{key}s にありません")
        try:
            icon = resolve_icon_path(node["icon"])
        except ValueError:
            s.err(f"nodes.{name}.icon は slidegen/assets/ 内の相対パスにしてください")
        else:
            if not icon.is_file():
                s.err(f"nodes.{name}.icon が assets/ にありません")
            try:
                policy_error = icon_policy_error(node["title"], node["icon"], node.get("service"))
            except ValueError as error:
                s.err(f"nodes.{name}.service: {error}")
            else:
                if policy_error:
                    s.err(f"nodes.{name}.icon: {policy_error}")
    containers = d.get("containers", [])
    names = {container["name"] for container in containers}

    def has_ref(value: str) -> bool:
        return value[1:] in names if value.startswith("@") else value in nodes

    for index, container in enumerate(containers):
        for member in container["members"]:
            if not has_ref(member):
                s.err(f"containers[{index}].members が nodes / @コンテナ名 に見つかりません")
    channels = d.get("channels", {})
    for name, (kind, reference) in channels.items():
        if kind in {"left_of_col", "right_of_col"}:
            if reference not in cols:
                s.err(f"channels.{name} の基準が diagram.cols にありません")
        elif kind in {"above_row", "below_row"}:
            if reference not in rows:
                s.err(f"channels.{name} の基準が diagram.rows にありません")
        else:
            group, _side = reference
            if (isinstance(group, str) and group not in names) or (
                isinstance(group, list) and any(node not in nodes for node in group)
            ):
                s.err(
                    f"channels.{name} のoutside_container基準が未定義コンテナ・ノードを参照しています"
                )
    for index, edge in enumerate(d["edges"]):
        for key in ("from", "to"):
            if not has_ref(edge[key]):
                s.err(f"edges[{index}].{key} が nodes / @コンテナ名 に見つかりません")
        for via in edge.get("via", []):
            if via not in channels:
                s.err(f"edges[{index}].via が diagram.channels にありません")
        if edge["from"].startswith("@"):
            if edge.get("from_row") not in rows:
                s.err(
                    f"edges[{index}].from_row はコンテナ始点の接続行としてdiagram.rowsから指定してください"
                )
        elif "from_row" in edge:
            s.err(f"edges[{index}].from_row はfromが@コンテナ名の場合だけ指定できます")
