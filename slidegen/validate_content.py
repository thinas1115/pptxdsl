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
from timeline_layout import resolve_marker, resolve_program_span

# noteを実際に描画するtype。それ以外への指定はエラーにする。
NOTE_TYPES = {"table", "chart", "process", "program_roadmap",
              "matrix", "org", "diagram"}
_PLACEHOLDER = re.compile(r"^<[^<>]+>$")
_UNRESOLVED = re.compile(r"^(?:TBD|TODO|要確認|未定|仮入力|仮文言)$", re.IGNORECASE)
_TITLE_SENTENCE_MARKS = re.compile(r"[、。！？!?；;]|\r|\n")
_TITLE_PREDICATE_ENDING = re.compile(
    r"(?:る|す|く|ぐ|む|ぶ|ぬ|つ|う|た|だ|ない|なかった|"
    r"できます|できる|できない|必要です|不要です)$"
)
_TITLE_ASSERTIVE_NOUN = re.compile(
    r"(?:を|が|は|では|には).*(?:短縮|削減|増加|減少|上昇|低下|改善|向上|"
    r"実現|確立|統一|明確化|可視化|最適化|自動化)$"
)
_TITLE_ASSERTIVE_QUALITY = re.compile(
    r"(?:が|は|では|には).*(?:重要|必要|不要|有効|無効|可能|不可能|最適|"
    r"優位|劣位|高い|低い|大きい|小さい|困難|容易|べき)$"
)

