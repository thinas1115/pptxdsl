"""単一定義からの生成物、構造・意味の分離、外部参照禁止を検証する。"""

from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator

from slidegen.schema_definition import content_schema, slide_schemas
from slidegen.schema_validation import envelope_errors, slide_errors
from slidegen.validate_content import validate
from tools.schema.generate import ROOT, _fixture, artifacts


class ContentSchemaTests(unittest.TestCase):
    def test_schema_is_standard_and_uses_local_references_only(self):
        schema = content_schema()
        Draft202012Validator.check_schema(schema)

        def walk(value):
            if isinstance(value, dict):
                if "$ref" in value:
                    self.assertTrue(value["$ref"].startswith("#/$defs/"))
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(schema)
        self.assertEqual(schema, json.loads((ROOT / "schemas/content.schema.json").read_text(encoding="utf-8")))
        schema["$defs"].clear()
        self.assertTrue(content_schema()["$defs"], "呼び出し側による変更を共有しない")

    def test_all_generated_artifacts_match_definition(self):
        for name, expected in artifacts().items():
            with self.subTest(path=name):
                self.assertEqual((ROOT / name).read_text(encoding="utf-8"), expected)

    def test_structural_fixtures_cover_every_type(self):
        fixtures = json.loads((ROOT / "tests/fixtures/content-structure.json").read_text(encoding="utf-8"))
        definitions = slide_schemas()
        self.assertEqual({slide["type"] for slide in fixtures}, set(definitions))
        for slide in fixtures:
            with self.subTest(kind=slide["type"]):
                before = deepcopy(slide)
                self.assertFalse(slide_errors(slide))
                self.assertEqual(slide, before)
                for required in definitions[slide["type"]]["required"]:
                    invalid = deepcopy(slide)
                    del invalid[required]
                    self.assertTrue(slide_errors(invalid), required)
                self.assertTrue(slide_errors({**slide, "unknown": True}))

    def test_invalid_shapes_never_enter_semantic_layer(self):
        data = {"meta": {"title": "構造試験"}, "slides": [{
            "type": "diagram", "kicker": "試験", "title": "構成",
            "diagram": {"nodes": [], "edges": [{"from": [], "to": {}}]},
        }]}
        with patch("slidegen.validate_content.validate_semantics") as semantics:
            self.assertTrue(validate(data))
            semantics.assert_not_called()

    def test_structurally_valid_input_still_requires_semantic_validation(self):
        slide = {"type": "chart", "kicker": "試験", "title": "数量",
                 "chart": {"categories": ["区分"], "series": [["系列", [1, 2]]]}}
        self.assertFalse(slide_errors(slide))
        self.assertIn("同数", "\n".join(validate({"meta": {"title": "構造試験"}, "slides": [slide]})))

    def test_nested_bounds_enums_and_integer_types_come_from_schema(self):
        slide = {"type": "knowledge_check", "kicker": "試験", "title": "選択問題", "mode": "questions",
                 "questions": [{"question": "問題文", "options": ["甲", "乙"], "answer": 0, "explanation": "解説"}]}
        for value in (True, 0.0, "0", []):
            invalid = deepcopy(slide)
            invalid["questions"][0]["answer"] = value
            self.assertTrue(slide_errors(invalid))
        for value in ([], ["甲"], ["甲"] * 5):
            invalid = deepcopy(slide)
            invalid["questions"][0]["options"] = value
            self.assertTrue(slide_errors(invalid))
        self.assertTrue(slide_errors({**slide, "mode": "unsupported"}))
        self.assertTrue(envelope_errors({"meta": {"title": "資料"}, "slides": [], "extra": True}))

    def test_user_values_are_not_quoted_in_structure_errors(self):
        secret = "https://private.invalid/credential"
        slide = {"type": "image", "title": "資料", "kicker": "試験", "image": "assets.png", "fit": secret}
        self.assertNotIn(secret, "\n".join(slide_errors(slide)))

    def test_deeply_malformed_inputs_return_errors_without_mutation(self):
        fixtures = json.loads((ROOT / "tests/fixtures/content-structure.json").read_text(encoding="utf-8"))
        for slide in fixtures:
            for key in slide:
                for value in (None, [], {}, True, 1, ""):
                    invalid = deepcopy(slide)
                    invalid[key] = value
                    before = deepcopy(invalid)
                    data = {"meta": {"title": "構造試験"}, "slides": [invalid]}
                    with self.subTest(kind=slide["type"], key=key, value=value):
                        self.assertIsInstance(validate(data, allow_sample_content=True), list)
                        self.assertEqual(invalid, before)

    def test_every_declared_array_limit_is_checked_without_copied_thresholds(self):
        root = content_schema()
        checked = 0

        def walk(value, path=""):
            nonlocal checked
            if isinstance(value, dict):
                if value.get("type") == "array" and isinstance(value.get("items"), dict):
                    definition = {**value, "$defs": root["$defs"]}
                    validator = Draft202012Validator(definition)
                    sample = _fixture(value["items"], root)
                    low, high = value.get("minItems", 0), value.get("maxItems")
                    if low:
                        self.assertTrue(any(error.validator == "minItems" for error in validator.iter_errors([sample] * (low - 1))), path)
                        checked += 1
                    if high is not None:
                        self.assertTrue(any(error.validator == "maxItems" for error in validator.iter_errors([sample] * (high + 1))), path)
                        checked += 1
                for key, child in value.items():
                    walk(child, f"{path}/{key}")
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    walk(child, f"{path}/{index}")

        walk(root)
        self.assertGreater(checked, 70)


if __name__ == "__main__":
    unittest.main()
