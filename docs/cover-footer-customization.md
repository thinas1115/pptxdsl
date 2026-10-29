# テンプレート設定（本文背景・表紙・フッター）

利用者のスライドテンプレートへ合わせる場合は、`content.json`とは別の設定JSONに本文背景、表紙背景、
フッター文字と色をまとめる。本文領域の座標や図解の構造は変更しない。
既存の`--cover-footer-config`と設定JSONはそのまま使える。新しい`--template-config`は同じ指定の別名。

## 雛形を1コマンドで作る

```text
python -m slidegen.template_config out/template.json --background-color FFFFFF --footer-text "社内限定"
python slidegen/generate_from_json.py content.json out/deck.pptx --template-config out/template.json
```

背景画像を使う場合は、文字を含まないPNG/JPEGを用意して指定する。配置場所を固定せず、
設定ファイルからの相対参照を自動で作る。既存ファイルは上書きしない。

```text
python -m slidegen.template_config out/template.json --background-image assets/body.png --cover-background-image assets/cover.png --footer-text "{organization} / {footer}"
```

生成したJSONの`slide`、`cover`、`footer`を一か所で編集し、別のデッキにも再利用できる。
個人設定と素材は利用者の作業領域へ置く。Pluginの同梱コードや画像を差し替える必要はない。
これはPPTX/POTXのマスター・自由配置を丸ごと取り込む機能ではない。背景に本文やフッター文字を焼き込むと
生成テキストと二重になるため、背景素材からは除く。
Release配布のSkill/Pluginでは、同梱の`run.py template out/template.json`で雛形を作り、
`run.py generate content.json out/deck.pptx --template-config out/template.json`で適用する。

## 実行方法

設定例を指定して生成する。

```powershell
python slidegen/generate_from_json.py content.json out/deck.pptx --cover-footer-config examples/cover_footer.json
python slidegen/check_layout.py out/deck.pptx
```

`--cover-footer-config` を省略すると、標準の表紙・フッター設定で生成する。
個人や部署専用の設定をリポジトリへ登録しない場合は、リポジトリ直下の
`cover_footer.local.json` を使用できる。このファイルは `.gitignore` 対象だが、
自動読込はしないためCLIで明示する。

```powershell
python slidegen/generate_from_json.py content.json out/deck.pptx --cover-footer-config cover_footer.local.json
```

カスタム表紙背景は `slidegen/assets/cover/` に配置する。ルートの
`cover_footer.local.json` からは `slidegen/assets/cover/<ファイル名>`、同梱の
`examples/cover_footer.json` からは `../slidegen/assets/cover/<ファイル名>` で参照する。

同じオプションは次のgeneratorでも使用できる。

- `tools/gallery/generate_basic.py`
- `tools/gallery/generate_extended.py`
- `tools/gallery/generate_patterns.py`

## content.jsonとの責任分担

`content.json` の `meta` は資料ごとに変わる内容を持つ。

| 項目 | 用途 |
|---|---|
| `meta.title` | 必須。資料名。フッター設定の `{title}` から参照できる |
| `meta.footer` | 任意。資料固有のフッター文言。`{footer}` から参照できる |
| `meta.date` | 任意。標準表紙の`DATE`と `{date}` |
| `meta.organization` | 任意。標準表紙の`ORGANIZATION`と `{organization}` |
| `meta.author` | 任意。標準表紙の`AUTHOR`と `{author}` |

任意項目を省略すると、対応する表紙・フッター要素は描画されない。

表紙・フッター設定JSONは、表示する要素、固定文言、配色、表紙背景画像を持つ。資料内容とブランド設定を
分離することで、同じ `content.json` を利用者別の表紙・フッターで再生成できる。

## 設定項目

### slide

| 項目 | 型 | 既定値 / 説明 |
|---|---|---|
| `background_color` | string | 本文・章扉の背景色。6桁HEX、既定`F7F5EF` |
| `background_image` | string / null | 本文・章扉の背景PNG/JPEG。設定JSONからの相対パス。既定`null` |

表紙には`cover`の設定を使う。画像は縦横比を保って中央基準で全面へトリミングし、PPTXへ埋め込む。
既存の紺色文字・図形を読み取れる明るい背景を使い、本文・図形を覆わないよう背景の模様やロゴ位置を確認する。
背景色の変更は本文の文字色・全図形の配色を自動変換しない。暗い本文背景の全面テーマ変換は対象外。
背景画像内部のコントラストは機械検査で保証できないため、全ページPNGで文字と線を確認する。

### cover

| 項目 | 型 | 既定値 / 説明 |
|---|---|---|
| `eyebrow` | string | 左上の文書区分。既定値は空文字。最大48文字 |
| `show_date` | boolean | 右上の日付を表示する。既定値は `false` |
| `show_author` | boolean | 左下の作成者を表示する。既定値は `false` |
| `show_rail` | boolean | 右側の補足情報を表示する。既定値は `true` |
| `rail` | array | `label` / `value` の組。0〜3件。既定値は`DATE / ORGANIZATION / AUTHOR` |
| `background_image` | string / null | 表紙背景のPNG/JPEG。既定値は同梱の`slidegen/assets/cover/cover-background.png`。利用者の指定は設定JSONからの相対パスに限定する |
| `background_color` | string | 表紙背景の6桁HEX色 |
| `title_color` | string | タイトル・作成者・rail値の6桁HEX色 |
| `secondary_color` | string | サブタイトル・日付・rail線の6桁HEX色 |

### footer

