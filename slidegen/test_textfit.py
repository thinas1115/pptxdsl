"""textfitの動作確認。結果をUTF-8ファイルに出力する。"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from textfit import (
    balance_last_line,
    fit_font_size,
    fits,
    text_width_in,
    title_lines_are_natural,
    wrap_body,
    wrap_compact,
    wrap_natural,
    wrap_text,
    wrap_title,
)

out = []
w = text_width_in("生成AIスライド調査報告", 24, "bold")
out.append(f"width(11chars,24pt,bold) = {w:.3f} in")
assert 2.5 < w < 5.0, "幅が想定レンジ外"

lines = wrap_text("どのツールでも生成後に15〜30分の手作業調整が必須という実測結果。", 3.0, 14)
out.append("wrap 3.0in/14pt:")
for l in lines:
    lw = text_width_in(l, 14)
    out.append(f"  [{lw:.2f}in] {l}")
    assert lw <= 3.0 + 0.01, f"行が幅超過: {l}"
# 行頭禁則: 「。」「、」で始まる行がないこと
assert not any(l and l[0] in "、。" for l in lines), "行頭禁則違反"
assert any("15〜30分" in l for l in lines), lines
assert "15〜3\n0分" not in "\n".join(lines), lines

balanced = balance_last_line(
    ["プライベート接続でハマった落とし穴", "3選"],
    8.05, 42, "bold")
assert balanced[-1] != "3選", balanced
assert all(text_width_in(line, 42, "bold") <= 8.05 for line in balanced)

explicit_break = wrap_title(
    "プライベート接続でハマった落とし穴\n3選", 8.05, 42, "bold")
assert "ハマった" not in explicit_break, explicit_break
assert explicit_break[-1].endswith("落とし穴3選"), explicit_break

english = balance_last_line(
    ["Site-to-Site VPN over Direct Connect ", "3選"],
    8.05, 36, "bold")
assert "Connec\nt" not in "\n".join(english), english

long_title = (
    "Site-to-Site VPN over Direct Connectのプライベート接続で"
    "ハマった落とし穴3選")
title_size, title_lines = fit_font_size(
    long_title, 8.05, 2.15, 42, min_pt=34, weight="bold",
    spacing=1.08, wrapper=wrap_title,
    line_validator=title_lines_are_natural)
for word in ("Site-to-Site", "Direct", "Connect", "プライベート"):
    assert any(word in line for line in title_lines), title_lines
assert title_lines[-1] != "3選", title_lines
assert title_size < 42, title_size
assert title_lines_are_natural(title_lines), title_lines

size, flines = fit_font_size("社内テンプレート準拠の現実解を検証する", 2.5, 1.0, 20)
out.append(f"fit -> {size}pt, {len(flines)} lines: {flines}")
assert fits("社内テンプレート準拠の現実解を検証する", 2.5, 1.0, size)
assert not any(line.endswith("準") for line in flines), flines
assert not any(line.startswith("拠") for line in flines), flines
assert len(flines[-1]) > 1, flines

private = wrap_text("プライベート接続を構成する", 1.7, 16)
assert not any("プライベー" in line and "ト" not in line for line in private), private
for wrapper in (wrap_natural, wrap_body, wrap_compact):
    protected = wrapper("プライベート接続", 0.8, 16)
    assert not any(line in {"プライベー", "ト"} for line in protected), protected
    assert any("プライベート" in line for line in protected), protected

japanese = wrap_compact("運用監視改善計画", 0.8, 16)
assert len(japanese) > 1
assert all(text_width_in(line, 16) <= 0.81 for line in japanese), japanese

out.append("ALL OK")
print("\n".join(out))
