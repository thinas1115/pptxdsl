"""複数失敗・skip・最適化対策を実プロセスで確認する。"""
import os
import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tests.__main__ import run_cases


class RunnerTests(unittest.TestCase):
    def test_collects_all_failures_and_skip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tests = root / "tests"
            tests.mkdir()
            (tests / "__init__.py").touch()
            cases = []
            for name, code in (
                ("test_first", "raise RuntimeError('first failure')"),
                ("test_second", "assert False, 'second failure'"),
                ("test_last", "print('SKIP: optional-render: backendなし')"),
            ):
                path = tests / (name + ".py")
                path.write_text(code, encoding="utf-8")
                cases.append(path)
            with patch.dict(os.environ, {"PYTHONOPTIMIZE": "1"}), \
                    redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                records = run_cases(root, cases)
            self.assertEqual([r["status"] for r in records],
                             ["failed", "failed", "passed"])
            self.assertIn("first failure", records[0]["stderr"])
            self.assertIn("second failure", records[1]["stderr"])
            self.assertEqual(records[2]["skips"], ["optional-render: backendなし"])
            self.assertTrue(all(r["seconds"] >= 0 for r in records))

    def test_collects_unittest_decorator_and_dynamic_skip_reasons(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tests = root / "tests"
            tests.mkdir()
            (tests / "__init__.py").touch()
            case = tests / "test_unittest_skips.py"
            case.write_text(
                "import unittest\n"
                "class OptionalTests(unittest.TestCase):\n"
                "    @unittest.skip('可変フォント未指定')\n"
                "    def test_decorator(self): pass\n"
                "    def test_dynamic(self): self.skipTest('素材変換依存なし')\n"
                "if __name__ == '__main__': unittest.main()\n", encoding="utf-8")
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                records = run_cases(root, [case])
            self.assertEqual(records[0]["status"], "passed")
            skips = records[0]["skips"]
            self.assertEqual(len(skips), 2)
            self.assertTrue(any("test_decorator: 可変フォント未指定" in s for s in skips))
            self.assertTrue(any("test_dynamic: 素材変換依存なし" in s for s in skips))

    def test_optimized_entrypoint_refuses_to_run(self):
        result = subprocess.run([sys.executable, "-O", "-m", "tests"],
                                capture_output=True, encoding="utf-8",
                                env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("最適化を無効", result.stderr)


if __name__ == "__main__":
    unittest.main()
