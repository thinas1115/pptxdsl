"""全テストを独立プロセスで実行する: python -m tests。"""
import os
from pathlib import Path
import subprocess
import sys


def main():
    if not __debug__:
        raise SystemExit("NG: assert検証のためPythonの最適化を無効にしてください。")
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    cases = sorted(Path(__file__).parent.glob("test_*.py"))
    if not cases:
        raise SystemExit("NG: テストが見つかりません。")
    for case in cases:
        print(f"==> {case.name}", flush=True)
        result = subprocess.run(
            [sys.executable, "-m", f"tests.{case.stem}"], cwd=root, env=env)
        if result.returncode:
            raise SystemExit(result.returncode)
    print(f"OK: {len(cases)} テストモジュール")


if __name__ == "__main__":
    main()
