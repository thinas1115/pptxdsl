"""直角配線ユーティリティ。

ポイント: プリセットのカギ線コネクタは折れ位置を制御できず他ノードを
貫通しうるため、ウェイポイント明示のroute()で配線レーンを決める。
"""
from pptx.enum.shapes import MSO_CONNECTOR
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

from diagrams import LINE, add_arrow


def plain_line(slide, x1, y1, x2, y2, *, color=LINE, width=1.25, dash=None):
    conn = slide.shapes.add_connector(
        MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    conn.line.color.rgb = color
    conn.line.width = Pt(width)
    conn.shadow.inherit = False
    if dash:
        ln = conn.line._get_or_add_ln()
        ln.insert(0, ln.makeelement(qn("a:prstDash"), {"val": dash}))
    return conn


def route(slide, pts, *, dash=None, width=1.25, both=False, color=LINE):
    """ウェイポイント列を直線で結び、最終セグメントだけ矢印にする。"""
    if both and len(pts) == 2:
        add_arrow(slide, *pts[0], *pts[1], color=color, dash=dash,
                  width=width, both=True)
        return
    start = 0
    if both:
        # add_arrowの矢印は第2点側へ付くため、始点側だけ逆向きに描く。
        add_arrow(slide, *pts[1], *pts[0], color=color, dash=dash,
                  width=width)
        start = 1
    for (x1, y1), (x2, y2) in zip(pts[start:-2], pts[start + 1:-1]):
        plain_line(slide, x1, y1, x2, y2, color=color, dash=dash,
                   width=width)
    (x1, y1), (x2, y2) = pts[-2], pts[-1]
    add_arrow(slide, x1, y1, x2, y2, color=color, dash=dash, width=width)

