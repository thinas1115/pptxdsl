"""符号付きグラフ。実測した文字と数値を標準→余白圧縮→縮小の順で収容する。"""
from dataclasses import dataclass, field
from decimal import Decimal

from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn

from slidegen import generate as g
from slidegen.chart_model import axis_scale, decimal_value, format_axis_value, format_value, range_values
from slidegen.layout_fit import FitError
from slidegen.textfit import line_height_in, text_width_in, wrap_natural


MIN_TEXT_PT = 10.5
_GUIDANCE = "カテゴリ・系列を減らすか名前を短くし、必要なら複数ページへ分けてください。"


@dataclass
class Plan:
    stage: str
    size: float
    texts: list = field(default_factory=list)
    bars: list = field(default_factory=list)
    lines: list = field(default_factory=list)
    dots: list = field(default_factory=list)


def _box(x, y, w, h):
    return x, y, x + w, y + h


def _overlap(a, b, gap=0.025):
    return not (a[2] + gap <= b[0] or b[2] + gap <= a[0]
                or a[3] + gap <= b[1] or b[3] + gap <= a[1])


def _contains(outer, inner):
    return outer[0] <= inner[0] and outer[1] <= inner[1] and outer[2] >= inner[2] and outer[3] >= inner[3]


def _segment_hits(line, rect):
    # 線分と開矩形のslab交差。サンプリングで短い交差を見落とさない。
    first, last = 0.0, 1.0
    for start, end, low, high in ((line[0], line[2], rect[0], rect[2]),
                                   (line[1], line[3], rect[1], rect[3])):
        delta = end - start
        if delta == 0:
            if not low < start < high:
                return False
        else:
            a, b = sorted(((low - start) / delta, (high - start) / delta))
            first, last = max(first, a), min(last, b)
            if first >= last:
                return False
    return first < last


def _wrapped(text, width, size, *, bold=False, max_lines=2):
    lines = wrap_natural(str(text), width, size, "bold" if bold else "regular")
    if len(lines) > max_lines or any(text_width_in(line, size, "bold" if bold else "regular") > width + 0.001 for line in lines):
        raise FitError("chart: ラベルの最小幅が不足しています。" + _GUIDANCE)
    return "\n".join(lines), len(lines) * line_height_in(size, 1.3) + 0.02


def _text(plan, text, x, y, w, h, role, *, bold=False, color=None, align=PP_ALIGN.LEFT):
    plan.texts.append((str(text), x, y, w, h, bold, color or g.GRAY, align, role))


def _text_rect(item):
    _, x, y, w, h, *_ = item
    return _box(x, y, w, h)


def _inside_color(fill):
    def luminance(rgb):
        channels = [value / 255 for value in rgb]
        return sum(weight * (value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4)
                   for weight, value in zip((0.2126, 0.7152, 0.0722), channels))
    background = luminance(fill)
    for color in (g.WHITE, g.TEXT):
        high, low = sorted((background, luminance(color)), reverse=True)
        if (high + 0.05) / (low + 0.05) >= 4.5:
            return color
    return None


def _legend(plan, names, width, gap):
    """長い系列名は折り返し、横幅が足りなければ次の行へ送る。"""
    entries, row, cursor, row_h = [], 0, 0.0, 0.0
    heights = []
    for index, name in enumerate(names):
        # 互換Officeではwrap=Falseでも実測幅ちょうどの系列名が再改行される。
        # 語尾の単位を次行へ送らないよう、文字幅に組版差の余裕を持たせる。
        label_w = min(2.8, max(0.5, text_width_in(name, plan.size) + 0.12))
        text, height = _wrapped(name, label_w, plan.size)
        item_w = label_w + 0.22 + gap
        if cursor and cursor + item_w > width:
            heights.append(row_h)
            row, cursor, row_h = row + 1, 0.0, 0.0
        entries.append((index, text, cursor, label_w, height, row))
        cursor += item_w
        row_h = max(row_h, height)
    if entries:
        heights.append(row_h)
    return entries, heights


