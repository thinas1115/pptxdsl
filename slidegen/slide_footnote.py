"""typeから独立したスライド下部の任意補足欄。"""
from dataclasses import dataclass

from slidegen.layout_fit import select_fit, stepped
from slidegen.textfit import line_height_in, wrap_compact


@dataclass(frozen=True)
class FootnoteLayout:
    size: float
    label_size: float
    lines: tuple
    label_lines: tuple
    label_width: float
    height: float
    padding: float
    stage: str


def fit_footnote(spec, width):
    """標準余白、余白圧縮、文字縮小の順で補足を収容する。"""
    label = spec.get("label", "")
    label_width = 1.55 if label else 0.0
    text_width = width - label_width

    def candidate(size, padding):
        label_size = max(10.0, size - 1.5)
        lines = tuple(wrap_compact(spec["text"], text_width, size))
        label_lines = tuple(wrap_compact(label, label_width - 0.16, label_size, "bold")) if label else ()
        height = max(len(lines) * line_height_in(size, 1.12),
                     len(label_lines) * line_height_in(label_size, 1.12)) + 0.04
        values = dict(size=size, label_size=label_size, lines=lines,
                      label_lines=label_lines, label_width=label_width,
                      height=height, padding=padding)
        return values, height + padding * 2

    def candidates():
        values, used = candidate(13.0, 0.12)
        yield "standard", values, used
        for padding in stepped(0.10, 0.06, 0.02):
            values, used = candidate(13.0, padding)
            yield "gap", values, used
        for size in stepped(12.5, 11.5, 0.5):
            values, used = candidate(size, 0.06)
            yield "font", values, used

    fitted = select_fit("footnote", 0.80, candidates(),
                        guidance="補足の文言を短くするか、詳細を本文へ移してください。")
    return FootnoteLayout(**fitted.values, stage=fitted.stage)
