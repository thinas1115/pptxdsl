"""構造検証に合格した入力の意味を検証する。フィールドや型の定義を重複しない。"""

from __future__ import annotations

from collections import Counter
from typing import Any, Protocol
from urllib.parse import urlsplit

from PIL import Image

from slidegen.asset_paths import resolve_icon_path, resolve_image_path
from slidegen.schema_definition import content_schema, slide_schemas
from slidegen.diagram_contract import validate_diagram
from slidegen.timeline_layout import resolve_marker, resolve_program_span


class Context(Protocol):
    spec: dict[str, Any]

    def err(self, message: str) -> None: ...


_SCHEMA = content_schema()
_SLIDES = slide_schemas()


def web_url(value: str, *, https_only: bool = False) -> bool:
    if "\\" in value or any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value):
        return False
    try:
        parsed = urlsplit(value)
        return (
            parsed.scheme in ({"https"} if https_only else {"http", "https"})
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
            and parsed.port != 0
        )
    except ValueError:
        return False


def _ids(s: Context, items: list[dict[str, Any]], path: str) -> set[str]:
    seen: set[str] = set()
    for index, item in enumerate(items):
        key = item["id"]
        if key in seen:
            s.err(f"{path}[{index}].id={key!r} が重複しています")
        seen.add(key)
    return seen


def _icon(s: Context, value: str, path: str) -> None:
    try:
        resolved = resolve_icon_path(value)
    except ValueError:
        s.err(f"{path} は slidegen/assets/ 内の相対パスにしてください")
    else:
        if not resolved.is_file():
            s.err(f"{path}={value!r} がassets/にありません")


def _image(s: Context, value: str, path: str) -> None:
    try:
        resolved = resolve_image_path(value)
    except ValueError as error:
        s.err(f"{path}: {error}")
        return
    if not resolved.is_file():
        s.err(f"{path}={value!r} がassets/にありません")
        return
    try:
        with Image.open(resolved) as image:
            image.verify()
    except (OSError, ValueError):
        s.err(f"{path}={value!r} は有効なPNG/JPEGではありません")


def _table(s: Context) -> None:
    for index, row in enumerate(s.spec["rows"]):
        if len(row) != len(s.spec["columns"]):
            s.err(f"rows[{index}] は columns と同じ要素数の文字列配列にしてください")
    if "note_link" in s.spec and not web_url(s.spec["note_link"]["url"], https_only=True):
        s.err(
            "note_link.url は https:// で始まる完全なURLにしてください（認証情報・空白は含めないでください）"
        )


def _chart(s: Context) -> None:
    chart = s.spec["chart"]
    for index, (_, values) in enumerate(chart["series"]):
        if len(values) != len(chart["categories"]):
            s.err(f"series[{index}] の値を categories と同数にしてください")


def _levels(s: Context, value: dict[str, Any], path: str) -> dict[str, int]:
    placed: dict[str, int] = {}
    for index, level in enumerate(value["levels"]):
        for key in level:
            if key not in value["nodes"]:
                s.err(f"{path}.levels[{index}] が未定義ノード {key!r} を参照しています")
            if key in placed:
                s.err(f"{path}.nodes.{key} は複数の階層に配置されています")
            placed[key] = index
    for key in value["nodes"]:
        if key not in placed:
            s.err(f"{path}.nodes.{key} がlevelsに配置されていません")
    return placed


def _edges(
    s: Context,
    edges: list[dict[str, Any]],
    ids: set[str],
    path: str,
    *,
    default: str = "forward",
    directed: bool = True,
    entity: str = "ノード",
) -> None:
    seen: set[tuple[str, ...]] = set()
    for index, edge in enumerate(edges):
        source, target = edge["from"], edge["to"]
        if source not in ids or target not in ids:
            s.err(f"{path}[{index}] が未定義{entity}を参照しています")
        if source == target:
            s.err(f"{path}[{index}] は同じノードへ接続できません")
        pair = (source, target) if directed else tuple(sorted((source, target)))
        key = (*pair, edge.get("kind", default)) if default == "reporting" else pair
        if key in seen:
            detail = "重複しています" if directed else "向きを問わず重複しています"
            s.err(f"{path}[{index}] の接続が{detail}")
        seen.add(key)