_TOP_LEVEL_KEYS = {"meta", "slides"}
_META_KEYS = {"title", "footer", "date", "organization", "author"}
_BASE_SLIDE_KEYS = {"type", "kicker", "title", "lead"}
_TYPE_KEYS = {
    "title": {"type", "title", "subtitle"},
    "bullets": _BASE_SLIDE_KEYS | {"style", "bullets"},
    "cards": _BASE_SLIDE_KEYS | {"style", "cards"},
    "table": _BASE_SLIDE_KEYS | {"columns", "rows", "note", "note_link"},
    "twocol": _BASE_SLIDE_KEYS | {"left", "right"},
    "chart": _BASE_SLIDE_KEYS | {"chart", "note"},
    "image": _BASE_SLIDE_KEYS | {"image", "fit", "shadow", "alt"},
    "process": _BASE_SLIDE_KEYS | {"steps", "emph", "flow", "note"},
    "program_roadmap": _BASE_SLIDE_KEYS | {"periods", "tracks", "note"},
    "matrix": _BASE_SLIDE_KEYS | {
        "x_axis", "y_axis", "points", "quadrants", "target_label", "note",
    },
    "org": _BASE_SLIDE_KEYS | {"org", "note"},
    "diagram": _BASE_SLIDE_KEYS | {"diagram", "note"},
    "scope": _BASE_SLIDE_KEYS | {
        "in_label", "out_label", "in_scope", "out_of_scope", "assumptions",
    },
    "summary": _BASE_SLIDE_KEYS | {
        "sections", "conclusion", "conclusion_label",
    },
    "paired_comparison": _BASE_SLIDE_KEYS | {
        "left_label", "right_label", "criterion_label", "rows", "takeaway",
    },
    "mapping": _BASE_SLIDE_KEYS | {
        "left_label", "right_label", "left_items", "right_items", "links",
        "takeaway",
    },
    "swimlane": _BASE_SLIDE_KEYS | {
        "lanes", "stages", "steps", "edges", "takeaway",
    },
    "sequence": _BASE_SLIDE_KEYS | {
        "participants", "messages", "phases", "takeaway",
    },
    "concept": _BASE_SLIDE_KEYS | {
        "term", "definition", "points", "misconception", "icon",
    },
    "network": _BASE_SLIDE_KEYS | {
        "lanes", "columns", "nodes", "links",
    },
    "protocol_state_flow": _BASE_SLIDE_KEYS | {
        "stages", "flows", "takeaway",
    },
    "protocol_anatomy": _BASE_SLIDE_KEYS | {
        "frames", "takeaway",
    },
    "code_lab": _BASE_SLIDE_KEYS | {
        "sections", "checks", "check_label", "takeaway",
    },
    "knowledge_check": _BASE_SLIDE_KEYS | {
        "mode", "questions",
    },
}


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _title_policy_error(value):
    """通常資料のページタイトルが、見出しではなく主張文なら理由を返す。"""
    if not _is_str(value):
        return None
    title = value.strip()
    if _TITLE_SENTENCE_MARKS.search(title):
        return "読点・句点・改行を含む文章"
    if _TITLE_PREDICATE_ENDING.search(title):
        return "文末が述語になっている文章"
    if _TITLE_ASSERTIVE_NOUN.search(title):
        return "結論や効果を言い切る文章"
    if _TITLE_ASSERTIVE_QUALITY.search(title):
        return "評価や必要性を言い切る文章"
    return None


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
    style = s.spec.get("style", "numbered")
    if style not in {"numbered", "bullet", "checklist"}:
        s.err('bullets.style は "numbered" / "bullet" / "checklist" にしてください')
    items = s.req_list("bullets", 1, 6, "項目")
    for i, item in enumerate(items or []):
        if isinstance(item, list):
            if not (len(item) == 2 and _is_str(item[0]) and item[1] is None):
                s.err(f"bullets[{i}] は text を持つオブジェクトにしてください")
            continue
        if not (isinstance(item, dict) and _is_str(item.get("text"))):
            s.err(f"bullets[{i}] は text を持つオブジェクトにしてください")
            continue
        s.allow_keys(item, {"text", "checked"}, f"bullets[{i}]")
        if "checked" in item:
            if style != "checklist":
                s.err(f"bullets[{i}].checked はstyle=checklistの場合だけ指定できます")
            elif not isinstance(item["checked"], bool):
                s.err(f"bullets[{i}].checked は真偽値にしてください")


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
    link = s.spec.get("note_link")
    if link is not None:
        if not isinstance(link, dict):
            s.err("note_link は label / url を持つオブジェクトにしてください")
        else:
            s.allow_keys(link, {"label", "url"}, "note_link")
            if not _is_str(link.get("label")):
                s.err("note_link.label は空でない文字列にしてください")
            if not (_is_str(link.get("url"))
                    and link["url"].startswith("https://")):
                s.err("note_link.url は https:// で始まるURLにしてください")
        if not _is_str(s.spec.get("note")):
            s.err("note_link を指定する場合は note も指定してください")


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
        s.allow_keys(track, {"name", "goal", "activities", "milestone"},
                     f"tracks[{i}]")
        if "goal" in track and not _is_str(track.get("goal")):
            s.err(f"tracks[{i}].goal は空でない文字列にしてください")
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
        milestone = track.get("milestone")
        if milestone is not None:
            if not (isinstance(milestone, dict)
                    and (_is_num(milestone.get("at"))
                         or _is_str(milestone.get("at")))
                    and _is_str(milestone.get("label"))):
                s.err(f"tracks[{i}].milestone には at (数値または期間ラベル) と "
                      "label (文字列) が必要です")
                continue
            s.allow_keys(milestone, {"at", "label"},
                         f"tracks[{i}].milestone")
            if periods:
                try:
                    marker = resolve_marker(milestone["at"], periods)
                except ValueError as exc:
                    s.err(f"tracks[{i}].milestone の{exc}")
                else:
                    steps = marker / 0.25
                    if abs(steps - round(steps)) > 1e-8:
                        s.err(f"tracks[{i}].milestone.at は0.25刻みの期間位置で"
                              "指定してください")
                    spans = []
                    for activity in activities:
                        try:
                            spans.append(resolve_program_span(activity, periods))
                        except (AttributeError, ValueError):
                            pass
                    if spans and not any(start <= marker <= end
                                         for start, end in spans):
                        s.err(f"tracks[{i}].milestone.at は同じテーマ内のいずれかの"
                              "作業期間内にしてください")
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


def _string_list(s, key, min_n, max_n):
    values = s.req_list(key, min_n, max_n, "空でない文字列")
    if values is not None and not all(_is_str(value) for value in values):
        s.err(f"{key} は空でない文字列の配列にしてください")
    return values or []


def _v_scope(s):
    _string_list(s, "in_scope", 1, 6)
    _string_list(s, "out_of_scope", 1, 6)
    for key in ("in_label", "out_label"):
        if key in s.spec and not _is_str(s.spec[key]):
            s.err(f"{key} は空でない文字列にしてください")
    if "assumptions" in s.spec:
        _string_list(s, "assumptions", 1, 4)


