"""PPTXの文字実測モデルを使わず、実PNGの画素で指定領域を補助検査する。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path, PureWindowsPath
import re
import sys

from PIL import Image


def _box(value, size):
    if (not isinstance(value, list) or len(value) != 4
            or any(type(n) is not int for n in value)):
        raise ValueError("矩形は整数4値で指定してください")
    x0, y0, x1, y1 = value
    if not (0 <= x0 < x1 <= size[0] and 0 <= y0 < y1 <= size[1]):
        raise ValueError("検査矩形がPNG領域外です")
    return tuple(value)


def _integer(spec, key, default, maximum):
    value = spec.get(key, default)
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError(f"{key}が許容範囲外です")
    return value


def _color(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9A-Fa-f]{6}", value):
        raise ValueError("inkは6桁のRGBで指定してください")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def inspect(manifest, png_dir):
    """信頼済み検査仕様と実画素を照合する。目視済み・承認済みは出力しない。"""
    if not isinstance(manifest, dict) or manifest.get("version") != 1:
        raise ValueError("PNG検査仕様のversionは1です")
    backend = manifest.get("backend")
    if (not isinstance(backend, dict) or backend.get("name") not in {
            "powerpoint", "libreoffice", "other"}
            or not isinstance(backend.get("version"), str) or not backend["version"].strip()):
        raise ValueError("実行したbackend名とバージョンを記録してください")
    pages = manifest.get("pages")
    if not isinstance(pages, list) or not pages:
        raise ValueError("pagesには全ページを列挙してください")
    root = Path(png_dir).resolve()
    findings, records, seen = [], [], set()
    count = 0
    for index, page in enumerate(pages, 1):
        if not isinstance(page, dict):
            raise ValueError("pageはオブジェクトです")
        name = page.get("png")
        if (not isinstance(name, str) or not name or Path(name).name != name
                or PureWindowsPath(name).name != name or Path(name).suffix.lower() != ".png"
                or name in seen):
            raise ValueError("PNGは重複しないファイル名で指定してください")
        seen.add(name)
        path = (root / name).resolve()
        if path.parent != root:
            raise ValueError("PNGの参照先が検査ディレクトリ外です")
        with Image.open(path) as source:
            if source.format != "PNG":
                raise ValueError("PNG以外の画像は検査できません")
            image = source.convert("RGBA")
            # 透過領域は白へ合成する。通常のスライドPNGは不透明。
            background = Image.new("RGBA", image.size, "white")
            background.alpha_composite(image)
            image = background.convert("RGB")
        expected_size = page.get("size")
        if (not isinstance(expected_size, list) or len(expected_size) != 2
                or any(type(n) is not int or n <= 0 for n in expected_size)):
            raise ValueError("PNGの期待寸法は正の整数2値です")
        if list(image.size) != expected_size:
            findings.append({"page": index, "code": "PNG-SIZE", "check": "page-size"})
            records.append({"page": index, "png": name, "checks": 0})
            continue
        checks = page.get("checks", [])
        if not isinstance(checks, list):
            raise ValueError("checksは配列です")
        ids = set()
        for rule in checks:
            if (not isinstance(rule, dict) or not isinstance(rule.get("id"), str)
                    or not rule["id"] or rule["id"] in ids):
                raise ValueError("検査idはページ内で重複しない文字列です")
            ids.add(rule["id"])
            if rule.get("kind") not in {"ink_bounds", "ink_presence"}:
                raise ValueError("未対応のPNG検査種別です")
            region = _box(rule.get("region"), image.size)
            color = _color(rule.get("ink"))
            tolerance = _integer(rule, "tolerance", 24, 255)
            minimum = _integer(rule, "min_pixels", 1, image.width * image.height)
            if not minimum:
                raise ValueError("min_pixelsは1以上です")
            allowance = _integer(rule, "allowance_px", 1, 3)
            bounds = _box(rule.get("bounds"), image.size) if rule["kind"] == "ink_bounds" else region
            if rule["kind"] == "ink_bounds" and not (
                    region[0] <= bounds[0] < bounds[2] <= region[2]
                    and region[1] <= bounds[1] < bounds[3] <= region[3]):
                raise ValueError("boundsは検査region内へ置いてください")
            pixels, outside = 0, 0
            for y in range(region[1], region[3]):
                for x in range(region[0], region[2]):
                    if max(abs(a - b) for a, b in zip(image.getpixel((x, y)), color)) > tolerance:
                        continue
                    pixels += 1
                    if not (bounds[0] - allowance <= x < bounds[2] + allowance
                            and bounds[1] - allowance <= y < bounds[3] + allowance):
                        outside += 1
            count += 1
            if pixels < minimum:
                findings.append({"page": index, "code": "PNG-INK-MISSING", "check": rule["id"],
                                 "pixels": pixels, "minimum": minimum})
            if outside:
                findings.append({"page": index, "code": "PNG-INK-OOB", "check": rule["id"],
                                 "outside_pixels": outside})
        records.append({"page": index, "png": name, "checks": len(checks)})
    actual = {path.name for path in root.glob("slide_*.png")}
    if actual != seen:
        findings.append({"code": "PNG-PAGES", "check": "page-inventory",
                         "missing": sorted(seen - actual), "unexpected": sorted(actual - seen)})
    return {"version": 1, "backend_declared": backend, "automatic_checks": count,
            "automatic_status": "failed" if findings else "passed" if count else "incomplete",
            "visual_review": "not_performed", "powerpoint_visual_review": "not_performed",
            "human_approval": "not_recorded", "pages": records, "findings": findings}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("png_dir", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.report.suffix.lower() != ".json" or args.report.resolve() == args.manifest.resolve():
        print("NG: 入力と異なるJSONを結果の保存先に指定してください。", file=sys.stderr)
        return 2
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        report = inspect(manifest, args.png_dir)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, TypeError, Image.DecompressionBombError):
        # 前回の合格記録を、今回の入力不正後にそのまま残さない。
        failed = {"version": 1, "automatic_status": "failed", "automatic_checks": 0,
                  "visual_review": "not_performed", "powerpoint_visual_review": "not_performed",
                  "human_approval": "not_recorded", "findings": [{"code": "PNG-INPUT"}]}
        try:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(failed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except OSError:
            print("NG: 今回の結果を保存できません。既存の記録を今回の結果として使用しないでください。", file=sys.stderr)
        print("NG: PNG検査仕様・画像・保存先を確認してください。入力不正または読み書き不能です。", file=sys.stderr)
        return 2
    print(f"PNG補助検査: {report['automatic_status']} / 検査{report['automatic_checks']}件 / 指摘{len(report['findings'])}件。目視QAは別途必要です。")
    return 0 if report["automatic_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
