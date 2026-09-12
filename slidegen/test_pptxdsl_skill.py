"""pptxdsl Skillの参照整合性とレンダリングbackend選択を検証する。"""

from pathlib import Path
import importlib.util
import re
import subprocess
import tempfile
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / ".agents" / "skills" / "pptxdsl"
SCRIPT = SKILL_DIR / "scripts" / "render_preview.py"

spec = importlib.util.spec_from_file_location("render_preview", SCRIPT)
assert spec and spec.loader
render_preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render_preview)


def _broken_local_links(markdown: Path) -> list[str]:
    text = markdown.read_text(encoding="utf-8")
    links = re.findall(r"\[[^]]+\]\(([^)]+)\)", text)
    broken = []
    for link in links:
        if link.startswith(("http://", "https://", "#")):
            continue
        target = link.split("#", 1)[0]
        if target and not (markdown.parent / target).exists():
            broken.append(link)
    return broken


def test_skill_links() -> None:
    skill_file = SKILL_DIR / "SKILL.md"
    text = skill_file.read_text(encoding="utf-8")
    assert re.search(r"\[[^]]+\]\(([^)]+)\)", text), (
        "SKILL.mdから内部リファレンスが見つかりません"
    )
    for markdown in (ROOT / "AGENTS.md", ROOT / "README.md", skill_file):
        broken = _broken_local_links(markdown)
        assert not broken, f"{markdown.name}に存在しないリンクがあります: {broken}"
    assert render_preview.REPO_ROOT == ROOT
    for required in (
        "AGENTS.md",
        "CONTENT_SCHEMA.md",
        "docs/type-selection-guide.md",
        "contact_sheet.py",
        "render.ps1",
    ):
        assert (ROOT / required).is_file(), f"Skillが参照するファイルがありません: {required}"


def test_slide_number_parser() -> None:
    assert render_preview._slide_numbers("3,1,3") == [3, 1]
    try:
        render_preview._slide_numbers("0")
    except render_preview.RenderError:
        pass
    else:
        raise AssertionError("0をスライド番号として受理しました")


def test_libreoffice_page_selection() -> None:
    def fake_run(command: list[str]) -> subprocess.CompletedProcess[str]:
        if "--convert-to" in command:
            out_index = command.index("--outdir") + 1
            input_path = Path(command[-1])
            Path(command[out_index], f"{input_path.stem}.pdf").write_bytes(b"pdf")
        return subprocess.CompletedProcess(command, 0, "", "")

    def fake_pdf_render(
        pdf: Path, temp_dir: Path, width: int, executable: str
    ) -> list[Path]:
        assert pdf.is_file()
        assert width == 800
        assert executable == "pdftoppm"
        pages = []
        for number in range(1, 4):
            page = temp_dir / f"page-{number}.png"
            page.write_bytes(f"page {number}".encode())
            pages.append(page)
        return pages

    details = {
        "libreoffice": {
            "office_cli": "soffice",
            "pdftoppm": "pdftoppm",
            "pymupdf": False,
        }
    }
    with tempfile.TemporaryDirectory(prefix="pptxdsl-skill-test-") as temp_name:
        temp_dir = Path(temp_name)
        pptx = temp_dir / "deck.pptx"
        pptx.write_bytes(b"pptx")
        out_dir = temp_dir / "png"
        with patch.object(render_preview, "_run", side_effect=fake_run), patch.object(
            render_preview, "_render_pdf_with_pdftoppm", side_effect=fake_pdf_render
        ):
            count = render_preview._render_libreoffice(
                pptx, out_dir, 800, [2], details
            )
        assert count == 1
        assert (out_dir / "slide_02.png").read_bytes() == b"page 2"
        assert not (out_dir / "slide_01.png").exists()


def test_auto_backend_fallback() -> None:
    details = {
        "available_backends": ["powerpoint", "libreoffice"],
        "powerpoint": {},
        "libreoffice": {},
    }
    with tempfile.TemporaryDirectory(prefix="pptxdsl-skill-test-") as temp_name:
        temp_dir = Path(temp_name)
        pptx = temp_dir / "deck.pptx"
        pptx.write_bytes(b"pptx")
        with patch.object(render_preview, "probe", return_value=details), patch.object(
            render_preview,
            "_render_powerpoint",
            side_effect=render_preview.RenderError("PowerPoint失敗"),
        ), patch.object(render_preview, "_render_libreoffice", return_value=2):
            backend, count = render_preview.render(
                pptx, temp_dir / "png", 800, None, "auto"
            )
        assert (backend, count) == ("libreoffice", 2)


def main() -> None:
    test_skill_links()
    test_slide_number_parser()
    test_libreoffice_page_selection()
    test_auto_backend_fallback()
    print("pptxdsl skill: ALL OK")


if __name__ == "__main__":
    main()
