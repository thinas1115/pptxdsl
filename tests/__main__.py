"""全テストを独立プロセスで実行する: python -m tests。"""
import os
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time


# 単体実行の入口を変えず、unittestのskipも既存scriptと同じ形式で報告する。
_CASE_RUNNER = """
import runpy
import sys
import unittest

original_add_skip = unittest.TextTestResult.addSkip

def report_skip(result, test, reason):
    original_add_skip(result, test, reason)
    print(f"SKIP: {test.id()}: {reason}", flush=True)

unittest.TextTestResult.addSkip = report_skip
module = sys.argv[1]
sys.argv = [module]
runpy.run_module(module, run_name="__main__", alter_sys=True)
"""


def run_cases(root, cases):
    """既存script形式を独立実行し、全失敗と明示されたskipを収集する。"""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    # 親が最適化されていなくても環境変数だけで子のassertが消えるのを防ぐ。
    env.pop("PYTHONOPTIMIZE", None)
    records = []
    for case in cases:
        print(f"==> {case.name}", flush=True)
        started = time.perf_counter()
        result = subprocess.run(
            [sys.executable, "-c", _CASE_RUNNER, f"tests.{case.stem}"], cwd=root, env=env,
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        elapsed = time.perf_counter() - started
        print(result.stdout, end="", flush=True)
        print(result.stderr, end="", file=sys.stderr, flush=True)
        records.append({
            "module": f"tests.{case.stem}",
            "status": "passed" if result.returncode == 0 else "failed",
            "exit_code": result.returncode,
            "seconds": round(elapsed, 3),
            "skips": [line[6:] for line in result.stdout.splitlines()
                      if line.startswith("SKIP: ")],
            "stdout": result.stdout, "stderr": result.stderr,
        })
    return records


def main():
    if not __debug__:
        raise SystemExit("NG: assert検証のためPythonの最適化を無効にしてください。")
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=Path("out/test-results.json"),
                        help="全モジュールの結果・所要時間・skip理由の保存先")
    args = parser.parse_args()
    cases = sorted(Path(__file__).parent.glob("test_*.py"))
    if not cases:
        raise SystemExit("NG: テストが見つかりません。")
    records = run_cases(root, cases)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(records, ensure_ascii=False, indent=2),
                           encoding="utf-8")
    for record in records:
        print(f"{record['status']}: {record['module']} ({record['seconds']:.3f}s)")
        for reason in record["skips"]:
            print(f"  SKIP: {reason}")
    failures = [record for record in records if record["status"] == "failed"]
    print(f"結果: {len(records)}モジュール、成功{len(records) - len(failures)}、"
          f"失敗{len(failures)}、skip {sum(len(r['skips']) for r in records)}")
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
