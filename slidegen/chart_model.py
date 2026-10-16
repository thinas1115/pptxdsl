"""グラフの数値範囲と表示形式。値の合計から百分率という意味を推測しない。"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, localcontext
import math
import re


NUMBER_FORMAT = re.compile(r'(?:0|#,##0)(?:\.0{1,6})?(?:%|"[^"\\\r\n]{1,12}")?')


def finite_number(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and (isinstance(value, int) or math.isfinite(value)))


def decimal_value(value):
    if not finite_number(value):
        raise ValueError("chartの値は有限の数値にしてください（真偽値・NaN・Infinityは使用できません）")
    return Decimal(str(value))


def format_value(value, number_format=None):
    """指定なしは有効数字を保持。明示%だけ100倍し、Excel形式の一部を扱う。"""
    number = value if isinstance(value, Decimal) else decimal_value(value)
    if not number.is_finite():
        raise ValueError("chartの値は有限の数値にしてください")
    if number == 0:
        number = abs(number)
    if number_format is None:
        plain = format(number, "f")
        return plain.rstrip("0").rstrip(".") if "." in plain else plain
    if not isinstance(number_format, str) or not NUMBER_FORMAT.fullmatch(number_format):
        raise ValueError("chart.number_format は0 / 0.0〜0.000000 / #,##0と任意の小数・%を指定してください")
    suffix = number_format[number_format.index('"') + 1:-1] if '"' in number_format else ""
    body = number_format.split('"')[0]
    percent = body.endswith("%")
    body = body.rstrip("%")
    places = len(body.split(".")[1]) if "." in body else 0
    with localcontext() as context:
        context.prec = max(32, len(number.as_tuple().digits) + max(0, number.adjusted()) + places + 6)
        if percent:
            number *= 100
        rounded = number.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
        if rounded == 0:
            rounded = abs(rounded)
        return format(rounded, f"{',' if ',' in body else ''}.{places}f") + ("%" if percent else suffix)


def format_axis_value(value, number_format=None):
    """明示された単位は軸にも付け、目盛り間隔を潰さない桁数で表示する。"""
    if number_format is None:
        return format_value(value)
    if not isinstance(number_format, str) or not NUMBER_FORMAT.fullmatch(number_format):
        raise ValueError("chart.number_format が未対応です")
    if number_format.endswith("%"):
        number = value if isinstance(value, Decimal) else decimal_value(value)
        return format_value(number * 100) + "%"
    if '"' in number_format:
        suffix = number_format[number_format.index('"') + 1:-1]
        return format_value(value) + suffix
    return format_value(value)


@dataclass(frozen=True)
class Axis:
    minimum: Decimal
    maximum: Decimal
    step: Decimal
    ticks: tuple[Decimal, ...]

    def ratio(self, value):
        number = value if isinstance(value, Decimal) else decimal_value(value)
        if not number.is_finite():
            raise ValueError("chartの値は有限の数値にしてください")
        return float((number - self.minimum) / (self.maximum - self.minimum))


def axis_scale(values):
    """ゼロを含む有限の符号付き範囲へ、過大な上側余白を作らず目盛りを置く。"""
    numbers = [value if isinstance(value, Decimal) else decimal_value(value) for value in values]
    if any(not value.is_finite() for value in numbers):
        raise ValueError("chartの軸範囲は有限の数値にしてください")
    low, high = min([Decimal(0), *numbers]), max([Decimal(0), *numbers])
    if low == high:
        high = Decimal(1)
    raw = (high - low) / 5
    magnitude = Decimal(1).scaleb(raw.adjusted())
    step = next(Decimal(value) * magnitude for value in ("1", "2", "2.5", "5", "10")
                if Decimal(value) * magnitude >= raw)
    lower = (low / step).to_integral_value(rounding=ROUND_FLOOR) * step
    upper = (high / step).to_integral_value(rounding=ROUND_CEILING) * step
    count = int((upper - lower) / step)
    return Axis(lower, upper, step, tuple(lower + step * index for index in range(count + 1)))


def range_values(series, *, stacked):
    if not stacked:
        return [decimal_value(value) for _, values in series for value in values]
    # 正負はゼロの両側へ別々に積む。相殺後の合計から軸上限を決めない。
    extents = []
    for category in range(len(series[0][1])):
        values = [decimal_value(values[category]) for _, values in series]
        extents.extend((sum((value for value in values if value > 0), Decimal(0)),
                        sum((value for value in values if value < 0), Decimal(0))))
    return extents
