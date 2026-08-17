"""スライドPNG群を1枚のコンタクトシート(グリッド画像)に合成する。

AI目視のToken節約用: 全枚を1回のReadで俯瞰し、怪しいスライドだけ
render.ps1 -Slides で高解像度に出し直して確認する。

使い方: python contact_sheet.py out\\png [列数=4] [タイル幅=400]
出力:   <dir>\\sheet.png
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

def main(png_dir, cols=4, tile_w=400):
    d = Path(png_dir)
    files = list(d.glob("slide_*.png")) + list(d.glob("slide-*.png"))
    files.sort(key=lambda path: int(path.stem.replace("slide_", "").replace("slide-", "")))
    if not files:
        sys.exit(f"no slide_*.png or slide-*.png in {d}")
    tile_h = tile_w * 9 // 16
    label_h = 18
    rows = (len(files) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile_w, rows * (tile_h + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    for i, f in enumerate(files):
        img = Image.open(f).resize((tile_w, tile_h))
        x = (i % cols) * tile_w
        y = (i // cols) * (tile_h + label_h)
        sheet.paste(img, (x, y + label_h))
        draw.text((x + 4, y + 2), f.stem, fill="black")
        draw.rectangle([x, y + label_h, x + tile_w - 1, y + label_h + tile_h - 1],
                       outline="#cccccc")
    out = d / "sheet.png"
    sheet.save(out)
    print(f"wrote {out} ({sheet.width}x{sheet.height}, {len(files)} slides)")

if __name__ == "__main__":
    main(sys.argv[1],
         int(sys.argv[2]) if len(sys.argv) > 2 else 4,
         int(sys.argv[3]) if len(sys.argv) > 3 else 400)
