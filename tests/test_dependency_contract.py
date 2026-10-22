"""用途別依存と、最小環境でのSkill・Plugin隔離実行を検証する。"""
import importlib.util
from importlib.metadata import version
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
import zipfile

from tools.distribution.build import ROOT, build_plugin, build_skill
from tests.test_plugin_package import _run
from tests.test_pptxdsl_skill import _broken_local_links, _smoke_deck


def _pins(filename):
    result = {}
    for line in (ROOT / filename).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith(("#", "-r ")):
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+-]+)", line)
        if not match:
            raise AssertionError(f"固定されていない依存: {line}")
        name, pinned = match.groups()
        result[name] = pinned
    return result


class DependencyContractTests(unittest.TestCase):
    def test_dependency_groups_are_pinned_and_documented(self):
        runtime = _pins("requirements.txt")
        assets = _pins("requirements-assets.txt")
        quality = _pins("requirements-quality.txt")
        self.assertEqual(set(runtime), {"python-pptx", "Pillow", "lxml", "XlsxWriter", "typing_extensions"})
        self.assertEqual(len(assets), 9)
        self.assertFalse(runtime.keys() & assets.keys())
        self.assertFalse(_pins("requirements-dev.txt"))
        self.assertIn("-r requirements.txt", (ROOT / "requirements-assets.txt").read_text(encoding="utf-8"))
        self.assertIn("-r requirements-assets.txt", (ROOT / "requirements-dev.txt").read_text(encoding="utf-8"))
        self.assertIn("-r requirements-quality.txt", (ROOT / "requirements-dev.txt").read_text(encoding="utf-8"))
        self.assertEqual(set(quality), {"ruff", "mypy", "mypy_extensions", "pathspec", "typing_extensions", "coverage"})
        for name in runtime.keys() & quality.keys():
            self.assertEqual(runtime[name], quality[name], f"共通依存の固定値が不一致: {name}")
        document = ROOT / "docs/dependencies.md"
        text = document.read_text(encoding="utf-8")
        for name in (*runtime, *assets, *quality):
            self.assertIn(f"| {name} |", text)
        self.assertFalse(_broken_local_links(document))
        self.assertFalse(_broken_local_links(ROOT / "THIRD_PARTY_NOTICES.md"))

    @unittest.skipUnless(os.environ.get("PPTXDSL_RUNTIME_ONLY") == "1", "最小依存環境でのみ導入済みパッケージを厳密検査する")
    def test_minimal_environment_has_no_asset_dependencies(self):
        modules = ("reportlab", "svglib", "charset_normalizer", "cssselect2", "tinycss2",
                   "webencodings", "rlPyCairo", "cairo", "freetype", "ruff", "mypy",
                   "mypy_extensions", "pathspec", "coverage")
        for module in modules:
            self.assertIsNone(importlib.util.find_spec(module), f"開発専用依存が混入: {module}")
        for package, pinned in _pins("requirements.txt").items():
            self.assertEqual(version(package), pinned)

    def test_skill_and_plugin_use_only_runtime_requirements(self):
        with tempfile.TemporaryDirectory(prefix="pptxdsl-minimal-") as temporary:
            base = Path(temporary)
            for kind, build in (("skill", build_skill), ("plugin", build_plugin)):
                with self.subTest(kind=kind):
                    _, archive = build(base / (kind + "-build"))
                    installed = base / (kind + "-installed")
                    with zipfile.ZipFile(archive) as bundle:
                        self.assertFalse(any(Path(name).name in ("requirements-dev.txt", "requirements-assets.txt", "requirements-quality.txt")
                                             for name in bundle.namelist()))
                        bundle.extractall(installed)
                    skill = installed / ("pptxdsl" if kind == "skill" else "skills/pptxdsl")
                    project = skill / "project"
                    self.assertEqual((project / "requirements.txt").read_bytes(), (ROOT / "requirements.txt").read_bytes())
                    task = base / (kind + " task")
                    task.mkdir()
                    (task / "content.json").write_text(json.dumps(_smoke_deck(), ensure_ascii=False), encoding="utf-8")
                    runner = skill / "scripts/run.py"
                    _run(runner, task, "validate", "content.json")
                    _run(runner, task, "generate", "content.json", "out/deck.pptx")
                    _run(runner, task, "check", "out/deck.pptx")
                    for markdown in installed.rglob("*.md"):
                        self.assertFalse(_broken_local_links(markdown), markdown.name)


if __name__ == "__main__":
    unittest.main()
