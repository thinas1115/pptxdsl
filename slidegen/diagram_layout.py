"""宣言的レイアウトエンジン: グリッド仕様から図解の座標を計算する。

AIが書くのは離散的な仕様(セル・メンバー・経由チャネル名)のみ。
座標はすべて本エンジンが決定論的に導出するため、いつ誰が(どのモデルが)
仕様を書いても同じ図になる。仕様の形式は CONTENT_SCHEMA.md を参照。
"""
from generate import BODY_BOTTOM, BODY_TOP, BODY_W, MARGIN, note_line
from diagrams import (ACCENT, EDGE_GAP, EDGE_LABEL_PAD_X, EDGE_LABEL_PAD_Y,
                      ICON_R, LINE, NAVY, add_arrow, arrow_label, container,
                      icon_node)
from diagrams3 import route
from layout_fit import FitError, stepped
from textfit import line_height_in, text_width_in

AREA = (MARGIN + 0.15, BODY_TOP + 0.05, MARGIN + BODY_W - 0.15, 6.85)
DENSE_AREA = (AREA[0], BODY_TOP - 0.12, AREA[2], BODY_BOTTOM)
DENSE_ROW_THRESHOLD = 4
ICON_SIZE = ICON_R * 2
MIN_ICON_SIZE = 0.46
ICON_STEP = 0.04
LABEL_W = 2.1          # icon_nodeのラベル幅
TITLE_H = 0.33         # アイコン下端からタイトル行下端まで
SUB_H = 0.26
CONT_HEAD = 0.30       # コンテナラベルの余白(上辺に追加)
SLOT_PITCH = 0.26      # 同一辺から複数エッジを出すときの間隔
LABEL_ROW_GAP = 0.03    # ラベル下端と次行アイコンの間に残す必須余白
MIN_SEG = 0.12          # via指定後の最終進入区間の最短長。これより短い/逆走
                        # する場合はp1側にクランプする(実際に0.04inの逆走が
                        # 発生し、矢印の向きが逆に見える不具合になった)
PORT_STUB = 0.05         # via方向が接続辺に対して接線方向になる場合、最初に
                        # アイコン辺から垂直に離す長さ。圧縮時の隣接行間にも
                        # 収まり、接続先を誤認しない見た目を両立する。
MIN_SEG_CLAMP = {
    "left":   lambda c, p1: (min(c[0], p1[0] - MIN_SEG), c[1]),
    "right":  lambda c, p1: (max(c[0], p1[0] + MIN_SEG), c[1]),
    "top":    lambda c, p1: (c[0], min(c[1], p1[1] - MIN_SEG)),
    "bottom": lambda c, p1: (c[0], max(c[1], p1[1] + MIN_SEG)),
}
COLORS = {"line": LINE, "navy": NAVY, "accent": ACCENT}


def _linspace(a, b, n):
    if n == 1:
        return [(a + b) / 2]
    return [a + i * (b - a) / (n - 1) for i in range(n)]


GAP = 0.06             # 行間の最小クリアランス
OVERLAP_MIN = 0.1      # コンテナ帯と前行の「横方向重なり」判定しきい値


def _max_overlapping_stack(intervals, overlap_min=OVERLAP_MIN):
    """横方向に同時に重なる帯だけを積算し、必要な最大厚を返す。"""
    reduced = []
    solo_max = 0.0
    inset = overlap_min / 2
    for lo, hi, value in intervals:
        if hi - lo <= overlap_min:
            solo_max = max(solo_max, value)
            continue
        reduced.append((lo + inset, hi - inset, value))

    if not reduced:
        return solo_max

    bounds = sorted({point for lo, hi, _ in reduced for point in (lo, hi)})
    candidates = [(lo + hi) / 2 for lo, hi, _ in reduced]
    candidates += [(left + right) / 2
                   for left, right in zip(bounds, bounds[1:])
                   if right > left]
    overlap_max = max(
        sum(value for lo, hi, value in reduced if lo < x < hi)
        for x in candidates
    )
    return max(solo_max, overlap_max)


