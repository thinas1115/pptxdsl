"""巻末の参考資料を、実URL付きで表示する専用renderer。"""

from pptx.enum.text import MSO_ANCHOR, PP_ALIGN

from slidegen.generate import (
    ACCENT, BODY_W, LIGHT, MARGIN, NAVY, RULE, WHITE,
    add_rect, add_text, header,
)
from slidegen.layout_fit import fit_text_or_raise, select_fit, stepped
from slidegen.textfit import line_height_in, wrap_text


def _fit_references(area, entries):
    available = area.height - 0.18

    def measure(values):
        heights = []
        for entry in entries:
            title_lines = wrap_text(entry["title"], 8.30, values["title"], "bold")
            display_url = f"↗  {entry['url']}"
            url_lines = wrap_text(display_url, 10.55, values["url"], "regular")
            content_h = (
                len(title_lines) * line_height_in(values["title"], 1.04)
                + values["inside"]
                + len(url_lines) * line_height_in(values["url"], 1.00)
            )
            heights.append(max(values["min_row"], content_h + 0.25))
        return heights, sum(heights) + max(0, len(entries) - 1) * values["gap"]

    def candidates():
        standard = {
            "title": 14.5,
            "url": 9.5,
            "scope": 9.0,
            "inside": 0.06,
            "gap": 0.08,
            "min_row": 0.80 if len(entries) >= 5 else 0.92,
        }
        heights, used = measure(standard)
        yield "standard", (standard, heights), used
        for gap in stepped(0.06, 0.02, 0.02):
            values = dict(standard, gap=gap, min_row=0.76)
            heights, used = measure(values)
            yield "gap", (values, heights), used
        for title_size in stepped(14.0, 11.5, 0.5):
            values = {
                "title": title_size,
                "url": max(8.5, title_size - 5.0),
                "scope": 8.5,
                "inside": 0.04,
                "gap": 0.02,
                "min_row": 0.70,
            }
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
    y = area.top + 0.10
    badge_x = MARGIN + 0.02
    badge_w = 0.50
    content_x = MARGIN + 0.74
    content_w = 8.30
    scope_w = 1.65
    scope_x = MARGIN + BODY_W - scope_w
    url_w = scope_x + scope_w - content_x

    for index, (entry, row_h) in enumerate(zip(entries, row_heights)):
        # 全面塗りの表にはせず、番号・資料名・URLの順で読ませる編集リストにする。
        add_rect(slide, content_x, y, BODY_W - (content_x - MARGIN), 0.010, RULE)
        add_rect(slide, content_x, y, 0.88, 0.035, ACCENT)

        badge_y = y + 0.12
        badge = add_rect(slide, badge_x, badge_y, badge_w, 0.32, ACCENT, round_=True)
        badge.name = f"references:index[{index}]"
        add_text(
            slide, badge_x, badge_y, badge_w, 0.32, entry["id"], 9.0,
            bold=True, color=WHITE, align=PP_ALIGN.CENTER,
            anchor=MSO_ANCHOR.MIDDLE,
        )

        title_y = y + 0.10
        title_h = min(0.36, row_h * 0.40)
        title_size, title_lines = fit_text_or_raise(
            "references", f"references[{index}].title", entry["title"],
            content_w, title_h, values["title"], min_pt=11.0,
            weight="bold", spacing=1.04,
        )
        add_text(
            slide, content_x, title_y, content_w, title_h,
            "\n".join(title_lines), title_size, bold=True, color=NAVY,
            spacing=1.04,
        )

        if entry.get("scope"):
            scope_h = 0.28
            scope_y = y + 0.10
            scope_size, scope_lines = fit_text_or_raise(
                "references", f"references[{index}].scope", entry["scope"],
                scope_w, scope_h, values["scope"], min_pt=8.0,
                weight="bold", spacing=1.00,
            )
            add_rect(slide, scope_x, scope_y, scope_w, scope_h, LIGHT, round_=True)
            add_text(
                slide, scope_x + 0.08, scope_y, scope_w - 0.16, scope_h,
                "\n".join(scope_lines), scope_size, bold=True, color=ACCENT,
                align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE,
                spacing=1.00,
            )

        url_y = title_y + title_h + values["inside"]
        url_h = row_h - (url_y - y) - 0.10
        display_url = f"↗  {entry['url']}"
        url_size, url_lines = fit_text_or_raise(
            "references", f"references[{index}].url", display_url,
            url_w, url_h, values["url"], min_pt=8.5, spacing=1.00,
        )
        url_box = add_text(
            slide, content_x, url_y, url_w, url_h,
            "\n".join(url_lines), url_size, color=ACCENT, spacing=1.00,
        )
        url_box.name = f"references:url[{index}]"
        # 文字リンクにするとPowerPointが標準の青下線を強制するため、
        # 表示文字はテーマ色のままにして透明なクリック領域を重ねる。
        link_hit = add_rect(slide, content_x, url_y, url_w, url_h, LIGHT)
        link_hit.fill.background()
        link_hit.line.fill.background()
        link_hit.name = f"references:link[{index}]"
        link_hit.click_action.hyperlink.address = entry["url"]
        y += row_h + values["gap"]