def _v_summary(s):
    sections = s.req_list("sections", 2, 4, "論点") or []
    for index, section in enumerate(sections):
        if not isinstance(section, dict):
            s.err(f"sections[{index}] はオブジェクトにしてください")
            continue
        s.allow_keys(section, {"heading", "body", "icon"}, f"sections[{index}]")
        for key in ("heading", "body"):
            if not _is_str(section.get(key)):
                s.err(f"sections[{index}].{key} は空でない文字列にしてください")
        if "icon" in section:
            if not _is_str(section["icon"]):
                s.err(f"sections[{index}].icon はFluentアイコン名にしてください")
            elif not resolve_icon_path(
                    f"icons/fluent/{section['icon']}.png").is_file():
                s.err(f"sections[{index}].icon={section['icon']!r} が見つかりません")
    if "conclusion" in s.spec and not _is_str(s.spec["conclusion"]):
        s.err("conclusion は空でない文字列にしてください")
    if "conclusion_label" in s.spec:
        if "conclusion" not in s.spec:
            s.err("conclusion_label はconclusionを指定した場合だけ使用できます")
        elif not _is_str(s.spec["conclusion_label"]):
            s.err("conclusion_label は空でない文字列にしてください")


def _v_paired_comparison(s):
    for key in ("left_label", "right_label"):
        s.req_str(key)
    if "criterion_label" in s.spec and not _is_str(s.spec["criterion_label"]):
        s.err("criterion_label は空でない文字列にしてください")
    rows = s.req_list("rows", 2, 6, "比較行") or []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            s.err(f"rows[{index}] はオブジェクトにしてください")
            continue
        s.allow_keys(row, {"criterion", "left", "right"}, f"rows[{index}]")
        for key in ("criterion", "left", "right"):
            if not _is_str(row.get(key)):
                s.err(f"rows[{index}].{key} は空でない文字列にしてください")
    if "takeaway" in s.spec and not _is_str(s.spec["takeaway"]):
        s.err("takeaway は空でない文字列にしてください")


def _mapping_items(s, key):
    items = s.req_list(key, 2, 6, "対応項目") or []
    ids = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            s.err(f"{key}[{index}] はオブジェクトにしてください")
            continue
        s.allow_keys(item, {"id", "text"}, f"{key}[{index}]")
        if not _is_str(item.get("id")) or not _is_str(item.get("text")):
            s.err(f"{key}[{index}] にはid / text (文字列) が必要です")
            continue
        if item["id"] in ids:
            s.err(f"{key}[{index}].id={item['id']!r} が重複しています")
        ids.add(item["id"])
    return ids


def _v_mapping(s):
    for key in ("left_label", "right_label"):
        s.req_str(key)
    left_ids = _mapping_items(s, "left_items")
    right_ids = _mapping_items(s, "right_items")
    links = s.req_list("links", 1, 10, "対応線") or []
    seen = set()
    for index, link in enumerate(links):
        if not isinstance(link, dict):
            s.err(f"links[{index}] はオブジェクトにしてください")
            continue
        s.allow_keys(link, {"from", "to", "emphasis"}, f"links[{index}]")
        source, target = link.get("from"), link.get("to")
        if source not in left_ids or target not in right_ids:
            s.err(f"links[{index}] がleft_items / right_itemsの未定義idを参照しています")
        if (source, target) in seen:
            s.err(f"links[{index}] の対応が重複しています")
        seen.add((source, target))
        if "emphasis" in link and not isinstance(link["emphasis"], bool):
            s.err(f"links[{index}].emphasis は真偽値にしてください")
    if "takeaway" in s.spec and not _is_str(s.spec["takeaway"]):
        s.err("takeaway は空でない文字列にしてください")


def _id_label_list(s, key, min_n, max_n):
    values = s.req_list(key, min_n, max_n, "id / labelを持つ項目") or []
    ids = set()
    for index, value in enumerate(values):
        if not isinstance(value, dict):
            s.err(f"{key}[{index}] はオブジェクトにしてください")
            continue
        s.allow_keys(value, {"id", "label"}, f"{key}[{index}]")
        if not _is_str(value.get("id")) or not _is_str(value.get("label")):
            s.err(f"{key}[{index}] にはid / label (文字列) が必要です")
            continue
        if value["id"] in ids:
            s.err(f"{key}[{index}].id={value['id']!r} が重複しています")
        ids.add(value["id"])
    return values, ids