def _spread_empty_stacks(requests, *, horizontal):
    """全系列ゼロの内訳は、存在しない棒の一点へ重ねず系列順に並べる。"""
    groups = {}
    for index, request in enumerate(requests):
        groups.setdefault(request[4], []).append(index)
    requests = list(requests)
    for cell, indices in groups.items():
        if len(indices) < 2 or not all(requests[index][2] is None and requests[index][5] for index in indices):
            continue
        for order, index in enumerate(indices):
            text, (x, y), own, color, _, inside = requests[index]
            if horizontal:
                y = cell[1] + (order + 0.5) * (cell[3] - cell[1]) / len(indices)
            else:
                x = cell[0] + (order + 0.5) * (cell[2] - cell[0]) / len(indices)
            requests[index] = (text, (x, y), own, color, cell, inside)
    return requests


def _place_values(plan, requests, bounds, *, horizontal):
    """表示指定された値を省略しない。空きがなければ小さい候補か明示停止へ進む。"""
    height = line_height_in(plan.size, 1.3) + 0.02
    obstacles = [_text_rect(item) for item in plan.texts]
    bar_rects = [_box(x, y, w, h) for x, y, w, h, _, _ in plan.bars]
    data_lines = [item[:4] for item in plan.lines if item[-1] != "grid"]
    for text, point, own, color, cell, inside in _spread_empty_stacks(requests, horizontal=horizontal):
        width = text_width_in(text, plan.size) + 0.035
        x, y = point
        candidates = []
        inside_color = _inside_color(color)
        if inside and inside_color and own and own[2] - own[0] >= width + 0.10 and own[3] - own[1] >= height + 0.07:
            candidates.append(((own[0] + own[2] - width) / 2, (own[1] + own[3] - height) / 2, True))
        candidates.extend((
            (x + 0.09, y - height / 2, False),
            (x - width - 0.09, y - height / 2, False),
            (x - width / 2, y - height - 0.10, False),
            (x - width / 2, y + 0.06, False),
            (x + 0.10, y - height - 0.10, False),
            (x - width - 0.10, y - height - 0.10, False),
            (x + 0.10, y + 0.06, False),
            (x - width - 0.10, y + 0.06, False),
            (x + 0.50, y - height - 0.10, False),
            (x - width - 0.50, y - height - 0.10, False),
            (x + 0.50, y + 0.06, False),
            (x - width - 0.50, y + 0.06, False),
            (x + 0.10, y - height - 0.36, False),
            (x - width - 0.10, y - height - 0.36, False),
            (x + 0.10, y + 0.36, False),
            (x - width - 0.10, y + 0.36, False),
        ))
        for tx, ty, internal in candidates:
            rect = _box(tx, ty, width, height)
            if not _contains(bounds, rect) or not _contains(cell, rect):
                continue
            if any(_overlap(rect, other) for other in obstacles):
                continue
            if any(_overlap(rect, other) for other in bar_rects if not (internal and other == own)):
                continue
            padded = (rect[0] - 0.035, rect[1] - 0.035, rect[2] + 0.035, rect[3] + 0.035)
            if any(_segment_hits(line, padded) for line in data_lines):
                continue
            if any(_overlap(rect, _box(dx - 0.065, dy - 0.065, 0.13, 0.13)) for dx, dy, _ in plan.dots):
                continue
            _text(plan, text, tx, ty, width, height, "data-value", color=inside_color if internal else g.TEXT)
            obstacles.append(rect)
            break
        else:
            raise FitError(f"chart: 数値ラベル({text})を省略せずに配置できません。" + _GUIDANCE)


