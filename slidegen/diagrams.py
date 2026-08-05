"""構成図で共有する描画部品。"""

from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

from asset_paths import ASSET_DIR, resolve_icon_path
from generate import CANVAS, GRAY, NAVY, TEXT, add_text
from layout_fit import fit_text_or_raise
from textfit import line_height_in, text_width_in

ORANGE = RGBColor(0xE8, 0x7B, 0x1E)   # compute
GREEN = RGBColor(0x3F, 0x86, 0x24)    # storage
PURPLE = RGBColor(0x7D, 0x3F, 0x98)   # ML
LINE = RGBColor(0x6C, 0x73, 0x72)
NODE_LABEL_PAD_X = 0.10  # 左右0.05in。配線以外を隠さない最小限のマスク余白
NODE_LABEL_PAD_Y = 0.04  # 上下0.02in。文字のアンチエイリアス分だけ確保
EDGE_LABEL_PAD_X = 0.10
EDGE_LABEL_PAD_Y = 0.04


def add_arrow(slide, x1, y1, x2, y2, *, color=LINE, width=1.5, both=False,
              dash=None):
    conn = slide.shapes.add_connector(
        MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    conn.line.color.rgb = color
    conn.line.width = Pt(width)
    conn.shadow.inherit = False
    ln = conn.line._get_or_add_ln()
    heads = [("a:tailEnd", True), ("a:headEnd", both)]
    for tag, on in heads:
        if on:
            el = ln.makeelement(qn(tag), {"type": "triangle", "w": "med", "len": "med"})
            ln.append(el)
    if dash:
        d = ln.makeelement(qn("a:prstDash"), {"val": dash})
        ln.insert(0, d)
    return conn


def arrow_label(slide, cx, cy, text, w=1.6, size=9):
    """線をまたぐラベル。白背景マスクは実測テキスト幅に合わせ、wは上限として扱う
    (固定幅だと短い文字列ほど余計な範囲まで線を隠してしまうため)。
    """
    box_h = line_height_in(size, 1.1) + EDGE_LABEL_PAD_Y
    actual_size, _ = fit_text_or_raise(
        "arrow_label", "text", text, w - EDGE_LABEL_PAD_X, box_h, size,
        min_pt=max(7, size - 2), spacing=1.1, role="compact")
    actual_w = min(w, text_width_in(text, actual_size) + EDGE_LABEL_PAD_X)
    actual_h = line_height_in(actual_size, 1.1) + EDGE_LABEL_PAD_Y
    tb = add_text(slide, cx - actual_w / 2, cy - actual_h / 2, actual_w, actual_h,
                  text, actual_size, color=TEXT, align=PP_ALIGN.CENTER,
                  anchor=MSO_ANCHOR.MIDDLE)
    tb.fill.solid()
    tb.fill.fore_color.rgb = CANVAS
    return tb


def container(slide, x, y, w, h, label, color=LINE, dash=None):
    sp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y),
                                Inches(w), Inches(h))
    sp.fill.background()
    sp.line.color.rgb = color
    sp.line.width = Pt(1.25)
    sp.shadow.inherit = False
    if dash:
        ln = sp.line._get_or_add_ln()
        ln.insert(0, ln.makeelement(qn("a:prstDash"), {"val": dash}))
    label_size, _ = fit_text_or_raise(
        "container", "label", label, w - 0.3, 0.28, 10.5,
        min_pt=8.5, weight="bold", spacing=1.1, role="natural")
    label_w = min(w - 0.3, text_width_in(label, label_size, "bold") + 0.08)
    add_text(slide, x + 0.12, y + 0.06, label_w, 0.28, label, label_size, bold=True,
             color=color)


def _masked_node_label(slide, cx, y, text, *, max_w, slot_h, size, min_pt,
                       color, bold=False, attach="top"):
    """配線を背後へ通すため、文字の実測外形だけを背景色でマスクする。"""
    weight = "bold" if bold else "regular"
    actual_size, lines = fit_text_or_raise(
        "icon_node", "title" if bold else "sub", text, max_w, slot_h, size,
        min_pt=min_pt, weight=weight, spacing=1.1,
        role="natural" if bold else "compact")
    rendered = "\n".join(lines)
    actual_w = min(max_w, text_width_in(rendered, actual_size, weight)
                   + NODE_LABEL_PAD_X)
    actual_h = min(slot_h, line_height_in(actual_size, 1.1) * len(lines)
                   + NODE_LABEL_PAD_Y)
    box_y = y if attach == "top" else y + slot_h - actual_h
    tb = add_text(
        slide, cx - actual_w / 2, box_y,
        actual_w, actual_h, rendered, actual_size, bold=bold, color=color,
        align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, spacing=1.1)
    tb.fill.solid()
    tb.fill.fore_color.rgb = CANVAS
    return tb


# ---- 構成図アイコンノード ----
ICON_R = 0.31        # アイコン半径(0.62角の半分)
EDGE_GAP = 0.06      # 矢印端点とアイコン縁の隙間


def icon_node(slide, cx, cy, img, title, sub=None, size=0.62, *, label_above=False):
    """アイコンと直下のサービス名ラベルを描画する。"""
    p = resolve_icon_path(img)
    if not p.exists():
        raise FileNotFoundError(
            f"アイコン {img} が {ASSET_DIR} にありません。extract_aws_icons.py で"
            f"AWS公式デッキを指定して生成するか、fetch_fluent_icons.py --list で同梱アイコンを確認して"
            f"ください。")
    slide.shapes.add_picture(str(p), Inches(cx - size / 2),
                             Inches(cy - size / 2), Inches(size), Inches(size))
    title_y = cy - size / 2 - 0.59 if label_above else cy + size / 2 + 0.05
    _masked_node_label(slide, cx, title_y, title, max_w=2.1, slot_h=0.28,
                       size=11, min_pt=9.5, color=NAVY, bold=True,
                       attach="bottom" if label_above else "top")
    if sub:
        sub_y = cy - size / 2 - 0.31 if label_above else cy + size / 2 + 0.33
        _masked_node_label(slide, cx, sub_y, sub, max_w=2.1, slot_h=0.26,
                           size=9, min_pt=8, color=GRAY,
                           attach="bottom" if label_above else "top")


def right_of(cx):
    """アイコン右縁の矢印端点X。"""
    return cx + ICON_R + EDGE_GAP


def left_of(cx):
    return cx - ICON_R - EDGE_GAP


# (旧ハンドコード版 s_aws は diagram_layout.py + diagram_specs.py に移行済み)