def _v_swimlane(s):
    lanes, lane_ids = _id_label_list(s, "lanes", 2, 6)
    stages, stage_ids = _id_label_list(s, "stages", 2, 6)
    stage_index = {stage.get("id"): index for index, stage in enumerate(stages)}
    steps = s.req_list("steps", 2, 14, "工程") or []
    step_ids, cell_counts, step_stage, step_numbers = set(), {}, {}, set()
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            s.err(f"steps[{index}] はオブジェクトにしてください")
            continue
        s.allow_keys(step, {"id", "name", "lane", "stage", "style", "number"},
                     f"steps[{index}]")
        if not _is_str(step.get("id")) or not _is_str(step.get("name")):
            s.err(f"steps[{index}] にはid / name (文字列) が必要です")
            continue
        if step["id"] in step_ids:
            s.err(f"steps[{index}].id={step['id']!r} が重複しています")
        step_ids.add(step["id"])
        if step.get("lane") not in lane_ids or step.get("stage") not in stage_ids:
            s.err(f"steps[{index}] がlanes / stagesの未定義idを参照しています")
        cell = (step.get("lane"), step.get("stage"))
        cell_counts[cell] = cell_counts.get(cell, 0) + 1
        if cell_counts[cell] > 2:
            s.err(f"steps[{index}] と同じlane / stageには最大2工程までです")
        if step.get("style", "standard") not in {"standard", "accent"}:
            s.err(f"steps[{index}].style はstandard / accentにしてください")
        if "number" in step and step["number"] is not None:
            number = step["number"]
            if not isinstance(number, int) or isinstance(number, bool) or not 1 <= number <= 99:
                s.err(f"steps[{index}].number は1〜99の整数またはnullにしてください")
            elif number in step_numbers:
                s.err(f"steps[{index}].number={number} が重複しています")
            else:
                step_numbers.add(number)
        step_stage[step["id"]] = stage_index.get(step.get("stage"), -1)
    edges = s.req_list("edges", 1, 20, "工程接続") or []
    seen = set()
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            s.err(f"edges[{index}] はオブジェクトにしてください")
            continue
        s.allow_keys(edge, {"from", "to", "kind"}, f"edges[{index}]")
        source, target = edge.get("from"), edge.get("to")
        if source not in step_ids or target not in step_ids:
            s.err(f"edges[{index}] が未定義stepを参照しています")
            continue
        if source == target:
            s.err(f"edges[{index}] は同じ工程へ接続できません")
        if (source, target) in seen:
            s.err(f"edges[{index}] の接続が重複しています")
        seen.add((source, target))
        kind = edge.get("kind", "forward")
        if kind not in {"forward", "feedback"}:
            s.err(f"edges[{index}].kind はforward / feedbackにしてください")
        if step_stage.get(target, -1) < step_stage.get(source, -1) and kind != "feedback":
            s.err(f"edges[{index}] の前フェーズへの接続にはkind=feedbackが必要です")
    if "takeaway" in s.spec and not _is_str(s.spec["takeaway"]):
        s.err("takeaway は空でない文字列にしてください")


def _v_sequence(s):
    participants, participant_ids = _id_label_list(s, "participants", 2, 6)
    messages = s.req_list("messages", 2, 12, "メッセージ") or []
    message_ids = set()
    message_index = {}
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            s.err(f"messages[{index}] はオブジェクトにしてください")
            continue
        s.allow_keys(message, {"id", "from", "to", "label", "kind"},
                     f"messages[{index}]")
        if not _is_str(message.get("id")) or not _is_str(message.get("label")):
            s.err(f"messages[{index}] にはid / label (文字列) が必要です")
            continue
        if message["id"] in message_ids:
            s.err(f"messages[{index}].id={message['id']!r} が重複しています")
        message_ids.add(message["id"])
        message_index[message["id"]] = index
        if message.get("from") not in participant_ids or message.get("to") not in participant_ids:
            s.err(f"messages[{index}] が未定義participantを参照しています")
        if message.get("kind", "request") not in {"request", "return", "async"}:
            s.err(f"messages[{index}].kind はrequest / return / asyncにしてください")
    phases = s.spec.get("phases", [])
    if not isinstance(phases, list) or len(phases) > 3:
        s.err("phases は最大3件の配列にしてください")
        phases = []
    for index, phase in enumerate(phases):
        if not isinstance(phase, dict):
            s.err(f"phases[{index}] はオブジェクトにしてください")
            continue
        s.allow_keys(phase, {"label", "from", "to"}, f"phases[{index}]")
        if not _is_str(phase.get("label")):
            s.err(f"phases[{index}].label は空でない文字列にしてください")
        if phase.get("from") not in message_ids or phase.get("to") not in message_ids:
            s.err(f"phases[{index}] が未定義messageを参照しています")
        elif message_index[phase["from"]] > message_index[phase["to"]]:
            s.err(f"phases[{index}] はfromより後のmessageをtoへ指定してください")
    if "takeaway" in s.spec and not _is_str(s.spec["takeaway"]):
        s.err("takeaway は空でない文字列にしてください")


