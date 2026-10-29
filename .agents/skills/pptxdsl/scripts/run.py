"""clone・Plugin同梱の両方で、作業ディレクトリからpptxdslを実行する。"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


def project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        for candidate in (parent / "project", parent):
            if (candidate / "slidegen/generate_from_json.py").is_file():
                return candidate
    raise RuntimeError("同梱のpptxdsl生成コードが見つかりません")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "check", "sheet"):
        entry = commands.add_parser(command)
        entry.add_argument("input")
        if command == "validate":
            entry.add_argument("--asset-dir")
    generate = commands.add_parser("generate")
    generate.add_argument("content")
    generate.add_argument("output")
    generate.add_argument("--cover-footer-config", "--template-config")
    generate.add_argument("--asset-dir")
    template = commands.add_parser("template")
    template.add_argument("output")
    template.add_argument("--background-color", default="F7F5EF")
    template.add_argument("--background-image")
    template.add_argument("--cover-background-image")
    template.add_argument("--footer-text", default="{footer}")
    render = commands.add_parser("render")
    render.add_argument("pptx")
    render.add_argument("output")
    render.add_argument("--backend", choices=("auto", "powerpoint", "libreoffice"), default="auto")
    render.add_argument("--width", type=int, default=1600)
    render.add_argument("--slides")
    commands.add_parser("probe")
    commands.add_parser("fonts")
    raster = commands.add_parser("raster")
    raster.add_argument("manifest")
    raster.add_argument("png_dir")
    raster.add_argument("--report", required=True)
    args = parser.parse_args()
    try:
        root = project_root()
    except RuntimeError as error:
        print(f"NG: {error}", file=sys.stderr)
        return 2
    scripts = {
        "validate": root / "slidegen/validate_content.py",
        "generate": root / "slidegen/generate_from_json.py",
        "check": root / "slidegen/check_layout.py",
        "sheet": root / "contact_sheet.py",
        "render": Path(__file__).with_name("render_preview.py"),
        "probe": Path(__file__).with_name("render_preview.py"),
        "fonts": root / "slidegen/font_config.py",
        "raster": root / "slidegen/raster_qa.py",
        "template": root / "slidegen/template_config.py",
    }
    command = [sys.executable, str(scripts[args.command])]
    if args.command == "generate":
        command.extend([args.content, args.output])
        if args.cover_footer_config:
            command.extend(["--cover-footer-config", args.cover_footer_config])
    elif args.command == "template":
        command.extend([args.output, "--background-color", args.background_color,
                        "--footer-text", args.footer_text])
        for option in ("background_image", "cover_background_image"):
            if getattr(args, option):
                command.extend(["--" + option.replace("_", "-"), getattr(args, option)])
    elif args.command == "render":
        command.extend([args.pptx, args.output, "--backend", args.backend,
                        "--width", str(args.width)])
        if args.slides:
            command.extend(["--slides", args.slides])
    elif args.command == "probe":
        command.append("--probe")
    elif args.command == "raster":
        command.extend([args.manifest, args.png_dir, "--report", args.report])
    elif args.command != "fonts":
        command.append(args.input)
    if args.command in ("validate", "generate") and args.asset_dir:
        command.extend(["--asset-dir", args.asset_dir])
    # 入出力は呼び出し元の作業領域。インストール先へのchdirはしない。
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
