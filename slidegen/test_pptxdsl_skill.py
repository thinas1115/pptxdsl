"""pptxdsl Skillの参照整合性とレンダリングbackend選択を検証する。"""

from pathlib import Path
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from unittest.mock import patch

from pptx import Presentation


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / ".agents" / "skills" / "pptxdsl"
SCRIPT = SKILL_DIR / "scripts" / "render_preview.py"

spec = importlib.util.spec_from_file_location("render_preview", SCRIPT)
assert spec and spec.loader
render_preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render_preview)


def _run_repo_command(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    assert result.returncode == 0, (
        f"command failed: {args}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    return result


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


def test_content_to_pptx_smoke() -> None:
    deck = {
        "meta": {"title": "Skill動作確認"},
        "slides": [
            {
                "type": "title",
                "title": "Skill動作確認",
                "subtitle": "新規JSONからPPTXを生成する受け入れ試験",
            },
            {
                "type": "bullets",
                "style": "numbered",
                "kicker": "INPUT",
                "title": "入力内容",
                "bullets": [
                    {"text": "資料の目的と読み手を確認する"},
                    {"text": "内容構造に合うtypeを選択する"},
                    {"text": "許可フィールドだけでJSONを記述する"},
                ],
            },
            {
                "type": "process",
                "kicker": "VERIFY",
                "title": "検証工程",
                "steps": [
                    {"name": "入力検証", "desc": "schema違反を検出します。"},
                    {"name": "資料生成", "desc": "PPTXファイルを生成します。"},
                    {"name": "配置検査", "desc": "はみ出しと重なりを検査します。"},
                ],
            },
        ],
    }
    with tempfile.TemporaryDirectory(prefix="pptxdsl-skill-e2e-") as temp_name:
        temp_dir = Path(temp_name)
        content_path = temp_dir / "content.json"
        pptx_path = temp_dir / "deck.pptx"
        content_path.write_text(
            json.dumps(deck, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        _run_repo_command("slidegen/validate_content.py", str(content_path))
        _run_repo_command(
            "slidegen/generate_from_json.py", str(content_path), str(pptx_path)
        )
        _run_repo_command("slidegen/check_layout.py", str(pptx_path))

        assert pptx_path.is_file() and pptx_path.stat().st_size > 0
        assert len(Presentation(pptx_path).slides) == len(deck["slides"])


def main() -> None:
    test_skill_links()
    test_slide_number_parser()
    test_libreoffice_page_selection()
    test_auto_backend_fallback()
    test_content_to_pptx_smoke()
    print("pptxdsl skill: ALL OK")


if __name__ == "__main__":
    main()
