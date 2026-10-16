"""CLIが入力エラーを安全かつ修正可能な形で返すか検証する。"""
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "slidegen" / "generate_from_json.py"


with TemporaryDirectory() as td:
    invalid = Path(td) / "invalid-content.json"
    invalid.write_text('{"meta": {"title": "資料"}, "slides": [}', encoding="utf-8")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(invalid), str(Path(td) / "out.pptx")],
        capture_output=True, text=True, encoding="utf-8", env=env,
        cwd=ROOT, check=False)
    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "JSON構文が不正" in output, output
    assert "行1" in output and "列" in output, output
    assert "Traceback" not in output, output
    assert str(invalid.parent) not in output, output
    assert invalid.name in output, output

print("generate_from_json safe error handling: ALL OK")

# 検証単独CLIも同じ読込契約を使い、パス・tracebackを出さない。
with TemporaryDirectory() as td:
    source = Path(td) / "input.json"
    for raw, expected in ((b"\xff", "UTF-8"), (b"{", "JSON構文が不正"),
                          (None, "見つかりません")):
        if raw is not None:
            source.write_bytes(raw)
        elif source.exists():
            source.unlink()
        for module in ("slidegen.validate_content", "slidegen.generate_from_json"):
            result = subprocess.run(
                [sys.executable, "-m", module, str(source)],
                capture_output=True, text=True, encoding="utf-8", env=env,
                cwd=ROOT, check=False)
            output = result.stdout + result.stderr
            assert result.returncode != 0 and expected in output, output
            assert "Traceback" not in output and td not in output, output

print("検証・生成CLIの入力読込エラー: ALL OK")