def _trim_grid_around_values(plan):
    """補助目盛り線だけを数値ラベルの手前で切る。データ線・ゼロ軸は切らない。"""
    labels = [_text_rect(item) for item in plan.texts if item[-1] == "data-value"]
    lines = []
    for line in plan.lines:
        x1, y1, x2, y2, *style = line
        if line[-1] != "grid":
            lines.append(line)
            continue
        vertical = x1 == x2
        segments = [(min(y1, y2), max(y1, y2))] if vertical else [(min(x1, x2), max(x1, x2))]
        for rect in labels:
            cross = x1 if vertical else y1
            cross_low, cross_high = (rect[0], rect[2]) if vertical else (rect[1], rect[3])
            if not cross_low - 0.04 < cross < cross_high + 0.04:
                continue
            cut_low, cut_high = (rect[1] - 0.04, rect[3] + 0.04) if vertical else (rect[0] - 0.04, rect[2] + 0.04)
            remaining = []
            for low, high in segments:
                if cut_high <= low or cut_low >= high:
                    remaining.append((low, high))
                else:
                    if low < cut_low:
                        remaining.append((low, cut_low))
                    if high > cut_high:
                        remaining.append((cut_high, high))
            segments = remaining
        for low, high in segments:
            lines.append((x1, low, x2, high, *style) if vertical else (low, y1, high, y2, *style))
    plan.lines = lines