def _v_network(s):
    lanes = s.req_list("lanes", 1, 4, "id / labelを持つ論理セグメント") or []
    lane_ids = set()
    for index, lane in enumerate(lanes):
        if not isinstance(lane, dict):
            s.err(f"lanes[{index}] はオブジェクトにしてください")
            continue
        s.allow_keys(lane, {"id", "label", "sub"}, f"lanes[{index}]")
        if not _is_str(lane.get("id")) or not _is_str(lane.get("label")):
            s.err(f"lanes[{index}] にはid / label (文字列) が必要です")
            continue
        if lane["id"] in lane_ids:
            s.err(f"lanes[{index}].id={lane['id']!r} が重複しています")
        lane_ids.add(lane["id"])
        if "sub" in lane and not _is_str(lane["sub"]):
            s.err(f"lanes[{index}].sub は空でない文字列にしてください")
    columns, column_ids = _id_label_list(s, "columns", 2, 6)
    for index, column in enumerate(columns):
        s.allow_keys(column, {"id", "label"}, f"columns[{index}]")

    nodes = s.req_list("nodes", 2, 12, "ネットワーク機器") or []
    node_ids = set()
    node_lanes = {}
    placements = {}
    for index, node in enumerate(nodes):
        path = f"nodes[{index}]"
        if not isinstance(node, dict):
            s.err(f"{path} はオブジェクトにしてください")
            continue
        s.allow_keys(node, {"id", "label", "sub", "icon", "column", "lanes"}, path)
        if not _is_str(node.get("id")) or not _is_str(node.get("label")):
            s.err(f"{path} にはid / label (文字列) が必要です")
            continue
        if node["id"] in node_ids:
            s.err(f"{path}.id={node['id']!r} が重複しています")
        node_ids.add(node["id"])
        if node.get("column") not in column_ids:
            s.err(f"{path}.column がcolumnsの未定義idを参照しています")
        memberships = node.get("lanes")
        if not (isinstance(memberships, list) and memberships
                and all(lane in lane_ids for lane in memberships)
                and len(set(memberships)) == len(memberships)):
            s.err(f"{path}.lanes はlanesのidを1件以上、重複なしで指定してください")
            memberships = []
        node_lanes[node["id"]] = set(memberships)
        if node.get("column") in column_ids and memberships:
            placement = (node["column"], tuple(sorted(memberships)))
            placements.setdefault(placement, []).append(path)
        if "sub" in node and not _is_str(node["sub"]):
            s.err(f"{path}.sub は空でない文字列にしてください")
        if not _is_str(node.get("icon")):
            s.err(f"{path}.icon は必須です")
        else:
            try:
                icon_path = resolve_icon_path(node["icon"])
            except ValueError:
                s.err(f"{path}.icon は slidegen/assets/ 内の相対パスにしてください")
            else:
                if not icon_path.is_file():
                    s.err(f"{path}.icon={node['icon']!r} がassets/にありません")

    for placement, paths in placements.items():
        if len(paths) > 2:
            column, memberships = placement
            s.err(
                f"nodes: column={column!r}, lanes={list(memberships)!r} には"
                "2件まで配置できます。列を追加するかスライドを分割してください")

    links = s.req_list("links", 1, 18, "ネットワーク接続") or []
    seen = set()
    for index, link in enumerate(links):
        path = f"links[{index}]"
        if not isinstance(link, dict):
            s.err(f"{path} はオブジェクトにしてください")
            continue
        s.allow_keys(link, {"from", "to", "kind", "lanes", "label"}, path)
        source, target = link.get("from"), link.get("to")
        if source not in node_ids or target not in node_ids:
            s.err(f"{path} が未定義nodeを参照しています")
        if source == target:
            s.err(f"{path} は同じnodeへ接続できません")
        pair = tuple(sorted((source, target))) if source and target else (source, target)
        if pair in seen:
            s.err(f"{path} の接続が向きを問わず重複しています")
        seen.add(pair)
        kind = link.get("kind", "access")
        if kind not in {"access", "trunk", "routed", "control", "broadcast", "blocked"}:
            s.err(
                f"{path}.kind はaccess / trunk / routed / control / broadcast / blockedにしてください"
            )
        memberships = link.get("lanes", [])
        if not (isinstance(memberships, list)
                and all(lane in lane_ids for lane in memberships)
                and len(set(memberships)) == len(memberships)):
            s.err(f"{path}.lanes はlanesのidを重複なしで指定してください")
            memberships = []
        if kind == "trunk" and len(memberships) < 2:
            s.err(f"{path}: trunkは運ぶlanesを2件以上指定してください")
        if kind in {"access", "broadcast", "blocked"} and len(memberships) != 1:
            s.err(f"{path}: {kind}のlanesは1件指定してください")
        if kind == "blocked" and source in node_lanes and target in node_lanes:
            unavailable = [
                lane for lane in memberships
                if lane not in node_lanes[source] or lane in node_lanes[target]
            ]
            if unavailable:
                s.err(
                    f"{path}.lanes={unavailable!r} は接続元だけが所属し、"
                    "接続先が所属しないlaneを指定してください")
        elif source in node_lanes and target in node_lanes:
            unavailable = [
                lane for lane in memberships
                if lane not in node_lanes[source] or lane not in node_lanes[target]
            ]
            if unavailable:
                s.err(
                    f"{path}.lanes={unavailable!r} は接続元・接続先の"
                    "双方に所属するlaneを指定してください")
        if "label" in link and not _is_str(link["label"]):
            s.err(f"{path}.label は空でない文字列にしてください")


