"""自己完結型Skillを作る: python -m tools.skill.build。"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess

from tools.distribution.build import ROOT, build_skill


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("out/skills"))
    args = parser.parse_args()
    try:
        _, archive = build_skill(args.output_dir, ROOT)
    except ValueError as error:
        raise SystemExit(f"NG: {error}") from None
    except (OSError, subprocess.CalledProcessError):
        raise SystemExit("NG: Skillビルドに失敗しました。必要な入力と未使用の出力先を確認してください。") from None
    print(f"配布ZIP: {archive.name}")


if __name__ == "__main__":
    main()
