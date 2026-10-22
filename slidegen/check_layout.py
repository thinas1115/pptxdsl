"""生成済みPPTXのレイアウト衝突を機械検知する品質ゲート。

使い方: python slidegen/check_layout.py out/deck.pptx
検知対象:
  T-T: テキストグリフ同士の交差
  T-P: テキストグリフ×画像(アイコン)
  T-S: テキストグリフ×塗り図形の「部分重なり」(完全内包=意図的デザインは許可)
  T-F: テキストグリフがコンテナ枠線をまたぐ
  L-T: 矢印・線×テキストグリフ(白塗りマスクラベルは除外)
  CELL-OOB: 表セルからのテキストはみ出し
  TEXT-OOB: 通常図形の文字領域からのテキストはみ出し
  TEXT-METRICS: 保存書式・書体が文字矩形の測定契約に対応しない
  OOB: スライド境界からの図形・画像・表・グラフのはみ出し
  VIS-CONTRAST: 背景に接する意味面とキャンバスの分離不足
  SEQ-CLEARANCE: sequence自己処理の戻り線とメッセージラベルの接触
  SEQ-LIFELINE: sequenceライフラインが応答と同じ破線になっている

文字矩形は保存書式からの行ボックス推定であり、実グリフの描画範囲ではない。
対応範囲と限界はdocs/text-metrics.mdを参照する。PNGの目視確認は別途必要。
"""
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pptx import Presentation
from pptx.enum.dml import MSO_FILL_TYPE
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.oxml.ns import qn
from slidegen.cover_footer import COVER_BACKGROUND_NAME
from slidegen.quality_markers import (
    MIN_SURFACE_CONTRAST,
    MIN_SURFACE_EDGE_CONTRAST,
    SEQUENCE_LABEL_CLEARANCE,
    SEQUENCE_LIFELINE_PREFIX,
    SEQUENCE_MESSAGE_LABEL_PREFIX,
    SEQUENCE_SELF_ROUTE_PREFIX,
    SURFACE_ON_CANVAS_PREFIX,
)
from slidegen.text_metrics import TextMetricsError, layout_text_frame

EMU = 914400
EDGE = 0.03          # 枠線の当たり判定幅
SEG_TRIM = 0.08      # 線分端はノード接続なので判定から除外する長さ
EPS = 0.03           # 視認できない接触(スリバー)を無視する許容量
BACKGROUND_PREFIX = "layout-background:"


def rect_of(sh):
    return (sh.left / EMU, sh.top / EMU, (sh.left + sh.width) / EMU,
            (sh.top + sh.height) / EMU)


def intersects(a, b, eps=EPS):
    return not (a[2] - eps <= b[0] or b[2] - eps <= a[0]
                or a[3] - eps <= b[1] or b[3] - eps <= a[1])


def expanded(rect, amount):
    return (rect[0] - amount, rect[1] - amount,
            rect[2] + amount, rect[3] + amount)


def contains(outer, inner, eps=EPS):
    return (outer[0] - eps <= inner[0] and outer[1] - eps <= inner[1]
            and outer[2] + eps >= inner[2] and outer[3] + eps >= inner[3])


def glyph_rect_for_text_frame(tf, box, *, box_is_inner=False):
    """保存書式を反映した各行矩形の外接矩形。衝突検査本体では行ごとに扱う。"""
    return layout_text_frame(tf, box, box_is_inner=box_is_inner).bounds


def glyph_rect(sh):
    """通常図形の実グリフ矩形をtextfitで推定する。"""
    return glyph_rect_for_text_frame(sh.text_frame, rect_of(sh))


