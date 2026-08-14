# content.json schema

`content.json` はスライド内容を表すJSON。座標、余白、フォント、色、描画順は renderer が決める。

重要: 「content.jsonだけで生成できる」とは、各 `type` が要求する必須フィールドをすべて持つJSONを用意する、という意味。自由文だけでは生成できない。

`content.json` は資料ごとに新規作成するGit管理外の入力ファイル。リポジトリの回帰検証用データを
新規資料の題材として流用しない。

この文書のJSONは、許可フィールドと入れ子構造を示す最小限の断片である。`分類`、`タイトル`、`本文`などの
値や、typeの掲載順を新規資料へ流用しない。typeの選定は
[docs/type-selection-guide.md](docs/type-selection-guide.md)の「選ぶ場面・選ばない場面・代替」に従い、
実際の文言・固有名詞・数値は資料要件と指定された情報源から作成する。

`slidegen/content*.py`と`slidegen/diagram_specs.py`はrendererの回帰検証と目視QAのためのデータであり、
schema例ではない。通常のvalidatorは、そこにある正規化後14文字以上の日本語文言を流用した入力を拒否する。

## 機械検証

このschemaの必須フィールド、許可フィールド、件数制約は `slidegen/validate_content.py` が機械的に検証する。
`generate_from_json.py` は生成前に自動で検証し、NGなら生成せずエラー一覧を出す。
件数制約を通過しても、実際の文言量によってはrendererの収容判定で生成を停止する。rendererは
標準配置、裁量余白の圧縮、ジャンルごとに定めた文字・図形の縮小を順に試し、提出品質を保つ
最小値でも収まらない場合は黙って溢れさせない。エラーに従って文言を短くする、項目を減らす、
スライドを分割する、または新しいレイアウタを実装する。`content.json`へ座標やサイズを追加して回避しない。
単体で検証だけ行う場合:

```powershell
python slidegen/validate_content.py content.json
```

エラーメッセージは `slides[番号] (type=種別): 内容` の形式。生成AIにそのまま渡して直させる。

## トップレベル

必須:

- `meta.title`: string
- `slides`: slide object の配列

任意:

- `meta.footer`: フッターへ表示する資料固有の文言
- `meta.date`: 表紙右側railの`DATE`へ表示する日付
- `meta.organization`: 表紙右側railの`ORGANIZATION`へ表示する会社・組織・部門名
- `meta.author`: 表紙右側railの`AUTHOR`へ表示する作成者・責任者

値が不明または表示不要な任意項目は、空文字や仮文言を入れずキー自体を省略する。

```json
{
  "meta": {
    "title": "<資料要件から作成した資料名>"
  },
  "slides": [
    {
      "type": "title",
      "title": "<資料の主題>",
      "subtitle": "<対象範囲または目的>"
    }
  ]
}
```

`<...>` は入力箇所を示すschema表記であり、実際の `content.json` に残すとvalidatorが拒否する。

## 共通ルール

- `slides[*].type` は必須。
- この文書に記載のないフィールドは、トップレベル・meta・slide・入れ子objectのどこに書いてもvalidatorが拒否する。rendererが黙って無視するフィールドは作らない。
- `type: "title"` は任意。表紙なし、任意位置、複数枚のいずれも使用できる。
- `type: "title"` 以外は `kicker` と `title` が必須。
- すべての`slides[*].title`は、`研修の目的`、`前提知識`、`VLANとは`、`同一VLAN内の通信`のような
  **名詞句または短い疑問形の見出し**にする。結論・因果・行動を言い切る文章、読点・句点・改行、
  文末の述語を含めず、疑問形にも疑問符を付けない。結論や読み方は`lead`、根拠は本文へ書く。
- 文章型タイトルを許可するのは回帰検証ギャラリーの内部生成だけであり、通常の`content.json`は
  `validate_content.py`が生成前に拒否する。
- `type: "title"` 以外は `lead` (string) を任意指定できる。タイトル直下に要旨を置き、指定時だけ本文開始位置が下がる。未指定時の本文位置は変わらない。
- `lead` は本文を読む前に伝える結論・前提・読み方を1〜2行で書く。単なるタイトルの言い換えや本文項目の列挙には使わない。文字数の固定上限はないが、最小フォントでも領域へ収まらない場合は生成を停止する。
- JSONなので、Pythonのタプルではなく配列を使う。
- `note` (右下の注記) が描画されるのは `table` / `chart` / `process` / `program_roadmap` / `matrix` / `org` / `diagram` のみ。それ以外のtypeに書いても無視される(validatorがエラーにする)。
- 一般的なシステム構成・クラウド構成・データフローは`diagram`で書く。物理機器と論理セグメント、
  Access・Trunk・L3接続を同時に示すネットワーク図は`network`で書く。どちらにも座標の数値は書かない。

```json
{
  "type": "bullets",
  "kicker": "分類",
  "title": "検討事項",
  "lead": "本文を読む前に必要な要旨を記載します。",
  "bullets": [
    ["箇条書き本文A", null],
    ["箇条書き本文B", null]
  ]
}
```

## 対応type

### title

用途: 表紙・章扉。

必須:

- `type`: `"title"`
- `title`: string
- `subtitle`: string

制約:

- `title`は資料の主題を端的に示す。
- `subtitle`は対象範囲または目的を1文で示し、タイトルを言い換えない。
- ページ数、PowerPoint/PDFなどのファイル形式、生成・検証工程は記載しない。
- 日付、組織名、責任者は表紙・フッター設定側で表示し、`title` / `subtitle`へ重複して書かない。

```json
{
  "type": "title",
  "title": "資料タイトル",
  "subtitle": "サブタイトル"
}
```

### bullets

用途: 順序付きの説明、順序を持たない要点列挙、タスク一覧。

必須:

- `type`: `"bullets"`
- `kicker`: string
- `title`: string
- `bullets`: object の配列
- `bullets[*].text`: string

任意:

