"""Fluent UI System Icons (MIT) を取得し、図解用PNGに変換して assets/icons/fluent/ に置く。

使い方:
  python fetch_fluent_icons.py          # ICONS 全部
  python fetch_fluent_icons.py server database   # 指定分のみ
  python fetch_fluent_icons.py --list   # 利用可能な出力名を一覧表示

- 出典: https://github.com/microsoft/fluentui-system-icons (MITライセンス)。
  PowerPointの「挿入 > アイコン」と同じデザイン体系のアイコンセット。
- python-pptx はSVGを挿入できない(PIL依存)ため、svglib+reportlab でPNG化する。
  依存: pip install svglib reportlab rlPyCairo
  (rlPyCairo は reportlab 4.x のPNG描画バックエンド。無いと RenderPMError になる)
- 生成したPNGは slidegen/assets/CREDITS.md のクレジット表記とともにリポジトリに同梱する
  (MITライセンス。リカラー等の改変も許諾範囲内)。
- PNGは背景透過とし、SVGの実描画領域を256pxキャンバスの中央へ配置する。
- diagram仕様からは "icon": "icons/fluent/server.png" のように参照する。

アイコンを増やしたいときは ICONS に 出力名: リポジトリのassetsフォルダ名 を
追加する。フォルダ名は https://github.com/microsoft/fluentui-system-icons/tree/main/assets
で探す(例: "Lock Closed" のようにスペース入り)。
"""
import io
import re
import sys
import urllib.request
from urllib.error import HTTPError
from pathlib import Path

from PIL import Image, ImageChops
from reportlab.graphics import renderPM
from svglib.svglib import svg2rlg

# 出力名 → fluentui-system-icons/assets/ のフォルダ名
ICONS = {
    # インフラ・端末
    "server": "Server",
    "router": "Router",
    "database": "Database",
    "desktop": "Desktop",
    "laptop": "Laptop",
    "tablet": "Tablet",
    "phone": "Phone",
    "printer": "Print",
    "hard_drive": "Hard Drive",
    "storage": "Storage",

    # ネットワーク・クラウド
    "cloud": "Cloud",
    "globe": "Globe",
    "wifi": "WiFi 1",
    "ethernet": "Plug Connected",
    "link": "Link",
    "gateway": "Arrow Routing",
    "sync": "Arrow Sync",
    "upload": "Cloud Arrow Up",
    "download": "Cloud Arrow Down",
    "switch": "Arrow Swap",

    # セキュリティ
    "shield": "Shield",
    "shield_lock": "Shield Lock",
    "shield_check": "Shield Checkmark",
    "lock": "Lock Closed",
    "key": "Key",
    "certificate": "Certificate",

    # 人物・組織・拠点
    "people": "People",
    "team": "People Team",
    "person": "Person",
    "contact": "Contact Card",
    "organization": "Organization",
    "briefcase": "Briefcase",
    "building": "Building",
    "branch": "Building Multiple",
    "factory": "Building Factory",
    "store": "Building Retail",
    "warehouse": "Box Multiple",
    "home": "Home",

    # アプリ・データ・文書
    "app": "App Generic",
    "browser": "Window",
    "terminal": "Window Console",
    "code": "Code",
    "bot": "Bot",
    "ai": "Brain Circuit",
    "folder": "Folder",
    "document": "Document",
    "file_data": "Document Data",
    "archive": "Archive",

    # コミュニケーション・業務
    "mail": "Mail",
    "chat": "Chat",
    "video": "Video",
    "call": "Call",
    "send": "Send",
    "calendar": "Calendar",
    "task": "Task List Square LTR",
    "cart": "Cart",
    "money": "Money",
    "chart": "Data Bar Vertical",

    # 運用・状態
    "alert": "Alert",
    "warning": "Warning",
    "info": "Info",
    "check": "Checkmark Circle",
    "search": "Search",
    "clock": "Clock",
    "history": "History",
    "settings": "Settings",
    "toolbox": "Toolbox",
    "wrench": "Wrench",
    "monitor": "Pulse",

    # 物理移動
    "truck": "Vehicle Truck",
    "car": "Vehicle Car",
    "airplane": "Airplane",
}