class Layout:
    def __init__(self, spec, reserve_note=False, content_area=None):
        self.spec = spec
        self.strict_container_clearance = content_area is not None
        self.dense = len(spec["rows"]) >= DENSE_ROW_THRESHOLD
        if content_area is None:
            x0, y0, x1, y1 = DENSE_AREA if self.dense else AREA
        else:
            x0, x1 = AREA[0], AREA[2]
            if self.dense:
                y0, y1 = content_area.top - 0.12, content_area.bottom
            else:
                y0, y1 = content_area.top + 0.05, content_area.bottom
        if reserve_note:
            y1 -= 0.30          # 右下の出典注記スペースを確保
        cols, rows = spec["cols"], spec["rows"]
        self.cols, self.rows = cols, rows
        self.area = (x0, y0, x1, y1)
        self.containers = {c["name"]: c for c in spec.get("containers", [])}
        self.children = {
            c["name"]: [m[1:] for m in c["members"] if m.startswith("@")]
            for c in spec.get("containers", [])
        }
        self.parent_of = {
            child: parent for parent, children in self.children.items()
            for child in children
        }
        # 端の列のラベルが領域内に収まるよう内側に寄せて等配置
        self.col_x = dict(zip(cols, _linspace(x0 + LABEL_W / 2,
                                              x1 - LABEL_W / 2, len(cols))))
        last_error = None
        for icon_size in stepped(ICON_SIZE, MIN_ICON_SIZE, ICON_STEP):
            self.icon_size = icon_size
            self.icon_r = icon_size / 2
            try:
                self._auto_rows()
            except FitError as e:
                last_error = e
                continue
            if icon_size < ICON_SIZE:
                self.fit_stage = "icon"
            else:
                self.fit_stage = "gap" if self.gaps_compressed else "standard"
            break
        else:
            raise FitError(
                "diagram: 余白圧縮とアイコン縮小を行っても縦方向に収まりません。"
                f"最小アイコンは{MIN_ICON_SIZE:.2f}inです。行数を減らすかsubを"
                f"減らしてください。詳細: {last_error}") from last_error
        self.cont_rect = {}
        self._resolve_containers()

    def _container_padding(self, name):
        """Return vertical/horizontal padding derived from diagram structure.

        Dense diagrams need compact vertical margins to preserve mandatory row
        gaps, while nested parents need extra horizontal room for outside lanes.
        The values are engine policy, not content-level coordinates.
        """
        if not self.dense:
            return 0.30, 0.30
        if name not in self.parent_of:       # outer boundary
            return 0.08, 0.30
        if self.children.get(name):          # nested parent with routing lanes
            return 0.04, 0.44
        return 0.10, 0.28                    # leaf boundary with label band

    def _half_w(self, name):
        """ノードの実効半幅(アイコンとタイトル実測幅の大きい方)。"""
        n = self.spec["nodes"][name]
        tw = text_width_in(n["title"], 11, "bold") + 0.1
        return max(self.icon_r + 0.12, min(LABEL_W, tw) / 2)

    def _auto_rows(self):
        """内容(ラベル深さ・コンテナ帯)に応じて行位置を自動計算する。"""
        nodes = self.spec["nodes"]
        x0, y0, x1, y1 = self.area
        by_row = {r: [n for n, v in nodes.items() if v["row"] == r]
                  for r in self.rows}

        def bot_ext(r):     # 行中心→ラベル下端(bottom発進ポート+次行
                            # top着信ポートの両方の余白を含む必須値。片方だけだと、
                            # 隣接行が近い時に発信ポートが着信ポートより下に来て
                            # 矢印が逆走する不具合になる。実際に発生した)
                            #
                            # 列単位でSUB_H計上を省略する案も試したが、コンテナの
                            # 上端算出(_resolve_containers)は行ピッチとは独立に
                            # 「そのコンテナの最上段ノードの行」だけで決まるため、
                            # ピッチを圧縮すると前の行のノードの出力ポートより
                            # コンテナの上端が上に来てしまう(実際に発生:
                            # az_aの上端がALBの下端ポートより上になった)。
                            # 行全体のSUB_H無条件計上のままにしておく。
            return self.icon_r + TITLE_H + (SUB_H if any(
                nodes[n].get("sub") for n in by_row[r]) else 0) + LABEL_ROW_GAP + EDGE_GAP

        def x_range(names):
            lo = min(self.col_x[nodes[n]["col"]] - self._half_w(n) for n in names)
            hi = max(self.col_x[nodes[n]["col"]] + self._half_w(n) for n in names)
            return lo, hi

        # コンテナごとの葉ノード・行範囲・横範囲・帯の厚み
        conts = self.containers

        def leaves(c):
            out = []
            for m in c["members"]:
                out += leaves(conts[m[1:]]) if m.startswith("@") else [m]
            return out

        bands = []
        for c in self.spec.get("containers", []):
            ls = leaves(c)
            idx = [self.rows.index(nodes[n]["row"]) for n in ls]
            pad, pad_x = self._container_padding(c["name"])
            lo, hi = x_range(ls)
            bands.append(dict(top=min(idx), bot=max(idx), x=(lo - pad_x, hi + pad_x),
                              band=pad + CONT_HEAD, bband=pad * 0.6))
        # 入れ子コンテナの上下マージンは「1本のチェーン」だけを積算する。
        # az_a/az_cのような兄弟コンテナを両方サムに含めると、実際には並んで
        # いるだけの余白を二重に見積もってしまい、縦方向を不必要に圧迫する
        # (実際に発生した不具合: 4行構成でこの過大見積もりが行間圧縮の
        # トリガーになり、ラベルが次行アイコンに食い込んだ)。
        band_by_name = {c["name"]: b for c, b in
                        zip(self.spec.get("containers", []), bands)}
        children = self.children
        parent_of = self.parent_of
        roots = [c["name"] for c in self.spec.get("containers", [])
                 if c["name"] not in parent_of]

        def chain_stack(name, key, side):
            b = band_by_name[name]
            total = b[key] if b[side] == (0 if side == "top" else len(self.rows) - 1) \
                else 0.0
            if total == 0.0:
                return 0.0
            for ch in children.get(name, []):
                if band_by_name[ch][side] == b[side]:
                    return total + chain_stack(ch, key, side)
            return total

        # 横に離れたルートコンテナの帯は同じY領域を共有できる。全ルートを
        # 単純加算せず、同時に横重なりするチェーンの最大厚だけを確保する。
        top_stack = _max_overlapping_stack([
            (*band_by_name[r]["x"], chain_stack(r, "band", "top"))
            for r in roots
        ])
        bot_stack = _max_overlapping_stack([
            (*band_by_name[r]["x"], chain_stack(r, "bband", "bot"))
            for r in roots
        ])

        # 行ピッチ = 必須分(前行ラベル深さ+次行アイコン半径。重なり厳禁) +
        #            裁量分(横方向に重なるコンテナ帯+GAP。収まらない時はここだけ圧縮)。
        # 必須分まで圧縮すると「ラベルが次行アイコンに食い込む」実欠陥になる
        # (実際に発生した不具合)ため、両者を分離して裁量分だけを縮める。
        mandatory, discretionary = [], []
        for i in range(1, len(self.rows)):
            container_extra = 0.0
            prev = by_row[self.rows[i - 1]]
            for b in (b for b in bands if b["top"] == i):
                if any(min(x_range([n])[1], b["x"][1]) -
                       max(x_range([n])[0], b["x"][0]) > OVERLAP_MIN
                       for n in prev):        # ノード単位で重なり判定
                    container_extra += b["band"]
            current = by_row[self.rows[i]]
            for b in (b for b in bands if b["bot"] == i - 1):
                if any(min(x_range([n])[1], b["x"][1]) -
                       max(x_range([n])[0], b["x"][0]) > OVERLAP_MIN
                       for n in current):
                    container_extra += b["bband"]
            base = bot_ext(self.rows[i - 1]) + self.icon_r
            # lead指定時は、次行コンテナの見出し帯と前行コンテナの下余白を
            # すべて必須分として扱う。ここを裁量圧縮すると、兄弟コンテナの
            # 上下境界が重なるか、境界線がノードのラベルを横切る。
            if self.strict_container_clearance:
                base += container_extra
                extra = 0.0
            else:
                extra = container_extra
            mandatory.append(base)
            discretionary.append(extra + GAP)
        first = y0 + top_stack + self.icon_r
        avail = y1 - first - bot_ext(self.rows[-1]) - bot_stack
        need_m, need_d = sum(mandatory), sum(discretionary)
        avail_d = avail - need_m
        if avail_d < 0:
            raise FitError(
                "diagram_layout: 縦方向に収まりません(ラベル+アイコンの必須分だけで"
                f"{need_m:.2f}in必要、利用可能領域は{avail:.2f}in)。行数を減らすか"
                "subを減らすか、ラベルを短くしてください。")
        self.gaps_compressed = need_d > avail_d
        if self.gaps_compressed:                  # 裁量分(余白)だけを圧縮
            discretionary = [d * avail_d / need_d for d in discretionary]
        else:                                      # 余りは45%を上に配って重心を上げる
            first += (avail_d - need_d) * 0.45
        pitches = [m + d for m, d in zip(mandatory, discretionary)]
        ys = [first]
        for p in pitches:
            ys.append(ys[-1] + p)
        self.row_y = dict(zip(self.rows, ys))

    # ---- ノード ----
    def node_center(self, name):
        n = self.spec["nodes"][name]
        return self.col_x[n["col"]], self.row_y[n["row"]]

    def _label_bottom(self, name):
        n = self.spec["nodes"][name]
        cy = self.row_y[n["row"]]
        return cy + self.icon_r + TITLE_H + (SUB_H if n.get("sub") else 0)

    def node_box(self, name):
        """アイコン+ラベルの外接矩形(コンテナ計算用)。幅はタイトル実測。"""
        cx, cy = self.node_center(name)
        half_w = self._half_w(name)
        return (cx - half_w, cy - self.icon_r,
                cx + half_w, self._label_bottom(name))

    def port(self, name, side, offset=0.0):
        """アイコン外周の直後に置く矢印端点。上下線はラベルの背後を通す。"""
        cx, cy = self.node_center(name)
        if side == "left":
            return (cx - self.icon_r - EDGE_GAP, cy + offset)
        if side == "right":
            return (cx + self.icon_r + EDGE_GAP, cy + offset)
        if side == "top":
            return (cx + offset, cy - self.icon_r - EDGE_GAP)
        return (cx + offset, cy + self.icon_r + EDGE_GAP)

    # ---- コンテナ ----
    def _resolve_containers(self):
        for c in reversed(self.spec.get("containers", [])):
            rects = [self.cont_rect[m[1:]] if m.startswith("@")
                     else self.node_box(m) for m in c["members"]]
            pad, pad_x = self._container_padding(c["name"])
            self.cont_rect[c["name"]] = (
                min(r[0] for r in rects) - pad_x,
                min(r[1] for r in rects) - pad - CONT_HEAD,
                max(r[2] for r in rects) + pad_x,
                max(r[3] for r in rects) + pad * 0.6)

    # ---- チャネル(配線レーン) ----
    def channel(self, name):
        kind, ref = self.spec["channels"][name]
        if kind == "outside_container":
            # 「列の隙間」ではなく「特定コンテナ(またはノード群)のすぐ外側」を
            # 指すレーン。同じ列を共有するノード間のローカルループに使う
            # (列基準のチャネルを流用すると、隣接する無関係な列まで大回りして
            # 他コンテナの境界線を貫通する。実際に2箇所で発生した不具合)。
            ref_id, side = ref
            if isinstance(ref_id, (list, tuple)):
                # コンテナ化されていないノード群: 自前で外接矩形を計算
                boxes = [self.node_box(n) for n in ref_id]
                r = (min(b[0] for b in boxes), min(b[1] for b in boxes),
                     max(b[2] for b in boxes), max(b[3] for b in boxes))
            else:
                r = self.cont_rect[ref_id]
            # 同じ外周辺に複数レーンが必要な場合もcontentへ間隔値を書かせず、
            # 宣言順に外側へずらす。個別gap指定は座標調整の再導入になる。
            siblings = [
                channel_name for channel_name, channel_spec
                in self.spec["channels"].items()
                if (channel_spec[0] == "outside_container"
                    and channel_spec[1] == ref)
            ]
            gap = 0.12 + siblings.index(name) * 0.22
            if side == "top_inside":
                # コンテナの外側ではなく「ラベル帯のすぐ下・内側」を指す。
                # ALB→Fargateのような「上のノードから、下のコンテナの中へ
                # まっすぐ入る」配線で使う。外側(top)を使うと、コンテナの
                # パディングが大きい場合に始点より上に出てしまい、線が
                # 逆流して手前のノード自身のラベルを横切る(実際に発生)。
                return "h", r[1] + CONT_HEAD + gap
            axis, pos = {"left": ("v", r[0] - gap), "right": ("v", r[2] + gap),
                        "top": ("h", r[1] - gap), "bottom": ("h", r[3] + gap)}[side]
            return axis, pos
        seq, pos = (self.cols, self.col_x) if "col" in kind else (self.rows, self.row_y)
        i = seq.index(ref)
        if kind in ("left_of_col", "above_row"):
            prev = pos[seq[i - 1]] if i else \
                (self.area[0] - 0.1 if "col" in kind else self.area[1] - 0.15)
            return ("v" if "col" in kind else "h", (prev + pos[ref]) / 2)
        nxt = pos[seq[i + 1]] if i + 1 < len(seq) else \
            (self.area[2] + 0.1 if "col" in kind else self.area[3] + 0.1)
        return ("v" if "col" in kind else "h", (pos[ref] + nxt) / 2)

    # ---- エッジ ----
    def _sides(self, e):
        src, dst = e["from"], e["to"]
        scx = (self.cont_rect[src[1:]][2] if src.startswith("@")
               else self.node_center(src)[0])
        scy = (self.row_y[e["from_row"]] if src.startswith("@")
               else self.node_center(src)[1])
        tcx, tcy = self.node_center(dst)
        dx, dy = tcx - scx, tcy - scy
        exit_d = e.get("exit") or ("right" if dx > 0.01 else
                                   "left" if dx < -0.01 else
                                   ("bottom" if dy > 0 else "top"))
        enter_d = e.get("enter") or ("left" if dx > 0.01 else
                                     "right" if dx < -0.01 else
                                     ("top" if dy > 0 else "bottom"))
        return exit_d, enter_d

    def route_edges(self, edges):
        """全エッジの経路を計算。同一辺・同一方向の多重エッジのみスロットでずらす。

        (node, side)だけをキーにすると、あるノードに「その辺から入るエッジ」と
        「その辺から出るエッジ」がたまたま1本ずつあるだけの場合まで同じグループに
        入り、無関係な2本を不要にオフセットしてジグザグな経路を作ってしまう
        (実際に発生した不具合)。in/outを区別してキーに含める。
        """
        sides = [self._sides(e) for e in edges]
        usage = {}
        for e, (xd, ed) in zip(edges, sides):
            # top/bottomは意図的にオフセットしない: 分岐/合流は同一点から
            # 出て横方向のジョグで分かれるのが自然で、細いアイコンの下で
            # 左右にずらすとアイコンの縁に沿って平行に走る不自然な形になる
            # (実際に発生した不具合)。ずらす必要があるのはleft/rightのみ。
            if not e["from"].startswith("@") and xd not in ("top", "bottom"):
                usage.setdefault((e["from"], xd, "out"), []).append(id(e))
            if ed not in ("top", "bottom"):
                usage.setdefault((e["to"], ed, "in"), []).append(id(e))

        def off(key, eid):
            ids = usage.get(key, [])
            n = len(ids)
            return (ids.index(eid) - (n - 1) / 2) * SLOT_PITCH if n > 1 else 0.0

        result = []
        for e, (exit_d, enter_d) in zip(edges, sides):
            src, dst = e["from"], e["to"]
            if src.startswith("@"):
                r = self.cont_rect[src[1:]]
                p0 = (r[2] if exit_d == "right" else r[0],
                      self.row_y[e["from_row"]])
            else:
                p0 = self.port(src, exit_d, off((src, exit_d, "out"), id(e)))
            p1 = self.port(dst, enter_d, off((dst, enter_d, "in"), id(e)))
            pts, cur = [p0], p0
            if e.get("via") and not src.startswith("@"):
                first_axis, _ = self.channel(e["via"][0])
                tangential = (
                    exit_d in ("top", "bottom") and first_axis == "v"
                    or exit_d in ("left", "right") and first_axis == "h"
                )
                if tangential:
                    dx, dy = {
                        "top": (0.0, -PORT_STUB),
                        "bottom": (0.0, PORT_STUB),
                        "left": (-PORT_STUB, 0.0),
                        "right": (PORT_STUB, 0.0),
                    }[exit_d]
                    cur = (cur[0] + dx, cur[1] + dy)
                    pts.append(cur)
            for ch in e.get("via", []):
                axis, v = self.channel(ch)
                cur = (v, cur[1]) if axis == "v" else (cur[0], v)
                pts.append(cur)
            if e.get("via"):
                # via指定後の最終進入区間が、enterの向きと逆走(または極端に
                # 短い)にならないようクランプする。例えばenter="top"なら
                # 「上から下へ」入るはずなので、直前の点はp1よりさらに上に
                # ないといけない。channelの値がp1を行き過ぎると、矢印が
                # 逆向きに描かれる/一瞬だけ戻る不自然な線になる
                # (実際に発生した不具合: ALB→Fargateで0.04inだけ逆走していた)。
                cur = MIN_SEG_CLAMP[enter_d](cur, p1)
                pts[-1] = cur
            if enter_d in ("left", "right"):
                if abs(cur[1] - p1[1]) > 0.01:
                    if not e.get("via") and abs(cur[0] - p1[0]) > 0.01:
                        cur = ((cur[0] + p1[0]) / 2, cur[1])   # 自動Z
                        pts.append(cur)
                    pts.append((cur[0], p1[1]))
            else:
                if abs(cur[0] - p1[0]) > 0.01:
                    if not e.get("via") and abs(cur[1] - p1[1]) > 0.01:
                        cur = (cur[0], (cur[1] + p1[1]) / 2)
                        pts.append(cur)
                    pts.append((p1[0], cur[1]))
            pts.append(p1)
            result.append([p for i, p in enumerate(pts)
                           if i == 0 or p != pts[i - 1]])
        return result

    # ---- 意味情報を使った自己検証(check_layout.pyでは検出不可能な領域) ----
    def _container_leaves(self):
        conts = {c["name"]: c for c in self.spec.get("containers", [])}

        def leaves(c):
            out = []
            for m in c["members"]:
                out += leaves(conts[m[1:]]) if m.startswith("@") else [m]
            return out
        return {name: set(leaves(c)) for name, c in conts.items()}

    @staticmethod
    def _crossings(pts, rect):
        """折れ線ptsが矩形rectの境界を横切った回数。"""
        def inside(p):
            return rect[0] < p[0] < rect[2] and rect[1] < p[1] < rect[3]
        states = [inside(p) for p in pts]
        return sum(a != b for a, b in zip(states, states[1:]))

    def _exempt_containers(self, e):
        """このエッジのviaが outside_container(コンテナ名, ...) を明示的に
        経由している場合、そのコンテナは「意図的な迂回」として境界越境を許可する。
        (ノード群指定 [..] は実コンテナではないので対象外)
        """
        out = set()
        for ch in e.get("via", []):
            kind, ref = self.spec["channels"][ch]
            if kind == "outside_container" and not isinstance(ref[0], (list, tuple)):
                out.add(ref[0])
        return out

    def validate_edges(self, edges, routed):
        """コンテナ所属が同じノード同士のエッジが、そのコンテナの境界を
        不要に横切っていないかを検証する。列基準のチャネルを性質の違う
        配線(ローカルループ等)に流用すると起きる不具合(過去に2回発生)を、
        画像を見なくても生成時点で検出するための仕組み。
        via で outside_container(そのコンテナ, ...) を明示的に使っている
        エッジは、意図的な迂回として2回分の越境まで許可する。
        """
        leaves = self._container_leaves()
        errors = []
        for e, pts in zip(edges, routed):
            src, dst = e["from"], e["to"]
            if src.startswith("@") or dst.startswith("@"):
                continue
            exempt = self._exempt_containers(e)
            for cname, members in leaves.items():
                s_in, d_in = src in members, dst in members
                expected = 0 if s_in == d_in else 1
                if cname in exempt:
                    expected += 2
                actual = self._crossings(pts, self.cont_rect[cname])
                if actual > expected:
                    errors.append(
                        f"edge {src}->{dst} crosses container '{cname}' boundary "
                        f"{actual} time(s) (expected <= {expected}). "
                        f"列基準チャネルを流用していないか、またはoutside_containerの"
                        f"via指定漏れを確認してください。")
        if errors:
            raise ValueError("diagram_layout: 配線がコンテナ境界を貫通しています:\n  "
                             + "\n  ".join(errors))
        self._validate_segment_lengths(edges, routed)
        self._validate_edge_contacts(edges, routed)

    @staticmethod
    def _same_point(a, b, eps=0.01):
        return abs(a[0] - b[0]) <= eps and abs(a[1] - b[1]) <= eps

    def _shared_route_endpoints(self, edge_a, route_a, edge_b, route_b):
        """共通ノード上で一致する経路端点だけを、意図した接続として返す。"""
        candidates = []
        endpoint_pairs = (
            ("from", 0, "from", 0),
            ("from", 0, "to", -1),
            ("to", -1, "from", 0),
            ("to", -1, "to", -1),
        )
        for key_a, idx_a, key_b, idx_b in endpoint_pairs:
            node_a, node_b = edge_a[key_a], edge_b[key_b]
            if node_a.startswith("@") or node_a != node_b:
                continue
            if self._same_point(route_a[idx_a], route_b[idx_b]):
                candidates.append(route_a[idx_a])
        return candidates

    def _validate_edge_contacts(self, edges, routed):
        """別エッジが途中で重なる、交差する、T字接触する経路を拒否する。"""
        eps = 0.01
        errors = []

        def between(value, a, b):
            return min(a, b) - eps <= value <= max(a, b) + eps

        def point_allowed(point, allowed):
            return any(self._same_point(point, candidate, eps) for candidate in allowed)

        for i, (edge_a, route_a) in enumerate(zip(edges, routed)):
            for edge_b, route_b in zip(edges[i + 1:], routed[i + 1:]):
                allowed = self._shared_route_endpoints(
                    edge_a, route_a, edge_b, route_b)
                pair_failed = False
                for a1, a2 in zip(route_a[:-1], route_a[1:]):
                    a_horizontal = abs(a1[1] - a2[1]) <= eps
                    for b1, b2 in zip(route_b[:-1], route_b[1:]):
                        b_horizontal = abs(b1[1] - b2[1]) <= eps
                        if a_horizontal == b_horizontal:
                            same_axis = (
                                abs(a1[1] - b1[1]) <= eps if a_horizontal
                                else abs(a1[0] - b1[0]) <= eps
                            )
                            if not same_axis:
                                continue
                            a_lo, a_hi = sorted(
                                (a1[0], a2[0]) if a_horizontal else (a1[1], a2[1]))
                            b_lo, b_hi = sorted(
                                (b1[0], b2[0]) if b_horizontal else (b1[1], b2[1]))
                            overlap_lo, overlap_hi = max(a_lo, b_lo), min(a_hi, b_hi)
                            if overlap_hi - overlap_lo > eps:
                                overlap_points = (
                                    ((overlap_lo, a1[1]), (overlap_hi, a1[1]))
                                    if a_horizontal
                                    else ((a1[0], overlap_lo), (a1[0], overlap_hi))
                                )
                                # 共通ノード端点から続く部分だけは、分岐・合流の共通幹線。
                                if any(point_allowed(point, allowed)
                                       for point in overlap_points):
                                    allowed.extend(overlap_points)
                                    continue
                                errors.append(
                                    f"edge {edge_a['from']}->{edge_a['to']} と "
                                    f"{edge_b['from']}->{edge_b['to']} の線分が重複しています")
                                pair_failed = True
                                break
                            if overlap_hi >= overlap_lo - eps:
                                point = ((overlap_lo, a1[1]) if a_horizontal
                                         else (a1[0], overlap_lo))
                                if not point_allowed(point, allowed):
                                    errors.append(
                                        f"edge {edge_a['from']}->{edge_a['to']} と "
                                        f"{edge_b['from']}->{edge_b['to']} が途中接触しています")
                                    pair_failed = True
                                    break
                            continue

                        horizontal = (a1, a2) if a_horizontal else (b1, b2)
                        vertical = (b1, b2) if a_horizontal else (a1, a2)
                        point = (vertical[0][0], horizontal[0][1])
                        if (between(point[0], horizontal[0][0], horizontal[1][0])
                                and between(point[1], vertical[0][1], vertical[1][1])
                                and not point_allowed(point, allowed)):
                            errors.append(
                                f"edge {edge_a['from']}->{edge_a['to']} と "
                                f"{edge_b['from']}->{edge_b['to']} が交差しています")
                            pair_failed = True
                            break
                    if pair_failed:
                        break
                if pair_failed:
                    break
            if errors:
                break
        if errors:
            raise ValueError("diagram_layout: 別エッジ同士が接続して見える経路です:\n  "
                             + "\n  ".join(errors))

    def _validate_segment_lengths(self, edges, routed):
        """経路の中間区間が極端に短くないか、最終区間が逆走していないかを
        検証する。

        中間区間の短さチェックは3点以上の経路が対象(via/自動Zルートの
        計算ミスで一瞬だけ逆走・迂回しているサインになる。実際に0.04inの
        逆走が発生した)。最終区間の向きチェックは2点だけの直線も含めた
        **全エッジ**が対象: MIN_SEG_CLAMPはvia指定時にしか働かないため、
        2点直線(ノード同士が隣接行で近い等)で行間の必須スペース計算が
        僅かに不足すると、矢印が逆向きに描かれる不具合をすり抜けていた
        (実際にRoute53<->CloudFrontで発生。指摘されるまで気づけなかった)。
        """
        errors = []
        for e, pts in zip(edges, routed):
            for (x1, y1), (x2, y2) in zip(pts[:-1], pts[1:]):
                if abs(x2 - x1) > 0.01 and abs(y2 - y1) > 0.01:
                    errors.append(
                        f"edge {e['from']}->{e['to']}: segment "
                        f"({x1:.3f},{y1:.3f})-({x2:.3f},{y2:.3f}) が直角ではありません。"
                        f"via/exit/enterの組み合わせを見直してください。")
            exit_d, enter_d = self._sides(e)
            if not e["from"].startswith("@"):
                (x1, y1), (x2, y2) = pts[0], pts[1]
                starts_outward = {
                    "top": y2 < y1,
                    "bottom": y2 > y1,
                    "left": x2 < x1,
                    "right": x2 > x1,
                }[exit_d]
                if not starts_outward:
                    errors.append(
                        f"edge {e['from']}->{e['to']}: 開始区間が exit=\"{exit_d}\" "
                        f"に対して垂直外向きではありません"
                        f"({x1:.3f},{y1:.3f})->({x2:.3f},{y2:.3f})。"
                        f"接続辺または最初のviaを見直してください。")
            if len(pts) >= 3:
                for idx, ((x1, y1), (x2, y2)) in enumerate(
                        zip(pts[:-1], pts[1:])):
                    length = abs(x2 - x1) + abs(y2 - y1)
                    minimum = (PORT_STUB if idx == 0
                               and not e["from"].startswith("@") else MIN_SEG)
                    if length < minimum - 0.01:
                        errors.append(
                            f"edge {e['from']}->{e['to']}: segment "
                            f"({x1:.3f},{y1:.3f})-({x2:.3f},{y2:.3f}) の長さ"
                            f"{length:.3f}in は最小値({minimum})未満です。"
                            f"via/exit/enterの組み合わせを見直してください。")
            if e["to"].startswith("@"):
                continue
            (x1, y1), (x2, y2) = pts[-2], pts[-1]
            ok = {"top": y2 > y1, "bottom": y2 < y1,
                 "left": x2 > x1, "right": x2 < x1}[enter_d]
            if not ok:
                errors.append(
                    f"edge {e['from']}->{e['to']}: 最終区間が enter=\"{enter_d}\" "
                    f"の向きと逆走しています({x1:.3f},{y1:.3f})->({x2:.3f},{y2:.3f})。"
                    f"行/列の間隔が不足している可能性があります。")
            if len(pts) == 2:
                # via無しの直結2点エッジも中間区間チェックと同じ基準で見る
                # (これが漏れていたためRoute53<->CloudFrontが0.005inまで
                # 潰れて事実上消えても検知できなかった)。
                length = abs(x2 - x1) + abs(y2 - y1)
                if length < MIN_SEG - 0.01:
                    errors.append(
                        f"edge {e['from']}->{e['to']}: 直結区間の長さ{length:.3f}in "
                        f"はMIN_SEG({MIN_SEG})未満です。行/列の間隔が不足しています。")
        if errors:
            raise ValueError("diagram_layout: 経路に不正な区間があります:\n  "
                             + "\n  ".join(errors))


