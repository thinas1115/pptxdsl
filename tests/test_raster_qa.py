"""PNG実画素の既知NGと、目視・PowerPoint確認の誤表示を検証する。"""
from copy import deepcopy
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, ImageDraw

from slidegen.raster_qa import inspect, main


def fixture(root):
    image = Image.new("RGB", (320, 160), "white")
    draw = ImageDraw.Draw(image)
    draw.text((40, 40), "Rendering QA", fill="#182C43")
    draw.line((40, 120, 260, 120), fill="#182C43", width=2)
    image.save(root / "slide_01.png")
    return {"version": 1, "backend": {"name": "libreoffice", "version": "test-fixture"},
            "pages": [{"png": "slide_01.png", "size": [320, 160], "checks": [
                {"id": "text", "kind": "ink_bounds", "region": [20, 20, 300, 80],
                 "bounds": [40, 40, 140, 60], "ink": "182C43"},
                {"id": "connection", "kind": "ink_presence", "region": [145, 118, 155, 123],
                 "ink": "182C43", "min_pixels": 10}]}]}


class RasterQATest(unittest.TestCase):
    def test_good_png_passes_without_claiming_visual_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = fixture(root)
            spec["visual_review"] = "passed"
            spec["human_approval"] = "approved"
            result = inspect(spec, root)
            self.assertEqual(result["automatic_status"], "passed")
            self.assertEqual(result["automatic_checks"], 2)
            self.assertEqual(result["visual_review"], "not_performed")
            self.assertEqual(result["powerpoint_visual_review"], "not_performed")
            self.assertEqual(result["human_approval"], "not_recorded")
            self.assertEqual(result["backend_declared"]["name"], "libreoffice")

    def test_known_text_outside_declared_box_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = fixture(root)
            # 実際の文字は変更せず、文字枠を短くして既知NGを作る。
            spec["pages"][0]["checks"][0]["bounds"][2] = 65
            result = inspect(spec, root)
            self.assertEqual(result["automatic_status"], "failed")
            self.assertIn("PNG-INK-OOB", {item["code"] for item in result["findings"]})

    def test_missing_connection_segment_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = fixture(root)
            with Image.open(root / "slide_01.png") as image:
                draw = ImageDraw.Draw(image)
                draw.rectangle((140, 118, 160, 124), fill="white")
                image.save(root / "slide_01.png")
            result = inspect(spec, root)
            self.assertIn("PNG-INK-MISSING", {item["code"] for item in result["findings"]})

    def test_size_inventory_and_no_checks_do_not_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = fixture(root)
            no_checks = deepcopy(spec)
            no_checks["pages"][0]["checks"] = []
            self.assertEqual(inspect(no_checks, root)["automatic_status"], "incomplete")
            spec["pages"][0]["size"] = [300, 160]
            self.assertEqual(inspect(spec, root)["findings"][0]["code"], "PNG-SIZE")
            Image.new("RGB", (320, 160), "white").save(root / "slide_02.png")
            self.assertIn("PNG-PAGES", {item["code"] for item in inspect(no_checks, root)["findings"]})

    def test_paths_outside_root_and_invalid_regions_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = fixture(root)
            for value in ("../other.png", "..\\other.png", "C:\\private\\other.png"):
                spec = deepcopy(original)
                spec["pages"][0]["png"] = value
                with self.assertRaises(ValueError):
                    inspect(spec, root)
            for box in ([0, 0, 321, 80], [10, 10, 9, 30], [False, 0, 20, 30]):
                spec = deepcopy(original)
                spec["pages"][0]["checks"][0]["region"] = box
                with self.assertRaises(ValueError):
                    inspect(spec, root)

    def test_cli_exit_report_and_safe_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = fixture(root)
            source, report = root / "qa.json", root / "report.json"
            source.write_text(json.dumps(spec), encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main([str(source), str(root), "--report", str(report)]), 0)
            self.assertEqual(json.loads(report.read_text(encoding="utf-8"))["findings"], [])
            source.write_text("{", encoding="utf-8")
            errors = io.StringIO()
            with redirect_stderr(errors):
                self.assertEqual(main([str(source), str(root), "--report", str(report)]), 2)
            self.assertNotIn(str(root), errors.getvalue())
            self.assertNotIn("Traceback", errors.getvalue())
            self.assertEqual(json.loads(report.read_text(encoding="utf-8"))["automatic_status"], "failed")

    def test_input_is_not_overwritten_by_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input.json"
            source.write_text("{}", encoding="utf-8")
            with redirect_stderr(io.StringIO()):
                self.assertEqual(main([str(source), str(root), "--report", str(source)]), 2)
            self.assertEqual(source.read_text(encoding="utf-8"), "{}")

    def test_skill_and_plugin_run_png_check_outside_repository(self):
        from tools.distribution.build import build_plugin, build_skill

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            work = root / "work"
            work.mkdir()
            manifest = work / "input.json"
            manifest.write_text(json.dumps(fixture(work)), encoding="utf-8")
            packages = [build_skill(root / "skill")[0],
                        build_plugin(root / "plugin")[0] / "skills/pptxdsl"]
            env = dict(os.environ, PYTHONPATH="", PYTHONIOENCODING="utf-8")
            for index, package in enumerate(packages):
                report = work / f"report-{index}.json"
                result = subprocess.run([sys.executable, "-I", str(package / "scripts/run.py"),
                                         "raster", "input.json", ".", "--report", report.name],
                                        cwd=work, env=env, capture_output=True, text=True, encoding="utf-8")
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(json.loads(report.read_text(encoding="utf-8"))["visual_review"], "not_performed")


if __name__ == "__main__":
    unittest.main()
