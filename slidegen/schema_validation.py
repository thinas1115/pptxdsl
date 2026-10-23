"""固定のローカルスキーマで構造を検証し、入力値を引用せず日本語で返す。"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol, cast

from jsonschema import Draft202012Validator, TypeChecker, ValidationError, validators
from jsonschema.protocols import Validator
from referencing import Registry

from slidegen.chart_model import finite_number
from slidegen.schema_definition import content_schema, slide_schemas, split_block_schemas


SCHEMA = content_schema()
SLIDE_SCHEMAS = slide_schemas()
# JSONのnumberは有限数だけ。Pythonのboolは整数のサブクラスだが整数として受理しない。
_TYPES = Draft202012Validator.TYPE_CHECKER.redefine_many(
    {
        "number": lambda _checker, value: finite_number(value),
        "integer": lambda _checker, value: isinstance(value, int) and not isinstance(value, bool),
    }
)


class _Extend(Protocol):
    # 公式APIの使用する引数だけを型付けする。外部stubのextend自体は未型付け。
    def __call__(
        self, validator: type[Validator], *, type_checker: TypeChecker
    ) -> type[Validator]: ...


_extend = cast(_Extend, validators.extend)
_Validator = _extend(Draft202012Validator, type_checker=_TYPES)
# retrieveを与えないRegistryは外部参照を取得しない。入力からスキーマを受け取らない。
_REGISTRY: Registry[Any] = Registry()
_ROOT = _Validator(SCHEMA, registry=_REGISTRY)
_ENVELOPE = _ROOT.evolve(
    schema={
        **SCHEMA,
        "properties": {**SCHEMA["properties"], "slides": {"type": "array", "minItems": 1}},
    }
)
_SLIDES = {
    name: _ROOT.evolve(schema={**schema, "$defs": SCHEMA["$defs"]})
    for name, schema in SLIDE_SCHEMAS.items()
}
_BLOCKS = split_block_schemas()


def _path(parts: Iterable[object]) -> str:
    result = ""
    for part in parts:
        result += f"[{part}]" if isinstance(part, int) else ("." if result else "") + str(part)
    return result


def _message(error: ValidationError) -> list[str]:
    path = _path(error.absolute_path)
    if not isinstance(error.schema, dict):
        return [f"{path}: この位置への値の追加はできません"]
    custom = error.schema.get(f"x-error-{error.validator}") or error.schema.get("x-error")
    if custom:
        return [f"{path}: {custom.format(limit=error.validator_value)}"]
    keyword = str(error.validator)
    # 固定スキーマのキーワードに対応する値。jsonschemaは未設定も表すUnset型を公開する。
    limit: Any = error.validator_value
    instance: Any = error.instance
    if keyword == "required":
        return [
            f'{path + "." if path else ""}{key} は必須フィールドです（"{key}"）'
            for key in limit
            if key not in instance
        ]
    if keyword == "additionalProperties":
        allowed = error.schema.get("properties", {})
        return [
            f"{path + '.' if path else ''}{key}: "
            + error.schema.get("x-unknown-messages", {}).get(
                key, error.schema.get("x-unknown-message", "未対応のフィールドです")
            )
            for key in sorted(instance)
            if key not in allowed
        ]
    if keyword == "type":
        types = {
            "object": "オブジェクト",
            "array": "配列",
            "string": "文字列",
            "number": "有限の数値（NaN・Infinity・真偽値は使用できません）",
            "integer": "整数（真偽値は使用できません）",
            "boolean": "真偽値（true または false）",
            "null": "null",
        }
        detail = f"{types.get(limit, limit)}にしてください"
    elif keyword in ("enum", "const"):
        choices = limit if keyword == "enum" else [limit]
        detail = " / ".join(str(value) for value in choices) + "のいずれかにしてください"
    elif keyword in ("minItems", "maxItems"):
        low, high = error.schema.get("minItems", 0), error.schema.get("maxItems")
        detail = (
            f"{low}〜{high}件の配列にしてください"
            if high is not None
            else f"{low}件以上の配列にしてください"
        )
    elif keyword in ("minProperties", "maxProperties"):
        detail = f"{limit}件{'以上' if keyword == 'minProperties' else '以下'}の項目にしてください"
    elif keyword == "uniqueItems":
        detail = "重複しない値にしてください"
    elif keyword in ("minimum", "maximum", "minLength", "maxLength"):
        unit = "文字" if keyword.endswith("Length") else ""
        direction = "以上" if keyword in ("minimum", "minLength") else "以下"
        detail = f"{limit}{unit}{direction}にしてください"
    elif keyword == "pattern":
        detail = (
            "空でない文字列にしてください" if limit == r"\S" else "定義された書式にしてください"
        )
    elif keyword in ("anyOf", "oneOf"):
        detail = "指定可能な形式のいずれかにしてください"
    elif keyword == "not":
        detail = "この組み合わせは指定できません"
    elif keyword == "dependentRequired":
        for key, dependencies in limit.items():
            if key in instance:
                missing = [name for name in dependencies if name not in instance]
                if missing:
                    return [
                        f"{path}: {key} を指定する場合は {' / '.join(missing)} も指定してください"
                    ]
        detail = "関連する必須項目も指定してください"
    elif keyword == "propertyNames":
        detail = "キーは空でない文字列にしてください"
    else:
        detail = "スキーマの構造条件を満たしていません"
    return [f"{path} は{detail}"]


def envelope_errors(value: Any) -> list[str]:
    return [message for error in _ENVELOPE.iter_errors(value) for message in _message(error)]


def slide_errors(value: dict[str, Any]) -> list[str]:
    kind = value.get("type")
    if not isinstance(kind, str) or kind not in _SLIDES:
        return [f"未対応のtypeです。使用可能: {', '.join(sorted(_SLIDES))}"]
    validator = _SLIDES[kind]
    if kind == "split":
        # typeが分かる子だけへ絞り、無関係な全分岐のエラーを利用者へ列挙しない。
        properties = dict(SLIDE_SCHEMAS[kind]["properties"])
        for side in ("left", "right"):
            block = value.get(side)
            block_kind = block.get("type") if isinstance(block, dict) else None
            if isinstance(block_kind, str) and block_kind in _BLOCKS:
                properties[side] = {"$ref": f"#/$defs/split_{block_kind}"}
        validator = validator.evolve(
            schema={**SLIDE_SCHEMAS[kind], "properties": properties, "$defs": SCHEMA["$defs"]}
        )
    return list(
        dict.fromkeys(
            message for error in validator.iter_errors(value) for message in _message(error)
        )
    )
