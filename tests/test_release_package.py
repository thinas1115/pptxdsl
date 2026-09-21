"""Skill・Pluginを分けたReleaseアセットとClaude Marketplaceを検証する。"""
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

from tools.distribution.build import ROOT, build_release, version


VERSION = f"v{version()}"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_release_assets() -> None:
    with tempfile.TemporaryDirectory(prefix="pptxdsl-release-test-") as temporary:
        base = Path(temporary)
        first = build_release(base / "first", tag=VERSION)
        second = build_release(base / "second", tag=VERSION)
        expected = {
            f"pptxdsl-skill-{VERSION}.zip",
            f"pptxdsl-plugin-{VERSION}.zip",
            "pattern_gallery.pptx",
            "SHA256SUMS.txt",
        }
        assert {path.name for path in first.__dict__.values()} == expected
        for first_path, second_path in zip(first.__dict__.values(), second.__dict__.values()):
            assert first_path.read_bytes() == second_path.read_bytes(), first_path.name

        with zipfile.ZipFile(first.skill) as bundle:
            names = set(bundle.namelist())
            assert "pptxdsl/SKILL.md" in names
            assert "pptxdsl/project/slidegen/generate_from_json.py" in names
            assert "pptxdsl/plugin.json" not in names
            assert "pptxdsl/.codex-plugin/plugin.json" not in names
            assert "pptxdsl/.claude-plugin/plugin.json" not in names
            assert not any(set(Path(name).parts) & {"tests", "tools", ".git", "out", "__pycache__"}
                           for name in names)

        with zipfile.ZipFile(first.plugin) as bundle:
            names = set(bundle.namelist())
            assert "plugin.json" in names
            assert ".codex-plugin/plugin.json" in names
            assert ".claude-plugin/plugin.json" in names
            assert "skills/pptxdsl/SKILL.md" in names
            assert "skills/pptxdsl/project/slidegen/generate_from_json.py" in names

        marketplace = json.loads((ROOT / ".claude-plugin/marketplace.json")
                                 .read_text(encoding="utf-8"))
        assert marketplace["name"] == "pptxdsl-marketplace"
        assert marketplace["version"] == version()
        assert len(marketplace["plugins"]) == 1
        entry = marketplace["plugins"][0]
        assert entry["name"] == "pptxdsl"
        assert entry["source"] == {
            "source": "archive",
            "url": ("https://github.com/thinas1115/pptxdsl/releases/download/"
                    f"{VERSION}/{first.plugin.name}"),
            "sha256": _sha256(first.plugin),
        }

        checksums = {}
        for line in first.checksums.read_text(encoding="utf-8").splitlines():
            digest, name = line.split("  ", 1)
            checksums[name] = digest
        assert checksums == {
            first.skill.name: _sha256(first.skill),
            first.plugin.name: _sha256(first.plugin),
            first.gallery.name: _sha256(first.gallery),
        }
        assert first.gallery.read_bytes() == (ROOT / "examples/gallery/pattern_gallery.pptx").read_bytes()

        try:
            build_release(base / "wrong-tag", tag="v999.0.0")
        except ValueError as error:
            assert VERSION in str(error)
        else:
            raise AssertionError("manifestと異なるReleaseタグを拒否しませんでした")


if __name__ == "__main__":
    test_release_assets()
    print("Skill・Plugin別Releaseアセット: ALL OK")
