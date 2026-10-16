"""主要5デッキの生成・検査と、同一PPTXのOS間照合を記録する。"""
import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import urllib.request

from PIL import features

from slidegen.font_config import describe, font_face
from tools.quality.text_metrics_cases import compare as compare_text, prepare_font, report


DECKS = ("basic", "extended", "patterns", "lead_patterns", "stress_patterns")
CODE_URL = "https://raw.githubusercontent.com/notofonts/noto-cjk/523d033d6cb47f4a80c58a35753646f5c3608a78/Sans/Mono/NotoSansMonoCJKjp-Regular.otf"
CODE_SHA256 = "4d01725be822d144cf9a56ade981e6fb920cd7a610b8fc24cc601a920beea5b9"


def prepare_fonts(directory):
    """書体は検証時に取得し、配布物やGitには含めない。"""
    prepare_font(directory / "NotoSansJP-VF.ttf")
    code = directory / "NotoSansMonoCJKjp-Regular.otf"
    if not code.exists():
        with urllib.request.urlopen(CODE_URL, timeout=60) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != CODE_SHA256:
            raise ValueError("固定コード書体のSHA256が一致しません")
        code.write_bytes(data)
    if hashlib.sha256(code.read_bytes()).hexdigest() != CODE_SHA256:
        raise ValueError("固定コード書体のSHA256が一致しません")


def _font_identity(face):
    return {"family": face.family, "style": face.style, "index": face.index,
            "axes": list(face.axes), "sha256": hashlib.sha256(Path(face.path).read_bytes()).hexdigest()}


def environment():
    """端末名・パスは記録せず、測定依存と描画の未実施を明示する。"""
    executable = shutil.which("soffice") or shutil.which("libreoffice")
    office = {"status": "not_detected", "version": None}
    if executable:
        try:
            result = subprocess.run([executable, "--version"], capture_output=True, text=True,
                                    encoding="utf-8", errors="replace", timeout=15, check=False)
            # ローカルパスを含み得るstderrや任意の先頭行を成果物へ転記しない。
            line = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
            if result.returncode == 0 and line.startswith("LibreOffice ") and len(line) < 200:
                office = {"status": "detected", "version": line}
            else:
                office["status"] = "probe_failed"
        except (OSError, subprocess.TimeoutExpired):
            office["status"] = "probe_failed"
    return {"os": platform.system(), "python": platform.python_version(),
            "packages": {name: version(name) for name in ("python-pptx", "Pillow", "lxml", "XlsxWriter")},
            "measurement": {"engine": "BASIC", "freetype": features.version_module("freetype2")},
            "backend": "pptx-structure", "rendering": "not_performed",
            "libreoffice": office, "powerpoint": {"status": "not_probed", "version": None}}


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def build(output):
    output.mkdir(parents=True, exist_ok=True)
    records = []
    for name in DECKS:
        started = time.perf_counter()
        path = output / f"{name}.pptx"
        # 生成側の旧グローバル状態もデッキ間で持ち越さない。
        result = subprocess.run([sys.executable, "-m", f"tools.gallery.generate_{name}", str(path)],
                                capture_output=True, text=True, encoding="utf-8", errors="replace")
        record = {"name": name, "status": "failed", "exit_code": result.returncode}
        if result.returncode == 0:
            try:
                measured = report(path)
                _write(output / f"{name}.json", measured)
                record.update(status="passed" if not measured["findings"] else "failed",
                              sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                              pages=max(frame["slide"] for frame in measured["frames"]),
                              frames=len(measured["frames"]), findings=measured["findings"])
            except (ValueError, OSError):
                record["reason"] = "保存PPTXの検査に失敗しました。該当デッキを個別に検査してください"
        else:
            record["reason"] = "生成に失敗しました。該当generatorを個別に実行して原因を確認してください"
        record["seconds"] = round(time.perf_counter() - started, 3)
        records.append(record)
        print(f"{name}: {record['status']}", flush=True)
    manifest = {"environment": environment(), "fonts": describe(), "code_font": _font_identity(font_face("code")),
                "decks": records}
    _write(output / "manifest.json", manifest)
    if any(record["status"] != "passed" for record in records):
        raise ValueError("主要デッキの生成・検査に失敗しました。manifest.jsonを確認してください")
    return manifest


def compare(source, output):
    baseline = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    records = baseline["decks"]
    if [item["name"] for item in records] != list(DECKS) or any(item["status"] != "passed" for item in records):
        raise ValueError("主要5デッキの基準値が揃っていません")
    current = environment()
    outcomes = []
    fonts_match = baseline["fonts"] == json.loads(json.dumps(describe()))
    code_match = baseline["code_font"] == _font_identity(font_face("code"))
    for record in records:
        name = record["name"]
        path = source / f"{name}.pptx"
        matched = hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]
        try:
            if not (matched and fonts_match and code_match):
                raise ValueError("基準PPTXまたは測定書体の識別情報が一致しません")
            compare_text(path, source / f"{name}.json", output / f"{name}.json")
            outcomes.append({"name": name, "status": "passed"})
        except ValueError:
            outcomes.append({"name": name, "status": "failed"})
    result = {"origin": baseline["environment"], "checked_on": current,
              "fonts_match": fonts_match, "code_font_match": code_match, "decks": outcomes}
    _write(output / "manifest.json", result)
    if any(item["status"] != "passed" for item in outcomes):
        raise ValueError("同一PPTXのクロス検査に差があります。照合先のJSONを確認してください")
    return result


def compare_sources(source, output):
    """一方が失敗しても他方を検査し、PowerShellの最終終了値で失敗を隠さない。"""
    results = []
    for name in ("windows-latest", "ubuntu-latest"):
        try:
            compare(source / f"regression-origin-{name}" / "decks", output / name)
            results.append({"origin": name, "status": "passed"})
        except (ValueError, OSError, KeyError):
            results.append({"origin": name, "status": "failed"})
    _write(output / "summary.json", results)
    if any(item["status"] != "passed" for item in results):
        raise ValueError("クロス検査に失敗しました。summary.jsonを確認してください")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("prepare-fonts").add_argument("directory", type=Path)
    commands.add_parser("build").add_argument("output", type=Path)
    commands.add_parser("environment").add_argument("output", type=Path)
    command = commands.add_parser("compare")
    command.add_argument("source", type=Path)
    command.add_argument("output", type=Path)
    command = commands.add_parser("cross")
    command.add_argument("source", type=Path)
    command.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.command == "prepare-fonts":
        prepare_fonts(args.directory)
    elif args.command == "build":
        build(args.output)
    elif args.command == "environment":
        _write(args.output, {"environment": environment(), "fonts": describe(),
                             "code_font": _font_identity(font_face("code"))})
    elif args.command == "cross":
        compare_sources(args.source, args.output)
    else:
        compare(args.source, args.output)