def _process(s: Context) -> None:
    if "flow" not in s.spec:
        for index in s.spec.get("emph", []):
            if index >= len(s.spec["steps"]):
                s.err("emph は steps の0始まりindexの配列にしてください")
        return
    flow = s.spec["flow"]
    level = _levels(s, flow, "process.flow")
    _edges(s, flow["edges"], set(flow["nodes"]), "process.flow.edges")
    for index, edge in enumerate(flow["edges"]):
        if (
            edge["from"] in level
            and edge["to"] in level
            and level[edge["to"]] <= level[edge["from"]]
            and edge.get("kind", "forward") != "feedback"
        ):
            s.err(f"process.flow.edges[{index}] の戻り接続にはkind=feedbackを指定してください")


def _roadmap(s: Context) -> None:
    count = 0
    periods = s.spec["periods"]
    for index, track in enumerate(s.spec["tracks"]):
        spans = []
        for activity_index, activity in enumerate(track["activities"]):
            count += 1
            try:
                spans.append(resolve_program_span(activity, periods))
            except ValueError as error:
                s.err(f"tracks[{index}].activities[{activity_index}] の{error}")
        if "milestone" in track:
            try:
                marker = resolve_marker(track["milestone"]["at"], periods)
            except ValueError as error:
                s.err(f"tracks[{index}].milestone の{error}")
            else:
                if abs(marker / 0.25 - round(marker / 0.25)) > 1e-8:
                    s.err(f"tracks[{index}].milestone.at は0.25刻みの期間位置で指定してください")
                if spans and not any(start <= marker <= end for start, end in spans):
                    s.err(
                        f"tracks[{index}].milestone.at は同じテーマ内のいずれかの作業期間内にしてください"
                    )
    maximum = _SLIDES["program_roadmap"]["x-maxActivities"]
    if count > maximum:
        s.err(f"activities は全テーマ合計{maximum}件までです。工程表を分割してください")


def _org(s: Context) -> None:
    org = s.spec["org"]
    levels = _levels(s, org, "org")
    _edges(s, org.get("edges", []), set(org["nodes"]), "org.edges", default="reporting")
    for index, edge in enumerate(org.get("edges", [])):
        if edge.get("kind", "reporting") == "reporting":
            if "label" in edge:
                s.err(
                    f"org.edges[{index}].label は advice / collaboration の関係線だけに指定できます。reportingは共有幹へまとめるため、責任範囲はsubへ記載してください"
                )
            if (
                edge["from"] in levels
                and edge["to"] in levels
                and levels[edge["to"]] <= levels[edge["from"]]
            ):
                s.err(f"org.edges[{index}] のreportingは上位階層から下位階層へ接続してください")


def _mapping(s: Context) -> None:
    left = _ids(s, s.spec["left_items"], "left_items")
    right = _ids(s, s.spec["right_items"], "right_items")
    seen = set()
    for index, link in enumerate(s.spec["links"]):
        pair = (link["from"], link["to"])
        if pair[0] not in left or pair[1] not in right:
            s.err(f"links[{index}] がleft_items / right_itemsの未定義idを参照しています")
        if pair in seen:
            s.err(f"links[{index}] の対応が重複しています")
        seen.add(pair)


