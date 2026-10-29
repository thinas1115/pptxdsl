"""CI専用ミラー変更が対象外設定やローカル環境へ及ばないことを確認する。"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.quality import prepare_linux_packages as p


class LinuxPackageTests(unittest.TestCase):
    def test_only_azure_archive_urls_are_replaced(self):
        original = ("http://azure.archive.ubuntu.com/ubuntu priority:1\n"
                    "https://azure.archive.ubuntu.com/ubuntu\nhttps://security.ubuntu.com/ubuntu\n"
                    "URIs: mirror+file:/etc/apt/apt-mirrors.txt\n")
        expected = original.replace("http://azure.archive.ubuntu.com/ubuntu", "https://archive.ubuntu.com/ubuntu").replace(
            "https://azure.archive.ubuntu.com/ubuntu", "https://archive.ubuntu.com/ubuntu")
        self.assertEqual(p.mirror_text(original), expected)

    def test_local_or_non_linux_environment_stops_before_changes(self):
        for system, flag in (("Windows", "true"), ("Darwin", "true"), ("Linux", "false")):
            with self.subTest(system=system, flag=flag), patch.object(p.platform, "system", return_value=system), \
                    patch.dict(os.environ, {"GITHUB_ACTIONS": flag}), patch.object(p.subprocess, "run") as run:
                with self.assertRaisesRegex(ValueError, "専用"):
                    p.prepare(["libreoffice-impress"])
                run.assert_not_called()

    def test_rewrites_before_install_and_keeps_unrelated_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            azure, other = root / "azure", root / "other"
            azure.write_text("http://azure.archive.ubuntu.com/ubuntu\n", encoding="utf-8")
            other.write_text("https://security.ubuntu.com/ubuntu\n", encoding="utf-8")
            with patch.object(p, "MIRROR_FILES", (azure, other)), \
                    patch.object(p.platform, "system", return_value="Linux"), \
                    patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}), patch.object(p.subprocess, "run") as run:
                p.prepare(["libreoffice-impress", "poppler-utils"])
                self.assertEqual(run.call_count, 3)
                self.assertEqual(run.call_args_list[0].args[0], ["sudo", "tee", str(azure)])
                self.assertEqual(run.call_args_list[0].kwargs["input"], "https://archive.ubuntu.com/ubuntu\n")
                self.assertIn("update", run.call_args_list[1].args[0])
                self.assertEqual(run.call_args_list[2].args[0][-2:], ["libreoffice-impress", "poppler-utils"])
                self.assertTrue(all(call.kwargs["timeout"] <= 480 for call in run.call_args_list))
            self.assertEqual(other.read_text(encoding="utf-8"), "https://security.ubuntu.com/ubuntu\n")

    def test_install_failure_or_invalid_package_is_not_ignored(self):
        with patch.object(p, "MIRROR_FILES", ()), patch.object(p.platform, "system", return_value="Linux"), \
                patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}), patch.object(p.subprocess, "run") as run:
            for names in ([], ["--allow-unauthenticated"], ["x;echo"]):
                with self.assertRaises(ValueError):
                    p.prepare(names)
            run.assert_not_called()
            run.side_effect = subprocess.CalledProcessError(1, "apt-get")
            with self.assertRaises(subprocess.CalledProcessError):
                p.prepare(["libreoffice-impress"])
            self.assertEqual(run.call_count, 1)


if __name__ == "__main__":
    unittest.main()