BASE = ("https://raw.githubusercontent.com/microsoft/fluentui-system-icons/"
        "main/assets/{folder}/SVG/ic_fluent_{slug}_{size}_regular.svg")
COLOR = "#1F3864"   # generate.py の NAVY と合わせる
PX = 256            # 出力PNGの一辺(スライド上は0.62in≒60-120px で使うので十分)
OUT_DIR = Path(__file__).parent / "assets" / "icons" / "fluent"


def fetch_svg(folder: str) -> str:
    slug = folder.lower().replace(" ", "_")
    for size in (24, 20, 32, 16, 48):
        url = BASE.format(folder=urllib.request.quote(folder), slug=slug, size=size)
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return r.read().decode("utf-8")
        except HTTPError as e:
            if e.code != 404:
                raise
    raise RuntimeError(f"Fluentアイコンが見つかりません: {folder}")


def to_png(svg_text: str, out_path: Path):
    # Fluentのパス色(#212121 / currentColor)をスライドの配色に置換
    svg_text = svg_text.replace("#212121", COLOR).replace("currentColor", COLOR)
    m = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg_text)
    natural = int(m.group(1)) if m else 24
    drawing = svg2rlg(io.StringIO(svg_text))
    scale = PX / natural
    drawing.scale(scale, scale)
    drawing.width = drawing.height = PX
    renderPM.drawToFile(drawing, str(out_path), fmt="PNG")

    # renderPMは白背景で出力するため、指定色との合成率からalphaを復元する。
    # SVGのviewBox中心と実描画領域の中心は一致しないので、余白ではなく
    # 不透明ピクセルの外接矩形を基準にキャンバス中央へ移動する。
    rgb = Image.open(out_path).convert("RGB")
    fg = tuple(int(COLOR[i:i + 2], 16) for i in (1, 3, 5))

    def channel_alpha(channel, foreground):
        span = 255 - foreground
        return channel.point(
            lambda value: max(0, min(255, round((255 - value) * 255 / span))))

    channels = [channel_alpha(ch, color) for ch, color in zip(rgb.split(), fg)]
    alpha = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]),
                               channels[2])
    alpha = alpha.point(lambda value: 0 if value < 2 else value)

    icon = Image.new("RGBA", (PX, PX), (*fg, 0))
    icon.putalpha(alpha)
    bbox = alpha.getbbox()
    if not bbox:
        raise RuntimeError(f"Fluentアイコンの描画領域が空です: {out_path.name}")
    dx = round(PX / 2 - (bbox[0] + bbox[2]) / 2)
    dy = round(PX / 2 - (bbox[1] + bbox[3]) / 2)
    centered = Image.new("RGBA", (PX, PX), (0, 0, 0, 0))
    centered.alpha_composite(icon, (dx, dy))
    centered.save(out_path, "PNG")


def main(names):
    if names == ["--list"]:
        print("\n".join(sorted(ICONS)))
        print(f"total: {len(ICONS)}")
        return
    targets = {n: ICONS[n] for n in names} if names else ICONS
    unknown = [n for n in (names or []) if n not in ICONS]
    if unknown:
        raise SystemExit(f"未定義のアイコン名: {unknown}. ICONS に追加してください。"
                         f" 定義済み: {', '.join(sorted(ICONS))}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for out_name, folder in targets.items():
        out_path = OUT_DIR / f"{out_name}.png"
        to_png(fetch_svg(folder), out_path)
        print(f"wrote {out_path} ({folder})")
    print(f"done: {len(targets)} icons -> {OUT_DIR}")


if __name__ == "__main__":
    main(sys.argv[1:])
