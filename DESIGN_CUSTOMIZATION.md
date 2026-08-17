# スライドデザイン変更ガイド

## 結論

このリポジトリは、**1つのデザインを別のデザインへ置き換える作業**を局所的な変更で行える構成になっている。
配色・フォント・共通ヘッダー・基本rendererは `slidegen/generate.py`、表紙・フッターは
`slidegen/cover_footer.py` に集約され、
図解系も役割別のファイルに分離されているため、入力schemaを変えないデザイン変更は
rendererと共通部品の範囲に閉じ込めやすい。

表紙とフッターだけは `--cover-footer-config` でユーザー別の設定JSONを選択できる。
詳細は [`docs/cover-footer-customization.md`](docs/cover-footer-customization.md) を参照する。
本文を含むテーマ全体を実行時に切り替える仕組みはなく、デザインはPythonコード内の単一テーマとして
定義されているため、「テーマA / テーマBを切り替える」には別途テーマ層の実装が必要になる。

## 変更規模と難易度

| 変更規模 | 例 | 主な修正範囲 | 難易度 |
|---|---|---|---|
| テーマ差し替え | 色、背景、フォント、見出し、ページ番号、表紙 | 主に `generate.py` | 低〜中 |
| 表紙・フッター設定 | 背景画像、固定文言、表示項目、表紙とフッターだけの色 | `slidegen/cover_footer.py` + 設定JSON | 低 |
| 既存パターンの再デザイン | カード、比較、表、工程、ロードマップの造形変更 | `generate.py` + `diagrams*.py` | 中 |
| 図解の表現変更 | ノード、コンテナ、矢印、ラベル、構成図の色と線 | `diagrams.py` + `diagram_layout.py` | 中 |
| 新しいレイアウト追加 | 未対応のタイムライン、メッセージ1枚絵など新ジャンル | renderer + schema + validator + gallery | 高 |
| 複数テーマ切り替え | `--theme brand-a` のような実行時選択 | 新しいテーマ層 + 全rendererの参照変更 | 高 |

## 修正箇所一覧

| 対象 | ファイル / シンボル | 変更内容 |
|---|---|---|
| 基本配色 | `slidegen/generate.py` の `NAVY`〜`RULE` | 背景、本文、アクセント、罫線、薄色面のカラートークン。`WHITE`は濃色上の反転文字、`SURFACE`は通常の明るい塗り面に使い分ける |
| 基本フォント | `slidegen/generate.py` の `FONT` / `set_run()` | PowerPointに設定する日本語フォント、言語、太字、文字色 |
| フォント実測 | `slidegen/textfit.py` の `_font()` | `FONT` を変える場合に、Pillowが同じフォントファイルを測るよう変更 |
| スライド寸法・本文領域 | `generate.py` の `SLIDE_W` / `SLIDE_H` / `MARGIN` / `BODY_*` | 画面比率、余白、本文の使用可能領域。変更影響が大きいため全rendererを再検証 |
| 表紙・フッター | `slidegen/cover_footer.py` / `--cover-footer-config` | 表紙、ページ番号、フッター文言。利用者別設定はコード変更不要 |
| 共通ヘッダー・注記 | `generate.py` の `header()` / `note_line()` | 全本文スライドの背景、見出し、注記 |
| 箇条書き | `generate.py` の `s_bullets()` | 番号、区切り、縦詰め、本文サイズ |
| カード / KPI | `generate.py` の `s_cards()` | 列数計算、強調カード、背景面、見出しと本文の階層 |
| 比較表 | `generate.py` の `s_table()` / `_cell()` | ヘッダー、行高、交互色、列見出し、文字位置 |
| 2カラム比較 | `two_column` (`generate.py` の `s_twocol()`) | 左右のコントラスト、見出し、箇条書き、区切り |
| グラフ | `generate.py` の `s_chart()` | グラフ面、系列色、凡例、余白、データラベル |
| 大判画像 | `slidegen/image_slide.py` の `s_image()` / `fit_image_layout()` | 画像枠、contain/cover、右下影、縮小限界 |
| 図解共通部品 | `slidegen/diagrams.py` の `LINE` / `add_arrow()` / `arrow_label()` / `container()` / `icon_node()` | アイコンノード、枠、矢印、線上ラベルの見た目 |
| 体制図 | `org_layout.py` の `OrgLayout` | 階層DAG、関係線、ノードstyle、段階的収容 |
| 工程 / ロードマップ / 2軸図 | `slidegen/diagrams2.py` の各 `s_*()` | 各ジャンル固有の線、帯、点、ラベル、余白 |
| 構成図の色名 | `slidegen/diagram_layout.py` の `COLORS` | diagram specで指定できる離散的な色名と実色の対応 |
| 構成図レイアウト | `diagram_layout.py` の `Layout` / `render_diagram()` | 座標、行間、配線、コンテナ。色だけの変更では触らない |
| アイコン | `slidegen/assets/icons/` / `slidegen/assets/CREDITS.md` | 素材の追加とクレジット。AWSアイコン自体の色・比率・形状は変更禁止 |
| デザイン検証一覧 | `slidegen/content_patterns.py` | 全rendererを1デッキで確認するためのサンプル内容 |
| 品質検証 | `check_layout.py` / `render.ps1` / `contact_sheet.py` | 衝突検査、PowerPoint実レンダリング、一覧目視 |

