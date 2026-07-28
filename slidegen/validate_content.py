"""content.json をレンダリング前に機械検証する。

使い方:
  python slidegen/validate_content.py content.json

generate_from_json.py が生成前に自動で呼ぶため、通常は単体実行しなくてよい。
エラーメッセージは「slides[i] (type=xxx): 内容」の形式で、生成AIにそのまま
渡して content.json を直させることを想定した粒度にしてある。

ここで強制する件数上限は「段階的収容の最小値でも崩れる」値。
通常・余白圧縮・要素縮小・明示停止を実測して決める。
"""
import json
import re
import sys
from pathlib import Path

from PIL import Image

from asset_paths import resolve_icon_path, resolve_image_path
from sample_content_guard import sample_reuse_paths
from timeline_layout import resolve_marker, resolve_program_span, resolve_span

# noteを実際に描画するtype。それ以外への指定はエラーにする。
NOTE_TYPES = {"table", "chart", "process", "roadmap", "program_roadmap",
              "matrix", "hub", "org", "diagram"}
_PLACEHOLDER = re.compile(r"^<[^<>]+>$")
_UNRESOLVED = re.compile(r"^(?:TBD|TODO|要確認|未定|仮入力|仮文言)$", re.IGNORECASE)

_TOP_LEVEL_KEYS = {"meta", "slides"}
_META_KEYS = {"title", "footer", "date", "organization", "author"}
_BASE_SLIDE_KEYS = {"type", "kicker", "title", "lead"}
_TYPE_KEYS = {
    "title": {"type", "title", "subtitle"},
    "bullets": _BASE_SLIDE_KEYS | {"bullets"},
    "cards": _BASE_SLIDE_KEYS | {"style", "cards"},
    "table": _BASE_SLIDE_KEYS | {"columns", "rows", "note"},
    "twocol": _BASE_SLIDE_KEYS | {"left", "right"},
    "chart": _BASE_SLIDE_KEYS | {"chart", "note"},
    "image": _BASE_SLIDE_KEYS | {"image", "fit", "shadow", "alt"},
    "process": _BASE_SLIDE_KEYS | {"steps", "emph", "flow", "note"},
    "roadmap": _BASE_SLIDE_KEYS | {"months", "phases", "milestones", "note"},
    "program_roadmap": _BASE_SLIDE_KEYS | {"periods", "tracks", "note"},
    "matrix": _BASE_SLIDE_KEYS | {
        "x_axis", "y_axis", "points", "quadrants", "target_label", "note",
    },
    "hub": _BASE_SLIDE_KEYS | {"hub", "ring", "note"},
    "org": _BASE_SLIDE_KEYS | {"org", "note"},
    "diagram": _BASE_SLIDE_KEYS | {"diagram", "note"},
}


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _placeholder_paths(value, path=""):
    if isinstance(value, str) and _PLACEHOLDER.fullmatch(value.strip()):
        yield path or "トップレベル"
    elif isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            yield from _placeholder_paths(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _placeholder_paths(child, f"{path}[{index}]")


def _unresolved_paths(value, path=""):
    if isinstance(value, str) and _UNRESOLVED.fullmatch(value.strip()):
        yield path or "トップレベル"
    elif isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            yield from _unresolved_paths(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _unresolved_paths(child, f"{path}[{index}]")


def _unknown_keys(value, allowed):
    if not isinstance(value, dict):
        return []
    return sorted(set(value) - set(allowed))


class _Slide:
    """1スライド分の検証ヘルパー。エラーを共通形式で溜める。"""

    def __init__(self, idx, spec, errors):
        self.idx, self.spec, self.errors = idx, spec, errors

    def err(self, msg):
        t = self.spec.get("type", "?")
        self.errors.append(f"slides[{self.idx}] (type={t}): {msg}")

    def req_str(self, key):
        if not _is_str(self.spec.get(key)):
            self.err(f'"{key}" (文字列) が必要です')
            return False
        return True

    def req_list(self, key, min_n, max_n, what):
        v = self.spec.get(key)
        if not isinstance(v, list) or not (min_n <= len(v) <= max_n):
            self.err(f'"{key}" は{what}の配列 ({min_n}〜{max_n}件) が必要です'
                     f' (現在: {len(v) if isinstance(v, list) else "配列でない"})')
            return None
        return v

    def allow_keys(self, value, allowed, path):
        for key in _unknown_keys(value, allowed):
            self.err(
                f"{path}.{key}: 未対応のフィールドです。"
                "CONTENT_SCHEMA.mdに記載されたフィールドだけを使用してください")


def _v_title(s):
    s.req_str("title")
    s.req_str("subtitle")


def _v_bullets(s):
    items = s.req_list("bullets", 1, 6, "[本文, null]")
    for i, b in enumerate(items or []):
        if not (isinstance(b, list) and len(b) == 2
                and _is_str(b[0]) and b[1] is None):
            s.err(f'bullets[{i}] は ["本文", null] の2要素配列にしてください')


def _v_cards(s):
    items = s.req_list("cards", 2, 6, "カード")
    style = s.spec.get("style", "editorial")
    if style not in {"editorial", "metrics"}:
        s.err('cards.style は "editorial" または "metrics" にしてください')
    for i, c in enumerate(items or []):
        if not (isinstance(c, dict) and _is_str(c.get("heading"))
                and _is_str(c.get("body"))):
            s.err(f"cards[{i}] は heading / bodyを持つオブジェクトにしてください")
            continue
        s.allow_keys(c, {"heading", "body", "value", "emphasis"},
                     f"cards[{i}]")
        if "value" in c and not _is_str(c["value"]):
            s.err(f"cards[{i}].value は空でない文字列にしてください")
        if "emphasis" in c and not isinstance(c["emphasis"], bool):
            s.err(f"cards[{i}].emphasis は真偽値にしてください")
        if style == "metrics" and not _is_str(c.get("value")):
            s.err(f"cards[{i}].value はmetricsで必須です")


def _v_table(s):
    # 列数上限8: 既存サンプルの7列表が提出品質で通っている実績に合わせる
    cols = s.req_list("columns", 2, 8, "列名")
    rows = s.req_list("rows", 1, 8, "行")
    for i, row in enumerate(rows or []):
        if not (isinstance(row, list) and cols and len(row) == len(cols)
                and all(isinstance(c, str) for c in row)):
            s.err(f"rows[{i}] は columns と同じ要素数の文字列配列にしてください")


def _v_twocol(s):
    for side in ("left", "right"):
        p = s.spec.get(side)
        if not isinstance(p, dict):
            s.err(f'"{side}" (heading と bullets を持つオブジェクト) が必要です')
            continue
        s.allow_keys(p, {"label", "heading", "bullets"}, side)
        if not _is_str(p.get("heading")):
            s.err(f'{side}.heading (文字列) が必要です')
        if "label" in p and not _is_str(p["label"]):
            s.err(f"{side}.label は空でない文字列にしてください")
        b = p.get("bullets")
        if not (isinstance(b, list) and 1 <= len(b) <= 6
                and all(_is_str(x) for x in b)):
            s.err(f"{side}.bullets は文字列の配列 (1〜6件) にしてください")


def _v_chart(s):
    ch = s.spec.get("chart")
    if not isinstance(ch, dict):
        s.err('"chart" (categories と series を持つオブジェクト) が必要です')
        return
    s.allow_keys(ch, {
        "kind", "categories", "series", "show_legend", "show_values",
        "number_format",
    }, "chart")
    cats = ch.get("categories")
    if not (isinstance(cats, list) and 1 <= len(cats) <= 12
            and all(_is_str(c) for c in cats)):
        s.err("chart.categories は文字列の配列 (1〜12件) にしてください")
        cats = None
    series = ch.get("series")
    if not (isinstance(series, list) and 1 <= len(series) <= 4):
        s.err("chart.series は [系列名, 値配列] の配列 (1〜4件) にしてください")
        return
    if ch.get("kind", "bar") not in {
            "bar", "column", "line", "stacked_bar", "stacked_column"}:
        s.err("chart.kind は bar / column / line / stacked_bar / "
              "stacked_column のいずれかにしてください")
    for key in ("show_legend", "show_values"):
        if key in ch and not isinstance(ch[key], bool):
            s.err(f"chart.{key} は真偽値にしてください")
    if "number_format" in ch and not _is_str(ch["number_format"]):
        s.err("chart.number_format は空でない文字列にしてください")
    for i, sr in enumerate(series):
        ok = (isinstance(sr, list) and len(sr) == 2 and _is_str(sr[0])
              and isinstance(sr[1], list) and all(_is_num(v) for v in sr[1]))
        if not ok:
            s.err(f'series[{i}] は ["系列名", [数値, ...]] にしてください')
        elif cats and len(sr[1]) != len(cats):
            s.err(f"series[{i}] の値 ({len(sr[1])}件) を categories "
                  f"({len(cats)}件) と同数にしてください")


def _v_image(s):
    if not s.req_str("image"):
        return
    if "fit" in s.spec and s.spec["fit"] not in {"contain", "cover"}:
        s.err('image の "fit" は "contain" または "cover" にしてください')
    if "alt" in s.spec and not _is_str(s.spec["alt"]):
        s.err('"alt" は空でない文字列にしてください')
    if "shadow" in s.spec and not isinstance(s.spec["shadow"], bool):
        s.err('"shadow" は true または false にしてください')
    if "caption" in s.spec:
        s.err('imageの "caption" は廃止済みです。説明は "lead" へ移してください')
    if "source" in s.spec:
        s.err('imageの "source" は廃止済みです。表示枠を削除し、画像の権利情報はCREDITSへ記録してください')
    try:
        image_path = resolve_image_path(s.spec["image"])
    except ValueError as exc:
        s.err(str(exc))
        return
    if not image_path.is_file():
        s.err(f"image={s.spec['image']!r} がassets/にありません")
        return
    try:
        with Image.open(image_path) as image:
            image.verify()
    except (OSError, ValueError):
        s.err(f"image={s.spec['image']!r} は有効なPNG/JPEGではありません")


def _v_process(s):
    if "flow" in s.spec:
        if "steps" in s.spec or "emph" in s.spec:
            s.err("process.flow と旧steps/emphは同時に指定できません")
        _v_process_flow(s, s.spec["flow"])
        return
    steps = s.req_list("steps", 3, 6, "工程")
    for i, st in enumerate(steps or []):
        if not (isinstance(st, dict) and _is_str(st.get("name"))
                and _is_str(st.get("desc"))):
            s.err(f"steps[{i}] には name / desc (文字列) が必要です")
            continue
        s.allow_keys(st, {"name", "desc", "actor", "attribute"},
                     f"steps[{i}]")
        if "actor" in st and not _is_str(st["actor"]):
            s.err(f"steps[{i}].actor は空でない文字列にしてください")
        attribute = st.get("attribute")
        if "actor" in st and "attribute" in st:
            s.err(f"steps[{i}] は actor と attribute を同時に指定できません")
        if attribute is not None:
            if not isinstance(attribute, dict):
                s.err(f"steps[{i}].attribute は label / value を持つ"
                      "オブジェクトにしてください")
            else:
                s.allow_keys(attribute, {"label", "value"},
                             f"steps[{i}].attribute")
                for key in ("label", "value"):
                    if not _is_str(attribute.get(key)):
                        s.err(f"steps[{i}].attribute.{key} は空でない文字列に"
                              "してください")
    emph = s.spec.get("emph")
    if emph is not None and steps:
        if not (isinstance(emph, list)
                and all(isinstance(i, int) and 0 <= i < len(steps) for i in emph)):
            s.err(f"emph は steps の0始まりindex (0〜{len(steps) - 1}) の配列に"
                  f"してください")


def _v_process_flow(s, flow):
    if not isinstance(flow, dict):
        s.err("process.flow はnodes / levels / edgesを持つオブジェクトにしてください")
        return
    s.allow_keys(flow, {"nodes", "levels", "edges"}, "flow")
    nodes = flow.get("nodes")
    if not isinstance(nodes, dict) or not 2 <= len(nodes) <= 12:
        s.err("process.flow.nodes は2〜12件のノードを持つオブジェクトにしてください")
        nodes = {}
    for node_id, node in nodes.items():
        if not (_is_str(node_id) and isinstance(node, dict)
                and _is_str(node.get("name"))):
            s.err(f"process.flow.nodes.{node_id} にはname (文字列) が必要です")
            continue
        s.allow_keys(node, {"name", "desc", "actor", "style"},
                     f"flow.nodes.{node_id}")
        for key in ("desc", "actor"):
            if key in node and not _is_str(node[key]):
                s.err(f"process.flow.nodes.{node_id}.{key} は空でない文字列にしてください")
        if node.get("style", "standard") not in {
                "standard", "accent", "decision"}:
            s.err(f"process.flow.nodes.{node_id}.style はstandard / accent / "
                  "decisionのいずれかにしてください")
    levels = flow.get("levels")
    if not (isinstance(levels, list) and 2 <= len(levels) <= 6):
        s.err("process.flow.levels は2〜6列の配列にしてください")
        levels = []
    placed = set()
    level_of = {}
    for level_index, level in enumerate(levels):
        if not (isinstance(level, list) and 1 <= len(level) <= 3
                and all(_is_str(node_id) for node_id in level)):
            s.err(f"process.flow.levels[{level_index}] はノードIDの配列"
                  " (1〜3件) にしてください")
            continue
        for node_id in level:
            if node_id not in nodes:
                s.err(f"process.flow.levels[{level_index}] が未定義ノード"
                      f" {node_id!r} を参照しています")
            if node_id in placed:
                s.err(f"process.flow.nodes.{node_id} は複数列へ配置されています")
            placed.add(node_id)
            level_of[node_id] = level_index
    for node_id in nodes:
        if node_id not in placed:
            s.err(f"process.flow.nodes.{node_id} がlevelsに配置されていません")
    edges = flow.get("edges")
    if not (isinstance(edges, list) and 1 <= len(edges) <= 20):
        s.err("process.flow.edges は1〜20件の関係配列にしてください")
        return
    seen = set()
    for edge_index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            s.err(f"process.flow.edges[{edge_index}] はオブジェクトにしてください")
            continue
        s.allow_keys(edge, {"from", "to", "label", "kind"},
                     f"flow.edges[{edge_index}]")
        source, target = edge.get("from"), edge.get("to")
        if source not in nodes or target not in nodes:
            s.err(f"process.flow.edges[{edge_index}] が未定義ノードを参照しています")
            continue
        if source == target:
            s.err(f"process.flow.edges[{edge_index}] は同じノードへ接続できません")
        if (source, target) in seen:
            s.err(f"process.flow.edges[{edge_index}] は同じ接続が重複しています")
        seen.add((source, target))
        if "label" in edge and not _is_str(edge["label"]):
            s.err(f"process.flow.edges[{edge_index}].label は空でない文字列にしてください")
        kind = edge.get("kind", "forward")
        if kind not in {"forward", "feedback"}:
            s.err(f"process.flow.edges[{edge_index}].kind はforward / feedbackにしてください")
        if (source in level_of and target in level_of
                and level_of[target] <= level_of[source] and kind != "feedback"):
            s.err(f"process.flow.edges[{edge_index}] の戻り接続にはkind=feedbackを指定してください")


def _v_roadmap(s):
    months = s.req_list("months", 3, 12, "期間ラベル")
    if months and (not all(_is_str(month) for month in months)
                   or len(set(months)) != len(months)):
        s.err("months は重複しない空でない文字列の配列にしてください")
        months = None
    phases = s.req_list("phases", 1, 6, "フェーズ")
    for i, ph in enumerate(phases or []):
        if not (isinstance(ph, dict) and _is_str(ph.get("name"))
                and (_is_num(ph.get("start")) or _is_str(ph.get("start")))
                and (_is_num(ph.get("end")) or _is_str(ph.get("end")))):
            s.err(f"phases[{i}] には name (文字列) と "
                  f"start / end (数値または期間ラベル) が必要です")
            continue
        for field in ("goal", "bar"):
            if field in ph and not _is_str(ph.get(field)):
                s.err(f"phases[{i}].{field} は空でない文字列にしてください")
        s.allow_keys(ph, {"name", "goal", "bar", "start", "end"},
                     f"phases[{i}]")
        if months:
            try:
                resolve_span(ph, months)
            except ValueError as exc:
                s.err(f"phases[{i}] の{exc}")
    ms = s.spec.get("milestones", [])
    if not isinstance(ms, list):
        s.err('"milestones" は配列にしてください')
        return
    milestone_rows = set()
    for i, m in enumerate(ms):
        if not (isinstance(m, dict)
                and (_is_num(m.get("at")) or _is_str(m.get("at")))
                and isinstance(m.get("row"), int) and _is_str(m.get("label"))):
            s.err(f"milestones[{i}] には at (数値または期間ラベル) / "
                  f"row (整数) / label (文字列) が必要です")
            continue
        s.allow_keys(m, {"at", "row", "label"}, f"milestones[{i}]")
        if isinstance(m.get("row"), int):
            if m["row"] in milestone_rows:
                s.err(
                    f"milestones[{i}].row={m['row']} は重複しています。"
                    "1フェーズにつき1件にしてください")
            milestone_rows.add(m["row"])
        if months:
            try:
                marker = resolve_marker(m["at"], months)
            except ValueError as exc:
                s.err(f"milestones[{i}] の{exc}")
            else:
                if (phases and isinstance(m.get("row"), int)
                        and 0 <= m["row"] < len(phases)):
                    try:
                        start, end = resolve_span(phases[m["row"]], months)
                    except (AttributeError, ValueError):
                        pass
                    else:
                        if not start <= marker <= end:
                            s.err(
                                f"milestones[{i}].at は対応フェーズの"
                                "start〜end内にしてください")
        if phases and not 0 <= m["row"] < len(phases):
            s.err(f"milestones[{i}] の row={m['row']} は 0〜{len(phases) - 1} "
                  f"(phasesのindex) にしてください")


def _v_program_roadmap(s):
    periods = s.req_list("periods", 3, 12, "期間ラベル")
    if periods and (not all(_is_str(period) for period in periods)
                    or len(set(periods)) != len(periods)):
        s.err("periods は重複しない空でない文字列の配列にしてください")
        periods = None
    tracks = s.req_list("tracks", 1, 6, "テーマ")
    activity_count = 0
    for i, track in enumerate(tracks or []):
        if not isinstance(track, dict) or not _is_str(track.get("name")):
            s.err(f"tracks[{i}] には name (文字列) が必要です")
            continue
        s.allow_keys(track, {"name", "activities"}, f"tracks[{i}]")
        activities = track.get("activities")
        if not isinstance(activities, list) or not 1 <= len(activities) <= 8:
            s.err(f"tracks[{i}].activities は作業の配列 (1〜8件) にしてください")
            continue
        activity_count += len(activities)
        for j, activity in enumerate(activities):
            ok = (
                isinstance(activity, dict)
                and _is_str(activity.get("label"))
                and (_is_num(activity.get("start")) or _is_str(activity.get("start")))
                and (_is_num(activity.get("end")) or _is_str(activity.get("end")))
            )
            if not ok:
                s.err(f"tracks[{i}].activities[{j}] には label (文字列) と "
                      "start / end (数値または期間ラベル) が必要です")
                continue
            s.allow_keys(activity, {"label", "start", "end", "emph"},
                         f"tracks[{i}].activities[{j}]")
            if "emph" in activity and not isinstance(activity["emph"], bool):
                s.err(f"tracks[{i}].activities[{j}].emph は真偽値にしてください")
            if periods:
                try:
                    resolve_program_span(activity, periods)
                except ValueError as exc:
                    s.err(f"tracks[{i}].activities[{j}] の{exc}")
    if activity_count > 24:
        s.err(f"activities は全テーマ合計24件までです (現在: {activity_count}件)。"
              "工程表を複数スライドへ分割してください")


def _v_matrix(s):
    for key in ("x_axis", "y_axis"):
        s.req_str(key)
    points = s.req_list("points", 1, 8, "点")
    quadrants = s.spec.get("quadrants")
    if quadrants is not None and not (
            isinstance(quadrants, list) and len(quadrants) == 4
            and all(_is_str(label) for label in quadrants)):
        s.err("quadrants は [左下, 右下, 左上, 右上] の4文字列にしてください")
    if quadrants is None:
        s.req_str("target_label")
    for i, p in enumerate(points or []):
        if not (isinstance(p, dict) and _is_str(p.get("name"))
                and _is_num(p.get("x")) and _is_num(p.get("y"))):
            s.err(f"points[{i}] には name (文字列) と x / y (数値) が必要です")
            continue
        s.allow_keys(p, {"name", "x", "y", "emph"}, f"points[{i}]")
        if not (0.0 <= p["x"] <= 1.0 and 0.0 <= p["y"] <= 1.0):
            s.err(f"points[{i}] の x={p['x']} / y={p['y']} は 0.0〜1.0 にして"
                  f"ください")
        if "emph" in p and not isinstance(p["emph"], bool):
            s.err(f"points[{i}].emph は真偽値にしてください")


def _v_hub(s):
    s.req_str("hub")
    ring = s.req_list("ring", 3, 8, "周辺ノード")
    for i, r in enumerate(ring or []):
        if not (isinstance(r, dict) and _is_str(r.get("name"))
                and _is_str(r.get("label")) and _is_str(r.get("icon"))):
            s.err(f"ring[{i}] には name / label / icon (文字列) が必要です")
            continue
        s.allow_keys(r, {"name", "sub", "label", "icon"}, f"ring[{i}]")
        if "sub" in r and not _is_str(r["sub"]):
            s.err(f"ring[{i}].sub は空でない文字列にしてください")
        try:
            icon = resolve_icon_path(r["icon"])
        except ValueError:
            s.err(f"ring[{i}].icon は slidegen/assets/ 内の相対パスに"
                  "してください")
            continue
        if not icon.is_file():
            s.err(f"ring[{i}].icon のファイルがありません: {r['icon']}。"
                  "CONTENT_SCHEMA.md のFluentアイコン一覧から選んでください")


def _v_org(s):
    if any(key in s.spec for key in ("top", "pm", "teams", "external")):
        s.err('旧org形式の top / pm / teams / external は廃止しました。'
              'org.nodes / org.levels / org.edges へ移行してください')
        return

    org = s.spec.get("org")
    if not isinstance(org, dict):
        s.err('"org" (nodes/levels/edges を持つオブジェクト) が必要です')
        return
    s.allow_keys(org, {"nodes", "levels", "edges"}, "org")

    nodes = org.get("nodes")
    if not isinstance(nodes, dict) or not nodes:
        s.err("org.nodes は1件以上のノードを持つオブジェクトにしてください")
        nodes = {}
    for node_id, node in nodes.items():
        if not _is_str(node_id):
            s.err("org.nodes のキーは空でない文字列にしてください")
            continue
        if not isinstance(node, dict) or not _is_str(node.get("name")):
            s.err(f"org.nodes.{node_id} には name (文字列) が必要です")
            continue
        s.allow_keys(node, {"name", "sub", "members", "style"},
                     f"org.nodes.{node_id}")
        if "sub" in node and not _is_str(node["sub"]):
            s.err(f"org.nodes.{node_id}.sub は空でない文字列にしてください")
        members = node.get("members", [])
        if not (isinstance(members, list) and len(members) <= 4
                and all(_is_str(member) for member in members)):
            s.err(f"org.nodes.{node_id}.members は文字列の配列"
                  " (最大4件) にしてください")
        if node.get("style", "standard") not in {
                "primary", "accent", "standard", "external"}:
            s.err(f"org.nodes.{node_id}.style は primary / accent / standard / "
                  "external のいずれかにしてください")

    levels = org.get("levels")
    if not (isinstance(levels, list) and 1 <= len(levels) <= 6):
        s.err("org.levels は階層の配列 (1〜6階層) にしてください")
        levels = []
    level_of = {}
    for level_index, level in enumerate(levels):
        if not (isinstance(level, list) and 1 <= len(level) <= 5
                and all(_is_str(node_id) for node_id in level)):
            s.err(f"org.levels[{level_index}] はノードIDの配列"
                  " (1〜5件) にしてください")
            continue
        for node_id in level:
            if node_id not in nodes:
                s.err(f"org.levels[{level_index}] が未定義ノード"
                      f" {node_id!r} を参照しています")
            if node_id in level_of:
                s.err(f"org.nodes.{node_id} は複数の階層に配置されています")
            else:
                level_of[node_id] = level_index
    for node_id in nodes:
        if node_id not in level_of:
            s.err(f"org.nodes.{node_id} がorg.levelsに配置されていません")

    edges = org.get("edges", [])
    if not isinstance(edges, list) or len(edges) > 40:
        s.err("org.edges は関係の配列 (最大40件) にしてください")
        return
    seen = set()
    for edge_index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            s.err(f"org.edges[{edge_index}] はオブジェクトにしてください")
            continue
        s.allow_keys(edge, {"from", "to", "kind", "label"},
                     f"org.edges[{edge_index}]")
        source, target = edge.get("from"), edge.get("to")
        kind = edge.get("kind", "reporting")
        if not _is_str(source) or not _is_str(target):
            s.err(f"org.edges[{edge_index}] には from / to (文字列) が必要です")
            continue
        if source == target:
            s.err(f"org.edges[{edge_index}] は同じノード同士を接続できません")
        if source not in nodes or target not in nodes:
            s.err(f"org.edges[{edge_index}] が未定義ノードを参照しています")
            continue
        if kind not in {"reporting", "advice", "collaboration"}:
            s.err(f"org.edges[{edge_index}].kind は reporting / advice / "
                  "collaboration のいずれかにしてください")
        if "label" in edge and not _is_str(edge["label"]):
            s.err(f"org.edges[{edge_index}].label は空でない文字列にしてください")
        if kind == "reporting" and "label" in edge:
            s.err(f"org.edges[{edge_index}].label は advice / collaboration の"
                  "関係線だけに指定できます。reportingは階層間の共有幹へ"
                  "まとめるため、責任範囲はノードのsubへ記載してください")
        edge_key = (source, target, kind)
        if edge_key in seen:
            s.err(f"org.edges[{edge_index}] は同じ関係が重複しています")
        seen.add(edge_key)
        if (kind == "reporting" and source in level_of and target in level_of
                and level_of[target] <= level_of[source]):
            s.err(f"org.edges[{edge_index}] のreportingは上位階層から"
                  "下位階層へ接続してください")


_EDGE_SIDES = {"left", "right", "top", "bottom"}
_CHANNEL_KINDS = {"left_of_col", "right_of_col", "above_row", "below_row",
                  "outside_container"}


def _v_diagram(s):
    """構成図のグリッド仕様の構造検証。

    ここで見るのはJSONとしての整合(参照切れ・型違い)まで。行間に収まるか・
    配線がコンテナを貫通しないか等の実現可能性は、レンダリング時に
    diagram_layout.py エンジン自身が対処方法つきのエラーで検出する。
    """
    d = s.spec.get("diagram")
    if not isinstance(d, dict):
        s.err('"diagram" (cols/rows/nodes/edges を持つオブジェクト) が必要です。'
              '座標は書かない(グリッド仕様のみ)')
        return
    s.allow_keys(d, {"cols", "rows", "nodes", "containers", "channels", "edges"},
                 "diagram")
    if "spec" in s.spec or "spec" in d:
        s.err('"spec" (サンプル図の名前参照) は使えません。diagram の中に'
              'グリッド仕様をインラインで書いてください')
    if "area" in d:
        s.err("diagram.area は指定できません。描画領域は行数からエンジンが"
              "自動計算します")
    cols, rows = d.get("cols"), d.get("rows")
    for key, v in (("cols", cols), ("rows", rows)):
        if not (isinstance(v, list) and v and all(_is_str(c) for c in v)):
            s.err(f"diagram.{key} は文字列の配列 (1件以上) が必要です")
        elif len(set(v)) != len(v):
            s.err(f"diagram.{key} は重複しない名前にしてください")
    nodes = d.get("nodes")
    if not (isinstance(nodes, dict) and nodes):
        s.err("diagram.nodes (ノード名 → {col, row, title} のオブジェクト) が"
              "必要です")
        return
    for name, n in nodes.items():
        if not isinstance(n, dict):
            s.err(f"nodes.{name} はオブジェクトにしてください")
            continue
        s.allow_keys(n, {"col", "row", "title", "sub", "icon"},
                     f"diagram.nodes.{name}")
        if not _is_str(n.get("title")):
            s.err(f"nodes.{name}.title (文字列) が必要です")
        if "sub" in n and not _is_str(n["sub"]):
            s.err(f"nodes.{name}.sub は空でない文字列にしてください")
        if isinstance(cols, list) and n.get("col") not in cols:
            s.err(f"nodes.{name}.col={n.get('col')!r} が diagram.cols に"
                  f"ありません")
        if isinstance(rows, list) and n.get("row") not in rows:
            s.err(f"nodes.{name}.row={n.get('row')!r} が diagram.rows に"
                  f"ありません")
        if not _is_str(n.get("icon")):
            s.err(f"nodes.{name}.icon は必須です。CONTENT_SCHEMA.md の"
                  f"Fluent/AWSアイコン一覧から選んでください")
        else:
            try:
                icon_path = resolve_icon_path(n["icon"])
            except ValueError:
                s.err(f"nodes.{name}.icon は slidegen/assets/ 内の相対パスに"
                      f"してください")
            else:
                if not icon_path.is_file():
                    s.err(f"nodes.{name}.icon={n['icon']!r} が assets/ にありません。"
                          f"Fluent一覧は fetch_fluent_icons.py --list で確認してください")
    cont_names = set()
    containers = d.get("containers", [])
    if not isinstance(containers, list):
        s.err("diagram.containers は配列にしてください")
        containers = []
    for i, c in enumerate(containers):
        if not (isinstance(c, dict) and _is_str(c.get("name"))
                and _is_str(c.get("label")) and isinstance(c.get("members"), list)):
            s.err(f"containers[{i}] には name / label (文字列) と members (配列)"
                  f" が必要です")
            continue
        s.allow_keys(c, {"name", "label", "members", "color", "dash"},
                     f"diagram.containers[{i}]")
        if not c["members"] or not all(_is_str(member) for member in c["members"]):
            s.err(f"containers[{i}].members は1件以上の参照文字列にしてください")
        if c.get("color", "line") not in {"line", "navy", "accent"}:
            s.err(f"containers[{i}].color は line / navy / accent にしてください")
        if "dash" in c and c["dash"] != "dash":
            s.err(f'containers[{i}].dash は "dash" にしてください')
        for key in ("pad", "pad_x"):
            if key in c:
                s.err(f"containers[{i}].{key} は指定できません。余白は入れ子構造と"
                      "行数からエンジンが自動計算します")
        cont_names.add(c["name"])
    for i, c in enumerate(containers):
        for m in c.get("members", []):
            ref_ok = (m[1:] in cont_names if isinstance(m, str) and m.startswith("@")
                      else m in nodes)
            if not ref_ok:
                s.err(f"containers[{i}].members の {m!r} が nodes / @コンテナ名 "
                      f"に見つかりません")
    channels = d.get("channels", {})
    if not isinstance(channels, dict):
        s.err("diagram.channels はオブジェクトにしてください")
        channels = {}
    for name, ch in channels.items():
        if not _is_str(name):
            s.err("diagram.channels のキーは空でない文字列にしてください")
        if not (isinstance(ch, list) and len(ch) == 2
                and ch[0] in _CHANNEL_KINDS):
            s.err(f"channels.{name} は [種類, 基準] の2要素配列にしてください "
                  f"(種類: {', '.join(sorted(_CHANNEL_KINDS))})")
            continue
        kind, ref = ch
        if kind in {"left_of_col", "right_of_col"} and ref not in (cols or []):
            s.err(f"channels.{name} の基準 {ref!r} が diagram.cols にありません")
        elif kind in {"above_row", "below_row"} and ref not in (rows or []):
            s.err(f"channels.{name} の基準 {ref!r} が diagram.rows にありません")
        elif kind == "outside_container":
            valid_ref = (
                isinstance(ref, list) and len(ref) == 2
                and ref[1] in {"left", "right", "top", "bottom", "top_inside"}
                and (
                    (_is_str(ref[0]) and ref[0] in cont_names)
                    or (isinstance(ref[0], list) and ref[0]
                        and all(node in nodes for node in ref[0]))
                )
            )
            if not valid_ref:
                s.err(f"channels.{name} のoutside_container基準は "
                      "[コンテナ名またはノード名配列, 辺] にしてください")
    edges = d.get("edges")
    if not (isinstance(edges, list) and edges):
        s.err("diagram.edges ({from, to} の配列、1件以上) が必要です")
        return
    for i, e in enumerate(edges):
        if not isinstance(e, dict):
            s.err(f"edges[{i}] はオブジェクトにしてください")
            continue
        s.allow_keys(e, {
            "from", "to", "label", "exit", "enter", "via", "dash", "both",
            "from_row",
        }, f"diagram.edges[{i}]")
        for key in ("from", "to"):
            v = e.get(key)
            ref_ok = (v[1:] in cont_names if isinstance(v, str) and v.startswith("@")
                      else v in nodes)
            if not ref_ok:
                s.err(f"edges[{i}].{key}={v!r} が nodes / @コンテナ名 に"
                      f"見つかりません")
        for key in ("exit", "enter"):
            if key in e and e[key] not in _EDGE_SIDES:
                s.err(f"edges[{i}].{key} は {', '.join(sorted(_EDGE_SIDES))} の"
                      f"いずれかにしてください")
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
                s.err(f"edges[{i}].via の {v!r} が diagram.channels に"
                      f"ありません")
        source = e.get("from")
        if isinstance(source, str) and source.startswith("@"):
            if e.get("from_row") not in (rows or []):
                s.err(f"edges[{i}].from_row はコンテナ始点の接続行として"
                      "diagram.rowsから指定してください")
        elif "from_row" in e:
            s.err(f"edges[{i}].from_row はfromが@コンテナ名の場合だけ指定できます")


VALIDATORS = {
    "title": _v_title, "bullets": _v_bullets, "cards": _v_cards,
    "table": _v_table, "twocol": _v_twocol, "chart": _v_chart,
    "image": _v_image,
    "process": _v_process, "roadmap": _v_roadmap,
    "program_roadmap": _v_program_roadmap, "matrix": _v_matrix,
    "hub": _v_hub, "org": _v_org, "diagram": _v_diagram,
}


def validate(deck, *, allow_sample_content=False):
    """デッキ全体を検証し、エラーメッセージのリストを返す(空 = 合格)。

    allow_sample_content は回帰ギャラリー専用。通常のcontent.jsonでは指定しない。
    """
    errors = []
    if not isinstance(deck, dict):
        return ['トップレベルは "meta" と "slides" を持つオブジェクトにしてください']
    for key in _unknown_keys(deck, _TOP_LEVEL_KEYS):
        errors.append(
            f"{key}: 未対応のトップレベルフィールドです。meta / slidesだけを使用してください")
    for path in _placeholder_paths(deck):
        errors.append(
            f"{path}: <...> の入力欄が残っています。資料要件の値へ置き換えてください")
    for path in _unresolved_paths(deck):
        errors.append(
            f"{path}: 未確定マーカーが残っています。確定値へ置き換えるか、"
            "不要な任意フィールド・スライドを削除してください")
    if not allow_sample_content:
        for path, sample_text in sample_reuse_paths(deck):
            errors.append(
                f'{path}: 回帰検証サンプルの文言と一致します。資料要件と情報源から'
                f'新規作成してください (一致: "{sample_text}")')
    meta = deck.get("meta")
    if not isinstance(meta, dict):
        errors.append('トップレベルに "meta" (オブジェクト) が必要です')
    else:
        for key in _unknown_keys(meta, _META_KEYS):
            errors.append(
                f"meta.{key}: 未対応のフィールドです。"
                "CONTENT_SCHEMA.mdに記載されたフィールドだけを使用してください")
        if not _is_str(meta.get("title")):
            errors.append('meta.title (文字列) が必要です')
        for key in ("footer", "date", "organization", "author"):
            if key in meta and not _is_str(meta[key]):
                errors.append(
                    f'meta.{key} は指定する場合、空でない文字列にしてください')
    slides = deck.get("slides")
    if not (isinstance(slides, list) and slides):
        errors.append('トップレベルに "slides" (1件以上の配列) が必要です')
        return errors
    for idx, spec in enumerate(slides):
        if not isinstance(spec, dict):
            errors.append(f"slides[{idx}]: オブジェクトにしてください")
            continue
        s = _Slide(idx, spec, errors)
        t = spec.get("type")
        if t not in VALIDATORS:
            s.err(f"未対応のtypeです。使用可能: {', '.join(sorted(VALIDATORS))}")
            continue
        for key in _unknown_keys(spec, _TYPE_KEYS[t]):
            s.err(
                f"{key}: 未対応のフィールドです。"
                "CONTENT_SCHEMA.mdに記載されたフィールドだけを使用してください")
        if t != "title":
            s.req_str("kicker")
            s.req_str("title")
            if "lead" in spec and not _is_str(spec["lead"]):
                s.err('"lead" は空でない文字列にしてください')
        elif "lead" in spec:
            s.err('"lead" は表紙以外のスライドでのみ指定できます')
        if "note" in spec and t not in NOTE_TYPES:
            s.err(f'"note" は {", ".join(sorted(NOTE_TYPES))} でのみ描画され'
                  f"ます (このtypeでは無視されるため削除してください)")
        VALIDATORS[t](s)
    return errors


def main(json_path):
    deck = json.loads(Path(json_path).read_text(encoding="utf-8"))
    errors = validate(deck)
    if errors:
        print(f"NG: {json_path} に {len(errors)} 件の問題", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        raise SystemExit(1)
    print(f"OK: {json_path} ({len(deck['slides'])} slides) 検証通過")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "content.json")