def table_cells(sh):
    """表セルの外形・文字領域とtext frameを返す。"""
    table = sh.table
    x0, y0, _, _ = rect_of(sh)
    col_widths = [col.width / EMU for col in table.columns]
    row_heights = [row.height / EMU for row in table.rows]
    y = y0
    for ri, row in enumerate(table.rows):
        x = x0
        row_h = row_heights[ri]
        for ci, col in enumerate(table.columns):
            col_w = col_widths[ci]
            cell = table.cell(ri, ci)
            if not getattr(cell, "is_spanned", False):
                span_w = getattr(cell, "span_width", 1)
                span_h = getattr(cell, "span_height", 1)
                merged_w = sum(col_widths[ci:ci + span_w])
                merged_h = sum(row_heights[ri:ri + span_h])
                outer = (x, y, x + merged_w, y + merged_h)
                inner = (
                    x + cell.margin_left / EMU,
                    y + cell.margin_top / EMU,
                    x + merged_w - cell.margin_right / EMU,
                    y + merged_h - cell.margin_bottom / EMU,
                )
                yield outer, inner, cell.text_frame, ri, ci
            x += col_w
        y += row_h


def is_oob(rect, slide_w, slide_h):
    return (rect[0] < -EPS or rect[1] < -EPS
            or rect[2] > slide_w + EPS or rect[3] > slide_h + EPS)


def seg_of(sh):
    """コネクタの線分端点(flipで向きを解決)。"""
    x1, y1, x2, y2 = rect_of(sh)
    el = sh._element
    flip_h = el.spPr.xfrm.get("flipH") == "1" if el.spPr.xfrm is not None else False
    flip_v = el.spPr.xfrm.get("flipV") == "1" if el.spPr.xfrm is not None else False
    ax, bx = (x2, x1) if flip_h else (x1, x2)
    ay, by = (y2, y1) if flip_v else (y1, y2)
    return (ax, ay, bx, by)


def seg_hits_rect(seg, r, eps=EPS):
    """線分と矩形の交差(端をSEG_TRIMだけ縮めて接続点は無視)。"""
    x1, y1, x2, y2 = seg
    import math
    L = math.hypot(x2 - x1, y2 - y1)
    if L < SEG_TRIM * 2:
        return False
    ux, uy = (x2 - x1) / L, (y2 - y1) / L
    x1, y1 = x1 + ux * SEG_TRIM, y1 + uy * SEG_TRIM
    x2, y2 = x2 - ux * SEG_TRIM, y2 - uy * SEG_TRIM
    # 開矩形とのslab交差。サンプリング間隔より細いラベルも取り逃がさない。
    low, high = 0.0, 1.0
    for start, delta, minimum, maximum in (
        (x1, x2 - x1, r[0] + eps, r[2] - eps),
        (y1, y2 - y1, r[1] + eps, r[3] - eps),
    ):
        if minimum >= maximum:
            return False
        if delta == 0:
            if not minimum < start < maximum:
                return False
            continue
        entry, leave = sorted(((minimum - start) / delta,
                               (maximum - start) / delta))
        low, high = max(low, entry), min(high, leave)
        if low >= high:
            return False
    return low < high


def has_solid_fill(sh):
    # 属性や型を取得できない場合は例外を伝播し、不明を「塗りなし」へ偽装しない。
    return sh.fill.type == MSO_FILL_TYPE.SOLID


def solid_fill_rgb(sh):
    if not has_solid_fill(sh):
        return None
    try:
        return tuple(sh.fill.fore_color.rgb)
    except (AttributeError, TypeError):
        return None


def solid_line_rgb(sh):
    """図形の単色輪郭をRGBで返す。輪郭なし・テーマ色は判定不能とする。"""
    try:
        rgb = sh.line.color.rgb
        if rgb is None or sh.line.width <= 0:
            return None
        return tuple(rgb)
    except (AttributeError, TypeError, ValueError):
        return None


def preset_dash(sh):
    """線へ明示されたプリセット破線名を返す。実線または取得不能ならNone。"""
    try:
        dash = sh.line._get_or_add_ln().find(qn("a:prstDash"))
        return dash.get("val") if dash is not None else None
    except (AttributeError, TypeError, ValueError):
        return None


