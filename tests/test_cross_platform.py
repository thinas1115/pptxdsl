"""クロス環境記録の欠落・改変を拒否し、全デッキの失敗を収集する。"""
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.quality import cross_platform as c


class CrossPlatformTests(unittest.TestCase):
    def test_build_collects_all_failed_decks_and_environment(self):
        failed = subprocess.CompletedProcess([], 1, "private diagnostic", "private diagnostic")
        metadata = {"rendering": "not_performed", "powerpoint": {"status": "not_probed"}}
        # このテストの対象は5 generatorの失敗収集。Office/fontconfig探索まで
        # subprocessモックへ巻き込み、OSごとの探索回数・成否に依存させない。
        with TemporaryDirectory() as temporary, \
                patch.object(c.subprocess, "run", return_value=failed) as run, \
                patch.object(c, "environment", return_value=metadata), \
                patch.object(c, "describe", return_value={}), \
                patch.object(c, "font_face", return_value=None), \
                patch.object(c, "_font_identity", return_value={}):
            with self.assertRaisesRegex(ValueError, "主要デッキ"):
                c.build(Path(temporary))
            report = json.loads((Path(temporary) / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(run.call_count, len(c.DECKS))
        self.assertEqual([item["name"] for item in report["decks"]], list(c.DECKS))
        self.assertTrue(all(item["status"] == "failed" for item in report["decks"]))
        self.assertNotIn("private diagnostic", json.dumps(report))
        self.assertEqual(report["environment"]["rendering"], "not_performed")
        self.assertEqual(report["environment"]["powerpoint"]["status"], "not_probed")

    def test_compare_rejects_missing_or_failed_deck_baselines(self):
        with TemporaryDirectory() as temporary:
            source = Path(temporary)
            for records in ([], [{"name": "basic", "status": "failed"}]):
                c._write(source / "manifest.json", {"decks": records})
                with self.assertRaisesRegex(ValueError, "5デッキ"):
                    c.compare(source, source / "checked")

    def test_compare_rejects_mutated_deck_before_measurement(self):
        with TemporaryDirectory() as temporary:
            source = Path(temporary)
            records = []
            for name in c.DECKS:
                (source / f"{name}.pptx").write_bytes(b"changed")
                records.append({"name": name, "status": "passed", "sha256": "wrong"})
            c._write(source / "manifest.json", {"decks": records, "environment": c.environment(),
                                               "fonts": c.describe(), "code_font": c._font_identity(c.font_face("code"))})
            with patch.object(c, "compare_text") as measure:
                with self.assertRaisesRegex(ValueError, "差があります"):
                    c.compare(source, source / "checked")
                measure.assert_not_called()
            result = json.loads((source / "checked/manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(len(result["decks"]), 5)
            self.assertTrue(all(item["status"] == "failed" for item in result["decks"]))

    def test_libreoffice_probe_does_not_publish_arbitrary_output(self):
        completed = subprocess.CompletedProcess([], 0, "private location", "private diagnostic")
        with patch.object(c.shutil, "which", return_value="office"), patch.object(c.subprocess, "run", return_value=completed):
            report = c.environment()
        self.assertEqual(report["libreoffice"]["status"], "probe_failed")
        self.assertNotIn("private", json.dumps(report))

    def test_first_cross_failure_cannot_be_hidden_by_second_success(self):
        with TemporaryDirectory() as temporary, patch.object(c, "compare", side_effect=[ValueError("NG"), {}]) as compare:
            output = Path(temporary) / "checked"
            with self.assertRaisesRegex(ValueError, "クロス検査"):
                c.compare_sources(Path(temporary), output)
            self.assertEqual(compare.call_count, 2)
            results = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual([item["status"] for item in results], ["failed", "passed"])


if __name__ == "__main__":
    unittest.main()
