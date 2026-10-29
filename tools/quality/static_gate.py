"""固定ツールの静的検査と、必要に応じて全テストの分岐coverageを実行する。"""

import argparse
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
FORMATTED = (
    "slidegen/agenda_renderer.py",
    "slidegen/chart_model.py",
    "slidegen/layout_fit.py",
    "slidegen/layout_settings.py",
    "slidegen/network_layout.py",
    "slidegen/swimlane_layout.py",
    "slidegen/protocol_state_layout.py",
    "slidegen/timeline_layout.py",
    "slidegen/diagram_contract.py",
    "slidegen/schema_definition.py",
    "slidegen/semantic_validation.py",
    "slidegen/schema_validation.py",
    "tools/quality/static_gate.py",
)


def static_commands() -> list[list[str]]:
    return [
        [sys.executable, "-m", "ruff", "check", "slidegen", "tools/quality/static_gate.py"],
        [sys.executable, "-m", "ruff", "format", "--check", *FORMATTED],
        [sys.executable, "-m", "mypy", "--config-file", "mypy.ini"],
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--coverage", action="store_true", help="全テストを子プロセスも含め計測する"
    )
    args = parser.parse_args()
    statuses = [
        subprocess.run(command, cwd=ROOT, check=False).returncode for command in static_commands()
    ]
    if args.coverage:
        directory = ROOT / "out/coverage"
        directory.mkdir(parents=True, exist_ok=True)
        # 子が作業ディレクトリを変えても、測定結果を同じGit管理外フォルダへ集める。
        env = dict(
            os.environ,
            COVERAGE_FILE=str(directory / ".coverage"),
            COVERAGE_RCFILE=str(ROOT / ".coveragerc"),
            PYTHONIOENCODING="utf-8",
        )
        commands = [
            ["erase"],
            ["run", "-m", "tests", "--report", "out/coverage/tests.json"],
            ["combine"],
            ["report", "--include", "slidegen/*"],
            ["json", "--include", "slidegen/*"],
            ["xml", "--include", "slidegen/*"],
            ["html", "--include", "slidegen/*"],
        ]
        for command in commands:
            statuses.append(
                subprocess.run(
                    [sys.executable, "-m", "coverage", *command], cwd=ROOT, env=env, check=False
                ).returncode
            )
    failed = sum(status != 0 for status in statuses)
    print(f"静的品質ゲート: {len(statuses)}コマンド、失敗{failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
