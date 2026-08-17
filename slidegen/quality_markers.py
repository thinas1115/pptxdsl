"""生成後の品質ゲートへ意味を伝える図形名マーカー。"""

SURFACE_ON_CANVAS_PREFIX = "qa-surface-on-canvas:"
MIN_SURFACE_CONTRAST = 1.12
MIN_SURFACE_EDGE_CONTRAST = 1.30

# sequence rendererと生成後検査で共有する意味名。図形名を品質契約として扱う。
SEQUENCE_SELF_ROUTE_PREFIX = "sequence-self-route:"
SEQUENCE_MESSAGE_LABEL_PREFIX = "sequence-message-label:"
SEQUENCE_LABEL_CLEARANCE = 0.03