def _v_concept(s):
    for key in ("term", "definition"):
        if not _is_str(s.spec.get(key)):
            s.err(f"{key} は空でない文字列にしてください")
    points = s.req_list("points", 2, 4, "概念の要点") or []
    for index, point in enumerate(points):
        path = f"points[{index}]"
        if not isinstance(point, dict):
            s.err(f"{path} はオブジェクトにしてください")
            continue
        s.allow_keys(point, {"label", "text"}, path)
        if not _is_str(point.get("label")) or not _is_str(point.get("text")):
            s.err(f"{path} にはlabel / text (文字列) が必要です")
    if "misconception" in s.spec and not _is_str(s.spec["misconception"]):
        s.err("misconception は空でない文字列にしてください")
    if "icon" in s.spec:
        if not _is_str(s.spec["icon"]):
            s.err("icon は空でない文字列にしてください")
        else:
            try:
                icon_path = resolve_icon_path(s.spec["icon"])
            except ValueError:
                s.err("icon は slidegen/assets/ 内の相対パスにしてください")
            else:
                if not icon_path.is_file():
                    s.err(f"icon={s.spec['icon']!r} がassets/にありません")


def _v_protocol_state_flow(s):
    stages = s.req_list("stages", 3, 6, "処理段階") or []
    stage_ids = set()
    for index, stage in enumerate(stages):
        path = f"stages[{index}]"
        if not isinstance(stage, dict):
            s.err(f"{path} はオブジェクトにしてください")
            continue
        s.allow_keys(stage, {"id", "label", "icon", "role"}, path)
        if not _is_str(stage.get("id")) or not _is_str(stage.get("label")):
            s.err(f"{path} にはid / label (文字列) が必要です")
            continue
        if stage["id"] in stage_ids:
            s.err(f"{path}.id={stage['id']!r} が重複しています")
        stage_ids.add(stage["id"])
        if stage.get("role", "processor") not in {"endpoint", "processor", "link"}:
            s.err(f"{path}.role はendpoint / processor / linkにしてください")
        if not _is_str(stage.get("icon")):
            s.err(f"{path}.icon は必須です")
        else:
            try:
                icon_path = resolve_icon_path(stage["icon"])
            except ValueError:
                s.err(f"{path}.icon は slidegen/assets/ 内の相対パスにしてください")
            else:
                if not icon_path.is_file():
                    s.err(f"{path}.icon={stage['icon']!r} がassets/にありません")

    flows = s.req_list("flows", 1, 3, "状態を追うフロー") or []
    flow_labels = set()
    for flow_index, flow in enumerate(flows):
        path = f"flows[{flow_index}]"
        if not isinstance(flow, dict):
            s.err(f"{path} はオブジェクトにしてください")
            continue
        s.allow_keys(flow, {"label", "sub", "states"}, path)
        if not _is_str(flow.get("label")):
            s.err(f"{path}.label は空でない文字列にしてください")
        else:
            normalized_label = flow["label"].strip()
            if normalized_label in flow_labels:
                s.err(f"{path}.label={flow['label']!r} が重複しています")
            flow_labels.add(normalized_label)
        if "sub" in flow and not _is_str(flow["sub"]):
            s.err(f"{path}.sub は空でない文字列にしてください")
        states = flow.get("states")
        if not isinstance(states, list):
            s.err(f"{path}.states はstagesと同数の配列にしてください")
            continue
        seen_stages = set()
        for state_index, state in enumerate(states):
            state_path = f"{path}.states[{state_index}]"
            if not isinstance(state, dict):
                s.err(f"{state_path} はオブジェクトにしてください")
                continue
            s.allow_keys(state, {
                "stage", "label", "detail", "appearance", "encapsulation",
            },
                         state_path)
            stage_id = state.get("stage")
            if stage_id not in stage_ids:
                s.err(f"{state_path}.stage が未定義stageを参照しています")
            elif stage_id in seen_stages:
                s.err(f"{state_path}.stage={stage_id!r} が重複しています")
            seen_stages.add(stage_id)
            if not _is_str(state.get("label")):
                s.err(f"{state_path}.label は空でない文字列にしてください")
            if "detail" in state and not _is_str(state["detail"]):
                s.err(f"{state_path}.detail は空でない文字列にしてください")
            appearance = state.get("appearance", "plain")
            if appearance not in {
                    "plain", "encapsulated", "internal", "alert"}:
                s.err(
                    f"{state_path}.appearance はplain / encapsulated / "
                    "internal / alertにしてください")
            encapsulation = state.get("encapsulation")
            if appearance == "encapsulated":
                if not _is_str(encapsulation):
                    s.err(
                        f"{state_path}.encapsulation はencapsulatedで必須です")
                elif len(encapsulation.strip()) > 8:
                    s.err(f"{state_path}.encapsulation は8文字以内にしてください")
            elif "encapsulation" in state:
                s.err(
                    f"{state_path}.encapsulation はappearance=encapsulatedでのみ指定できます")
        if len(states) != len(stages) or seen_stages != stage_ids:
            s.err(
                f"{path}.states は全stageを1件ずつ指定してください "
                f"(期待={len(stages)}件, 実際={len(states)}件)")
    if "takeaway" in s.spec and not _is_str(s.spec["takeaway"]):
        s.err("takeaway は空でない文字列にしてください")