- `style`: `"numbered"` / `"bullet"` / `"checklist"`。省略時は`"numbered"`
- `bullets[*].checked`: boolean。`style: "checklist"`の場合だけ指定可能。省略時は`false`

制約:

- `bullets` は3〜5件程度が安全(validatorの上限は6件)。
- 手順・優先順位・読み順がある場合は`numbered`、順序を持たない要点は`bullet`、
  実施項目と完了状態は`checklist`を使う。
- `checklist`の完了項目はチェック済み、未完了項目は空のチェックボックスで描画する。
- 各項目を単なる文字列で直接並べるとエラーになる。

```json
{
  "type": "bullets",
  "style": "checklist",
  "kicker": "分類",
  "title": "タイトル",
  "bullets": [
    {"text": "完了した項目", "checked": true},
    {"text": "これから実施する項目", "checked": false}
  ]
}
```

### cards

用途: 主結論と複数の独立した根拠、KPI、選択肢、事例の比較。出力は枠線に頼らないフラットな編集的カードになる。

必須:

- `type`: `"cards"`
- `kicker`: string
- `title`: string
- `cards`: object の配列
- `cards[*].heading`: 見出し
- `cards[*].body`: 本文

任意:

- `style`: `"editorial"`(既定) / `"metrics"`
- `cards[*].value`: KPI値。`metrics`では必須
- `cards[*].emphasis`: boolean。主項目または強調KPIを示す

制約:

- `cards` は2〜6件。件数に応じて1〜2行の列数と幅が自動計算される。
- 各項目が独立して比較できる場合に使う。読み順のある要点、フェーズ名、図のノードなど、別の構造に属する要素には使わない。
- `editorial`: サマリ・選択肢・事例向け。4件で`emphasis: true`が1件なら、その項目を主項目として描画する。
- `metrics`: KPI向け。`heading`と`value`を分けて書き、rendererが文字列から数値を推測しないようにする。

```json
{
  "type": "cards",
  "style": "editorial",
  "kicker": "分類",
  "title": "タイトル",
  "cards": [
    {"heading": "最重要の要点", "body": "要点本文", "emphasis": true},
    {"heading": "要点見出し", "body": "要点本文"}
  ]
}
```

### table

用途: 比較表、評価表、一覧。

必須:

- `type`: `"table"`
- `kicker`: string
- `title`: string
- `columns`: string の配列
- `rows`: string配列の配列

任意:

- `note`: string
- `note_link`: 注記に続けて表示するリンク。`label`と`https://`で始まる`url`を指定する
制約:

- `columns`と各`rows[*]`の要素数は同じにする(2〜8列)。
- 列幅は列見出しと全セルの文字実測からrendererが自動計算する。インチ値を入力しない。
- 行数は3〜6行程度が安全(validatorの上限は8行)。

```json
{
  "type": "table",
  "kicker": "分類",
  "title": "タイトル",
  "columns": ["項目", "説明"],
  "rows": [
    ["値1", "説明1"],
    ["値2", "説明2"]
  ],
  "note": "※ 補足説明。参照先:",
  "note_link": {
    "label": "公式ドキュメント",
    "url": "https://example.com/official-document"
  }
}
```

### twocol

用途: Before/After、比較、メリット/注意点。

必須:

- `type`: `"twocol"`
- `kicker`: string
- `title`: string
- `left.heading`: string
- `left.bullets`: string の配列
- `right.heading`: string
- `right.bullets`: string の配列

任意:

- `left.label` / `right.label`: 左右の意味ラベル。省略時は`BEFORE` / `AFTER`

制約:

- 左右それぞれ3〜5項目程度が安全。
- 左右を枠付きパネルにせず、中央罫線とタイポグラフィで比較関係を示す。

```json
{
  "type": "twocol",
  "kicker": "分類",
  "title": "タイトル",
  "left": {
    "label": "現状",
    "heading": "左見出し",
    "bullets": ["本文", "本文"]
  },
  "right": {
    "label": "目標状態",
    "heading": "右見出し",
    "bullets": ["本文", "本文"]
  }
}
```

### chart

用途: 横棒、縦棒、折れ線、積み上げグラフ。

必須:

- `type`: `"chart"`
- `kicker`: string
- `title`: string
- `chart.categories`: string の配列
- `chart.series`: `[series_name, values]` の配列

任意:

- `chart.kind`: `"bar"`(既定) / `"column"` / `"line"` / `"stacked_bar"` / `"stacked_column"`
- `chart.show_legend`: boolean。省略時は系列が複数なら表示
- `chart.show_values`: boolean。省略時は折れ線以外で表示
- `chart.number_format`: データラベルの表示形式。例: `0%`、`0.0`
- `note`: string

制約:

- 各 `values` の長さは `categories` と同じにする。
- 系列は1〜4件、カテゴリは1〜12件。件数に応じて軸ラベル間隔と文字を段階的に縮小する。
- 円グラフ、ウォーターフォールなど制約モデルが異なる図は、このtypeへ詰め込まず別rendererとして追加する。

```json
{
  "type": "chart",
  "kicker": "分類",
  "title": "タイトル",
  "chart": {
    "kind": "line",
    "categories": ["カテゴリ1", "カテゴリ2"],
    "series": [
      ["系列名", [10, 20]]
    ]
  },
  "note": "任意の注記"
}
```

### image

用途: 写真、イラスト、画面キャプチャ、生成画像など、1枚の画像を本文の主役として大きく見せる。

必須:

- `type`: `"image"`
- `kicker`: string
- `title`: string
- `image`: `slidegen/assets/`からの相対PNG/JPEGパス。本文画像は`images/<ファイル名>`を推奨

任意:

- `fit`: `"contain"`または`"cover"`。既定値は`"contain"`
- `shadow`: boolean。`true`なら画像へ外側の「オフセット: 右下」影を付ける。既定値は`false`
- `alt`: 画像を見られない受け手向けの代替説明。PPTX内の画像説明へ設定する

挙動:

- `contain`は画像全体を表示し、余白が生じても縦横比を維持する。画面キャプチャ、図版、資料画像に向く。
- `cover`は本文枠全体を埋め、中央を基準に上下または左右をトリミングする。写真や背景的なビジュアルに向く。
- 画像は引き伸ばさない。leadで利用可能領域が減った場合は、裁量余白、画像の順で縮小し、最小値でも
  収まらなければ生成を停止する。
- 本文画像の下にcaption/source枠は置かない。画像の説明が必要な場合は`lead`を使う。
- URLを直接指定しない。画像生成、手元の画像、Web検索のいずれでも、使用可能なファイルを先に
  `slidegen/assets/images/`へ置いてから参照する。
- Web画像は取得元と利用条件を確認する。リポジトリへ同梱する場合は
  `slidegen/assets/CREDITS.md`にも出典とライセンスを記録する。

```json
{
  "type": "image",
  "kicker": "キービジュアル",
  "title": "画像タイトル",
  "image": "images/<配置済みファイル名>.png",
  "fit": "cover",
  "shadow": true,
  "alt": "<画像の内容を表す代替説明>"
}
```

### process

用途: 手順、業務フロー、導入ステップ。

直線工程の必須:

- `type`: `"process"`
- `kicker`: string
- `title`: string
- `steps`: object の配列
- `steps[*].name`: string
- `steps[*].desc`: string

任意:

- `steps[*].attribute`: 工程下部へ補足属性を出す場合の`{label, value}`。
  `label`は`OWNER`、`OUTPUT`、`TOOL`、`STATUS`など、値の意味に合わせる
- `steps[*].actor`: 担当者を示すstring。`OWNER`ラベルで表示する
- `emph`: 強調するstepの0始まりindex配列
- `note`: string

分岐工程の必須(`steps`の代わりに指定):

- `flow.nodes`: ノードID → object
- `flow.nodes[*].name`: 工程名
- `flow.levels`: 左から順に並べるノードID配列の配列
- `flow.edges`: `{from, to}` の配列

分岐工程の任意:

- `flow.nodes[*].desc`: 工程説明
- `flow.nodes[*].actor`: 担当。不要なら省略できる
- `flow.nodes[*].style`: `"standard"` / `"accent"` / `"decision"`
- `flow.edges[*].label`: 条件ラベル
- `flow.edges[*].kind`: `"forward"`(既定) / `"feedback"`

制約:

- `steps` は4〜5件が安全(validatorの範囲は3〜6件)。
- 下部属性が不要な工程は`actor`と`attribute`の両方を省略する。両者は同時に指定しない。
- `flow`は2〜12ノード、2〜6列、各列1〜3ノード、接続1〜20件。
- 戻り接続は`kind: "feedback"`を指定する。座標や配線経路はrendererが決める。
- `steps`と`flow`は同時に指定しない。

```json
{
  "type": "process",
  "kicker": "分類",
  "title": "タイトル",
  "steps": [
    {"name": "工程A", "desc": "工程Aの説明"},
    {"name": "工程B", "desc": "工程Bの説明",
     "attribute": {"label": "OUTPUT", "value": "成果物"}},
    {"name": "工程C", "desc": "工程Cの説明"}
  ],
  "emph": [1]
}
```

```json
{
  "type": "process",
  "kicker": "分岐フロー",
  "title": "承認フロー",
  "flow": {
    "nodes": {
      "start": {"name": "開始"},
      "decision": {"name": "条件判定", "style": "decision"},
      "next": {"name": "次工程", "style": "accent"},
      "retry": {"name": "再処理"}
    },
    "levels": [["start"], ["decision"], ["next", "retry"]],
    "edges": [
      {"from": "start", "to": "decision"},
      {"from": "decision", "to": "next", "label": "条件A"},
      {"from": "decision", "to": "retry", "label": "条件B"},
      {"from": "retry", "to": "decision", "kind": "feedback", "label": "再判定"}
    ]
  }
}
```

### program_roadmap

用途: 少数フェーズから複数テーマの並行作業まで、同じ時間軸で期間計画を示す工程表。
同じテーマ内で作業期間が重なる場合はrendererがレーンを自動で増やす。

必須:

- `type`: `"program_roadmap"`
- `kicker`: string
- `title`: string
- `periods`: 重複しないstringの配列
- `tracks`: objectの配列
- `tracks[*].name`: string
- `tracks[*].activities`: objectの配列
- `tracks[*].activities[*].label`: string
- `tracks[*].activities[*].start`: number または `periods` 内の期間ラベル
- `tracks[*].activities[*].end`: number または `periods` 内の期間ラベル

任意:

- `tracks[*].goal`: テーマの狙い。指定したテーマだけ左側の見出し欄へ表示する
- `tracks[*].milestone`: テーマ内の判定点。1テーマにつき1件まで
- `tracks[*].milestone.at`: number または `periods` 内の期間ラベル
- `tracks[*].milestone.label`: string
- `tracks[*].activities[*].emph`: boolean。重要作業を強調する
- `note`: string

制約:

- `periods` は3〜12件、`tracks` は1〜6件。
- 各`activities`は1〜8件、全テーマ合計24件まで。
- 月ヘッダーは`periods`の単位のまま変えず、作業線の開始・終了だけを1/4期間単位で動かせる。
- 数値の`start` / `end`は0.25刻みの期間境界index。12か月なら`0`から`12`の範囲。
  `0`は最初の月の開始、`0.25`は最初の月の1/4経過、`0.5`は月半ば、
  `0.75`は3/4経過、`1`は次月の開始を表す。
- 期間ラベルの`start`は該当期間の開始、`end`は該当期間を含む終了として扱う。
- 期間ラベルの`milestone.at`は該当期間の中央として扱う。数値指定は0.25刻みとし、
  同じテーマ内のいずれかの作業期間内に置く。
- 0.25刻み以外の数値はvalidatorが拒否する。
- 同じテーマ内で重なる作業は入力順や座標指定ではなく、期間の重なりから自動レーン配置する。
- `milestone`を指定したテーマだけ判定点用のレーンを追加する。未指定テーマの行高は変わらない。
- 最小設定でも収まらない場合は、テーマまたは同時並行作業を減らしてスライドを分割する。

