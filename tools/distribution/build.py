"""自己完結型Skill、Plugin、GitHub Release用アセットを再現可能に生成する。"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[2]
PROJECT_FILES = (
    "AI_DECK_PROMPT.md", "CONTENT_SCHEMA.md", "DESIGN_CUSTOMIZATION.md",
    "docs/type-selection-guide.md", "docs/cover-footer-customization.md",
    "docs/aws-icon-selection.md",
    "requirements.txt", "render.ps1", "contact_sheet.py",
    "LICENSE", "THIRD_PARTY_NOTICES.md",
)
SEMVER = re.compile(
    r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?"
)
TEXT_SUFFIXES = {
    ".csv", ".json", ".md", ".ps1", ".py", ".svg", ".toml", ".tsv",
    ".txt", ".xml", ".yaml", ".yml",
}
TEXT_FILENAMES = {"LICENSE"}


@dataclass(frozen=True)
class ReleaseAssets:
    skill: Path
    plugin: Path
    gallery: Path
    checksums: Path


def _manifest(source_root: Path) -> dict:
    codex = json.loads((source_root / "plugins/pptxdsl/.codex-plugin/plugin.json")
                       .read_text(encoding="utf-8"))
    claude = json.loads((source_root / "plugins/pptxdsl/.claude-plugin/plugin.json")
                        .read_text(encoding="utf-8"))
    if codex.get("name") != "pptxdsl" or not SEMVER.fullmatch(
            str(codex.get("version", ""))):
        raise ValueError("Plugin名またはバージョンが不正です")
    if (claude.get("name"), claude.get("version")) != (
            codex["name"], codex["version"]):
        raise ValueError("CodexとClaude CodeのPlugin名またはバージョンが一致しません")
    return codex


def version(source_root: Path = ROOT) -> str:
    return str(_manifest(source_root)["version"])


def _copy_tree(source: Path, destination: Path) -> None:
    """キャッシュとシンボリックリンクを配布へ持ち込まない。"""
    for path in sorted(source.rglob("*")):
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        if path.is_symlink():
            raise ValueError("配布対象にシンボリックリンクがあります")
        if path.is_file():
            target = destination / path.relative_to(source)
            _copy_content(path, target)


def _copy_content(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() in TEXT_SUFFIXES or source.name in TEXT_FILENAMES:
        text = source.read_text(encoding="utf-8")
        target.write_text(text.replace("\r\n", "\n").replace("\r", "\n"),
                          encoding="utf-8", newline="\n")
    else:
        shutil.copyfile(source, target)


def _copy_file(source: Path, target: Path, root: Path) -> None:
    for path in (source, *source.parents):
        if path.is_symlink():
            raise ValueError("配布対象にシンボリックリンクがあります")
        if path == root:
            break
    _copy_content(source, target)


def _populate_skill(skill: Path, source_root: Path) -> None:
    _copy_tree(source_root / ".agents/skills/pptxdsl", skill)
    project = skill / "project"
    tracked = subprocess.run(
        ["git", "-C", str(source_root), "ls-files", "-z", "--", "slidegen"],
        check=True, capture_output=True,
    ).stdout.decode("utf-8").split("\0")
    for relative in filter(None, tracked):
        _copy_file(source_root / relative, project / relative, source_root)
    for relative in PROJECT_FILES:
        _copy_file(source_root / relative, project / relative, source_root)


def _write_zip(source: Path, archive: Path, *, include_root: bool) -> None:
    relative_to = source.parent if include_root else source
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_STORED) as bundle:
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            info = zipfile.ZipInfo(
                path.relative_to(relative_to).as_posix(),
                date_time=(2020, 1, 1, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, path.read_bytes())


def build_skill(output_dir: Path, source_root: Path = ROOT) -> tuple[Path, Path]:
    output_dir = output_dir.resolve()
    package_version = version(source_root)
    skill = output_dir / "pptxdsl"
    archive = output_dir / f"pptxdsl-skill-v{package_version}.zip"
    if skill.exists() or archive.exists():
        raise ValueError("出力先にSkill配布物が既にあります。別の出力ディレクトリを指定してください")
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pptxdsl-skill-", dir=output_dir) as temporary:
        staging = Path(temporary) / "pptxdsl"
        _populate_skill(staging, source_root)
        temporary_zip = Path(temporary) / archive.name
        _write_zip(staging, temporary_zip, include_root=True)
        staging.rename(skill)
        temporary_zip.rename(archive)
    return skill, archive


def build_plugin(output_dir: Path, source_root: Path = ROOT) -> tuple[Path, Path]:
    output_dir = output_dir.resolve()
    manifest = _manifest(source_root)
    plugin = output_dir / "pptxdsl"
    archive = output_dir / f"pptxdsl-plugin-v{manifest['version']}.zip"
    if plugin.exists() or archive.exists():
        raise ValueError("出力先にPlugin配布物が既にあります。別の出力ディレクトリを指定してください")
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pptxdsl-plugin-", dir=output_dir) as temporary:
        staging = Path(temporary) / "pptxdsl"
        _copy_file(source_root / "plugins/pptxdsl/.codex-plugin/plugin.json",
                   staging / ".codex-plugin/plugin.json", source_root)
        _copy_file(source_root / "plugins/pptxdsl/.claude-plugin/plugin.json",
                   staging / ".claude-plugin/plugin.json", source_root)
        _populate_skill(staging / "skills/pptxdsl", source_root)
        portable = {key: value for key, value in manifest.items()
                    if key not in ("skills", "interface")}
        portable["$schema"] = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
        portable["extensions"] = {"com.openai": {"interface": manifest["interface"]}}
        (staging / "plugin.json").write_text(
            json.dumps(portable, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary_zip = Path(temporary) / archive.name
        _write_zip(staging, temporary_zip, include_root=False)
        staging.rename(plugin)
        temporary_zip.rename(archive)
    return plugin, archive


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_release(output_dir: Path, *, tag: str | None = None,
                  source_root: Path = ROOT) -> ReleaseAssets:
    output_dir = output_dir.resolve()
    package_version = version(source_root)
    expected_tag = f"v{package_version}"
    if tag is not None and tag != expected_tag:
        raise ValueError(f"Releaseタグは{expected_tag}である必要があります: {tag}")
    names = (
        f"pptxdsl-skill-{expected_tag}.zip",
        f"pptxdsl-plugin-{expected_tag}.zip",
        "pattern_gallery.pptx",
        "SHA256SUMS.txt",
    )
    if any((output_dir / name).exists() for name in names):
        raise ValueError("出力先にReleaseアセットが既にあります。別の出力ディレクトリを指定してください")
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pptxdsl-release-", dir=output_dir) as temporary:
        temporary_root = Path(temporary)
        _, skill_archive = build_skill(temporary_root / "skill", source_root)
        _, plugin_archive = build_plugin(temporary_root / "plugin", source_root)
        skill_target = output_dir / names[0]
        plugin_target = output_dir / names[1]
        gallery_target = output_dir / names[2]
        shutil.copyfile(skill_archive, skill_target)
        shutil.copyfile(plugin_archive, plugin_target)
        shutil.copyfile(source_root / "examples/gallery/pattern_gallery.pptx", gallery_target)
    checksums = output_dir / names[3]
    checksum_targets = (skill_target, plugin_target, gallery_target)
    checksums.write_text("".join(
        f"{_sha256(path)}  {path.name}\n" for path in checksum_targets
    ), encoding="utf-8", newline="\n")
    return ReleaseAssets(skill_target, plugin_target, gallery_target, checksums)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("out/release"))
    parser.add_argument("--tag", help="manifestと一致を確認するReleaseタグ（例: vX.Y.Z）")
    args = parser.parse_args()
    try:
        assets = build_release(args.output_dir, tag=args.tag)
    except ValueError as error:
        raise SystemExit(f"NG: {error}") from None
    except (OSError, subprocess.CalledProcessError):
        raise SystemExit("NG: Releaseアセット生成に失敗しました。入力と出力先を確認してください。") from None
    for path in (assets.skill, assets.plugin, assets.gallery, assets.checksums):
        print(f"Releaseアセット: {path.name}")


if __name__ == "__main__":
    main()
