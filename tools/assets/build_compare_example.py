"""同一の架空申請画面の変更前後を描く公開用比較素材。"""
from pathlib import Path

from PIL import Image, ImageDraw

from slidegen.textfit import _font


def build(output):
    output.mkdir(parents=True, exist_ok=True)
    for improved in (False, True):
        image = Image.new("RGB", (1360, 900), "#f3f5f7")
        draw = ImageDraw.Draw(image)

        def text(x, y, value, size=19, color="#26394b", bold=False):
            draw.text((x, y), value, font=_font("bold" if bold else "regular", size), fill=color)

        draw.rectangle((0, 0, 1360, 86), fill="#182c43")
        text(46, 22, "WORKSPACE  /  サービス申請", 26, "white", True)
        text(54, 120, "申請一覧", 32, bold=True)
        text(54, 181, "サンプル画面・架空の申請データ", 17, "#667780")
        draw.rounded_rectangle((48, 245, 1312, 360), radius=12, fill="white")
        text(76, 266, "表示条件", 16, "#667780")
        text(76, 302, "担当: 自分     状態: 承認待ち" if improved else "すべての申請", 21, bold=improved)
        if improved:
            draw.rounded_rectangle((1010, 277, 1278, 337), radius=8, fill="#0d7870")
            text(1038, 289, "条件を変更", 21, "white", True)
        draw.rounded_rectangle((48, 400, 1312, 794), radius=12, fill="white")
        columns = [(76, "申請名"), (655, "申請日"), (876, "状態"), (1100, "担当")]
        for x, value in columns:
            text(x, 421, value, 18, "#667780", True)
        rows = [("検証用アカウント", "10/01", "承認待ち"),
                ("開発環境の利用", "10/02", "承認待ち"),
                ("共有ストレージ", "10/03", "承認待ち")]
        for index, (title, date, status) in enumerate(rows):
            y = 488 + index * 96
            draw.line((76, y - 12, 1280, y - 12), fill="#dee4e9", width=2)
            text(76, y + 12, title, 23, bold=improved)
            text(655, y + 12, date, 21)
            if improved:
                draw.rounded_rectangle((858, y + 2, 1040, y + 56), radius=8, fill="#dceeea")
            text(880, y + 12, status, 20, "#0d7870" if improved else "#26394b", improved)
            text(1100, y + 12, "自分", 21)
        text(54, 835, "3件の申請を表示", 17, "#667780")
        image.save(output / ("request-list-after.png" if improved else "request-list-before.png"))


if __name__ == "__main__":
    build(Path("slidegen/assets/images"))