def render_diagram(slide, spec, note=None, content_area=None):
    lay = Layout(spec, reserve_note=bool(note), content_area=content_area)
    edges = spec.get("edges", [])
    routed = lay.route_edges(edges)
    lay.validate_edges(edges, routed)
    for c in spec.get("containers", []):
        r = lay.cont_rect[c["name"]]
        container(slide, r[0], r[1], r[2] - r[0], r[3] - r[1], c["label"],
                  COLORS.get(c.get("color", "line"), LINE), dash=c.get("dash"))
    # コネクタを先に描き、ノードと実測幅マスク付きラベルを前面に置く。
    # 経路検証は描画前に済ませるため、マスクで不正な貫通を隠すことはない。
    for e, pts in zip(edges, routed):
        if len(pts) == 2 and e.get("both"):
            add_arrow(slide, *pts[0], *pts[1], dash=e.get("dash"), both=True)
        else:
            route(slide, pts, dash=e.get("dash"))
    for name, n in spec["nodes"].items():
        cx, cy = lay.node_center(name)
        icon_node(slide, cx, cy, n["icon"], n["title"], n.get("sub"),
                  size=lay.icon_size)
    for e, pts in zip(edges, routed):
        if e.get("label"):
            segs = list(zip(pts[:-1], pts[1:]))
            a, b = max(segs, key=lambda s: abs(s[1][0] - s[0][0])
                       + abs(s[1][1] - s[0][1]))
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            label_w = min(1.6, max(0.32,
                          text_width_in(e["label"], 9) + EDGE_LABEL_PAD_X))
            # dxとdyの大小で判定する(片方の絶対量だけでの閾値判定だと、
            # 極端に短い垂直区間のdyが閾値未満になり「水平」と誤判定して
            # 横並び用の描画分岐に入ってしまう。実際にr53<->cfの0.005in区間
            # で発生し、ラベルが自ノードのタイトルと重なる不具合になった)。
            horizontal = abs(b[1] - a[1]) < abs(b[0] - a[0])
            seg_len = abs(b[1] - a[1]) if not horizontal else abs(b[0] - a[0])
            label_h = line_height_in(9, 1.1) + EDGE_LABEL_PAD_Y
            if horizontal:
                # 水平セグメント: 線の上側にずらす(近接ノードとの干渉回避)。
                arrow_label(slide, mx, my - 0.17, e["label"],
                           w=label_w, size=9)
            elif seg_len >= label_h:
                # ノード名のマスク区間を除き、ラベルが収まる最長の空き区間を使う。
                # 上下ポートはアイコン外周にあるため、単純な線分中央はノード名と
                # 重なることがある(Route 53→CloudFrontで実際に発生した)。
                free = [(min(a[1], b[1]), max(a[1], b[1]))]
                for name in (e["from"], e["to"]):
                    if name.startswith("@"):
                        continue
                    ncx, ncy = lay.node_center(name)
                    if abs(mx - ncx) > lay._half_w(name) + 0.02:
                        continue
                    blocked = (ncy + lay.icon_r + 0.03,
                               lay._label_bottom(name) + 0.01)
                    next_free = []
                    for lo, hi in free:
                        if blocked[1] <= lo or blocked[0] >= hi:
                            next_free.append((lo, hi))
                            continue
                        if blocked[0] > lo:
                            next_free.append((lo, blocked[0]))
                        if blocked[1] < hi:
                            next_free.append((blocked[1], hi))
                    free = next_free
                candidates = [(hi - lo, (lo + hi) / 2) for lo, hi in free
                              if hi - lo >= label_h]
                if candidates:
                    _length, safe_y = max(candidates)
                    arrow_label(slide, mx, safe_y, e["label"],
                               w=label_w, size=9)
                    continue
                if free:
                    _length, my = max((hi - lo, (lo + hi) / 2)
                                      for lo, hi in free)
                seg_len = 0.0
            if not horizontal and seg_len < label_h:
                # 垂直セグメントが短すぎてラベルが収まらない: 線上を広く
                # マスクせず横に添える。実測高に満たない場合や、ノード名を除いた
                # 空き区間が不足する場合のフォールバック。
                lw = label_w
                cx = mx - lay.icon_r - EDGE_GAP - 0.04 - lw / 2
                arrow_label(slide, cx, my, e["label"], w=lw, size=9)
    if note:
        note_line(slide, note)
