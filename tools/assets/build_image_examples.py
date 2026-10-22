"""実在サービスや個人情報を含まない、コード製の画面説明用図版を作る。"""
from io import BytesIO
from pathlib import Path

from reportlab.graphics import renderPM
from svglib.svglib import svg2rlg


ROOT = Path(__file__).resolve().parents[2]
# 同じベクター図版から全体と注目領域を描く。既存のスクリーンショットは編集しない。
SCENE = '''
<rect width="1600" height="900" fill="#F3F5F7"/>
<rect width="1600" height="90" fill="#182C43"/>
<text x="40" y="58" fill="white" font-size="34">DEMO / Request desk</text>
<rect y="90" width="280" height="810" fill="#E4EBEF"/>
<g fill="#182C43" font-size="28">
<text x="36" y="170">Overview</text><text x="36" y="250">Requests</text>
<text x="36" y="330">History</text><text x="36" y="410">Settings</text>
<text x="340" y="165" font-size="36">Request DEMO-001</text>
<text x="340" y="214" font-size="24">Fictional interface / no real account or operation</text>
</g>
<rect x="340" y="270" width="1180" height="490" rx="8" fill="white" stroke="#007F78" stroke-width="6"/>
<circle cx="370" cy="300" r="24" fill="#007F78"/>
<text x="362" y="310" fill="white" font-size="28">1</text>
<g fill="#182C43" font-size="30">
<text x="420" y="330" font-weight="bold">Notification settings</text>
<text x="400" y="410">Target</text>
<text x="400" y="510">Event</text>
</g>
<rect x="690" y="365" width="740" height="66" rx="4" fill="#F3F5F7" stroke="#52636D"/>
<rect x="690" y="465" width="740" height="66" rx="4" fill="#F3F5F7" stroke="#52636D"/>
<g fill="#182C43" font-size="30">
<text x="715" y="410">Demo team</text><text x="715" y="510">Request received</text>
<text x="400" y="590" font-size="25">Check target and event, then save.</text>
</g>
<rect x="1140" y="635" width="290" height="76" rx="5" fill="#007F78"/>
<text x="1240" y="685" fill="white" font-size="32">Save</text>
<text x="340" y="830" fill="#52636D" font-size="24">DEMO ONLY — no changes are sent anywhere.</text>
'''


def main():
    output = ROOT / "slidegen/assets/images"
    for name, width, height, viewbox in (
        ("demo-request-overview", 1600, 900, "0 0 1600 900"),
        ("demo-request-focus", 1220, 530, "320 250 1220 530"),
    ):
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
               f'viewBox="{viewbox}" font-family="Helvetica">{SCENE}</svg>')
        drawing = svg2rlg(BytesIO(svg.encode("utf-8")))
        renderPM.drawToFile(drawing, str(output / f"{name}.png"), fmt="PNG", dpi=96, backend="rlPyCairo")
        print(f"図版生成: {name}.png")


if __name__ == "__main__":
    main()