## 変更内容別の最小修正範囲

### 配色だけ変える

1. `generate.py` のカラートークンを変更する。
2. AWS以外の図解線色を変える場合は `diagrams.py` の `LINE` を変更する。
3. diagram specから新しい色名を使わせる場合だけ `diagram_layout.py` の `COLORS` を増やす。

本文スライドの面を真っ白に戻さない。`WHITE`は濃色面上の文字や輪郭に限定し、カード、表セル、
図解ノードなどの通常面には`SURFACE`を使う。`SURFACE`は`CANVAS`との差を小さく保ち、罫線や
`ZEBRA`との濃淡で構造を示す。

`content.json`、schema、validatorの変更は不要。

### フォントを変える

1. `generate.py` の `FONT` を変更する。
2. `textfit.py` のフォントファイル参照を同じ書体へ変更する。
3. グラフの `chart.font.name` も `FONT` を参照していることを確認する。
4. 全パターンを再生成し、折り返し・禁則・表の行高を再検証する。

PowerPoint側だけフォントを変え、`textfit.py` を変えない状態は禁止。測定値と実描画がずれて溢れの原因になる。

### 表紙とフッターだけ変える

利用者ごとの差し替えは、`generate.py` を編集せず `--cover-footer-config` を使う。
設定できる項目と実行方法は [`docs/cover-footer-customization.md`](docs/cover-footer-customization.md) を参照する。

標準デザイン自体を変更する場合は `slidegen/cover_footer.py` の標準設定と描画を変更する。

### 共通ヘッダーと注記も変える

`generate.py` の `header()`、`note_line()` が対象。
renderer内部の配置を変えなければ、本文パターンへの影響は限定的。

### 既存パターンの構図を変える

対象rendererの `s_*()` を変更する。入力フィールドを増減しない限り、`content.json` とschemaは変更不要。
入力フィールドや件数前提を変える場合は、`validate_content.py`、`CONTENT_SCHEMA.md`、
`AI_DECK_PROMPT.md`、`content_patterns.py` も同時変更する。

### 複数テーマを切り替えられるようにする

複数テーマの実行時切り替えは標準機能に含まれない。追加する場合は次の修正が必要。

1. カラー、フォント、余白、線幅などを持つ `Theme` 定義を新設する。
2. `generate.py` のモジュール定数参照を `theme.*` 参照へ置き換える。
3. `diagrams.py` / `diagrams2.py` / `diagram_layout.py` へ同じThemeを渡す。
4. `generate_from_json.py` にCLIオプションを追加する。
5. テーマごとにパターンギャラリーを生成し、全テーマを品質ゲートへ通す。

テーマ名を `content.json` に入れるか、CLIだけで選ぶかは運用設計が必要。資料内容とブランド指定を分離するなら、
`content.json` ではなくCLIまたは別設定ファイルで選ぶ方が安全。

## 通常は変更不要なもの

見た目だけを変更し、入力schemaとレイアウト能力を変えない場合は次を変更しない。

- `content.json`
- `CONTENT_SCHEMA.md`
- `AI_DECK_PROMPT.md`
- `slidegen/validate_content.py`
- `slidegen/diagram_specs.py`
- `slidegen/generate_from_json.py`

## 必須検証

デザイン変更は色・Z順・コントラストを伴うため、機械検査だけでは完了にしない。

```powershell
python slidegen/generate_patterns.py out\pattern_gallery.pptx
python slidegen/check_layout.py out\pattern_gallery.pptx
powershell -ExecutionPolicy Bypass -File render.ps1 -PptxPath out\pattern_gallery.pptx -OutDir out\png_pg
python contact_sheet.py out\png_pg

python slidegen/generate_from_json.py content.json out\content_deck.pptx
python slidegen/check_layout.py out\content_deck.pptx

python slidegen/generate2.py out\sample_16slides.pptx
python slidegen/check_layout.py out\sample_16slides.pptx
```

確認観点:

- 全ページでタイトル、本文、注記、ページ番号が読めるか
- 色のコントラストが十分か
- 長い日本語タイトルが不自然に折り返されていないか
- 表・カード・ロードマップの内容量が変わっても間延びや溢れがないか
- 図解の線、ラベル、コンテナ、アイコンが干渉していないか
- AWSアイコンを無改変で使用しているか
