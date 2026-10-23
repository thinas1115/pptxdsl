"""content.jsonの構造契約の正本。標準JSON Schemaと参照文書を同じ定義から作る。

参照先の存在、素材、タイトル方針など、値の意味はこの層では判定しない。
任意項目はoptional、必須項目はrequiredへ記載する。辞書の暗黙の共有変更を避ける。
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


Schema = dict[str, Any]
TEXT: Schema = {"type": "string", "pattern": r"\S"}
BOOL: Schema = {"type": "boolean"}
NUMBER: Schema = {"type": "number"}
INTEGER: Schema = {"type": "integer"}
NUMBER_FORMAT_PATTERN = r'(?:0|#,##0)(?:\.0{1,6})?(?:%|"[^"\\\r\n]{1,12}")?'
SPLIT_PAIRS = (("diagram", "cards"), ("image", "bullets"), ("chart", "table"), ("bullets", "cards"))


def enum(*values: str) -> Schema:
    return {"enum": list(values)}


def array(item: Schema, minimum: int = 0, maximum: int | None = None) -> Schema:
    result: Schema = {"type": "array", "items": item, "minItems": minimum}
    if maximum is not None:
        result["maxItems"] = maximum
    return result


def strings(minimum: int = 0, maximum: int | None = None) -> Schema:
    return array(TEXT, minimum, maximum)


def obj(required: Schema, optional: Schema | None = None) -> Schema:
    return {
        "type": "object",
        "properties": {**required, **(optional or {})},
        "required": list(required),
        "additionalProperties": False,
    }


def mapping(value: Schema, minimum: int = 0, maximum: int | None = None) -> Schema:
    result: Schema = {
        "type": "object",
        "propertyNames": TEXT,
        "additionalProperties": value,
        "minProperties": minimum,
    }
    if maximum is not None:
        result["maxProperties"] = maximum
    return result


def pair(first: Schema, second: Schema) -> Schema:
    return {
        "type": "array",
        "prefixItems": [first, second],
        "minItems": 2,
        "maxItems": 2,
        "items": False,
    }


def ref(name: str) -> Schema:
    return {"$ref": f"#/$defs/{name}"}


def _definitions() -> Schema:
    id_label = obj({"id": TEXT, "label": TEXT})
    edge = {"from": TEXT, "to": TEXT}
    forward = enum("forward", "feedback")
    node_style = enum("standard", "accent")
    image = obj({"image": TEXT}, {"label": TEXT, "alt": TEXT})
    position = {"anyOf": [NUMBER, TEXT]}
    resource = obj({"id": TEXT, "label": TEXT, "icon": TEXT}, {"sub": TEXT})
    return {
        "footnote": obj({"text": TEXT}, {"label": TEXT}),
        "title_nominal_review": obj({"title": TEXT, "reason": TEXT}),
        "bullet": {
            "anyOf": [obj({"text": TEXT}, {"checked": BOOL}), pair(TEXT, {"type": "null"})],
            "x-error": "text を持つオブジェクトにしてください（旧2要素配列は1.xのみ受理）",
        },
        "card": {
            **obj({"heading": TEXT, "body": TEXT}, {"value": TEXT, "emphasis": BOOL}),
            "x-error-type": "heading / bodyを持つオブジェクトにしてください",
        },
        "table_link": obj({"label": TEXT, "url": TEXT}),
        "column": obj({"heading": TEXT, "bullets": strings(1, 6)}, {"label": TEXT}),
        "chart": obj(
            {
                "categories": strings(1, 12),
                "series": array(pair(TEXT, array(NUMBER)), 1, 4),
            },
            {
                "kind": enum("bar", "column", "line", "stacked_bar", "stacked_column"),
                "show_legend": BOOL,
                "show_values": BOOL,
                "number_format": {"type": "string", "pattern": f"^(?:{NUMBER_FORMAT_PATTERN})$"},
            },
        ),
        "image_side": image,
        "process_step": {
            **obj(
                {"name": TEXT, "desc": TEXT},
                {
                    "actor": TEXT,
                    "attribute": obj({"label": TEXT, "value": TEXT}),
                },
            ),
            "not": {"required": ["actor", "attribute"]},
            "x-error-not": "actor と attribute を同時に指定できません",
        },
        "process_flow": obj(
            {
                "nodes": mapping(
                    obj(
                        {"name": TEXT},
                        {
                            "desc": TEXT,
                            "actor": TEXT,
                            "style": enum("standard", "accent", "decision"),
                        },
                    ),
                    2,
                    12,
                ),
                "levels": array(strings(1, 3), 2, 6),
                "edges": array(obj(edge, {"label": TEXT, "kind": forward}), 1, 20),
            }
        ),
        "roadmap_track": obj(
            {
                "name": TEXT,
                "activities": array(
                    obj(
                        {"label": TEXT, "start": position, "end": position},
                        {
                            "emph": BOOL,
                        },
                    ),
                    1,
                    8,
                ),
            },
            {"goal": TEXT, "milestone": obj({"at": position, "label": TEXT})},
        ),
        "matrix_point": obj(
            {
                "name": TEXT,
                "x": {**NUMBER, "minimum": 0, "maximum": 1},
                "y": {**NUMBER, "minimum": 0, "maximum": 1},
            },
            {"emph": BOOL},
        ),
        "paired_row": obj({"criterion": TEXT, "left": TEXT, "right": TEXT}),
        "mapping_item": obj({"id": TEXT, "text": TEXT}),
        "mapping_link": obj(edge, {"emphasis": BOOL}),
        "id_label": id_label,
        "swimlane_step": obj(
            {"id": TEXT, "name": TEXT, "lane": TEXT, "stage": TEXT},
            {
                "style": node_style,
                "number": {"anyOf": [{**INTEGER, "minimum": 1, "maximum": 99}, {"type": "null"}]},
            },
        ),
        "flow_edge": obj(edge, {"kind": forward}),
        "message": obj(
            {**edge, "id": TEXT, "label": TEXT},
            {
                "kind": enum("request", "return", "async"),
            },
        ),
        "message_phase": obj({**edge, "label": TEXT}),
        "concept_point": obj({"label": TEXT, "text": TEXT}),
        "reference": obj({"id": TEXT, "title": TEXT, "url": TEXT}, {"scope": TEXT}),
        "network_lane": obj({"id": TEXT, "label": TEXT}, {"sub": TEXT}),
        "network_node": obj(
            {
                "id": TEXT,
                "label": TEXT,
                "icon": TEXT,
                "column": TEXT,
                "lanes": {**strings(1), "uniqueItems": True},
            },
            {"sub": TEXT},
        ),
        "network_link": obj(
            edge,
            {
                "kind": enum("access", "trunk", "routed", "control", "broadcast", "blocked"),
                "lanes": {**strings(), "uniqueItems": True},
                "label": TEXT,
            },
        ),
        "protocol_stage": obj(
            {"id": TEXT, "label": TEXT, "icon": TEXT},
            {
                "role": enum("endpoint", "processor", "link"),
            },
        ),
        "protocol_flow": obj(
            {"label": TEXT, "states": array(ref("protocol_state"))}, {"sub": TEXT}
        ),
        "protocol_state": {
            **obj(
                {"stage": TEXT, "label": TEXT},
                {
                    "detail": TEXT,
                    "appearance": enum("plain", "encapsulated", "internal", "alert"),
                    "encapsulation": {**TEXT, "x-trimmed-maxLength": 8},
                },
            ),
            "if": {
                "properties": {"appearance": {"const": "encapsulated"}},
                "required": ["appearance"],
            },
            "then": {
                "required": ["encapsulation"],
                "x-error-required": "encapsulation はencapsulatedで必須です",
            },
            "else": {
                "not": {"required": ["encapsulation"]},
                "x-error-not": "encapsulation はappearance=encapsulatedでのみ指定できます",
            },
        },
        "frame": obj(
            {"label": TEXT, "fields": array(ref("frame_field"), 3, 9)},
            {
                "annotations": array(obj({"field": TEXT, "text": TEXT}), 0, 4),
            },
        ),
        "frame_field": obj(
            {
                "id": TEXT,
                "name": TEXT,
                "bits": {**INTEGER, "minimum": 1, "maximum": 65535},
            },
            {"size_label": TEXT, "role": enum("standard", "muted", "highlight", "alert")},
        ),
        "code_section": obj({"label": TEXT, "code": {**TEXT, "x-maxLines": 16}}),
        "question": obj(
            {
                "question": TEXT,
                "options": strings(2, 4),
                "answer": INTEGER,
                "explanation": TEXT,
            }
        ),
        "org": obj(
            {
                "nodes": mapping(
                    obj(
                        {"name": TEXT},
                        {
                            "sub": TEXT,
                            "members": strings(0, 4),
                            "style": enum("primary", "accent", "standard", "external"),
                        },
                    ),
                    1,
                ),
                "levels": array(strings(1, 5), 1, 6),
            },
            {
                "edges": array(
                    obj(
                        edge,
                        {
                            "kind": enum("reporting", "advice", "collaboration"),
                            "label": TEXT,
                        },
                    ),
                    0,
                    40,
                )
            },
        ),
        "diagram": obj(
            {
                "cols": {**strings(1), "uniqueItems": True},
                "rows": {**strings(1), "uniqueItems": True},
                "nodes": mapping(
                    obj(
                        {"col": TEXT, "row": TEXT, "title": TEXT, "icon": TEXT},
                        {
                            "sub": TEXT,
                            "service": TEXT,
                        },
                    ),
                    1,
                ),
                "edges": array(ref("diagram_edge"), 1),
            },
            {
                "containers": array(
                    obj(
                        {"name": TEXT, "label": TEXT, "members": strings(1)},
                        {
                            "color": enum("line", "navy", "accent"),
                            "dash": {"const": "dash"},
                        },
                    )
                ),
                "channels": mapping(ref("diagram_channel")),
            },
        ),
        "diagram_edge": obj(
            edge,
            {
                "label": TEXT,
                "exit": enum("left", "right", "top", "bottom"),
                "enter": enum("left", "right", "top", "bottom"),
                "via": strings(),
                "dash": {"const": "dash"},
                "both": BOOL,
                "from_row": TEXT,
            },
        ),
        "diagram_channel": {
            "anyOf": [
                pair(enum("left_of_col", "right_of_col", "above_row", "below_row"), TEXT),
                pair(
                    {"const": "outside_container"},
                    pair(
                        {"anyOf": [TEXT, strings(1)]},
                        enum("left", "right", "top", "bottom", "top_inside"),
                    ),
                ),
            ]
        },
        "vpc": obj({"label": TEXT}, {"cidr": TEXT}),
        "az": obj({"id": TEXT, "label": TEXT, "subnets": array(ref("subnet"), 1, 3)}),
        "subnet": obj(
            {"id": TEXT, "label": TEXT},
            {
                "cidr": TEXT,
                "resources": array(resource, 0, 2),
            },
        ),
        "resource": resource,
        "vpc_flow": obj(
            {key: {**TEXT, "x-error-type": "空でない参照文字列にしてください"} for key in edge},
            {"label": TEXT, "dash": {"const": "dash"}, "both": BOOL},
        ),
    }


def _slide_definitions() -> Schema:
    fit = enum("contain", "cover")
    definitions = {
        "title": obj({"subtitle": TEXT}),
        "section_divider": obj({}),
        "bullets": obj(
            {"bullets": array(ref("bullet"), 1, 6)},
            {
                "style": enum("numbered", "bullet", "checklist"),
            },
        ),
        "cards": obj({"cards": array(ref("card"), 2, 6)}, {"style": enum("editorial", "metrics")}),
        "table": obj(
            {"columns": strings(2, 8), "rows": array(array({"type": "string"}), 1, 8)},
            {
                "note": TEXT,
                "note_link": ref("table_link"),
            },
        ),
        "two_column": obj({"left": ref("column"), "right": ref("column")}),
        "chart": obj({"chart": ref("chart")}, {"note": TEXT}),
        "image": obj({"image": TEXT}, {"fit": fit, "shadow": BOOL, "alt": TEXT}),
        "image_compare": obj(
            {"left": ref("image_side"), "right": ref("image_side")},
            {
                "fit": fit,
                "shadow": BOOL,
            },
        ),
        "process": obj(
            {},
            {
                "steps": array(ref("process_step"), 3, 6),
                "flow": ref("process_flow"),
                "emph": array({**INTEGER, "minimum": 0}),
                "note": TEXT,
            },
        ),
        "program_roadmap": obj(
            {"periods": strings(3, 12), "tracks": array(ref("roadmap_track"), 1, 6)},
            {
                "note": TEXT,
            },
        ),
        "matrix": obj(
            {"x_axis": TEXT, "y_axis": TEXT, "points": array(ref("matrix_point"), 1, 8)},
            {
                "quadrants": strings(4, 4),
                "target_label": TEXT,
                "note": TEXT,
            },
        ),
        "scope_boundary": obj(
            {"in_scope": strings(1, 6), "out_of_scope": strings(1, 6)},
            {
                "in_label": TEXT,
                "out_label": TEXT,
            },
        ),
        "paired_comparison": obj(
            {
                "left_label": TEXT,
                "right_label": TEXT,
                "rows": array(ref("paired_row"), 2, 6),
            },
            {"criterion_label": TEXT},
        ),
        "relationship_map": obj(
            {
                "left_label": TEXT,
                "right_label": TEXT,
                "left_items": array(ref("mapping_item"), 2, 6),
                "right_items": array(ref("mapping_item"), 2, 6),
                "links": {
                    **array(ref("mapping_link"), 1, 10),
                    "x-error-maxItems": "対応線は1ページ{limit}本までです。論点ごとに分割してください",
                },
            }
        ),
        "swimlane_flow": obj(
            {
                "lanes": array(ref("id_label"), 2, 6),
                "stages": array(ref("id_label"), 2, 6),
                "steps": array(ref("swimlane_step"), 2, 14),
                "edges": array(ref("flow_edge"), 1, 20),
            }
        ),
        "message_sequence": obj(
            {
                "participants": array(ref("id_label"), 2, 6),
                "messages": array(ref("message"), 2, 12),
            },
            {"phases": array(ref("message_phase"), 0, 3)},
        ),
        "concept": obj(
            {
                "term": TEXT,
                "definition": TEXT,
                "icon": TEXT,
                "points": array(ref("concept_point"), 2, 4),
            }
        ),
        "references": obj({"references": array(ref("reference"), 1, 5)}),
        "nw_topology": obj(
            {
                "lanes": array(ref("network_lane"), 1, 4),
                "columns": array(ref("id_label"), 2, 6),
                "nodes": array(ref("network_node"), 2, 12),
                "links": array(ref("network_link"), 1, 18),
            }
        ),
        "nw_protocol_flow": obj(
            {
                "stages": array(ref("protocol_stage"), 3, 6),
                "flows": array(ref("protocol_flow"), 1, 3),
            }
        ),
        "nw_frame_anatomy": obj({"frames": array(ref("frame"), 1, 3)}),
        "config_lab": obj(
            {"sections": array(ref("code_section"), 1, 2), "checks": strings(2, 5)},
            {"check_label": TEXT},
        ),
        "knowledge_check": obj(
            {"mode": enum("questions", "answers"), "questions": array(ref("question"), 1, 3)}
        ),
        "org": obj({"org": ref("org")}, {"note": TEXT}),
        "diagram": obj({"diagram": ref("diagram")}, {"note": TEXT}),
        "aws_vpc_layout": obj(
            {"vpc": ref("vpc"), "azs": array(ref("az"), 1, 3)},
            {
                "external": array(ref("resource"), 0, 2),
                "flows": array(ref("vpc_flow"), 0, 10),
                "note": TEXT,
            },
        ),
        "split": obj({"left": ref("split_block"), "right": ref("split_block")}, {"note": TEXT}),
    }
    for name, schema in definitions.items():
        common_required = {"type": {"const": name}, "title": TEXT}
        common_optional = {
            "footnote": ref("footnote"),
            "title_nominal_review": ref("title_nominal_review"),
        }
        if name != "title":
            common_required["kicker"] = TEXT
            common_optional["lead"] = TEXT
        schema["properties"] = {**common_required, **common_optional, **schema["properties"]}
        schema["required"] = [*common_required, *schema["required"]]
    definitions["title"]["x-unknown-messages"] = {
        "lead": "lead は表紙以外のスライドでのみ指定できます"
    }
    definitions["process"]["oneOf"] = [
        {"required": ["steps"], "not": {"required": ["flow"]}},
        {"required": ["flow"], "not": {"anyOf": [{"required": ["steps"]}, {"required": ["emph"]}]}},
    ]
    definitions["process"]["x-error-oneOf"] = (
        "stepsまたはflowの一方を指定してください。process.flowと旧steps/emphは同時に指定できません"
    )
    definitions["matrix"]["anyOf"] = [{"required": ["quadrants"]}, {"required": ["target_label"]}]
    definitions["bullets"]["if"] = {
        "properties": {"style": {"const": "checklist"}},
        "required": ["style"],
    }
    definitions["bullets"]["else"] = {
        "properties": {
            "bullets": {
                "items": {
                    "if": {"type": "object"},
                    "then": {
                        "not": {"required": ["checked"]},
                        "x-error-not": "checked はstyle=checklistの場合だけ指定できます",
                    },
                }
            }
        }
    }
    definitions["cards"]["if"] = {
        "properties": {"style": {"const": "metrics"}},
        "required": ["style"],
    }
    definitions["cards"]["then"] = {"properties": {"cards": {"items": {"required": ["value"]}}}}
    definitions["cards"]["else"] = {
        "properties": {
            "cards": {
                "items": {
                    "not": {"required": ["emphasis"]},
                    "x-error-not": "emphasis はstyle=metricsの場合だけ指定できます",
                }
            }
        }
    }
    definitions["table"]["dependentRequired"] = {"note_link": ["note"]}
    definitions["program_roadmap"]["properties"]["periods"]["uniqueItems"] = True
    definitions["program_roadmap"]["x-maxActivities"] = 24
    pairs = [*SPLIT_PAIRS, *((right, left) for left, right in SPLIT_PAIRS)]
    definitions["split"]["anyOf"] = [
        {
            "properties": {
                "left": {"properties": {"type": {"const": left}}},
                "right": {"properties": {"type": {"const": right}}},
            }
        }
        for left, right in pairs
    ]
    definitions["split"]["x-error-anyOf"] = (
        "対応する組み合わせは "
        + " / ".join(f"{left} + {right}" for left, right in SPLIT_PAIRS)
        + " です（左右の逆順も指定可能）"
    )
    definitions["split"]["x-fixture-references"] = {
        side: f"#/$defs/split_{kind}" for side, kind in zip(("left", "right"), SPLIT_PAIRS[0])
    }
    return definitions


def split_block_schemas() -> dict[str, Schema]:
    """本文の契約は全幅版から導出し、共通ヘッダー・注記・再帰を子へ公開しない。"""
    definitions = _slide_definitions()
    kinds = dict.fromkeys(kind for pair in SPLIT_PAIRS for kind in pair)
    common = {"kicker", "title", "lead", "footnote", "title_nominal_review", "note", "note_link"}
    result = {}
    for kind in kinds:
        schema = deepcopy(definitions[kind])
        schema["properties"] = {
            key: value for key, value in schema["properties"].items() if key not in common
        }
        schema["required"] = [key for key in schema["required"] if key not in common]
        schema.pop("dependentRequired", None)
        result[kind] = schema
    return result


def content_schema() -> Schema:
    """呼び出し側が変更しても他の利用者へ影響しない、独立した標準スキーマ。"""
    definitions = _definitions()
    slides = _slide_definitions()
    blocks = split_block_schemas()
    definitions.update({f"split_{name}": schema for name, schema in blocks.items()})
    definitions["split_block"] = {
        "oneOf": [ref(f"split_{name}") for name in blocks],
        "x-error-oneOf": "対応する子typeと本文フィールドを指定してください。子の共通ヘッダー・注記やsplitの入れ子は指定できません",
        "x-reference-only": True,
        "x-display-type": "半幅の子本文: " + " / ".join(blocks),
    }
    definitions.update({f"slide_{name}": schema for name, schema in slides.items()})
    root = obj(
        {
            "meta": obj(
                {"title": TEXT},
                {"footer": TEXT, "date": TEXT, "organization": TEXT, "author": TEXT},
            ),
            "slides": array({"oneOf": [ref(f"slide_{name}") for name in slides]}, 1),
        }
    )
    root["x-unknown-message"] = (
        "未対応のトップレベルフィールドです。meta / slidesだけを使用してください"
    )
    return deepcopy(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://thinas1115.github.io/pptxdsl/content.schema.json",
            "title": "pptxdsl content.json",
            **root,
            "$defs": definitions,
        }
    )


def slide_schemas() -> dict[str, Schema]:
    return deepcopy(_slide_definitions())
