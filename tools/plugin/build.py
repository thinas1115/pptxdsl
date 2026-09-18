"""正本のSkillと本処理から自己完結型Pluginを作る: python -m tools.plugin.build。"""
from __future__ import annotations

import argparse
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


def _copy_tree(source: Path, destination: Path) -> None:
    """キャッシュとシンボリックリンクを配布へ持ち込まない。"""
    for path in sorted(source.rglob("*")):
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        if path.is_symlink():
            raise ValueError("配布対象にシンボリックリンクがあります")
        if path.is_file():
            target = destination / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)


def _copy_file(source: Path, target: Path, root: Path) -> None:
    for path in (source, *source.parents):
        if path.is_symlink():
            raise ValueError("配布対象にシンボリックリンクがあります")
        if path == root:
            break
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def build(output_dir: Path, source_root: Path = ROOT) -> tuple[Path, Path]:
    output_dir = output_dir.resolve()
    manifest = json.loads((source_root / "plugins/pptxdsl/.codex-plugin/plugin.json")
                          .read_text(encoding="utf-8"))
    if manifest.get("name") != "pptxdsl" or not re.fullmatch(
            r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?",
            str(manifest.get("version", ""))):
        raise ValueError("Plugin名またはバージョンが不正です")
    plugin = output_dir / "pptxdsl"
    archive = output_dir / f"pptxdsl-{manifest['version']}.zip"
    if plugin.exists() or archive.exists():
        raise ValueError("出力先に配布物が既にあります。別の出力ディレクトリを指定してください")
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pptxdsl-build-", dir=output_dir) as temporary:
        staging = Path(temporary) / "pptxdsl"
        manifest_target = staging / ".codex-plugin/plugin.json"
        _copy_file(source_root / "plugins/pptxdsl/.codex-plugin/plugin.json", manifest_target, source_root)
        skill = staging / "skills/pptxdsl"
        _copy_tree(source_root / ".agents/skills/pptxdsl", skill)
        project = skill / "project"
        # 本処理に置かれた未追跡の利用者素材・ローカルファイルは公開しない。
        tracked = subprocess.run(["git", "-C", str(source_root), "ls-files", "-z", "--", "slidegen"],
                                 check=True, capture_output=True).stdout.decode("utf-8").split("\0")
        for relative in filter(None, tracked):
            source = source_root / relative
            target = project / relative
            _copy_file(source, target, source_root)
        for relative in PROJECT_FILES:
            target = project / relative
            _copy_file(source_root / relative, target, source_root)
        # Portable manifestの固定skills/検出と、旧Codex形式を両方提供する。
        portable = {key: value for key, value in manifest.items()
                    if key not in ("skills", "interface")}
        portable["$schema"] = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
        portable["extensions"] = {"com.openai": {"interface": manifest["interface"]}}
        (staging / "plugin.json").write_text(
            json.dumps(portable, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary_zip = Path(temporary) / archive.name
        with zipfile.ZipFile(temporary_zip, "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(staging.rglob("*")):
                if path.is_file():
                    # ZIPの直下がPluginルート。更新日時も固定する。
                    info = zipfile.ZipInfo(path.relative_to(staging).as_posix(),
                                           date_time=(2020, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o100644 << 16
                    bundle.writestr(info, path.read_bytes())
        staging.rename(plugin)
        temporary_zip.rename(archive)
    return plugin, archive


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("out/plugins"))
    args = parser.parse_args()
    try:
        _, archive = build(args.output_dir)
    except ValueError as error:
        raise SystemExit(f"NG: {error}") from None
    except (OSError, subprocess.CalledProcessError):
        raise SystemExit("NG: Pluginビルドに失敗しました。必要な入力と未使用の出力先を確認してください。") from None
    print(f"配布ZIP: {archive.name}")


if __name__ == "__main__":
    main()