def _swimlane(s: Context) -> None:
    lanes = _ids(s, s.spec["lanes"], "lanes")
    stages = _ids(s, s.spec["stages"], "stages")
    steps = _ids(s, s.spec["steps"], "steps")
    numbers: set[int] = set()
    cells: Counter[tuple[str, str]] = Counter()
    order = {stage["id"]: index for index, stage in enumerate(s.spec["stages"])}
    step_order = {}
    for index, step in enumerate(s.spec["steps"]):
        if step["lane"] not in lanes or step["stage"] not in stages:
            s.err(f"steps[{index}] がlanes / stagesの未定義idを参照しています")
        cell = (step["lane"], step["stage"])
        cells[cell] += 1
        if cells[cell] > 2:
            s.err(f"steps[{index}] と同じlane / stageには最大2工程までです")
        number = step.get("number")
        if number is not None:
            if number in numbers:
                s.err(f"steps[{index}].number={number} が重複しています")
            numbers.add(number)
        step_order[step["id"]] = order.get(step["stage"], -1)
    _edges(s, s.spec["edges"], steps, "edges")
    for index, edge in enumerate(s.spec["edges"]):
        if (
            step_order.get(edge["to"], -1) < step_order.get(edge["from"], -1)
            and edge.get("kind", "forward") != "feedback"
        ):
            s.err(f"edges[{index}] の前フェーズへの接続にはkind=feedbackが必要です")


def _sequence(s: Context) -> None:
    participants = _ids(s, s.spec["participants"], "participants")
    messages = _ids(s, s.spec["messages"], "messages")
    order = {message["id"]: index for index, message in enumerate(s.spec["messages"])}
    for index, message in enumerate(s.spec["messages"]):
        if message["from"] not in participants or message["to"] not in participants:
            s.err(f"messages[{index}] が未定義participantを参照しています")
    for index, phase in enumerate(s.spec.get("phases", [])):
        if phase["from"] not in messages or phase["to"] not in messages:
            s.err(f"phases[{index}] が未定義messageを参照しています")
        elif order[phase["from"]] > order[phase["to"]]:
            s.err(f"phases[{index}] はfromより後のmessageをtoへ指定してください")


def _network(s: Context) -> None:
    lanes = _ids(s, s.spec["lanes"], "lanes")
    columns = _ids(s, s.spec["columns"], "columns")
    nodes = _ids(s, s.spec["nodes"], "nodes")
    memberships = {node["id"]: set(node["lanes"]) for node in s.spec["nodes"]}
    cells: Counter[tuple[str, tuple[str, ...]]] = Counter()
    for index, node in enumerate(s.spec["nodes"]):
        if node["column"] not in columns:
            s.err(f"nodes[{index}].column がcolumnsの未定義idを参照しています")
        if not set(node["lanes"]) <= lanes:
            s.err(f"nodes[{index}].lanes がlanesの未定義idを参照しています")
        key = (node["column"], tuple(sorted(node["lanes"])))
        cells[key] += 1
        if cells[key] > 2:
            s.err(f"nodes[{index}] と同じcolumn / lanesには2件まで配置できます")
        _icon(s, node["icon"], f"nodes[{index}].icon")
    _edges(s, s.spec["links"], nodes, "links", directed=False)
    for index, link in enumerate(s.spec["links"]):
        members = set(link.get("lanes", []))
        if not members <= lanes:
            s.err(f"links[{index}].lanes がlanesの未定義idを参照しています")
        kind = link.get("kind", "access")
        if kind == "trunk" and len(members) < 2:
            s.err(f"links[{index}]: trunkは運ぶlanesを2件以上指定してください")
        if kind in {"access", "broadcast", "blocked"} and len(members) != 1:
            s.err(f"links[{index}]: {kind}のlanesは1件指定してください")
        source, target = link["from"], link["to"]
        if source in memberships and target in memberships:
            allowed = (
                memberships[source] - memberships[target]
                if kind == "blocked"
                else memberships[source] & memberships[target]
            )
            if not members <= allowed:
                detail = (
                    "接続元だけが所属し、接続先が所属しない"
                    if kind == "blocked"
                    else "接続元・接続先の双方に所属する"
                )
                s.err(f"links[{index}].lanes は{detail}laneを指定してください")