def relative_luminance(rgb):
    values = [value / 255 for value in rgb]
    linear = [
        value / 12.92 if value <= 0.04045
        else ((value + 0.055) / 1.055) ** 2.4
        for value in values
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(first, second):
    high, low = sorted(
        (relative_luminance(first), relative_luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def canvas_fill_rgb(slide, slide_w, slide_h):
    """全画面を覆う最背面の塗り図形をキャンバスとして扱う。"""
    for sh in slide.shapes:
        if sh.shape_type != MSO_SHAPE_TYPE.AUTO_SHAPE:
            continue
        bounds = rect_of(sh)
        if (bounds[0] <= EPS and bounds[1] <= EPS
                and bounds[2] >= slide_w - EPS
                and bounds[3] >= slide_h - EPS):
            color = solid_fill_rgb(sh)
            if color is not None:
                return color
    return None


def snippet(t):
    t = t.replace("\n", " ")
    return t[:16] + ("…" if len(t) > 16 else "")


def check(path):
    prs = Presentation(path)
    slide_w = prs.slide_width / EMU
    slide_h = prs.slide_height / EMU
    findings = []
    for si, slide in enumerate(prs.slides, 1):
        canvas_rgb = canvas_fill_rgb(slide, slide_w, slide_h)
        texts, pics, solids, frames, segs = [], [], [], [], []
        sequence_returns, sequence_labels = [], []
        for z, sh in enumerate(slide.shapes):  # zは描画順(後勝ち)
            st = sh.shape_type
            bounds = rect_of(sh)
            if is_oob(bounds, slide_w, slide_h):
                findings.append((si, "OOB", sh.name, ""))
            if st == MSO_SHAPE_TYPE.PICTURE:
                if sh.name != COVER_BACKGROUND_NAME:
                    pics.append((bounds, sh.name))
            elif st in (MSO_SHAPE_TYPE.AUTO_SHAPE,):
                if sh.name.startswith(SURFACE_ON_CANVAS_PREFIX):
                    surface_rgb = solid_fill_rgb(sh)
                    if surface_rgb is None or canvas_rgb is None:
                        findings.append((si, "VIS-CONTRAST", sh.name,
                                         "塗りまたはキャンバス色を取得できません"))
                    else:
                        fill_ratio = contrast_ratio(surface_rgb, canvas_rgb)
                        edge_rgb = solid_line_rgb(sh)
                        edge_ratio = (
                            contrast_ratio(edge_rgb, canvas_rgb)
                            if edge_rgb is not None else 0.0
                        )
                        if (fill_ratio < MIN_SURFACE_CONTRAST
                                and edge_ratio < MIN_SURFACE_EDGE_CONTRAST):
                            findings.append((
                                si, "VIS-CONTRAST", sh.name,
                                f"面={fill_ratio:.3f} < {MIN_SURFACE_CONTRAST:.2f}, "
                                f"輪郭={edge_ratio:.3f} < "
                                f"{MIN_SURFACE_EDGE_CONTRAST:.2f}"))
                if not sh.name.startswith(BACKGROUND_PREFIX):
                    (solids if has_solid_fill(sh) else frames).append(
                        (bounds, sh.name, z))
            elif st == MSO_SHAPE_TYPE.LINE:
                seg = seg_of(sh)
                segs.append((seg, sh.name, z))
                if (sh.name.startswith(SEQUENCE_LIFELINE_PREFIX)
                        and preset_dash(sh) not in (None, "solid")):
                    findings.append((
                        si, "SEQ-LIFELINE", sh.name,
                        "ライフラインは応答と区別できる実線にしてください"))
                if (sh.name.startswith(SEQUENCE_SELF_ROUTE_PREFIX)
                        and sh.name.endswith(":return")):
                    sequence_returns.append((seg, sh.name))
            elif st == MSO_SHAPE_TYPE.CHART:
                pics.append((bounds, sh.name))
            elif st == MSO_SHAPE_TYPE.TABLE:
                for _cell_rect, text_rect, tf, ri, ci in table_cells(sh):
                    if not tf.text.strip():
                        continue
                    try:
                        layout = layout_text_frame(tf, text_rect, box_is_inner=True, default_role="compact")
                    except TextMetricsError as error:
                        findings.append((si, "TEXT-METRICS", f"{sh.name}[{ri},{ci}]", str(error)))
                        continue
                    if layout.bounds:
                        label = snippet(tf.text)
                        texts.extend((line.rect, label, False) for line in layout.lines if line.text.strip())
                        if not contains(text_rect, layout.bounds, eps=0.01):
                            findings.append(
                                (si, "CELL-OOB", f"{sh.name}[{ri},{ci}]", label))
            if st != MSO_SHAPE_TYPE.TABLE \
                    and sh.has_text_frame and sh.text_frame.text.strip():
                try:
                    layout = layout_text_frame(sh.text_frame, bounds)
                except TextMetricsError as error:
                    findings.append((si, "TEXT-METRICS", sh.name, str(error)))
                    continue
                if layout.bounds:
                    texts.extend((line.rect, snippet(sh.text_frame.text), has_solid_fill(sh))
                                 for line in layout.lines if line.text.strip())
                    if not contains(layout.inner, layout.bounds):
                        findings.append((si, "TEXT-OOB", sh.name, snippet(sh.text_frame.text)))
                if sh.name.startswith(SEQUENCE_MESSAGE_LABEL_PREFIX):
                    sequence_labels.append((bounds, sh.name))
        # T-T
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                if intersects(texts[i][0], texts[j][0]):
                    findings.append((si, "T-T", texts[i][1], texts[j][1]))
        # T-P
        for g, t, _ in texts:
            for r, name in pics:
                if intersects(g, r):
                    findings.append((si, "T-P", t, name))
        # T-S: 部分重なりのみ(内包は許可)
        for g, t, _ in texts:
            for r, name, _z in solids:
                if intersects(g, r) and not contains(r, g):
                    findings.append((si, "T-S", t, name))
        # T-F: 枠線またぎ(内包/完全外は許可。白塗りマスクラベルは枠線を隠すので許可)
        for g, t, masked in texts:
            if masked:
                continue
            for r, name, _z in frames:
                if intersects(g, r, eps=-EDGE) and not contains(
                        (r[0] + EDGE, r[1] + EDGE, r[2] - EDGE, r[3] - EDGE), g) \
                        and intersects(g, r):
                    findings.append((si, "T-F", t, name))
        # L-T (マスクラベルと、線より後に描かれた塗り図形上のテキストは除外)
        for seg, name, lz in segs:
            for g, t, masked in texts:
                if masked or not seg_hits_rect(seg, g):
                    continue
                covered = any(contains(r, g) and sz > lz
                              for r, _n, sz in solids)
                if not covered:
                    findings.append((si, "L-T", name, t))
        # L-P
        for seg, name, _lz in segs:
            for r, pname in pics:
                if seg_hits_rect(seg, r):
                    findings.append((si, "L-P", name, pname))
        # 線上ラベルは塗りマスクを使うため汎用L-Tでは除外される。
        # 自己処理の戻り線は、別メッセージのラベルに隠れると経路が欠けるため意味名で検査する。
        for seg, route_name in sequence_returns:
            for label_rect, label_name in sequence_labels:
                if seg_hits_rect(
                        seg, expanded(label_rect, SEQUENCE_LABEL_CLEARANCE),
                        eps=0.0):
                    findings.append((
                        si, "SEQ-CLEARANCE", route_name, label_name))
        for g, t, _ in texts:
            if is_oob(g, slide_w, slide_h):
                findings.append((si, "OOB-TEXT", t, ""))
    return findings


if __name__ == "__main__":
    path = sys.argv[1]
    from slidegen.font_config import FontConfigError
    try:
        fs = check(path)
    except FontConfigError as error:
        raise SystemExit(f"NG: フォント設定: {error}") from None
    if not fs:
        print(f"OK: no layout or visual QA findings in {path}")
        sys.exit(0)
    print(f"NG: {len(fs)} finding(s) in {path}")
    for si, kind, a, b in fs:
        print(f"  slide{si:02d} [{kind}] {a!r} x {b!r}")
    sys.exit(1)
