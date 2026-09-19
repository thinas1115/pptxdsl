#!/usr/bin/env python3
"""実行環境で利用可能なbackendを選び、PPTXをスライド単位のPNGへ変換する。"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


def _project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        for candidate in (parent / "project", parent):
            if (candidate / "slidegen/generate_from_json.py").is_file():
                return candidate
    raise RuntimeError("同梱のpptxdsl生成コードが見つかりません")


REPO_ROOT = _project_root()
RENDER_PS1 = REPO_ROOT / "render.ps1"


class RenderError(RuntimeError):
    pass


def _which(*names: str) -> str | None:
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None


def _powerpoint_registered() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"PowerPoint.Application\CLSID"):
            return True
    except (FileNotFoundError, OSError):
        return False


def probe() -> dict[str, object]:
    powershell = (
        _which("powershell", "pwsh")
        if sys.platform == "win32"
        else _which("pwsh", "powershell")
    )
    office = _which("soffice", "libreoffice")
    pdftoppm = _which("pdftoppm")
    pymupdf = importlib.util.find_spec("fitz") is not None
    powerpoint = bool(
        sys.platform == "win32"
        and powershell
        and RENDER_PS1.is_file()
        and _powerpoint_registered()
    )
    libreoffice = bool(office and (pdftoppm or pymupdf))
    return {
        "platform": sys.platform,
        "available_backends": [
            name
            for name, available in (
                ("powerpoint", powerpoint),
                ("libreoffice", libreoffice),
            )
            if available
        ],
        "powerpoint": {
            "available": powerpoint,
            "powershell": powershell,
            "render_script": str(RENDER_PS1) if RENDER_PS1.is_file() else None,
            "com_registered": _powerpoint_registered(),
        },
        "libreoffice": {
            "available": libreoffice,
            "office_cli": office,
            "pdftoppm": pdftoppm,
            "pymupdf": pymupdf,
        },
    }


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        check=False,
    )
    if result.returncode:
        output = result.stdout.strip()
        raise RenderError(output or f"command failed with exit code {result.returncode}")
    return result


def _slide_numbers(value: str | None) -> list[int]:
    if not value:
        return []
    numbers: list[int] = []
    for token in value.split(","):
        token = token.strip()
        if not token or not token.isdigit() or int(token) < 1:
            raise RenderError("--slidesは1以上のスライド番号をカンマ区切りで指定してください")
        number = int(token)
        if number not in numbers:
            numbers.append(number)
    return numbers


def _clear_all_slide_pngs(out_dir: Path) -> None:
    for pattern in ("slide_*.png", "slide-*.png"):
        for path in out_dir.glob(pattern):
            if path.is_file():
                path.unlink()


def _render_powerpoint(
    pptx: Path, out_dir: Path, width: int, slides: list[int], details: dict[str, object]
) -> int:
    powerpoint_info = details["powerpoint"]
    if not isinstance(powerpoint_info, dict):
        raise RenderError("PowerPointの検出結果を読み取れません")
    powershell = powerpoint_info.get("powershell")
    if not isinstance(powershell, str):
        raise RenderError("PowerShellが見つかりません")
    out_dir.mkdir(parents=True, exist_ok=True)
    if not slides:
        _clear_all_slide_pngs(out_dir)
    else:
        for number in slides:
            target = out_dir / f"slide_{number:02d}.png"
            if target.is_file():
                target.unlink()
    command = [
        powershell,
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(RENDER_PS1),
        "-PptxPath",
        str(pptx),
        "-OutDir",
        str(out_dir),
        "-Width",
        str(width),
    ]
    if slides:
        command.extend(["-Slides", ",".join(str(number) for number in slides)])
    _run(command)
    rendered = list(out_dir.glob("slide_*.png"))
    missing = [
        number for number in slides if not (out_dir / f"slide_{number:02d}.png").is_file()
    ]
    if missing:
        raise RenderError(f"存在しないスライド番号です: {','.join(map(str, missing))}")
    if not rendered:
        raise RenderError("PowerPointは終了しましたがPNGが生成されませんでした")
    return len(rendered) if not slides else len(slides)


def _page_number(path: Path) -> int:
    match = re.search(r"-(\d+)$", path.stem)
    if not match:
        raise RenderError(f"PDF画像のページ番号を判定できません: {path.name}")
    return int(match.group(1))


def _render_pdf_with_pdftoppm(
    pdf: Path, temp_dir: Path, width: int, executable: str
) -> list[Path]:
    prefix = temp_dir / "page"
    _run(
        [
            executable,
            "-png",
            "-scale-to-x",
            str(width),
            "-scale-to-y",
            "-1",
            str(pdf),
            str(prefix),
        ]
    )
    return sorted(temp_dir.glob("page-*.png"), key=_page_number)


def _render_pdf_with_pymupdf(pdf: Path, temp_dir: Path, width: int) -> list[Path]:
    import fitz

    rendered: list[Path] = []
    document = fitz.open(pdf)
    try:
        for index, page in enumerate(document, start=1):
            scale = width / page.rect.width
            pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            output = temp_dir / f"page-{index}.png"
            pixmap.save(output)
            rendered.append(output)
    finally:
        document.close()
    return rendered


def _render_libreoffice(
    pptx: Path, out_dir: Path, width: int, slides: list[int], details: dict[str, object]
) -> int:
    office_info = details["libreoffice"]
    if not isinstance(office_info, dict):
        raise RenderError("LibreOfficeの検出結果を読み取れません")
    office = office_info.get("office_cli")
    if not isinstance(office, str):
        raise RenderError("LibreOfficeのCLIが見つかりません")
    out_dir.mkdir(parents=True, exist_ok=True)
    if not slides:
        _clear_all_slide_pngs(out_dir)

    with tempfile.TemporaryDirectory(prefix="pptxdsl-render-") as temp_name:
        temp_dir = Path(temp_name)
        _run(
            [
                office,
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(temp_dir),
                str(pptx),
            ]
        )
        pdf = temp_dir / f"{pptx.stem}.pdf"
        if not pdf.is_file():
            raise RenderError("LibreOfficeは終了しましたがPDFが生成されませんでした")

        pdftoppm = office_info.get("pdftoppm")
        if isinstance(pdftoppm, str):
            pages = _render_pdf_with_pdftoppm(pdf, temp_dir, width, pdftoppm)
        elif bool(office_info.get("pymupdf")):
            pages = _render_pdf_with_pymupdf(pdf, temp_dir, width)
        else:
            raise RenderError("PDFをPNGへ変換する手段が見つかりません")

        if not pages:
            raise RenderError("PDFは生成されましたがページ画像を取得できませんでした")

        selected = slides or list(range(1, len(pages) + 1))
        missing = [number for number in selected if number > len(pages)]
        if missing:
            raise RenderError(f"存在しないスライド番号です: {','.join(map(str, missing))}")
        for number in selected:
            shutil.copyfile(pages[number - 1], out_dir / f"slide_{number:02d}.png")
        return len(selected)


def render(
    pptx: Path, out_dir: Path, width: int, slides_text: str | None, backend: str
) -> tuple[str, int]:
    if not pptx.is_file():
        raise RenderError(f"PPTXが見つかりません: {pptx}")
    if width < 320:
        raise RenderError("--widthは320以上を指定してください")
    slides = _slide_numbers(slides_text)
    details = probe()
    available_value = details["available_backends"]
    available = list(available_value) if isinstance(available_value, list) else []
    candidates = available if backend == "auto" else [backend]
    if backend != "auto" and backend not in available:
        raise RenderError(f"指定backendは利用できません: {backend}")
    if not candidates:
        raise RenderError(
            "利用可能なレンダリングbackendがありません。"
            "PowerPoint、またはLibreOfficeとpdftoppm/PyMuPDFの組み合わせを用意してください"
        )

    failures: list[str] = []
    for candidate in candidates:
        try:
            if candidate == "powerpoint":
                count = _render_powerpoint(pptx, out_dir, width, slides, details)
            else:
                count = _render_libreoffice(pptx, out_dir, width, slides, details)
            return str(candidate), count
        except RenderError as error:
            failures.append(f"{candidate}: {error}")
            if backend != "auto":
                break
    raise RenderError("; ".join(failures))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pptx", nargs="?", type=Path)
    parser.add_argument("out_dir", nargs="?", type=Path)
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--slides", help="例: 3,7")
    parser.add_argument(
        "--backend", choices=("auto", "powerpoint", "libreoffice"), default="auto"
    )
    parser.add_argument("--probe", action="store_true", help="利用可能なbackendをJSONで表示する")
    args = parser.parse_args()

    if args.probe:
        print(json.dumps(probe(), ensure_ascii=False, indent=2))
        return 0
    if args.pptx is None or args.out_dir is None:
        parser.error("pptxとout_dirを指定してください。調査だけなら--probeを使います")

    try:
        backend, count = render(
            args.pptx.resolve(),
            args.out_dir.resolve(),
            args.width,
            args.slides,
            args.backend,
        )
    except RenderError as error:
        print(f"render error: {error}", file=sys.stderr)
        return 2
    print(f"renderer={backend} slides={count} out={args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