| 項目 | 型 | 既定値 / 説明 |
|---|---|---|
| `text` | string | 左側の文言。最大100文字 |
| `show_divider` | boolean | 本文との境界線を表示する |
| `show_text` | boolean | 左側の文言を表示する |
| `show_page_number` | boolean | 現在ページを表示する |
| `show_total` | boolean | 総ページ数も表示する |
| `text_color` | string | 左側文言・総ページ数の6桁HEX色 |
| `page_color` | string | 現在ページの6桁HEX色 |
| `divider_color` | string | 境界線の6桁HEX色 |

設定JSONは部分指定できる。省略した項目には標準設定が使われる。
個人パスを公開設定へ混入させないため、背景画像の絶対パス、ドライブ相対パス、
ホーム展開はOSにかかわらず拒否する。既存設定は画像を設定JSONの近くへ配置し、
その場所からの相対パスへ移行する。設定JSON自体のCLI引数には絶対パスを使用できる。
`background_image` を指定すると、画像の縦横比を維持したまま中央基準で表紙全面へトリミングする。
標準設定では同梱の`cover-background.png`を使用する。単色背景へ戻す場合は、設定JSONで
`background_image: null`を明示すると`background_color`が使われる。画像上の文字が読めるよう、画像に合わせて
`title_color` と `secondary_color` も指定する。背景には16:9で十分な解像度の画像を推奨する。
画像は生成時にPPTXへ埋め込まれるため、生成後の閲覧時に元画像は不要。
標準表紙は、タイトルとサブタイトルの右側に`DATE / ORGANIZATION / AUTHOR`のrailを表示する。

### 社内資料向けの日本語ラベル

既存の`cover.rail`だけで項目名を日本語化できる。
[日本語設定例](../examples/cover_footer.ja.json)では、標準の構図・配色・背景を維持し、
右欄を「日付・所属・作成者」へ変更している。

```powershell
python slidegen/generate_from_json.py content.json out/deck-ja.pptx --cover-footer-config examples/cover_footer.ja.json
python slidegen/check_layout.py out/deck-ja.pptx
```

設定JSONの内容は次のとおり。`{date}`などの参照名は翻訳せず、`label`だけを変更する。

```json
{
  "cover": {
    "show_date": false,
    "show_author": false,
    "show_rail": true,
    "rail": [
      {"label": "日付", "value": "{date}"},
      {"label": "所属", "value": "{organization}"},
      {"label": "作成者", "value": "{author}"}
    ]
  }
}
```

`organization`・`author`を参照する値は、日本語ラベルでも既存と同じ最大3行を使用できる。
会社名・部門名などを分ける場合は`meta.organization`などに`\n`で改行を入れる。
標準の英語ラベルと既存設定の動作は変更しない。

### 標準ラベルと省略時の動作

- `DATE`: `meta.date`を表示する
- `ORGANIZATION`: `meta.organization`を表示する
- `AUTHOR`: `meta.author`を表示する

未指定の値は項目ごと描画されず、残った項目だけでrailの高さと間隔を再計算する。3項目すべてが
未指定ならrail自体を描画せず、タイトルとサブタイトルは表紙の横幅を広く使用する。値が不明または
不要な場合は、空文字や仮文言を入れず`meta`のフィールド自体を省略する。

`ORGANIZATION`と`AUTHOR`の値は最大3行。JSON文字列内の`\n`で改行位置を指定でき、改行を
指定しない長い文言も幅に合わせて自動折り返しする。会社名・部門名・チーム名、または氏名・役職を
別の行へ分ける。4行以上になる場合は文字を潰して描画せず、生成を停止する。`DATE`などそれ以外の
補足値は1行で表示する。

従来の右上日付・左下作成者へ戻す場合は、`show_rail: false`、`show_date: true`、
`show_author: true`を明示する。railと従来位置へ同じ値を重複表示する設定は生成前に拒否する。

`SCOPE`へページ数やパターン数、`OUTPUT`へPowerPointやPDF、`QUALITY`へ生成・検証工程を書く例は、
受け手の判断情報にならないため使用しない。左上の`eyebrow`は「経営会議資料」「計画書」「レビュー版」
など文書区分が必要な場合だけ使い、タイトルの英訳や言い換えは書かない。補足情報自体が不要なら、
`meta.date`、`meta.organization`、`meta.author`を省略するか、カスタム設定で`show_rail`を`false`にする。

```json
{
  "cover": {
    "background_image": "../slidegen/assets/cover/cover-background.png",
    "title_color": "FFFFFF",
    "secondary_color": "E5ECEA",
    "show_date": false,
    "show_author": false,
    "show_rail": true,
    "rail": [
      {"label": "DATE", "value": "{date}"},
      {"label": "ORGANIZATION", "value": "{organization}"},
      {"label": "AUTHOR", "value": "{author}"}
    ]
  },
  "footer": {
    "text": "{footer}",
    "show_total": false
  }
}
```

## プレースホルダー

`cover.eyebrow`、`cover.rail[*].label`、`cover.rail[*].value`、`footer.text` では
次のプレースホルダーを使える。

- `{title}`
- `{footer}`
- `{date}`
- `{organization}`
- `{author}`
- `{page}`
- `{total}`

数値にはPythonの書式指定を使用できる。例: `{page:02d}`、`{total:02d}`。
未対応のプレースホルダー、6桁HEX以外の色、4件以上のrail、未知の設定項目は
PPTX生成前にエラーになる。

## 意図的に設定対象にしないもの

- 表紙・フッターの座標とサイズ
- 本文領域の上下端
- スライドタイトル、カード、表、図解など本文rendererの配色
- 構成図のノード・配線・コンテナ
- フォント

これらまで変更すると表紙・フッターの個人設定ではなく全体テーマ変更になり、全rendererの
再検証が必要になる。全体テーマを変更する場合は `DESIGN_CUSTOMIZATION.md` を参照する。