def _layout(chart, area, stage, size, gap):
    plan = Plan(stage, size)
    cats, series = chart["categories"], chart["series"]
    kind = chart.get("kind", "bar")
    horizontal, stacked = kind in {"bar", "stacked_bar"}, kind.startswith("stacked_")
    show_values = chart.get("show_values", kind != "line")
    palette = [g.ACCENT, g.NAVY, g.CORAL, g.GRAY]
    axis = axis_scale(range_values(series, stacked=stacked))
    axis_texts = [format_axis_value(value, chart.get("number_format")) for value in axis.ticks]
    value_texts = [[format_value(value, chart.get("number_format")) for value in values] for _, values in series]
    if stacked and len(series) > 1:
        value_texts = [[f"{name}: {text}" if decimal_value(value) == 0 else text
                        for value, text in zip(values, labels)]
                       for (name, values), labels in zip(series, value_texts)]
    line_h = line_height_in(size, 1.3) + 0.02
    x, y, w = 0.76, area.top + 0.18, 11.80
    if hasattr(area, "left"):
        x, w = area.left + 0.02, area.width - 0.04
    legend_entries, legend_heights = ([], [])
    if chart.get("show_legend", len(series) > 1):
        legend_entries, legend_heights = _legend(plan, [name for name, _ in series], w, gap)
    legend_h = sum(legend_heights) + gap * len(legend_heights)
    bottom = area.bottom - 0.14 - legend_h
    max_axis_w = max(text_width_in(text, size) for text in axis_texts) + 0.04
    max_value_w = max(text_width_in(text, size) for labels in value_texts for text in labels) + 0.12 if show_values else 0.0
    requests = []
    if horizontal:
        category_w = min(3.0, max(0.85, max(text_width_in(cat, size, "bold") for cat in cats)))
        category_text = [_wrapped(cat, category_w, size, bold=True) for cat in cats]
        pad = max(max_axis_w / 2, max_value_w) + gap
        px, py = x + category_w + gap + pad, y + line_h / 2 + 0.06
        pw, ph = w - category_w - gap - 2 * pad, bottom - y - line_h - 0.18
        if pw < 3.5 or ph <= 0:
            raise FitError("chart: プロット幅が不足しています。" + _GUIDANCE)
        row_h = ph / len(cats)
        groups = 1 if stacked else len(series)
        group_h = line_h * groups + gap * (groups - 1)
        if group_h + gap > row_h or any(h + gap > row_h for _, h in category_text):
            raise FitError("chart: カテゴリ行の高さが不足しています。" + _GUIDANCE)
        for tick, text in zip(axis.ticks, axis_texts):
            tx = px + pw * axis.ratio(tick)
            plan.lines.append((tx, py, tx, py + ph, g.RULE, 0.55, "grid"))
            tw = text_width_in(text, size) + 0.04
            _text(plan, text, tx - tw / 2, py + ph + 0.07, tw, line_h, "axis-value")
        zero_x = px + pw * axis.ratio(0)
        plan.lines.append((zero_x, py, zero_x, py + ph, g.GRAY, 0.9, "zero-axis"))
        for index, (cat, cat_h) in enumerate(category_text):
            mid = py + (index + 0.5) * row_h
            _text(plan, cat, x, mid - cat_h / 2, category_w, cat_h, "category", bold=True, color=g.NAVY, align=PP_ALIGN.RIGHT)
            pos, neg = Decimal(0), Decimal(0)
            for si, (_, values) in enumerate(series):
                value = decimal_value(values[index])
                start = (pos if value >= 0 else neg) if stacked else Decimal(0)
                end = start + value
                if stacked:
                    if value >= 0:
                        pos = end
                    else:
                        neg = end
                center = mid if stacked else mid - group_h / 2 + line_h / 2 + si * (line_h + gap)
                bx1, bx2 = px + pw * axis.ratio(start), px + pw * axis.ratio(end)
                bar_h = min(0.46 if stacked else 0.24, row_h - gap) if stacked else min(0.24, line_h - 0.03)
                own = None
                if value != 0:
                    own = _box(min(bx1, bx2), center - bar_h / 2, abs(bx2 - bx1), bar_h)
                    plan.bars.append((own[0], own[1], own[2] - own[0], bar_h, palette[si], "data-bar"))
                if show_values:
                    cell = (x + category_w + gap, py + index * row_h, x + w, py + (index + 1) * row_h)
                    requests.append((value_texts[si][index], (bx2, center), own, palette[si], cell, stacked))
    else:
        left_pad = max_axis_w + gap
        px, py = x + left_pad, y + line_h + gap
        pw = w - left_pad - max(line_h, max_axis_w / 2)
        cluster_w = pw / len(cats)
        category_text = [_wrapped(cat, cluster_w - gap, size) for cat in cats]
        category_h = max(height for _, height in category_text)
        ph = bottom - py - category_h - line_h - gap - 0.12
        if pw < 3.5 or ph < 1.6:
            raise FitError("chart: プロット領域が不足しています。" + _GUIDANCE)
        for tick, text in zip(axis.ticks, axis_texts):
            ty = py + ph * (1 - axis.ratio(tick))
            plan.lines.append((px, ty, px + pw, ty, g.RULE, 0.55, "grid"))
            _text(plan, text, x, ty - line_h / 2, max_axis_w, line_h, "axis-value", align=PP_ALIGN.RIGHT)
        zero_y = py + ph * (1 - axis.ratio(0))
        plan.lines.append((px, zero_y, px + pw, zero_y, g.GRAY, 0.9, "zero-axis"))
        for index, (cat, cat_h) in enumerate(category_text):
            cx = px + (index + 0.5) * cluster_w
            _text(plan, cat, px + index * cluster_w + gap / 2, py + ph + line_h + 0.10,
                  cluster_w - gap, cat_h, "category", align=PP_ALIGN.CENTER)
            pos, neg = Decimal(0), Decimal(0)
            groups = 1 if stacked else len(series)
            bar_gap = gap / 3
            bar_w = min(0.65 if stacked else 0.40, (cluster_w * 0.72 - bar_gap * (groups - 1)) / groups)
            if kind != "line" and bar_w < 0.07:
                raise FitError("chart: 棒の可視幅を確保できません。" + _GUIDANCE)
            for si, (_, values) in enumerate(series):
                value = decimal_value(values[index])
                if kind == "line":
                    continue
                start = (pos if value >= 0 else neg) if stacked else Decimal(0)
                end = start + value
                if stacked:
                    if value >= 0:
                        pos = end
                    else:
                        neg = end
                center = cx if stacked else cx - (bar_w * groups + bar_gap * (groups - 1)) / 2 + bar_w / 2 + si * (bar_w + bar_gap)
                by1, by2 = py + ph * (1 - axis.ratio(start)), py + ph * (1 - axis.ratio(end))
                own = None
                if value != 0:
                    own = _box(center - bar_w / 2, min(by1, by2), bar_w, abs(by2 - by1))
                    plan.bars.append((own[0], own[1], bar_w, own[3] - own[1], palette[si], "data-bar"))
                if show_values:
                    cell = (px + index * cluster_w, y, px + (index + 1) * cluster_w, py + ph + line_h + 0.08)
                    requests.append((value_texts[si][index], (center, by2), own, palette[si], cell, stacked))
        if kind == "line":
            for si, (_, values) in enumerate(series):
                points = [(px + (index + 0.5) * cluster_w, py + ph * (1 - axis.ratio(value))) for index, value in enumerate(values)]
                for a, b in zip(points, points[1:]):
                    plan.lines.append((*a, *b, palette[si], 1.8, "data-line"))
                for index, (dx, dy) in enumerate(points):
                    plan.dots.append((dx, dy, palette[si]))
                    if show_values:
                        cell = (px + index * cluster_w, y, px + (index + 1) * cluster_w, py + ph + line_h + 0.08)
                        requests.append((value_texts[si][index], (dx, dy), None, palette[si], cell, False))
    legend_y = bottom + 0.12
    offsets = [sum(legend_heights[:row]) + row * gap for row in range(len(legend_heights))]
    for si, text, dx, label_w, height, row in legend_entries:
        ly = legend_y + offsets[row]
        plan.bars.append((x + dx, ly + 0.04, 0.12, 0.12, palette[si], "legend-key"))
        _text(plan, text, x + dx + 0.22, ly, label_w, height, "legend")
    if show_values:
        _place_values(plan, requests, (x, y - 0.02, x + w, bottom), horizontal=horizontal)
        _trim_grid_around_values(plan)
    return plan


