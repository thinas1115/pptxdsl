"""巻末の参考資料を、実URL付きで表示する専用renderer。"""

from pptx.enum.text import MSO_ANCHOR, PP_ALIGN

from slidegen.generate import (
    ACCENT, BODY_W, GRAY, LIGHT, MARGIN, NAVY, RULE, SURFACE, TEXT,
    add_rect, add_text, header,
)
from slidegen.layout_fit import fit_text_or_raise, select_fit, stepped
from slidegen.textfit import line_height_in, wrap_text


def _fit_references(area, entries):
    available = area.height - 0.24

    def measure(values):
        heights = []
        for entry in entries:
            title_lines = wrap_text(entry["title"], 7.35, values["title"], "bold")
            url_lines = wrap_text(entry["url"], 7.35, values["url"], "regular")
            scope_lines = wrap_text(entry.get("scope", ""), 2.45, values["scope"], "regular")
            content_h = (
                len(title_lines) * line_height_in(values["title"], 1.08)
                + values["inside"]
                + len(url_lines) * line_height_in(values["url"], 1.03)
            )
            scope_h = len(scope_lines) * line_height_in(values["scope"], 1.08)
            heights.append(max(values["min_row"], content_h + 0.18, scope_h + 0.18))
        return heights, sum(heights) + max(0, len(entries) - 1) * values["gap"]

    def candidates():
        standard = {"title": 13.0, "url": 9.0, "scope": 11.0,
                    "inside": 0.07, "gap": 0.10, "min_row": 0.76}
        heights, used = measure(standard)
        yield "standard", (standard, heights), used
        for gap in stepped(0.08, 0.04, 0.02):
            values = dict(standard, gap=gap, min_row=0.72)
            heights, used = measure(values)
            yield "gap", (values, heights), used
        for title_size in stepped(12.5, 11.0, 0.5):
            values = {"title": title_size, "url": max(8.0, title_size - 4.0),
                      "scope": max(9.5, title_size - 2.0), "inside": 0.05,
                      "gap": 0.04, "min_row": 0.66}
            heights, used = measure(values)
            yield "font", (values, heights), used

    return select_fit(
        "references", available, candidates(),
        guidance="参考資料を5件以内に分けるか、タイトルを短くしてください。",
    )


def s_references(slide, spec, page):
    area = header(slide, spec["kicker"], spec["title"], spec.get("lead"))
    entries = spec["references"]
    fitted = _fit_references(area, entries)
    values, row_heights = fitted.values
    y = area.top + 0.12
    number_w = 0.72
    content_x = MARGIN + number_w + 0.18
    content_w = 7.35
    scope_x = content_x + content_w + 0.28
    scope_w = MARGIN + BODY_W - scope_x

    for index, (entry, row_h) in enumerate(zip(entries, row_heights)):
        fill = SURFACE if index % 2 else LIGHT
        panel = add_rect(slide, MARGIN, y, BODY_W, row_h, fill)
        panel.name = f"references:row[{index}]"
        add_text(slide, MARGIN + 0.10, y, number_w - 0.12, row_h,
                 entry["id"], 11.0, bold=True, color=NAVY,
                 anchor=MSO_ANCHOR.MIDDLE)
        title_h = min(0.40, row_h * 0.42)
        title_size, title_lines = fit_text_or_raise(
            "references", f"references[{index}].title", entry["title"],
            content_w, title_h, values["title"], min_pt=11.0,
            weight="bold", spacing=1.08,
        )
        add_text(slide, content_x, y + 0.10, content_w, title_h,
                 "\n".join(title_lines), title_size, bold=True, color=NAVY,
                 spacing=1.08)
        url_y = y + 0.10 + title_h + values["inside"]
        url_h = row_h - (url_y - y) - 0.08
        url_size, url_lines = fit_text_or_raise(
            "references", f"references[{index}].url", entry["url"],
            content_w, url_h, values["url"], min_pt=8.0, spacing=1.03,
        )
        url_box = add_text(slide, content_x, url_y, content_w, url_h,
                           "\n".join(url_lines), url_size, color=ACCENT,
                           spacing=1.03)
        url_box.name = f"references:url[{index}]"
        for paragraph in url_box.text_frame.paragraphs:
            for run in paragraph.runs:
                run.font.underline = True
                run.hyperlink.address = entry["url"]
        if entry.get("scope"):
            scope_size, scope_lines = fit_text_or_raise(
                "references", f"references[{index}].scope", entry["scope"],
                scope_w, row_h - 0.18, values["scope"], min_pt=9.5,
                spacing=1.08,
            )
            add_text(slide, scope_x, y + 0.09, scope_w, row_h - 0.18,
                     "\n".join(scope_lines), scope_size, color=GRAY,
                     align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE,
                     spacing=1.08)
        if index < len(entries) - 1:
            add_rect(slide, MARGIN, y + row_h + values["gap"] / 2,
                     BODY_W, 0.008, RULE)
        y += row_h + values["gap"]