def _protocol(s: Context) -> None:
    stages = _ids(s, s.spec["stages"], "stages")
    seen: set[str] = set()
    for index, stage in enumerate(s.spec["stages"]):
        _icon(s, stage["icon"], f"stages[{index}].icon")
    for index, flow in enumerate(s.spec["flows"]):
        label = flow["label"].strip()
        if label in seen:
            s.err(f"flows[{index}].label が重複しています")
        seen.add(label)
        ids = [state["stage"] for state in flow["states"]]
        for stage_id, count in Counter(ids).items():
            if count > 1:
                s.err(f"flows[{index}].states のstage={stage_id!r} が重複しています")
        if len(ids) != len(stages) or set(ids) != stages:
            s.err(f"flows[{index}].states は全stageを1件ずつ指定してください")
        for state_index, state in enumerate(flow["states"]):
            if "encapsulation" in state:
                maximum = _SCHEMA["$defs"]["protocol_state"]["properties"]["encapsulation"][
                    "x-trimmed-maxLength"
                ]
                if len(state["encapsulation"].strip()) > maximum:
                    s.err(
                        f"flows[{index}].states[{state_index}].encapsulation は{maximum}文字以内にしてください"
                    )


def _anatomy(s: Context) -> None:
    for index, frame in enumerate(s.spec["frames"]):
        ids = _ids(s, frame["fields"], f"frames[{index}].fields")
        for annotation_index, annotation in enumerate(frame.get("annotations", [])):
            if annotation["field"] not in ids:
                s.err(
                    f"frames[{index}].annotations[{annotation_index}] は定義済みfieldを指定してください"
                )


def _references(s: Context) -> None:
    _ids(s, s.spec["references"], "references")
    seen = set()
    for index, item in enumerate(s.spec["references"]):
        if not web_url(item["url"]):
            s.err(
                f"references[{index}].url はhttpまたはhttpsの完全なURLにしてください（認証情報・空白は含めないでください）"
            )
        if item["url"] in seen:
            s.err(f"references[{index}].url が同じスライド内で重複しています")
        seen.add(item["url"])


def _vpc(s: Context) -> None:
    all_items = []
    resources = list(s.spec.get("external", []))
    for az in s.spec["azs"]:
        all_items.append(az)
        for subnet in az["subnets"]:
            all_items.append(subnet)
            resources.extend(subnet.get("resources", []))
    _ids(s, [*all_items, *resources], "azs / subnets / resources / external")
    for index, item in enumerate(resources):
        _icon(s, item["icon"], f"resources / external[{index}].icon")
    _edges(
        s,
        s.spec.get("flows", []),
        {item["id"] for item in resources},
        "flows",
        entity="resourceまたはexternal",
    )


def validate_semantics(s: Context) -> None:
    kind = s.spec["type"]
    functions = {
        "table": _table,
        "chart": _chart,
        "process": _process,
        "program_roadmap": _roadmap,
        "org": _org,
        "relationship_map": _mapping,
        "swimlane_flow": _swimlane,
        "message_sequence": _sequence,
        "nw_topology": _network,
        "nw_protocol_flow": _protocol,
        "nw_frame_anatomy": _anatomy,
        "references": _references,
        "aws_vpc_layout": _vpc,
    }
    if kind in functions:
        functions[kind](s)
    elif kind == "image":
        _image(s, s.spec["image"], "image")
    elif kind == "image_compare":
        for side in ("left", "right"):
            _image(s, s.spec[side]["image"], f"{side}.image")
    elif kind == "concept":
        _icon(s, s.spec["icon"], "icon")
    elif kind == "config_lab":
        maximum = _SCHEMA["$defs"]["code_section"]["properties"]["code"]["x-maxLines"]
        for index, section in enumerate(s.spec["sections"]):
            if len(section["code"].splitlines()) > maximum:
                s.err(f"sections[{index}].code は{maximum}行以内にしてください")
    elif kind == "knowledge_check":
        for index, question in enumerate(s.spec["questions"]):
            if not 0 <= question["answer"] < len(question["options"]):
                s.err(f"questions[{index}].answer はoptionsの0始まりindexにしてください")
    elif kind == "diagram":
        validate_diagram(s)
