"""Fluentアイコン定義と同梱PNGの整合を検証する。"""
from PIL import Image

from fetch_fluent_icons import ICONS, OUT_DIR, PX


def main():
    expected = {f"{name}.png" for name in ICONS}
    actual = {path.name for path in OUT_DIR.glob("*.png")}
    assert actual == expected, (
        f"missing={sorted(expected - actual)}, extra={sorted(actual - expected)}")

    for name in sorted(expected):
        with Image.open(OUT_DIR / name) as image:
            image.verify()
        with Image.open(OUT_DIR / name) as image:
            assert image.format == "PNG", name
            assert image.size == (PX, PX), f"{name}: {image.size}"
            assert image.mode == "RGBA", f"{name}: {image.mode}"
            alpha = image.getchannel("A")
            assert alpha.getextrema() == (0, 255), f"{name}: alpha range"
            bbox = alpha.getbbox()
            center_x = (bbox[0] + bbox[2]) / 2
            center_y = (bbox[1] + bbox[3]) / 2
            assert abs(center_x - PX / 2) <= 0.5, f"{name}: center_x={center_x}"
            assert abs(center_y - PX / 2) <= 0.5, f"{name}: center_y={center_y}"
    print(f"OK: {len(expected)} Fluent icons are centered transparent PNGs")


if __name__ == "__main__":
    main()