def plan_chart(chart, area):
    last = None
    for stage, size, gap in (("normal", 12, 0.18), ("gap", 12, 0.08),
                             ("element", 11.5, 0.08), ("element", 11, 0.08), ("element", 10.5, 0.08)):
        try:
            return _layout(chart, area, stage, size, gap)
        except FitError as error:
            last = error
    raise FitError(f"chart({chart.get('kind', 'bar')}): 最小文字{MIN_TEXT_PT}ptでも収まりません。{last}")


def _no_effect(shape):
    shape.shadow.inherit = False
    for effect in shape._element.findall(".//" + qn("a:effectRef")):
        effect.set("idx", "0")


def render_chart(slide, chart, area):
    try:
        plan = plan_chart(chart, area)
    except ValueError as error:
        if isinstance(error, FitError):
            raise
        raise FitError(str(error)) from None
    for x1, y1, x2, y2, color, width, role in plan.lines:
        shape = g._chart_line(slide, x1, y1, x2, y2, color, width)
        shape.name = f"chart:{role}"
        _no_effect(shape)
    for x, y, w, h, color, role in plan.bars:
        shape = g.add_rect(slide, x, y, w, h, color)
        shape.name = f"chart:{role}"
        _no_effect(shape)
    for x, y, color in plan.dots:
        shape = g._chart_dot(slide, x, y, color, 0.10, line_color=g.WHITE)
        shape.name = "chart:data-dot"
        _no_effect(shape)
    for text, x, y, w, h, bold, color, align, role in plan.texts:
        # 折り返しは計画時に確定済み。互換Officeの再組版で系列名や値を分断しない。
        shape = g.add_text(slide, x, y, w, h, text, plan.size, bold=bold, color=color,
                           align=align, spacing=1.3, wrap=False)
        shape.name = f"chart:{role}"
    return plan
