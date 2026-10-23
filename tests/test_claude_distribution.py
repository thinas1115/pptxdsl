"""Claude Code用manifestとOSに依存しないPlugin配布を検証する。"""
from pathlib import Path
import json
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from tools.distribution.build import (
    ROOT, PROJECT_FILES, TEXT_FILENAMES, TEXT_SUFFIXES,
    _copy_content, _manifest, _write_zip, build_plugin,
)


class ClaudeDistributionTests(unittest.TestCase):
    def test_three_manifests_share_identity_and_skill_root(self):
        with tempfile.TemporaryDirectory() as directory:
            package, archive = build_plugin(Path(directory))
            manifests = [json.loads((package / relative).read_text(encoding="utf-8"))
                         for relative in ("plugin.json", ".codex-plugin/plugin.json", ".claude-plugin/plugin.json")]
            self.assertEqual({(item["name"], item["version"]) for item in manifests}, {("pptxdsl", "1.0.2")})
            self.assertEqual(manifests[0]["extensions"]["com.openai"]["interface"], manifests[1]["interface"])
            self.assertNotIn("skills", manifests[2])
            self.assertTrue((package / "skills/pptxdsl/SKILL.md").is_file())
            with zipfile.ZipFile(archive) as bundle:
                self.assertIsNone(bundle.testzip())
                self.assertEqual(bundle.namelist(), sorted(bundle.namelist()))
                for item in bundle.infolist():
                    self.assertEqual(item.create_system, 3)
                    self.assertEqual(item.compress_type, zipfile.ZIP_STORED)
                    self.assertEqual(item.date_time, (2020, 1, 1, 0, 0, 0))

    def test_different_claude_name_or_version_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for host in ("codex", "claude"):
                target = root / f"plugins/pptxdsl/.{host}-plugin/plugin.json"
                target.parent.mkdir(parents=True)
                shutil.copyfile(ROOT / f"plugins/pptxdsl/.{host}-plugin/plugin.json", target)
            target = root / "plugins/pptxdsl/.claude-plugin/plugin.json"
            original = json.loads(target.read_text(encoding="utf-8"))
            for key, value in (("name", "other"), ("version", "1.0.3")):
                with self.subTest(key=key):
                    target.write_text(json.dumps(dict(original, **{key: value})), encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "一致しません"):
                        _manifest(root)

    def test_text_is_normalized_but_binary_is_identical(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for filename in ("a.py", "a.md", "a.json", "a.svg", "LICENSE"):
                with self.subTest(filename=filename):
                    source, target = root / filename, root / "dest" / filename
                    source.write_bytes("説明\r\n本文\r次行\n".encode("utf-8"))
                    _copy_content(source, target)
                    self.assertEqual(target.read_bytes(), "説明\n本文\n次行\n".encode("utf-8"))
            source, target = root / "binary.png", root / "dest/binary.png"
            source.write_bytes(b"\x89PNG\r\n\x00\xff\r\n")
            _copy_content(source, target)
            self.assertEqual(target.read_bytes(), source.read_bytes())

    def test_archive_order_is_case_sensitive_on_every_os(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            for name in ("a.txt", "B.txt", "Z.txt", "c.txt"):
                (source / name).write_bytes(b"same")
            archive = root / "test.zip"
            _write_zip(source, archive, include_root=False)
            with zipfile.ZipFile(archive) as bundle:
                self.assertEqual(bundle.namelist(), ["B.txt", "Z.txt", "a.txt", "c.txt"])

    def test_crlf_and_lf_checkouts_produce_identical_plugin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            paths = set(PROJECT_FILES)
            tracked = subprocess.run(["git", "ls-files", "-z", "--", "slidegen", ".agents/skills/pptxdsl"],
                                     cwd=ROOT, check=True, capture_output=True).stdout.decode("utf-8").split("\0")
            paths.update(filter(None, tracked))
            paths.update(f"plugins/pptxdsl/.{host}-plugin/plugin.json" for host in ("codex", "claude"))
            for relative in paths:
                target = source / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, target)
            subprocess.run(["git", "init", "-q", str(source)], check=True)
            subprocess.run(["git", "-C", str(source), "add", "slidegen"], check=True, capture_output=True)
            for ending in (b"\n", b"\r\n"):
                for relative in paths:
                    target = source / relative
                    if target.suffix.lower() in TEXT_SUFFIXES or target.name in TEXT_FILENAMES:
                        data = target.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
                        target.write_bytes(data.replace(b"\n", ending))
                _, archive = build_plugin(root / ("lf" if ending == b"\n" else "crlf"), source)
            self.assertEqual((root / "lf" / archive.name).read_bytes(), archive.read_bytes())


if __name__ == "__main__":
    unittest.main()
