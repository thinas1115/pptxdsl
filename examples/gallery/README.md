# サンプルスライドギャラリー

対応する28種類のtypeを、38枚の出力例で比較できます。Gitには下の縮小一覧を置き、
PowerPointで編集できるPPTXはRelease・CI成果物として配布します。

![TYPE別パターンギャラリー](../../docs/pattern-gallery-by-type.png)

## PPTXを取得する

- 安定版は[最新Release](https://github.com/thinas1115/pptxdsl/releases/latest)の`pattern_gallery.pptx`を取得してください。Pythonやcloneは不要です。
- 開発中の版は[品質ゲート](https://github.com/thinas1115/pptxdsl/actions/workflows/quality-gate.yml)で対象PR・コミットの実行を開き、`pptxdsl-distributions`を取得してください。PNGは`font-contract-*`に含まれます。CI成果物の保存期限やアクセス権に注意してください。
- オフラインやforkでは、次の手順で手元のコミットから生成できます。Releaseの取得権限は不要です。

## 手元のコードから生成する

リポジトリルートで[セットアップ](../../README.md#セットアップ)を済ませてから実行してください。
PPTX生成にPowerPointは不要です。PNG描画にはPowerPoint、またはLibreOfficeとPDF画像化手段が必要です。

```powershell
python -m tools.gallery.generate_patterns out/pattern_gallery.pptx
python -m slidegen.check_layout out/pattern_gallery.pptx
python .agents/skills/pptxdsl/scripts/render_preview.py out/pattern_gallery.pptx out/gallery-png
python contact_sheet.py out/gallery-png
```

各ページの原寸PNGと一覧を確認します。Gitへ載せるtype別一覧は960px幅です。
詳細を見るための1920px版は`out/`へ保存できます。

```powershell
python -m tools.gallery.build_gallery_overview out/gallery-png docs/pattern-gallery-by-type.png
python -m tools.gallery.build_gallery_overview out/gallery-png out/gallery-overview.png --width 1920
```

## ギャラリーを新規資料の題材へ流用しない

ギャラリーは人間のレイアウト選定とrendererの回帰検証用です。新しい資料を作る生成AIへ
題材・文言・数値・ページ順の見本として渡さないでください。生成AIへ渡す資料は、
記入済みの[AI_DECK_PROMPT.md](../../AI_DECK_PROMPT.md)、
[CONTENT_SCHEMA.md](../../CONTENT_SCHEMA.md)、[type選定ガイド](../../docs/type-selection-guide.md)です。

追跡対象、Release生成、履歴の扱いは[ギャラリー配布方針](../../docs/gallery-distribution.md)を参照してください。
取得・生成で解決しない問題は、利用したコミットと公開可能なエラー概要を添えて
[Issue](https://github.com/thinas1115/pptxdsl/issues)へ報告してください。
