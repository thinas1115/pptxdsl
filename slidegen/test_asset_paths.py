"""画像資産ディレクトリと旧アイコン指定の互換性を検証する。"""
from asset_paths import AWS_ICON_DIR, FLUENT_ICON_DIR, resolve_icon_path


def main():
    assert resolve_icon_path("icons/aws/rds.png") == AWS_ICON_DIR / "rds.png"
    assert resolve_icon_path("icons/fluent/server.png") == (
        FLUENT_ICON_DIR / "server.png"
    )

    # 既存content.jsonの指定はディレクトリ整理後も利用できる。
    assert resolve_icon_path("rds.png") == AWS_ICON_DIR / "rds.png"
    assert resolve_icon_path("fluent/server.png") == (
        FLUENT_ICON_DIR / "server.png"
    )

    assert resolve_icon_path("icons/aws/rds.png").is_file()
    assert resolve_icon_path("icons/fluent/server.png").is_file()

    try:
        resolve_icon_path("../../outside.png")
    except ValueError:
        pass
    else:
        raise AssertionError("assets外へのパスを拒否できませんでした")

    print("asset path tests passed")


if __name__ == "__main__":
    main()