```json
{
  "type": "program_roadmap",
  "kicker": "複数テーマ計画",
  "title": "年間プログラム",
  "periods": ["期間1", "期間2", "期間3", "期間4"],
  "tracks": [
    {
      "name": "テーマA",
      "goal": "対象業務を確定する",
      "activities": [
        {"label": "作業A1", "start": 0.25, "end": 2.75},
        {"label": "作業A2", "start": 2.0, "end": 4.0, "emph": true}
      ],
      "milestone": {"at": 2.75, "label": "実施判断"}
    },
    {
      "name": "テーマB",
      "activities": [
        {"label": "作業B1", "start": "期間1", "end": "期間2"},
        {"label": "作業B2", "start": "期間2", "end": "期間4"}
      ]
    }
  ]
}
```

### matrix

用途: 2軸マップ、ポジショニング。

必須:

- `type`: `"matrix"`
- `kicker`: string
- `title`: string
- `x_axis`: string
- `y_axis`: string
- `points`: object の配列
- `points[*].name`: string
- `points[*].x`: number
- `points[*].y`: number

任意:

- `points[*].emph`: boolean
- `target_label`: string。`quadrants`を省略した場合に必須
- `quadrants`: `[左下, 右下, 左上, 右上]` の4文字列
- `note`: string

制約:

- `x`, `y` は `0.0` から `1.0` の比率(validator強制)。
- 点は4〜7件程度が安全(validatorの上限は8件)。
- ラベルは点の周囲8方向から、他の点・ラベル・プロット境界と衝突しない位置をrendererが選ぶ。
- 衝突を解消できない場合はラベル間隔、ラベル幅の順に縮小し、それでも無理なら生成を停止する。
- ラベル位置を指定する`lx` / `ly`は受け付けない。位置はrendererが自動計算する。

```json
{
  "type": "matrix",
  "kicker": "分類",
  "title": "タイトル",
  "x_axis": "横軸ラベル",
  "y_axis": "縦軸ラベル",
  "target_label": "強調領域ラベル",
  "quadrants": ["左下", "右下", "左上", "右上"],
  "points": [
    {"name": "点ラベル", "x": 0.5, "y": 0.5, "emph": true}
  ],
  "note": "任意の注記"
}
```

### scope

用途: 実施範囲と対象外を左右に分け、責任境界を明確にする。必要な場合だけ前提条件を下部へ示す。

必須:

- `type`: `"scope"`
- `kicker` / `title`: string
- `in_scope`: 実施範囲の文字列配列(1〜6件)
- `out_of_scope`: 対象外の文字列配列(1〜6件)

任意:

- `in_label` / `out_label`: 左右の見出し
- `assumptions`: 前提条件の文字列配列(1〜4件)

```json
{
  "type": "scope",
  "kicker": "対象範囲",
  "title": "対象範囲",
  "in_scope": ["実施する作業"],
  "out_of_scope": ["実施しない作業"],
  "assumptions": ["成立に必要な前提条件"]
}
```

### summary

用途: 2〜4個の論点を読み順に並べ、必要なら最終判断を1文で示す。

必須:

- `type`: `"summary"`
- `kicker` / `title`: string
- `sections`: 2〜4件
  - `heading`: 論点見出し
  - `body`: 論点の説明

任意:

- `conclusion`: 最終判断
- `conclusion_label`: 結論帯の短いラベル。`conclusion`指定時だけ使用できる

```json
{
  "type": "summary",
  "kicker": "意思決定",
  "title": "エグゼクティブサマリー",
  "sections": [
    {"heading": "背景", "body": "判断の前提となる事実。"},
    {"heading": "判断", "body": "比較して得られた示唆。"},
    {"heading": "提案", "body": "次に実施する内容。"}
  ],
  "conclusion": "最終判断を1文で記載する。"
}
```

### paired_comparison

用途: 2案を共通の評価軸で1行ずつ対応させて比較する。

必須:

- `type`: `"paired_comparison"`
- `kicker` / `title`: string
- `left_label` / `right_label`: 比較対象名
- `rows`: 2〜6件
  - `criterion`: 評価軸
  - `left` / `right`: 各対象の評価内容

任意:

- `criterion_label`: 評価軸列の見出し。省略時は`評価軸`
- `takeaway`: 比較から得られる判断

```json
{
  "type": "paired_comparison",
  "kicker": "方式比較",
  "title": "方式比較",
  "left_label": "案A",
  "right_label": "案B",
  "rows": [
    {"criterion": "導入期間", "left": "短い", "right": "準備期間が必要"},
    {"criterion": "運用負荷", "left": "個別対応", "right": "共通化できる"}
  ]
}
```

### mapping

用途: 課題と施策、要件と機能など、左右項目の対応漏れと一対多・多対多の関係を確認する。

必須:

- `type`: `"mapping"`
- `kicker` / `title`: string
- `left_label` / `right_label`: 左右の見出し
- `left_items` / `right_items`: 各2〜6件
  - `id`: スライド内で一意な参照ID
  - `text`: 表示文
- `links`: 1〜10件
  - `from`: `left_items`のID
  - `to`: `right_items`のID

任意:

- `links[*].emphasis`: trueなら主要な対応線を強調する
- `takeaway`: 対応関係から得られる判断

同じ対応を重複指定できない。未定義IDへの接続はvalidatorが拒否する。工程順やシステム境界を表す
typeではないため、その場合は`process`、`swimlane`、`diagram`を選ぶ。

```json
{
  "type": "mapping",
  "kicker": "対応関係",
  "title": "課題と対応施策",
  "left_label": "課題",
  "right_label": "施策",
  "left_items": [{"id": "issue_a", "text": "課題A"}, {"id": "issue_b", "text": "課題B"}],
  "right_items": [{"id": "action_a", "text": "施策A"}, {"id": "action_b", "text": "施策B"}],
  "links": [
    {"from": "issue_a", "to": "action_a", "emphasis": true},
    {"from": "issue_a", "to": "action_b"},
    {"from": "issue_b", "to": "action_b"}
  ]
}
```