def _v_protocol_anatomy(s):
    frames = s.req_list("frames", 1, 3, "フレームまたはパケット") or []
    for frame_index, frame in enumerate(frames):
        path = f"frames[{frame_index}]"
        if not isinstance(frame, dict):
            s.err(f"{path} はオブジェクトにしてください")
            continue
        s.allow_keys(frame, {"label", "fields", "annotations"}, path)
        if not _is_str(frame.get("label")):
            s.err(f"{path}.label は空でない文字列にしてください")
        fields = frame.get("fields")
        if not (isinstance(fields, list) and 3 <= len(fields) <= 9):
            s.err(f"{path}.fields は3〜9件の配列にしてください")
            fields = []
        field_ids = set()
        for field_index, field in enumerate(fields):
            field_path = f"{path}.fields[{field_index}]"
            if not isinstance(field, dict):
                s.err(f"{field_path} はオブジェクトにしてください")
                continue
            s.allow_keys(field, {"id", "name", "bits", "size_label", "role"},
                         field_path)
            if not _is_str(field.get("id")) or not _is_str(field.get("name")):
                s.err(f"{field_path} にはid / name (文字列) が必要です")
                continue
            if field["id"] in field_ids:
                s.err(f"{field_path}.id={field['id']!r} が重複しています")
            field_ids.add(field["id"])
            if not isinstance(field.get("bits"), int) or isinstance(field.get("bits"), bool) \
                    or not 1 <= field["bits"] <= 65535:
                s.err(f"{field_path}.bits は1〜65535の整数にしてください")
            if "size_label" in field and not _is_str(field["size_label"]):
                s.err(f"{field_path}.size_label は空でない文字列にしてください")
            if field.get("role", "standard") not in {
                    "standard", "muted", "highlight", "alert"}:
                s.err(f"{field_path}.role はstandard / muted / highlight / alertにしてください")
        annotations = frame.get("annotations", [])
        if not isinstance(annotations, list) or len(annotations) > 4:
            s.err(f"{path}.annotations は最大4件の配列にしてください")
            annotations = []
        for annotation_index, annotation in enumerate(annotations):
            annotation_path = f"{path}.annotations[{annotation_index}]"
            if not isinstance(annotation, dict):
                s.err(f"{annotation_path} はオブジェクトにしてください")
                continue
            s.allow_keys(annotation, {"field", "text"}, annotation_path)
            if annotation.get("field") not in field_ids or not _is_str(annotation.get("text")):
                s.err(f"{annotation_path} には定義済みfieldとtextが必要です")
    if "takeaway" in s.spec and not _is_str(s.spec["takeaway"]):
        s.err("takeaway は空でない文字列にしてください")


