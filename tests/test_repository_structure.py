"""本処理だけをコピーしても通常生成でき、開発資産へ依存しないことを検証する。"""
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]


def main():
    for path in (ROOT / "slidegen").glob("*.py"):
        assert not path.name.startswith(("test_", "content", "build_", "fetch_", "extract_", "inspect_")), path.name
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            assert not any(name.split(".")[0] in {"tests", "tools"} for name in names), path.name
    deck = {
        "meta": {"title": "分離動作確認"},
        "slides": [{"type": "bullets", "kicker": "TEST", "title": "生成経路",
                    "bullets": [{"text": "利用者が用意した入力から生成します。"}]}],
    }
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env.pop("PYTHONPATH", None)
    with TemporaryDirectory() as directory:
        sandbox = Path(directory)
        shutil.copytree(ROOT / "slidegen", sandbox / "slidegen",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        (sandbox / "content.json").write_text(json.dumps(deck, ensure_ascii=False), encoding="utf-8")
        for args in (
            ["slidegen/validate_content.py", "content.json"],
            ["slidegen/generate_from_json.py", "content.json", "out/deck.pptx"],
            ["slidegen/check_layout.py", "out/deck.pptx"],
            ["-m", "slidegen.validate_content", "content.json"],
            ["-m", "slidegen.generate_from_json", "content.json", "out/module.pptx"],
            ["-m", "slidegen.check_layout", "out/module.pptx"],
        ):
            result = subprocess.run([sys.executable, *args], cwd=sandbox, env=env,
                                    capture_output=True, text=True, encoding="utf-8")
            assert result.returncode == 0, result.stdout + result.stderr
        retired = subprocess.run([sys.executable, "slidegen/generate.py"], cwd=sandbox,
                                 env=env, capture_output=True, text=True, encoding="utf-8")
        assert retired.returncode != 0
        assert "python -m tools.gallery.generate_basic" in retired.stderr
        assert "Traceback" not in retired.stderr
    print("OK: 本処理だけでファイル実行・module実行の生成と検証が完了")


if __name__ == "__main__":
    main()
