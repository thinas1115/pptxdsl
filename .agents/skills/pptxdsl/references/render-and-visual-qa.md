# レンダリングと目視QA

PPTX生成と`check_layout.py`の成功だけでは完成にしない。実行環境で使えるbackendを確認し、全ページをPNGへ変換して確認する。

## Backendの探索と実行

最初に同梱スクリプトで利用可能な方法を確認する。

```text
python .agents/skills/pptxdsl/scripts/render_preview.py --probe
```

`auto`は、WindowsでPowerPoint COMと`render.ps1`を利用できる場合はPowerPointを優先し、それ以外ではLibreOfficeとPDF画像化手段の組み合わせを使う。

非WindowsでPPTXを生成する場合は、`fontconfig`から検出できる日本語sansフォントも必要になる。
Noto Sans CJKを推奨する。環境側のフォントを明示する場合は、
`PPTXDSL_FONT_REGULAR`、`PPTXDSL_FONT_MEDIUM`、`PPTXDSL_FONT_BOLD`へファイルパスを設定する。

```text
python .agents/skills/pptxdsl/scripts/render_preview.py out/deck.pptx out/png
python contact_sheet.py out/png
```

必要なら`--backend powerpoint`または`--backend libreoffice`で固定する。スライド番号を限定した再確認には`--slides 3,7`を使う。代替backendを追加できる環境では、同じくページ単位のPNGが得られる方法を使ってよい。使用した製品・コマンド・制約を最終報告へ残す。

## 確認順

1. `out/png/sheet.png`を表示し、全体のリズム、密度、欠落、極端な余白、ページ間の不整合を確認する。
2. 全ページの`slide_*.png`を原寸で表示し、文字切れ、重なり、不自然な改行、コントラスト、線幅、整列、余白を確認する。
3. 構成図、工程図、関係図では、接続点から終点までを線ごとに追い、矢印、線上ラベル、差戻し経路、ラベル背景による線の欠けを確認する。
4. 内容を情報源と照合し、数値・単位・固有名詞・線の向き・強調対象が正しいか確認する。
5. 問題を直し、validate、generate、check_layout、render、目視QAを再実行する。

PowerPoint以外のbackendでは、フォント置換や描画差が残る可能性を明記する。利用可能な方法を調査してもPNG化できない場合は、調査内容を報告して停止し、目視確認済みとは扱わない。
