"""backendが存在しても実変換できない環境を利用可と誤判定しない。"""
import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from PIL import Image

SCRIPT = Path(__file__).resolve().parents[1] / ".agents/skills/pptxdsl/scripts/render_preview.py"
spec = importlib.util.spec_from_file_location("render_probe_test", SCRIPT)
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)


class ProbeTests(unittest.TestCase):
    def test_installed_but_broken_impress_is_unavailable(self):
        def which(*names):
            return {"soffice": "soffice", "pdftoppm": "pdftoppm"}.get(names[0])

        with patch.object(renderer, "_which", side_effect=which), \
                patch.object(renderer, "_run", return_value=None):
            details = renderer.probe()
        self.assertFalse(details["libreoffice"]["available"])
        self.assertNotIn("libreoffice", details["available_backends"])
        self.assertIn("libreoffice-impress", details["libreoffice"]["reason"])

    def test_generated_png_is_required_and_temporary_files_are_removed(self):
        sources = []

        def render(source, output, width, slides, details):
            sources.append(source)
            output.mkdir()
            Image.new("RGB", (320, 180)).save(output / "slide_01.png")
            return 1

        with patch.object(renderer, "_render_libreoffice", side_effect=render):
            renderer._probe_conversion("libreoffice", {})
        self.assertFalse(sources[0].parent.exists())

    def test_powerpoint_failure_is_reported(self):
        with patch.object(renderer, "_render_powerpoint", side_effect=renderer.RenderError("COM")):
            with self.assertRaisesRegex(renderer.RenderError, "起動可能"):
                renderer._probe_conversion("powerpoint", {})

    def test_invalid_png_is_rejected(self):
        def render(source, output, width, slides, details):
            output.mkdir()
            (output / "slide_01.png").write_bytes(b"not a PNG")
            return 1

        with patch.object(renderer, "_render_libreoffice", side_effect=render):
            with self.assertRaises(renderer.RenderError):
                renderer._probe_conversion("libreoffice", {})

    def test_conversion_has_timeout(self):
        with patch.object(renderer.subprocess, "run", side_effect=subprocess.TimeoutExpired("office", 60)):
            with self.assertRaisesRegex(renderer.RenderError, "60秒"):
                renderer._run(["office"])

    def test_timeout_is_limited_to_probe_and_restored_on_failure(self):
        def broken_render(*args):
            renderer._run(["office"])

        with patch.object(renderer, "_render_libreoffice", side_effect=broken_render), \
                patch.object(renderer.subprocess, "run", side_effect=subprocess.TimeoutExpired("office", 60)) as run:
            with self.assertRaises(renderer.RenderError):
                renderer._probe_conversion("libreoffice", {})
            self.assertEqual(run.call_args.kwargs["timeout"], 60)
        with patch.object(renderer.subprocess, "run", return_value=subprocess.CompletedProcess("office", 0, "")) as run:
            renderer._run(["office"])
            self.assertIsNone(run.call_args.kwargs["timeout"])


if __name__ == "__main__":
    unittest.main()
