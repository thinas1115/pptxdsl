"""構成図の各節で異常な参照型を利用者向けエラーとして拒否する。"""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from slidegen.validate_content import validate


def deck():
    return {"meta": {"title": "構成図検証"}, "slides": [{
        "type": "diagram", "kicker": "分類", "title": "設備構成", "diagram": {
            "cols": ["a", "b"], "rows": ["r"],
            "nodes": {name: {"col": name, "row": "r", "title": "設備", "icon": "icons/fluent/wrench.png"}
                      for name in ("a", "b")},
            "containers": [{"name": "zone", "label": "領域", "members": ["a"]}],
            "channels": {"route": ["left_of_col", "a"]},
            "edges": [{"from": "a", "to": "b", "via": ["route"]}],
        },
    }]}


def invalid_cases():
    cases = [
        ("containers", [None]),
        ("containers", [{"name": "zone", "label": "領域", "members": [["a"]]}]),
        ("containers", [{"name": "zone", "label": "領域", "members": {"a": True}}]),
        ("containers", [{"name": "zone", "label": "領域", "members": ["a"], "color": []}]),
        ("channels", {"route": [["left_of_col"], "a"]}),
        ("channels", {"route": ["outside_container", ["zone", []]]}),
        ("channels", {"route": ["outside_container", [[["a"]], "left"]]}),
        ("channels", {"route": ["outside_container", [{"name": "zone"}, "left"]]}),
        ("edges", [{"from": [], "to": "b"}]),
        ("edges", [{"from": "a", "to": {"id": "b"}}]),
        ("edges", [{"from": "a", "to": "b", "exit": [], "enter": {}}]),
        ("edges", [{"from": "@zone", "to": "b", "from_row": ["r"]}]),
        ("cols", {"a": True}),
        ("rows", [["r"]]),
        ("nodes", {"a": []}),
    ]
    for key, value in cases:
        data = deck()
        data["slides"][0]["diagram"][key] = value
        yield key, data


class DiagramContractTests(unittest.TestCase):
    def test_normal_and_container_channel_references(self):
        data = deck()
        self.assertFalse(validate(data))
        diagram = data["slides"][0]["diagram"]
        diagram["containers"].append({"name": "outer", "label": "外部", "members": ["@zone", "b"]})
        diagram["channels"]["route"] = ["outside_container", ["outer", "top"]]
        diagram["edges"][0].update({"from": "@zone", "from_row": "r"})
        before = deepcopy(data)
        self.assertFalse(validate(data))
        self.assertEqual(data, before)

    def test_invalid_sections_return_errors_without_exception_or_mutation(self):
        for key, data in invalid_cases():
            with self.subTest(key=key, value=data):
                before = deepcopy(data)
                errors = validate(data)
                self.assertTrue(errors)
                self.assertTrue(all(message.startswith("slides[0] (type=diagram):") for message in errors))
                self.assertEqual(data, before)

    def test_bad_reference_cli_does_not_expose_traceback_or_paths(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / "invalid-diagram.json"
            data = deck()
            data["slides"][0]["diagram"]["containers"] = [None]
            source.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            for module in ("slidegen.validate_content", "slidegen.generate_from_json"):
                result = subprocess.run([sys.executable, "-m", module, str(source)],
                                        cwd=Path(__file__).resolve().parents[1],
                                        env=dict(os.environ, PYTHONIOENCODING="utf-8"),
                                        capture_output=True, encoding="utf-8", check=False)
                output = result.stdout + result.stderr
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("containers[0]", output)
                self.assertNotIn("Traceback", output)
                self.assertNotIn(directory, output)


if __name__ == "__main__":
    unittest.main()