### swimlane

用途: 担当レーンと工程段階を同時に示し、作業の分岐・合流・引き継ぎを確認する。

必須:

- `type`: `"swimlane"`
- `kicker` / `title`: string
- `lanes`: 2〜6件。`id` / `label`を持つ
- `stages`: 2〜6件。`id` / `label`を持つ
- `steps`: 2〜14件
  - `id` / `name`: 参照IDと表示名
  - `lane` / `stage`: 所属するレーンIDと段階ID
- `edges`: 1〜20件。`from` / `to`でstep IDを接続する

任意:

- `steps[*].style`: `"standard" | "accent"`
- `edges[*].kind`: `"forward" | "feedback"`。前段階へ戻る線は`feedback`必須
- `takeaway`: フローから得られる示唆

同じlane / stageセルへ配置できるstepは最大2件。座標や線の経由点は入力せず、rendererがレーン境界を
使って配線する。厳密な時刻や期間が主役なら`program_roadmap`、機器間メッセージなら`sequence`を使う。
`forward`と`feedback`が同じスライドに存在する場合は、rendererが実線と破線の凡例を自動表示する。

```json
{
  "type": "swimlane",
  "kicker": "業務フロー",
  "title": "担当別業務フロー",
  "lanes": [{"id": "requester", "label": "申請部門"}, {"id": "reviewer", "label": "審査部門"}],
  "stages": [{"id": "apply", "label": "申請"}, {"id": "review", "label": "審査"}],
  "steps": [
    {"id": "submit", "name": "申請", "lane": "requester", "stage": "apply"},
    {"id": "check", "name": "確認", "lane": "reviewer", "stage": "review"}
  ],
  "edges": [{"from": "submit", "to": "check"}]
}
```

### sequence

用途: 関係者・機器間のメッセージを上から時系列に並べ、送信者・受信者・戻り応答を示す。

必須:

- `type`: `"sequence"`
- `kicker` / `title`: string
- `participants`: 2〜6件。`id` / `label`を持つ
- `messages`: 2〜12件
  - `id`: メッセージID
  - `from` / `to`: participant ID。同一participantなら自己処理として描画する
  - `label`: メッセージ名

任意:

- `messages[*].kind`: `"request" | "return" | "async"`
- `phases`: 最大3件。`label`と、範囲の先頭・末尾message IDを`from` / `to`へ指定する
- `takeaway`: シーケンスから得られる示唆

`messages`の配列順が上から下への実行順になる。rendererは同じ順序を重複して示す通番を表示しない。
工程のまとまりを読み手へ示す必要がある場合だけ`phases`を指定する。

```json
{
  "type": "sequence",
  "kicker": "処理シーケンス",
  "title": "変更作業シーケンス",
  "participants": [{"id": "user", "label": "利用者"}, {"id": "system", "label": "システム"}],
  "messages": [
    {"id": "request", "from": "user", "to": "system", "label": "処理依頼"},
    {"id": "response", "from": "system", "to": "user", "label": "処理結果", "kind": "return"}
  ],
  "phases": [{"label": "実行", "from": "request", "to": "response"}]
}
```

### concept

用途: 専門用語や判断基準を初めて示すときに、定義、理解に必要な要点、誤解しやすい境界を一続きで説明する。
研修資料では、未定義の用語を使った構成図や詳細手順より前へ置く。

必須:

- `type`: `"concept"`
- `term`: 定義する用語または判断基準
- `definition`: 用語の意味を単独で理解できる定義文
- `points`: 2〜4件
  - `label`: 観点名
  - `text`: その観点で理解すべき説明

任意:

- `icon`: `slidegen/assets/`からの相対パス。用語の意味を補助できる場合だけ指定する
- `misconception`: 読み手が混同しやすい概念、適用範囲外、誤った理解
- `lead`: 定義を読む前に必要な前提

制約:

- `definition`は略語の展開だけで終わらせず、何を表し、どの境界を持つかまで書く。
- `points`は定義の繰り返しではなく、識別方法、挙動、設計への反映など別の観点を置く。
- 複数の独立項目を比較する用途には使わず、`cards`または`table`を選ぶ。

```json
{
  "type": "concept",
  "kicker": "言葉の定義",
  "title": "RTOとは",
  "term": "RTO",
  "definition": "障害が起きてから、業務を再開するまでに許容する目標時間です。",
  "points": [
    {"label": "起点", "text": "業務へ影響する障害が発生した時点。"},
    {"label": "終点", "text": "利用者が必要な業務を再開できる状態へ戻った時点。"}
  ],
  "misconception": "実際に要した復旧時間の実績値ではなく、事前に合意する目標値です。"
}
```

### network

用途: VLAN、セキュリティゾーン、テナント分離など、物理機器と論理セグメント、接続種別を同時に示すネットワーク図。
一般的なシステム構成やクラウドのデータフローは`diagram`を使う。

必須:

- `type`: `"network"`
- `lanes`: 1〜4件。論理セグメントを表す`id / label`の配列
- `columns`: 2〜6件。物理的な読み順を表す`id / label`の配列
- `nodes`: 2〜12件
  - `id / label`: ノードIDと表示名
  - `icon`: `slidegen/assets/`からの相対パス
  - `column`: 所属する`columns[*].id`
  - `lanes`: 所属する`lanes[*].id`を1件以上
- `links`: 1〜18件
  - `from / to`: 接続するnode ID
  - `kind`: `"access" | "trunk" | "routed" | "control" | "broadcast" | "blocked"`
  - `lanes`: その接続が運ぶ論理セグメント

任意:

- `lanes[*].sub`: セグメントの用途やアドレス帯
- `nodes[*].sub`: 機器の役割、IPアドレスなどの短い補足
- `links[*].label`: 物理インターフェース名などの短いラベル
- `lead`: 読み方や結論

制約:

- `trunk`は`lanes`を2件以上、`access` / `broadcast` / `blocked`は1件指定する。
- 同じ`column`かつ同じ`lanes`へ置けるnodeは2件まで。2件はセル内で自動分散し、3件以上は列を追加するかスライドを分ける。
- `broadcast`は同じ送信元・laneから複数宛先へ指定すると、1つのフレームを複製する共通分岐として描画する。
- `blocked`は接続元だけが所属し、接続先が所属しないlaneを1件指定する。線はlane境界で停止し、別セグメントへ届かないことを示す。
- `blocked`以外のlinkの`lanes`は、接続元と接続先の両方が所属するlaneだけを指定する。
- 座標、幅、高さ、線の経路、色は書かない。

```json
{
  "type": "network",
  "kicker": "論理分割",
  "title": "Trunkポート",
  "lanes": [
    {"id": "staff", "label": "業務VLAN"},
    {"id": "guest", "label": "ゲストVLAN"}
  ],
  "columns": [
    {"id": "left", "label": "フロアA"},
    {"id": "sw1", "label": "スイッチA"},
    {"id": "sw2", "label": "スイッチB"},
    {"id": "right", "label": "フロアB"}
  ],
  "nodes": [
    {"id": "pc_a", "label": "業務PC A", "icon": "icons/fluent/laptop.png", "column": "left", "lanes": ["staff"]},
    {"id": "sw_a", "label": "スイッチA", "icon": "icons/fluent/switch.png", "column": "sw1", "lanes": ["staff", "guest"]},
    {"id": "sw_b", "label": "スイッチB", "icon": "icons/fluent/switch.png", "column": "sw2", "lanes": ["staff", "guest"]},
    {"id": "pc_b", "label": "業務PC B", "icon": "icons/fluent/desktop.png", "column": "right", "lanes": ["staff"]}
  ],
  "links": [
    {"from": "pc_a", "to": "sw_a", "kind": "access", "lanes": ["staff"]},
    {"from": "sw_a", "to": "sw_b", "kind": "trunk", "lanes": ["staff", "guest"], "label": "1本の物理リンク"},
    {"from": "sw_b", "to": "pc_b", "kind": "access", "lanes": ["staff"]}
  ]
}
```

### protocol_state_flow

用途: 同じフレームやパケットが端末、装置内部、伝送区間を通る間に、どの情報を維持・追加・削除・変換するかを段階ごとに追跡する。

必須:

- `type`: `"protocol_state_flow"`
- `stages`: 3〜6件。左から右へ並ぶ処理段階
  - `id / label`: 段階IDと表示名
  - `icon`: `slidegen/assets/`からの相対パス
- `flows`: 1〜3件。比較する状態系列
  - `label`: 系列名
  - `states`: 全`stages`を1件ずつ指定する配列
    - `stage`: 対応する`stages[*].id`
    - `label`: その段階での状態

任意:

- `stages[*].role`: `"endpoint" | "processor" | "link"`。伝送区間は`link`を指定する
- `flows[*].sub`: 系列の短い補足
- `states[*].detail`: 状態になった理由や処理内容
- `states[*].appearance`: 状態の見せ方。内容に合うものだけを指定する
  - `plain`: 通常のフレーム、パケット、値
  - `encapsulated`: タグまたはヘッダーが付与された状態
  - `internal`: 装置内部の分類、変換、検索などの処理状態
  - `alert`: 不一致、破棄、異常など注意が必要な状態
- `states[*].encapsulation`: `appearance: "encapsulated"`で付加されたタグまたはヘッダーの短い名称。8文字以内で必須
- `takeaway`: 各系列の比較から読み取る要点
- `lead`: このページで追う単位と前提

制約:

- 物理接続や論理セグメントの全体構成は`network`、メッセージの時系列は`sequence`、ビット配置は`protocol_anatomy`を使う。
- 各`flow`は全段階の状態を省略せず、同じ`stage`を重複させない。
- `flows[*].label`は系列を区別できる名前にし、同じスライド内で重複させない。
- 1枚で追う単位を統一する。L2の転送は「フレーム」、L3の転送は「IPパケット」など対象に合う語を使い、
  「パケット」を通信データ全般の総称として使わない。
- 各系列では同じ属性を追う。送信元IPと宛先IPのように属性が異なる場合は系列を分け、段階ごとに比較対象を変えない。
- `appearance`は装飾目的で使わない。実際の状態が変わる段階だけ`encapsulated / internal / alert`を指定する。
- `encapsulated`では`encapsulation`に`TAG`、`TLS`、`HDR`など実際に付加されたものを書く。rendererは固定の表示名を補わない。
- 座標、段階幅、行高、色は書かない。

```json
{
  "type": "protocol_state_flow",
  "kicker": "IPパケット状態の追跡",
  "title": "NAT前後の送信元IP",
  "stages": [
    {"id": "client", "label": "社内端末", "icon": "icons/fluent/laptop.png", "role": "endpoint"},
    {"id": "router", "label": "NATルーター", "icon": "icons/fluent/switch.png", "role": "processor"},
    {"id": "internet", "label": "インターネット区間", "icon": "icons/fluent/link.png", "role": "link"},
    {"id": "server", "label": "外部サーバー", "icon": "icons/fluent/server.png", "role": "endpoint"}
  ],
  "flows": [{
    "label": "送信元IP",
    "states": [
      {"stage": "client", "label": "10.0.0.25", "appearance": "plain"},
      {"stage": "router", "label": "203.0.113.10", "detail": "送信元を書き換え", "appearance": "internal"},
      {"stage": "internet", "label": "203.0.113.10", "appearance": "plain"},
      {"stage": "server", "label": "203.0.113.10", "appearance": "plain"}
    ]
  }],
  "takeaway": "NATルーターで送信元IPが変わり、変換後の値が外部へ届く。"
}
```

### protocol_anatomy

用途: フレームやパケットをフィールドへ分解し、ビット長と注目箇所を示す。

必須:

- `type`: `"protocol_anatomy"`
- `frames`: 1〜3件
  - `label`: フレームまたはパケット名
  - `fields`: 3〜9件
    - `id / name`: フィールドIDと表示名
    - `bits`: 1〜65535の整数

任意:

- `fields[*].role`: `"standard" | "muted" | "highlight" | "alert"`
- `fields[*].size_label`: フィールド下部へ表示する長さ。可変長フィールドでは`"可変長"`などを指定する。
  `bits`は相対幅の計算に引き続き使用する
- `frames[*].annotations`: 最大4件。`field`にfield ID、`text`に説明を書く
- `takeaway`: 構造から読み取る結論

複数の`frames`では同じ`bits`のフィールドを同じ幅で描画する。`bits`合計が異なる場合は、
追加フィールドの分だけ全長を伸ばし、右端へ差分を表示する。
可変長フィールドを含むフレーム同士の長さを比較するときは、同じデータ長を表す代表`bits`値を双方へ設定する。

```json
{
  "type": "protocol_anatomy",
  "kicker": "プロトコル構造",
  "title": "サンプルフレームの構造",
  "frames": [{
    "label": "サンプルフレーム",
    "fields": [
      {"id": "dst", "name": "宛先", "bits": 48},
      {"id": "src", "name": "送信元", "bits": 48},
      {"id": "tag", "name": "識別タグ", "bits": 16, "role": "highlight"},
      {"id": "payload", "name": "Payload", "bits": 368, "size_label": "可変長", "role": "muted"}
    ],
    "annotations": [{"field": "tag", "text": "論理的な通信範囲を識別する。"}]
  }],
  "takeaway": "注目するフィールドと、その役割を対応させる。"
}
```

### code_lab

用途: 設定例やコードと、実行後に確認する状態を同じページで示す。

必須:

- `type`: `"code_lab"`
- `sections`: 1〜2件。`label / code`を持ち、`code`は1区画16行以内
- `checks`: 2〜5件の文字列

任意:

- `check_label`: 確認観点の見出し
- `takeaway`: 実行と確認を結ぶ結論
- `lead`: 製品・OS・バージョンなどの前提

```json
{
  "type": "code_lab",
  "kicker": "設定と確認",
  "title": "設定と状態確認",
  "sections": [
    {"label": "設定例", "code": "interface port1\n mode access\n segment 10"},
    {"label": "確認例", "code": "show segment\nshow interface port1"}
  ],
  "check_label": "確認する状態",
  "checks": ["対象ポートがsegment 10へ所属している", "意図しないポート変更がない"],
  "takeaway": "コマンド終了ではなく、期待状態との一致を完了条件にする。"
}
```

### knowledge_check

用途: 研修内の選択式問題と、対応する正答・解説を示す。

必須:

- `type`: `"knowledge_check"`
- `mode`: `"questions" | "answers"`
- `questions`: 1〜3件
  - `question`: 設問
  - `options`: 2〜4件の選択肢
  - `answer`: 正答の**0始まりindex**
  - `explanation`: 正答の理由

`questions`と`answers`を別スライドで使う場合は、同じ設問・選択肢・正答・解説を渡し、`mode`だけを変える。

```json
{
  "type": "knowledge_check",
  "mode": "questions",
  "kicker": "理解度チェック",
  "title": "理解度チェック",
  "questions": [{
    "question": "複数の論理セグメントを1本の物理リンクで運ぶ接続はどれか。",
    "options": ["Access", "Trunk", "Loopback"],
    "answer": 1,
    "explanation": "Trunkは識別タグを使って複数セグメントを運ぶ。"
  }]
}
```

### org

用途: 組織図・プロジェクト体制図・責任分担図。複数の責任者、複数階層、
分岐・合流、助言関係、横連携を表現できる。

必須:

- `type`: `"org"`
- `kicker`: string
- `title`: string
- `org.nodes`: ノードID → object
  - `name`: 表示名
- `org.levels`: 上位から順に並べた階層の配列。各階層はノードIDの配列

任意:

- `org.nodes[*].sub`: 役割・責任範囲などの補足
- `org.nodes[*].members`: メンバー名・担当名の配列
- `org.nodes[*].style`: `"primary" | "accent" | "standard" | "external"`
- `org.edges`: 関係の配列
  - `from` / `to`: 接続するノードID
  - `kind`: `"reporting" | "advice" | "collaboration"`。省略時は`reporting`
  - `label`: 関係ラベル。`advice`と`collaboration`だけに指定できる
- `note`: string

制約:

- `levels` は1〜6階層、1階層あたり1〜5ノード。
- すべてのノードを`levels`のいずれか1階層へ1回だけ配置する。
- `members` は各ノード0〜4件。
- `reporting`は上位階層から下位階層へ接続する。1段飛ばし、複数親、複数子を指定できる。
- 隣接階層の`reporting`は、同じ連結成分の親群と子群を1本の共有幹へまとめる。
  一般的な体制図と同じく、親ごと・子ごとに横線を重ねない。
- `advice`と`collaboration`は点線。`collaboration`は双方向矢印になる。
- 座標・箱サイズ・線の経由点は書かない。レイアウタが階層数と情報量から自動計算する。
- 標準配置で収まらない場合は、階層間余白の圧縮、箱と文字の縮小を順に行う。
  提出品質を保つ最小値でも収まらない場合は生成を停止する。

```json
{
  "type": "org",
  "kicker": "分類",
  "title": "タイトル",
  "org": {
    "nodes": {
      "project_owner": {"name": "プロジェクト責任者", "sub": "方針・予算", "style": "primary"},
      "system_owner": {"name": "システム責任者", "sub": "システム方針", "style": "primary"},
      "project_manager": {"name": "プロジェクトマネージャー", "sub": "計画・課題・品質管理", "style": "accent"},
      "business_team": {"name": "業務チーム", "sub": "業務要件・受入"},
      "development_team": {"name": "開発チーム", "sub": "設計・開発・試験"},
      "platform_team": {"name": "基盤チーム", "sub": "基盤・ネットワーク"}
    },
    "levels": [
      ["project_owner", "system_owner"],
      ["project_manager"],
      ["business_team", "development_team", "platform_team"]
    ],
    "edges": [
      {"from": "project_owner", "to": "project_manager"},
      {"from": "system_owner", "to": "project_manager"},
      {"from": "project_manager", "to": "business_team"},
      {"from": "project_manager", "to": "development_team"},
      {"from": "project_manager", "to": "platform_team"}
    ]
  }
}
```

