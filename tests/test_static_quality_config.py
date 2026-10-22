"""ローカルとCIの検査対象・固定バージョンを保つ。検査ツール自体は専用環境で実行。"""
from pathlib import Path
import unittest

from tools.quality.static_gate import FORMATTED, static_commands


ROOT = Path(__file__).resolve().parents[1]


class StaticQualityConfigTests(unittest.TestCase):
    def test_fixed_tools_and_shared_entry(self):
        requirements = (ROOT / "requirements-quality.txt").read_text(encoding="utf-8")
        for package in ("ruff", "mypy", "coverage"):
            self.assertRegex(requirements, rf"(?m)^{package}==[0-9]+\.[0-9]+\.[0-9]+$")
            self.assertNotRegex((ROOT / "requirements.txt").read_text(encoding="utf-8"),
                                rf"(?m)^{package}==")
        workflow = (ROOT / ".github/workflows/quality-gate.yml").read_text(encoding="utf-8")
        self.assertIn("python -m tools.quality.static_gate --coverage", workflow)
        self.assertIn("requirements-quality.txt", workflow)
        self.assertEqual(len(static_commands()), 3)
        self.assertIn("slidegen", static_commands()[0])
        self.assertEqual(set(FORMATTED), {"slidegen/chart_model.py", "slidegen/layout_fit.py",
                                         "slidegen/layout_settings.py", "slidegen/network_layout.py",
                                         "slidegen/swimlane_layout.py", "slidegen/protocol_state_layout.py",
                                         "slidegen/timeline_layout.py", "slidegen/diagram_contract.py",
                                         "tools/quality/static_gate.py"})
        config = (ROOT / "mypy.ini").read_text(encoding="utf-8")
        for path in FORMATTED:
            if path.startswith("slidegen/"):
                self.assertIn(path, config)

    def test_coverage_collects_child_processes_and_stays_untracked(self):
        config = (ROOT / ".coveragerc").read_text(encoding="utf-8")
        for setting in ("branch = True", "parallel = True", "patch = subprocess",
                        "relative_files = True", "data_file = out/coverage/.coverage"):
            self.assertIn(setting, config)


if __name__ == "__main__":
    unittest.main()