def _v_code_lab(s):
    sections = s.req_list("sections", 1, 2, "コード区画") or []
    for index, section in enumerate(sections):
        path = f"sections[{index}]"
        if not isinstance(section, dict):
            s.err(f"{path} はオブジェクトにしてください")
            continue
        s.allow_keys(section, {"label", "code"}, path)
        if not _is_str(section.get("label")) or not _is_str(section.get("code")):
            s.err(f"{path} にはlabel / code (文字列) が必要です")
        elif len(section["code"].splitlines()) > 16:
            s.err(f"{path}.code は16行以内にしてください")
    _string_list(s, "checks", 2, 5)
    for key in ("check_label", "takeaway"):
        if key in s.spec and not _is_str(s.spec[key]):
            s.err(f"{key} は空でない文字列にしてください")


def _v_knowledge_check(s):
    if s.spec.get("mode") not in {"questions", "answers"}:
        s.err("mode はquestions / answersにしてください")
    questions = s.req_list("questions", 1, 3, "設問") or []
    for index, question in enumerate(questions):
        path = f"questions[{index}]"
        if not isinstance(question, dict):
            s.err(f"{path} はオブジェクトにしてください")
            continue
        s.allow_keys(question, {"question", "options", "answer", "explanation"}, path)
        if not _is_str(question.get("question")):
            s.err(f"{path}.question は空でない文字列にしてください")
        options = question.get("options")
        if not (isinstance(options, list) and 2 <= len(options) <= 4
                and all(_is_str(option) for option in options)):
            s.err(f"{path}.options は2〜4件の文字列配列にしてください")
            options = []
        answer = question.get("answer")
        if not isinstance(answer, int) or isinstance(answer, bool) \
                or not 0 <= answer < len(options):
            s.err(f"{path}.answer はoptionsの0始まりindexにしてください")
        if not _is_str(question.get("explanation")):
            s.err(f"{path}.explanation は空でない文字列にしてください")


VALIDATORS = {
    "title": _v_title, "bullets": _v_bullets, "cards": _v_cards,
    "table": _v_table, "twocol": _v_twocol, "chart": _v_chart,
    "image": _v_image,
    "process": _v_process, "program_roadmap": _v_program_roadmap,
    "matrix": _v_matrix,
    "org": _v_org, "diagram": _v_diagram,
    "scope": _v_scope, "summary": _v_summary,
    "paired_comparison": _v_paired_comparison, "mapping": _v_mapping,
    "swimlane": _v_swimlane, "sequence": _v_sequence,
    "concept": _v_concept, "network": _v_network,
    "protocol_state_flow": _v_protocol_state_flow,
    "protocol_anatomy": _v_protocol_anatomy,
    "code_lab": _v_code_lab, "knowledge_check": _v_knowledge_check,
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
        if not allow_sample_content:
            title_error = _title_policy_error(spec.get("title"))
            if title_error:
                s.err(
                    f'"title" は名詞句または短い疑問形の見出しにしてください '
                    f"({title_error})。結論・因果・行動はsubtitle、leadまたは本文へ移してください")
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