### diagram

用途: システム構成図・ネットワーク構成図など、ノードと配線の図。

**座標・サイズの数値は一切書かない。** グリッド仕様(列・行・メンバー列挙)だけを書き、座標は `diagram_layout.py` エンジンが決定論的に計算する。「9.55のような数値を書きたくなったら仕様の書き方が間違っている」が設計思想。

必須:

- `type`: `"diagram"`
- `kicker`: string
- `title`: string
- `diagram.cols`: 列名の配列(左から順)
- `diagram.rows`: 行名の配列(上から順)
- `diagram.nodes`: ノード名 → object
  - `col` / `row`: 所属セル(cols/rowsの名前)
  - `title`: 表示名
  - `sub`: 補足ラベル(任意)
  - `icon`: `slidegen/assets/` からの相対PNGパス(必須)。同梱Fluent/AWSアイコンから選ぶ
    - Fluentアイコン(`icons/fluent/<名前>.png`、72種同梱済み)。次の名前だけを使い、ファイル名を発明しない。`python slidegen/fetch_fluent_icons.py --list` でも確認できる
      - インフラ・端末: `server` `router` `database` `desktop` `laptop` `tablet` `phone` `printer` `hard_drive` `storage`
      - ネットワーク・クラウド: `cloud` `globe` `wifi` `ethernet` `link` `gateway` `sync` `upload` `download` `switch`
      - セキュリティ: `shield` `shield_lock` `shield_check` `lock` `key` `certificate`
      - 人物・組織・拠点: `people` `team` `person` `contact` `organization` `briefcase` `building` `branch` `factory` `store` `warehouse` `home`
      - アプリ・データ・文書: `app` `browser` `terminal` `code` `bot` `ai` `folder` `document` `file_data` `archive`
      - コミュニケーション・業務: `mail` `chat` `video` `call` `send` `calendar` `task` `cart` `money` `chart`
      - 運用・状態: `alert` `warning` `info` `check` `search` `clock` `history` `settings` `toolbox` `wrench` `monitor`
      - 物理移動: `truck` `car` `airplane`
    - AWSアイコン(同梱済み): `icons/aws/alb.png` `icons/aws/bedrock.png` `icons/aws/cloudfront.png` `icons/aws/cloudwatch.png` `icons/aws/dynamodb.png` `icons/aws/ecr.png` `icons/aws/fargate.png` `icons/aws/rds.png` `icons/aws/route53.png` `icons/aws/s3.png` `icons/aws/sqs.png` `icons/aws/user.png` `icons/aws/users.png` のみ。増やす場合は `extract_aws_icons.py`
- `diagram.edges`: object の配列
  - `from` / `to`: ノード名(または `@コンテナ名`)
  - `label`: 線上ラベル(任意)。幅と配置区間はrendererが文字実測と経路から決める
  - `exit` / `enter`: 発着辺 `"left" | "right" | "top" | "bottom"`(任意。省略時は位置関係から自動)
  - `via`: 経由チャネル名の配列(任意)
  - `dash`: `"dash"` で点線、`both`: true で双方向(任意)
  - `from_row`: `from`が`@コンテナ名`の場合だけ必須。接続元に使う`diagram.rows`の名前

任意:

- `diagram.containers`: 外接枠。object の配列(外側から順)
  - `name` / `label` / `members`(ノード名または `@子コンテナ名` の列挙)
  - `color` / `dash`
- `diagram.channels`: 配線レーン。`名前: [種類, 基準]` のobject
  - 種類: `"left_of_col"` / `"right_of_col"` / `"above_row"` / `"below_row"` / `"outside_container"`
  - `outside_container` の基準は `[コンテナ名, "left"|"right"|"top"|"bottom"|"top_inside"]`
  - 同じ列を共有するノード間のローカルループ(折り返し)には必ず `outside_container` を使う
  - 同じコンテナ辺へ複数チャネルを宣言すると、rendererが宣言順に外側へ離す。間隔値は指定しない
- `note`: string

```json
{
  "type": "diagram",
  "kicker": "構成図",
  "title": "システム構成",
  "diagram": {
    "cols": ["left", "center", "right"],
    "rows": ["main"],
    "nodes": {
      "node_a": {"col": "left", "row": "main", "icon": "icons/fluent/desktop.png", "title": "ノードA"},
      "node_b": {"col": "center", "row": "main", "icon": "icons/fluent/shield.png", "title": "ノードB"},
      "node_c": {"col": "right", "row": "main", "icon": "icons/fluent/server.png", "title": "ノードC", "sub": "補足"}
    },
    "containers": [
      {"name": "group", "label": "グループ", "members": ["node_b", "node_c"]}
    ],
    "channels": {},
    "edges": [
      {"from": "node_a", "to": "node_b", "label": "接続A"},
      {"from": "node_b", "to": "node_c"}
    ]
  }
}
```

制約:

- 参照整合(col/rowの存在、edges/membersのノード参照、viaのチャネル参照)はvalidatorが検証する。
- 描画領域、コンテナ余白、線ラベル幅・配置区間は、構造と文字実測からエンジンが自動計算する。`area` / `pad` / `pad_x` / `label_w` / `label_seg` は入力できない。
- 行間に収まるか・配線がコンテナを貫通しないか等は、生成時にエンジン自身が対処方法つきのエラーで検出する(収まらない場合は行数・sub・ラベルを減らす)。
- ノードは10個程度・4行程度までが安全(それ以上は縦に収まらずエラーになる)。
- 名前付きテンプレート参照はない。仕様は必ず `diagram` にインラインで書く。
