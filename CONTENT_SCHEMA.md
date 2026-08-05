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
- `type: "title"` 以外は `lead` (string) を任意指定できる。タイトル直下に要旨を置き、指定時だけ本文開始位置が下がる。未指定時の本文位置は変わらない。
- `lead` は本文を読む前に伝える結論・前提・読み方を1〜2行で書く。単なるタイトルの言い換えや本文項目の列挙には使わない。文字数の固定上限はないが、最小フォントでも領域へ収まらない場合は生成を停止する。
- JSONなので、Pythonのタプルではなく配列を使う。
- `note` (右下の注記) が描画されるのは `table` / `chart` / `process` / `program_roadmap` / `matrix` / `org` / `diagram` のみ。それ以外のtypeに書いても無視される(validatorがエラーにする)。
- 構成図は `diagram` type で書く(グリッド仕様のみ、座標の数値は書かない)。

```json
{
  "type": "bullets",
  "kicker": "分類",
  "title": "タイトル",
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
  "note": "任意の注記"
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
  "title": "条件に応じた分岐と戻り経路を示す",
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
  "title": "複数テーマ内の並行作業を俯瞰する",
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
  "title": "ノード間の接続関係を示す",
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
