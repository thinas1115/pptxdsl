"""構造契約からJSON Schema・全フィールド表・構造試験入力を生成する。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from slidegen.schema_definition import Schema, content_schema, slide_schemas


ROOT = Path(__file__).resolve().parents[2]


def _dereference(schema: Schema, root: Schema) -> Schema:
    return root["$defs"][schema["$ref"].split("/")[-1]] if "$ref" in schema else schema


def _description(schema: Schema) -> str:
    if "const" in schema:
        return f'固定値 `{schema["const"]}`'
    if "enum" in schema:
        return " / ".join(f"`{value}`" for value in schema["enum"])
    names = {"object": "オブジェクト", "array": "配列", "string": "文字列", "number": "有限数", "integer": "整数", "boolean": "真偽値", "null": "null"}
    result = names.get(schema.get("type", ""), "複数形式")
    if schema.get("pattern") == r"\S":
        result = "空でない文字列"
    for low, high, unit in (("minItems", "maxItems", "件"), ("minProperties", "maxProperties", "項目"), ("minimum", "maximum", "")):
        if low in schema or high in schema:
            result += f"、{schema.get(low, '制限なし')}〜{schema.get(high, '制限なし')}{unit}"
    if schema.get("uniqueItems"):
        result += "、重複不可"
    if "pattern" in schema and schema["pattern"] != r"\S":
        result += "、書式はJSON Schemaのpatternを参照"
    return result


def _rows(schema: Schema, root: Schema, path: str = "") -> list[str]:
    schema = _dereference(schema, root)
    result = []
    for name, child in schema.get("properties", {}).items():
        field = f"{path}.{name}" if path else name
        resolved = _dereference(child, root)
        required = "必須" if name in schema.get("required", []) else "任意"
        result.append(f"| `{field}` | {required} | {_description(resolved)} |")
        result.extend(_rows(child, root, field))
    if schema.get("type") == "array":
        item = schema.get("items")
        if isinstance(item, dict):
            resolved = _dereference(item, root)
            result.append(f"| `{path}[]` | 各要素 | {_description(resolved)} |")
            result.extend(_rows(item, root, path + "[]"))
        for index, child in enumerate(schema.get("prefixItems", [])):
            result.append(f"| `{path}[{index}]` | 必須 | {_description(_dereference(child, root))} |")
            result.extend(_rows(child, root, f"{path}[{index}]"))
    additional = schema.get("additionalProperties")
    if isinstance(additional, dict):
        result.append(f"| `{path}.<id>` | 名前付き要素 | {_description(_dereference(additional, root))} |")
        result.extend(_rows(additional, root, path + ".<id>"))
    for keyword in ("anyOf", "oneOf"):
        for index, child in enumerate(schema.get(keyword, [])):
            result.extend(_rows(child, root, f"{path}（形式{index + 1}）"))
    return result


def _fixture(schema: Schema, root: Schema) -> Any:
    """意味的に妥当な資料ではなく、構造条件だけを試す最小入力。"""
    schema = _dereference(schema, root)
    if "const" in schema:
        return schema["const"]
    if "enum" in schema:
        return schema["enum"][0]
    if "anyOf" in schema and "type" not in schema:
        return _fixture(schema["anyOf"][0], root)
    kind = schema.get("type")
    if kind == "object":
        result = {name: _fixture(schema["properties"][name], root) for name in schema.get("required", [])}
        if isinstance(schema.get("additionalProperties"), dict):
            result.update({f"item{index}": _fixture(schema["additionalProperties"], root)
                           for index in range(schema.get("minProperties", 0))})
        if schema.get("oneOf"):
            for name in schema["oneOf"][0].get("required", []):
                result[name] = _fixture(schema["properties"][name], root)
        if schema.get("anyOf"):
            for name in schema["anyOf"][0].get("required", []):
                result[name] = _fixture(schema["properties"][name], root)
        return result
    if kind == "array":
        if "prefixItems" in schema:
            return [_fixture(item, root) for item in schema["prefixItems"]]
        result = [_fixture(schema["items"], root) for _ in range(schema.get("minItems", 0))]
        return [f"試験項目{index}" for index in range(len(result))] if schema.get("uniqueItems") else result
    if kind in ("integer", "number"):
        return schema.get("minimum", 0)
    return {"string": "構造試験専用", "boolean": False, "null": None}.get(kind)


def artifacts() -> dict[str, str]:
    schema, slides = content_schema(), slide_schemas()
    lines = [
        "# content.jsonの構造契約", "",
        "この文書は`slidegen/schema_definition.py`から自動生成する。直接編集しない。", "",
        "更新: `python -m tools.schema.generate`。整合検査: `python -m tools.schema.generate --check`。", "",
        "[標準JSON Schema](schemas/content.schema.json)はフィールド、型、必須項目、件数、選択肢の正本から生成する。",
        "表の必須・任意は直近の親オブジェクト内での指定。親自体が任意なら子も親を指定した場合に限る。",
        "追加キーは原則禁止。条件付き必須・排他的指定はJSON Schemaのif/then/else等を参照する。", "",
        "素材の実在、参照整合性、タイトル方針などは[意味検証と記述方針](docs/content-semantics.md)を参照する。",
        "typeの選び方は[type選択ガイド](docs/type-selection-guide.md)、入力例は[執筆用例](examples/authoring/README.md)を参照する。", "",
        "## 共通構造", "", "| フィールド | 指定 | 構造 |", "|---|---|---|",
    ]
    envelope = {**schema, "properties": {**schema["properties"], "slides": {"type": "array", "minItems": 1}}}
    lines.extend(_rows(envelope, schema))
    fixtures = []
    index_lines = ["<!-- BEGIN GENERATED CONTENT TYPES -->", "", "| type | 必須の固有フィールド |", "|---|---|"]
    for name, definition in slides.items():
        lines.extend(["", f"## {name}", "", "| フィールド | 指定 | 構造 |", "|---|---|---|"])
        lines.extend(_rows(definition, schema))
        fixtures.append(_fixture(definition, schema))
        required = [key for key in definition["required"] if key not in ("type", "title", "kicker")]
        index_lines.append(f"| `{name}` | {', '.join(f'`{key}`' for key in required) or 'なし（条件付き項目は構造契約を参照）'} |")
    index_lines.extend(["", "<!-- END GENERATED CONTENT TYPES -->"])
    return {
        "schemas/content.schema.json": json.dumps(schema, ensure_ascii=False, indent=2) + "\n",
        "CONTENT_SCHEMA.md": "\n".join(lines) + "\n",
        "tests/fixtures/content-structure.json": json.dumps(fixtures, ensure_ascii=False, indent=2) + "\n",
        "docs/content-type-index.md": "# AI向けtype一覧\n\n" + "\n".join(index_lines) + "\n",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="書き込まず生成結果との差を検査する")
    args = parser.parse_args()
    differences = []
    for relative, text in artifacts().items():
        path = ROOT / relative
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != text:
                differences.append(relative)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
    for path in differences:
        print(f"NG: スキーマ由来の生成物が不一致: {path}")
    if not differences:
        print("OK: スキーマ由来の4成果物が一致" if args.check else "OK: スキーマ由来の4成果物を更新")
    return bool(differences)


if __name__ == "__main__":
    raise SystemExit(main())
