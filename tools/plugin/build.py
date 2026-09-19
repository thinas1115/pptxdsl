"""自己完結型Pluginを作る互換入口: python -m tools.plugin.build。"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess

from tools.distribution.build import PROJECT_FILES, ROOT, build_plugin


def build(output_dir: Path, source_root: Path = ROOT) -> tuple[Path, Path]:
    return build_plugin(output_dir, source_root)


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
