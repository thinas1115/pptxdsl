"""段階的収容ポリシーの単体検証。"""
from layout_fit import (
    FitError,
    fit_text_or_raise,
    fit_vertical_stacks,
    select_fit,
    stepped,
)


def main():
    assert list(stepped(1.0, 0.8, 0.1)) == [1.0, 0.9, 0.8]

    result = select_fit(
        "sample", 4.0,
        [
            ("standard", {"gap": 0.5}, 4.3),
            ("gap", {"gap": 0.3}, 3.9),
            ("scale", {"gap": 0.3, "size": 0.5}, 3.6),
        ],
        guidance="項目を減らしてください。",
    )
    assert result.stage == "gap"
    assert result.values["gap"] == 0.3

    result = select_fit(
        "sample", 3.7,
        [
            ("standard", {"gap": 0.5}, 4.3),
            ("gap", {"gap": 0.3}, 3.9),
            ("scale", {"gap": 0.3, "size": 0.5}, 3.6),
        ],
        guidance="項目を減らしてください。",
    )
    assert result.stage == "scale"
    assert result.values["size"] == 0.5

    packed = fit_vertical_stacks(
        "sample.stack", 4.5, [[2, 2], [1]],
        lambda item, size: item * size,
        standard_size=1.0, min_size=0.5, font_step=0.25,
        standard_gap=1.0, min_gap=0.5, gap_step=0.5,
        guidance="項目を減らしてください。",
    )
    assert packed.stage == "gap"
    assert packed.size == 1.0
    assert packed.gap == 0.5
    assert packed.stacks == [[2.0, 2.0], [1.0]]
    assert packed.used == 4.5

    packed = fit_vertical_stacks(
        "sample.stack", 3.5, [[2, 2]],
        lambda item, size: item * size,
        standard_size=1.0, min_size=0.5, font_step=0.25,
        standard_gap=1.0, min_gap=0.5, gap_step=0.5,
        guidance="項目を減らしてください。",
    )
    assert packed.stage == "font"
    assert packed.size == 0.75
    assert packed.used == 3.5

    try:
        fit_vertical_stacks(
            "sample.stack", 1.0, [[2, 2]],
            lambda item, size: item * size,
            standard_size=1.0, min_size=0.5, font_step=0.25,
            standard_gap=1.0, min_gap=0.5, gap_step=0.5,
            guidance="項目を減らしてください。",
        )
    except FitError as e:
        assert "sample.stack" in str(e)
        assert "不足" in str(e)
    else:
        raise AssertionError("過密な縦詰めを拒否しませんでした")

    size, lines = fit_text_or_raise(
        "sample", "body", "短い本文", 2.0, 0.5, 14, min_pt=11,
    )
    assert size == 14
    assert len(lines) == 1

    try:
        fit_text_or_raise(
            "sample", "body", "長い本文" * 100, 1.0, 0.2, 14,
            min_pt=11,
        )
    except FitError as e:
        assert "不足" in str(e)
        assert "文言を短く" in str(e)
    else:
        raise AssertionError("過密テキストを拒否しませんでした")

    print("layout fit tests passed")


if __name__ == "__main__":
    main()
