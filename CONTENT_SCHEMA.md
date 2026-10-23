# content.jsonの構造契約

この文書は`slidegen/schema_definition.py`から自動生成する。直接編集しない。

更新: `python -m tools.schema.generate`。整合検査: `python -m tools.schema.generate --check`。

[標準JSON Schema](schemas/content.schema.json)はフィールド、型、必須項目、件数、選択肢の正本から生成する。
表の必須・任意は直近の親オブジェクト内での指定。親自体が任意なら子も親を指定した場合に限る。
追加キーは原則禁止。条件付き必須・排他的指定はJSON Schemaのif/then/else等を参照する。

素材の実在、参照整合性、タイトル方針などは[意味検証と記述方針](docs/content-semantics.md)を参照する。
typeの選び方は[type選択ガイド](docs/type-selection-guide.md)、入力例は[執筆用例](examples/authoring/README.md)を参照する。

## 共通構造

| フィールド | 指定 | 構造 |
|---|---|---|
| `meta` | 必須 | オブジェクト |
| `meta.title` | 必須 | 空でない文字列 |
| `meta.footer` | 任意 | 空でない文字列 |
| `meta.date` | 任意 | 空でない文字列 |
| `meta.organization` | 任意 | 空でない文字列 |
| `meta.author` | 任意 | 空でない文字列 |
| `slides` | 必須 | 配列、1〜制限なし件 |

## title

| フィールド | 指定 | 構造 |
|---|---|---|
| `type` | 必須 | 固定値 `title` |
| `title` | 必須 | 空でない文字列 |
| `footnote` | 任意 | オブジェクト |
| `footnote.text` | 必須 | 空でない文字列 |
| `footnote.label` | 任意 | 空でない文字列 |
| `title_nominal_review` | 任意 | オブジェクト |
| `title_nominal_review.title` | 必須 | 空でない文字列 |
| `title_nominal_review.reason` | 必須 | 空でない文字列 |
| `subtitle` | 必須 | 空でない文字列 |

## section_divider

| フィールド | 指定 | 構造 |
|---|---|---|
| `type` | 必須 | 固定値 `section_divider` |
| `title` | 必須 | 空でない文字列 |
| `kicker` | 必須 | 空でない文字列 |
| `footnote` | 任意 | オブジェクト |
| `footnote.text` | 必須 | 空でない文字列 |
| `footnote.label` | 任意 | 空でない文字列 |
| `title_nominal_review` | 任意 | オブジェクト |
| `title_nominal_review.title` | 必須 | 空でない文字列 |
| `title_nominal_review.reason` | 必須 | 空でない文字列 |
| `lead` | 任意 | 空でない文字列 |

## bullets

| フィールド | 指定 | 構造 |
|---|---|---|
| `type` | 必須 | 固定値 `bullets` |
| `title` | 必須 | 空でない文字列 |
| `kicker` | 必須 | 空でない文字列 |
| `footnote` | 任意 | オブジェクト |
| `footnote.text` | 必須 | 空でない文字列 |
| `footnote.label` | 任意 | 空でない文字列 |
| `title_nominal_review` | 任意 | オブジェクト |
| `title_nominal_review.title` | 必須 | 空でない文字列 |
| `title_nominal_review.reason` | 必須 | 空でない文字列 |
| `lead` | 任意 | 空でない文字列 |
| `bullets` | 必須 | 配列、1〜6件 |
| `bullets[]` | 各要素 | 複数形式 |
| `bullets[]（形式1）.text` | 必須 | 空でない文字列 |
| `bullets[]（形式1）.checked` | 任意 | 真偽値 |
| `bullets[]（形式2）[0]` | 必須 | 空でない文字列 |
| `bullets[]（形式2）[1]` | 必須 | null |
| `style` | 任意 | `numbered` / `bullet` / `checklist` |

## cards

| フィールド | 指定 | 構造 |
|---|---|---|
| `type` | 必須 | 固定値 `cards` |
| `title` | 必須 | 空でない文字列 |
| `kicker` | 必須 | 空でない文字列 |
| `footnote` | 任意 | オブジェクト |
| `footnote.text` | 必須 | 空でない文字列 |
| `footnote.label` | 任意 | 空でない文字列 |
| `title_nominal_review` | 任意 | オブジェクト |
| `title_nominal_review.title` | 必須 | 空でない文字列 |
| `title_nominal_review.reason` | 必須 | 空でない文字列 |
| `lead` | 任意 | 空でない文字列 |
| `cards` | 必須 | 配列、2〜6件 |
| `cards[]` | 各要素 | オブジェクト |
| `cards[].heading` | 必須 | 空でない文字列 |
| `cards[].body` | 必須 | 空でない文字列 |
| `cards[].value` | 任意 | 空でない文字列 |
| `cards[].emphasis` | 任意 | 真偽値 |
| `style` | 任意 | `editorial` / `metrics` |

## table

| フィールド | 指定 | 構造 |
|---|---|---|
| `type` | 必須 | 固定値 `table` |
| `title` | 必須 | 空でない文字列 |
| `kicker` | 必須 | 空でない文字列 |
| `footnote` | 任意 | オブジェクト |
| `footnote.text` | 必須 | 空でない文字列 |
| `footnote.label` | 任意 | 空でない文字列 |
| `title_nominal_review` | 任意 | オブジェクト |
| `title_nominal_review.title` | 必須 | 空でない文字列 |
| `title_nominal_review.reason` | 必須 | 空でない文字列 |
| `lead` | 任意 | 空でない文字列 |
| `columns` | 必須 | 配列、2〜8件 |
| `columns[]` | 各要素 | 空でない文字列 |
| `rows` | 必須 | 配列、1〜8件 |
| `rows[]` | 各要素 | 配列、0〜制限なし件 |
| `rows[][]` | 各要素 | 文字列 |
| `note` | 任意 | 空でない文字列 |
| `note_link` | 任意 | オブジェクト |
| `note_link.label` | 必須 | 空でない文字列 |
| `note_link.url` | 必須 | 空でない文字列 |

## two_column

| フィールド | 指定 | 構造 |
|---|---|---|
| `type` | 必須 | 固定値 `two_column` |
| `title` | 必須 | 空でない文字列 |
| `kicker` | 必須 | 空でない文字列 |
| `footnote` | 任意 | オブジェクト |
| `footnote.text` | 必須 | 空でない文字列 |
| `footnote.label` | 任意 | 空でない文字列 |
| `title_nominal_review` | 任意 | オブジェクト |
| `title_nominal_review.title` | 必須 | 空でない文字列 |
| `title_nominal_review.reason` | 必須 | 空でない文字列 |
| `lead` | 任意 | 空でない文字列 |
| `left` | 必須 | オブジェクト |
| `left.heading` | 必須 | 空でない文字列 |
| `left.bullets` | 必須 | 配列、1〜6件 |
| `left.bullets[]` | 各要素 | 空でない文字列 |
| `left.label` | 任意 | 空でない文字列 |
| `right` | 必須 | オブジェクト |
| `right.heading` | 必須 | 空でない文字列 |
| `right.bullets` | 必須 | 配列、1〜6件 |
| `right.bullets[]` | 各要素 | 空でない文字列 |
| `right.label` | 任意 | 空でない文字列 |

## chart

| フィールド | 指定 | 構造 |
|---|---|---|
| `type` | 必須 | 固定値 `chart` |
| `title` | 必須 | 空でない文字列 |
| `kicker` | 必須 | 空でない文字列 |
| `footnote` | 任意 | オブジェクト |
| `footnote.text` | 必須 | 空でない文字列 |
| `footnote.label` | 任意 | 空でない文字列 |
| `title_nominal_review` | 任意 | オブジェクト |
| `title_nominal_review.title` | 必須 | 空でない文字列 |
| `title_nominal_review.reason` | 必須 | 空でない文字列 |
| `lead` | 任意 | 空でない文字列 |
| `chart` | 必須 | オブジェクト |
| `chart.categories` | 必須 | 配列、1〜12件 |
| `chart.categories[]` | 各要素 | 空でない文字列 |
| `chart.series` | 必須 | 配列、1〜4件 |
| `chart.series[]` | 各要素 | 配列、2〜2件 |
| `chart.series[][0]` | 必須 | 空でない文字列 |
| `chart.series[][1]` | 必須 | 配列、0〜制限なし件 |
| `chart.series[][1][]` | 各要素 | 有限数 |
| `chart.kind` | 任意 | `bar` / `column` / `line` / `stacked_bar` / `stacked_column` |
| `chart.show_legend` | 任意 | 真偽値 |
| `chart.show_values` | 任意 | 真偽値 |
| `chart.number_format` | 任意 | 文字列、書式はJSON Schemaのpatternを参照 |
| `note` | 任意 | 空でない文字列 |

## image

| フィールド | 指定 | 構造 |
|---|---|---|
| `type` | 必須 | 固定値 `image` |
| `title` | 必須 | 空でない文字列 |
| `kicker` | 必須 | 空でない文字列 |
| `footnote` | 任意 | オブジェクト |
| `footnote.text` | 必須 | 空でない文字列 |
| `footnote.label` | 任意 | 空でない文字列 |
| `title_nominal_review` | 任意 | オブジェクト |
| `title_nominal_review.title` | 必須 | 空でない文字列 |
| `title_nominal_review.reason` | 必須 | 空でない文字列 |
| `lead` | 任意 | 空でない文字列 |
| `image` | 必須 | 空でない文字列 |
| `fit` | 任意 | `contain` / `cover` |
| `shadow` | 任意 | 真偽値 |
| `alt` | 任意 | 空でない文字列 |

## image_compare

| フィールド | 指定 | 構造 |
|---|---|---|
| `type` | 必須 | 固定値 `image_compare` |
| `title` | 必須 | 空でない文字列 |
| `kicker` | 必須 | 空でない文字列 |
| `footnote` | 任意 | オブジェクト |
| `footnote.text` | 必須 | 空でない文字列 |
| `footnote.label` | 任意 | 空でない文字列 |
| `title_nominal_review` | 任意 | オブジェクト |
| `title_nominal_review.title` | 必須 | 空でない文字列 |
| `title_nominal_review.reason` | 必須 | 空でない文字列 |
| `lead` | 任意 | 空でない文字列 |
| `left` | 必須 | オブジェクト |
| `left.image` | 必須 | 空でない文字列 |
| `left.label` | 任意 | 空でない文字列 |
| `left.alt` | 任意 | 空でない文字列 |
| `right` | 必須 | オブジェクト |
| `right.image` | 必須 | 空でない文字列 |
| `right.label` | 任意 | 空でない文字列 |
| `right.alt` | 任意 | 空でない文字列 |
| `fit` | 任意 | `contain` / `cover` |
| `shadow` | 任意 | 真偽値 |

## process

| フィールド | 指定 | 構造 |
|---|---|---|
| `type` | 必須 | 固定値 `process` |
| `title` | 必須 | 空でない文字列 |
| `kicker` | 必須 | 空でない文字列 |
| `footnote` | 任意 | オブジェクト |
| `footnote.text` | 必須 | 空でない文字列 |
| `footnote.label` | 任意 | 空でない文字列 |
| `title_nominal_review` | 任意 | オブジェクト |
| `title_nominal_review.title` | 必須 | 空でない文字列 |
| `title_nominal_review.reason` | 必須 | 空でない文字列 |
| `lead` | 任意 | 空でない文字列 |
| `steps` | 任意 | 配列、3〜6件 |
| `steps[]` | 各要素 | オブジェクト |
| `steps[].name` | 必須 | 空でない文字列 |
| `steps[].desc` | 必須 | 空でない文字列 |
| `steps[].actor` | 任意 | 空でない文字列 |
| `steps[].attribute` | 任意 | オブジェクト |
| `steps[].attribute.label` | 必須 | 空でない文字列 |
| `steps[].attribute.value` | 必須 | 空でない文字列 |
| `flow` | 任意 | オブジェクト |
| `flow.nodes` | 必須 | オブジェクト、2〜12項目 |
| `flow.nodes.<id>` | 名前付き要素 | オブジェクト |
| `flow.nodes.<id>.name` | 必須 | 空でない文字列 |
| `flow.nodes.<id>.desc` | 任意 | 空でない文字列 |
| `flow.nodes.<id>.actor` | 任意 | 空でない文字列 |
| `flow.nodes.<id>.style` | 任意 | `standard` / `accent` / `decision` |
| `flow.levels` | 必須 | 配列、2〜6件 |
| `flow.levels[]` | 各要素 | 配列、1〜3件 |
| `flow.levels[][]` | 各要素 | 空でない文字列 |
| `flow.edges` | 必須 | 配列、1〜20件 |
| `flow.edges[]` | 各要素 | オブジェクト |
| `flow.edges[].from` | 必須 | 空でない文字列 |
| `flow.edges[].to` | 必須 | 空でない文字列 |
| `flow.edges[].label` | 任意 | 空でない文字列 |
| `flow.edges[].kind` | 任意 | `forward` / `feedback` |
| `emph` | 任意 | 配列、0〜制限なし件 |
| `emph[]` | 各要素 | 整数、0〜制限なし |
| `note` | 任意 | 空でない文字列 |

## program_roadmap

| フィールド | 指定 | 構造 |
|---|---|---|
| `type` | 必須 | 固定値 `program_roadmap` |
| `title` | 必須 | 空でない文字列 |
| `kicker` | 必須 | 空でない文字列 |
| `footnote` | 任意 | オブジェクト |
| `footnote.text` | 必須 | 空でない文字列 |
| `footnote.label` | 任意 | 空でない文字列 |
| `title_nominal_review` | 任意 | オブジェクト |
| `title_nominal_review.title` | 必須 | 空でない文字列 |
| `title_nominal_review.reason` | 必須 | 空でない文字列 |
| `lead` | 任意 | 空でない文字列 |
| `periods` | 必須 | 配列、3〜12件、重複不可 |
| `periods[]` | 各要素 | 空でない文字列 |
| `tracks` | 必須 | 配列、1〜6件 |
| `tracks[]` | 各要素 | オブジェクト |
| `tracks[].name` | 必須 | 空でない文字列 |
| `tracks[].activities` | 必須 | 配列、1〜8件 |
| `tracks[].activities[]` | 各要素 | オブジェクト |
| `tracks[].activities[].label` | 必須 | 空でない文字列 |
| `tracks[].activities[].start` | 必須 | 複数形式 |
| `tracks[].activities[].end` | 必須 | 複数形式 |
| `tracks[].activities[].emph` | 任意 | 真偽値 |
| `tracks[].goal` | 任意 | 空でない文字列 |
| `tracks[].milestone` | 任意 | オブジェクト |
| `tracks[].milestone.at` | 必須 | 複数形式 |
| `tracks[].milestone.label` | 必須 | 空でない文字列 |
| `note` | 任意 | 空でない文字列 |

## matrix

| フィールド | 指定 | 構造 |
|---|---|---|
| `type` | 必須 | 固定値 `matrix` |
| `title` | 必須 | 空でない文字列 |
| `kicker` | 必須 | 空でない文字列 |
| `footnote` | 任意 | オブジェクト |
| `footnote.text` | 必須 | 空でない文字列 |
| `footnote.label` | 任意 | 空でない文字列 |
| `title_nominal_review` | 任意 | オブジェクト |
| `title_nominal_review.title` | 必須 | 空でない文字列 |
| `title_nominal_review.reason` | 必須 | 空でない文字列 |
| `lead` | 任意 | 空でない文字列 |
| `x_axis` | 必須 | 空でない文字列 |
| `y_axis` | 必須 | 空でない文字列 |
| `points` | 必須 | 配列、1〜8件 |
| `points[]` | 各要素 | オブジェクト |
| `points[].name` | 必須 | 空でない文字列 |
| `points[].x` | 必須 | 有限数、0〜1 |
| `points[].y` | 必須 | 有限数、0〜1 |
| `points[].emph` | 任意 | 真偽値 |
| `quadrants` | 任意 | 配列、4〜4件 |
| `quadrants[]` | 各要素 | 空でない文字列 |
| `target_label` | 任意 | 空でない文字列 |
| `note` | 任意 | 空でない文字列 |

## scope_boundary

| フィールド | 指定 | 構造 |
|---|---|---|
| `type` | 必須 | 固定値 `scope_boundary` |
| `title` | 必須 | 空でない文字列 |
| `kicker` | 必須 | 空でない文字列 |
| `footnote` | 任意 | オブジェクト |
| `footnote.text` | 必須 | 空でない文字列 |
| `footnote.label` | 任意 | 空でない文字列 |
| `title_nominal_review` | 任意 | オブジェクト |
| `title_nominal_review.title` | 必須 | 空でない文字列 |
| `title_nominal_review.reason` | 必須 | 空でない文字列 |
| `lead` | 任意 | 空でない文字列 |
| `in_scope` | 必須 | 配列、1〜6件 |
| `in_scope[]` | 各要素 | 空でない文字列 |
| `out_of_scope` | 必須 | 配列、1〜6件 |
| `out_of_scope[]` | 各要素 | 空でない文字列 |
| `in_label` | 任意 | 空でない文字列 |
| `out_label` | 任意 | 空でない文字列 |

## paired_comparison

| フィールド | 指定 | 構造 |
|---|---|---|
| `type` | 必須 | 固定値 `paired_comparison` |
| `title` | 必須 | 空でない文字列 |
| `kicker` | 必須 | 空でない文字列 |
| `footnote` | 任意 | オブジェクト |
| `footnote.text` | 必須 | 空でない文字列 |
| `footnote.label` | 任意 | 空でない文字列 |
| `title_nominal_review` | 任意 | オブジェクト |
| `title_nominal_review.title` | 必須 | 空でない文字列 |
| `title_nominal_review.reason` | 必須 | 空でない文字列 |
| `lead` | 任意 | 空でない文字列 |
| `left_label` | 必須 | 空でない文字列 |
| `right_label` | 必須 | 空でない文字列 |
| `rows` | 必須 | 配列、2〜6件 |
| `rows[]` | 各要素 | オブジェクト |
| `rows[].criterion` | 必須 | 空でない文字列 |
| `rows[].left` | 必須 | 空でない文字列 |
| `rows[].right` | 必須 | 空でない文字列 |
| `criterion_label` | 任意 | 空でない文字列 |

## relationship_map

| フィールド | 指定 | 構造 |
|---|---|---|
| `type` | 必須 | 固定値 `relationship_map` |
| `title` | 必須 | 空でない文字列 |
| `kicker` | 必須 | 空でない文字列 |
| `footnote` | 任意 | オブジェクト |
| `footnote.text` | 必須 | 空でない文字列 |
| `footnote.label` | 任意 | 空でない文字列 |
| `title_nominal_review` | 任意 | オブジェクト |
| `title_nominal_review.title` | 必須 | 空でない文字列 |
| `title_nominal_review.reason` | 必須 | 空でない文字列 |
| `lead` | 任意 | 空でない文字列 |
| `left_label` | 必須 | 空でない文字列 |
| `right_label` | 必須 | 空でない文字列 |
| `left_items` | 必須 | 配列、2〜6件 |
| `left_items[]` | 各要素 | オブジェクト |
| `left_items[].id` | 必須 | 空でない文字列 |
| `left_items[].text` | 必須 | 空でない文字列 |
| `right_items` | 必須 | 配列、2〜6件 |
| `right_items[]` | 各要素 | オブジェクト |
| `right_items[].id` | 必須 | 空でない文字列 |
| `right_items[].text` | 必須 | 空でない文字列 |
| `links` | 必須 | 配列、1〜10件 |
| `links[]` | 各要素 | オブジェクト |
| `links[].from` | 必須 | 空でない文字列 |
| `links[].to` | 必須 | 空でない文字列 |
| `links[].emphasis` | 任意 | 真偽値 |

## swimlane_flow

| フィールド | 指定 | 構造 |
|---|---|---|
| `type` | 必須 | 固定値 `swimlane_flow` |
| `title` | 必須 | 空でない文字列 |
| `kicker` | 必須 | 空でない文字列 |
| `footnote` | 任意 | オブジェクト |
| `footnote.text` | 必須 | 空でない文字列 |
| `footnote.label` | 任意 | 空でない文字列 |
| `title_nominal_review` | 任意 | オブジェクト |
| `title_nominal_review.title` | 必須 | 空でない文字列 |
| `title_nominal_review.reason` | 必須 | 空でない文字列 |
| `lead` | 任意 | 空でない文字列 |
| `lanes` | 必須 | 配列、2〜6件 |
| `lanes[]` | 各要素 | オブジェクト |
| `lanes[].id` | 必須 | 空でない文字列 |
| `lanes[].label` | 必須 | 空でない文字列 |
| `stages` | 必須 | 配列、2〜6件 |
| `stages[]` | 各要素 | オブジェクト |
| `stages[].id` | 必須 | 空でない文字列 |
| `stages[].label` | 必須 | 空でない文字列 |
| `steps` | 必須 | 配列、2〜14件 |
| `steps[]` | 各要素 | オブジェクト |
| `steps[].id` | 必須 | 空でない文字列 |
| `steps[].name` | 必須 | 空でない文字列 |
| `steps[].lane` | 必須 | 空でない文字列 |
| `steps[].stage` | 必須 | 空でない文字列 |
| `steps[].style` | 任意 | `standard` / `accent` |
| `steps[].number` | 任意 | 複数形式 |
| `edges` | 必須 | 配列、1〜20件 |
| `edges[]` | 各要素 | オブジェクト |
| `edges[].from` | 必須 | 空でない文字列 |
| `edges[].to` | 必須 | 空でない文字列 |
| `edges[].kind` | 任意 | `forward` / `feedback` |

## message_sequence

| フィールド | 指定 | 構造 |
|---|---|---|
| `type` | 必須 | 固定値 `message_sequence` |
| `title` | 必須 | 空でない文字列 |
| `kicker` | 必須 | 空でない文字列 |
| `footnote` | 任意 | オブジェクト |
| `footnote.text` | 必須 | 空でない文字列 |
| `footnote.label` | 任意 | 空でない文字列 |
| `title_nominal_review` | 任意 | オブジェクト |
| `title_nominal_review.title` | 必須 | 空でない文字列 |
| `title_nominal_review.reason` | 必須 | 空でない文字列 |
| `lead` | 任意 | 空でない文字列 |
| `participants` | 必須 | 配列、2〜6件 |
| `participants[]` | 各要素 | オブジェクト |
| `participants[].id` | 必須 | 空でない文字列 |
| `participants[].label` | 必須 | 空でない文字列 |
| `messages` | 必須 | 配列、2〜12件 |
| `messages[]` | 各要素 | オブジェクト |
| `messages[].from` | 必須 | 空でない文字列 |
| `messages[].to` | 必須 | 空でない文字列 |
| `messages[].id` | 必須 | 空でない文字列 |
| `messages[].label` | 必須 | 空でない文字列 |
| `messages[].kind` | 任意 | `request` / `return` / `async` |
| `phases` | 任意 | 配列、0〜3件 |
| `phases[]` | 各要素 | オブジェクト |
| `phases[].from` | 必須 | 空でない文字列 |
| `phases[].to` | 必須 | 空でない文字列 |
| `phases[].label` | 必須 | 空でない文字列 |

## concept

| フィールド | 指定 | 構造 |
|---|---|---|
| `type` | 必須 | 固定値 `concept` |
| `title` | 必須 | 空でない文字列 |
| `kicker` | 必須 | 空でない文字列 |
| `footnote` | 任意 | オブジェクト |
| `footnote.text` | 必須 | 空でない文字列 |
| `footnote.label` | 任意 | 空でない文字列 |
| `title_nominal_review` | 任意 | オブジェクト |
| `title_nominal_review.title` | 必須 | 空でない文字列 |
| `title_nominal_review.reason` | 必須 | 空でない文字列 |
| `lead` | 任意 | 空でない文字列 |
| `term` | 必須 | 空でない文字列 |
| `definition` | 必須 | 空でない文字列 |
| `icon` | 必須 | 空でない文字列 |
| `points` | 必須 | 配列、2〜4件 |
| `points[]` | 各要素 | オブジェクト |
| `points[].label` | 必須 | 空でない文字列 |
| `points[].text` | 必須 | 空でない文字列 |

## references

| フィールド | 指定 | 構造 |
|---|---|---|
| `type` | 必須 | 固定値 `references` |
| `title` | 必須 | 空でない文字列 |
| `kicker` | 必須 | 空でない文字列 |
| `footnote` | 任意 | オブジェクト |
| `footnote.text` | 必須 | 空でない文字列 |
| `footnote.label` | 任意 | 空でない文字列 |
| `title_nominal_review` | 任意 | オブジェクト |
| `title_nominal_review.title` | 必須 | 空でない文字列 |
| `title_nominal_review.reason` | 必須 | 空でない文字列 |
| `lead` | 任意 | 空でない文字列 |
| `references` | 必須 | 配列、1〜5件 |
| `references[]` | 各要素 | オブジェクト |
| `references[].id` | 必須 | 空でない文字列 |
| `references[].title` | 必須 | 空でない文字列 |
| `references[].url` | 必須 | 空でない文字列 |
| `references[].scope` | 任意 | 空でない文字列 |

## nw_topology

| フィールド | 指定 | 構造 |
|---|---|---|
| `type` | 必須 | 固定値 `nw_topology` |
| `title` | 必須 | 空でない文字列 |
| `kicker` | 必須 | 空でない文字列 |
| `footnote` | 任意 | オブジェクト |
| `footnote.text` | 必須 | 空でない文字列 |
| `footnote.label` | 任意 | 空でない文字列 |
| `title_nominal_review` | 任意 | オブジェクト |
| `title_nominal_review.title` | 必須 | 空でない文字列 |
| `title_nominal_review.reason` | 必須 | 空でない文字列 |
| `lead` | 任意 | 空でない文字列 |
| `lanes` | 必須 | 配列、1〜4件 |
| `lanes[]` | 各要素 | オブジェクト |
| `lanes[].id` | 必須 | 空でない文字列 |
| `lanes[].label` | 必須 | 空でない文字列 |
| `lanes[].sub` | 任意 | 空でない文字列 |
| `columns` | 必須 | 配列、2〜6件 |
| `columns[]` | 各要素 | オブジェクト |
| `columns[].id` | 必須 | 空でない文字列 |
| `columns[].label` | 必須 | 空でない文字列 |
| `nodes` | 必須 | 配列、2〜12件 |
| `nodes[]` | 各要素 | オブジェクト |
| `nodes[].id` | 必須 | 空でない文字列 |
| `nodes[].label` | 必須 | 空でない文字列 |
| `nodes[].icon` | 必須 | 空でない文字列 |
| `nodes[].column` | 必須 | 空でない文字列 |
| `nodes[].lanes` | 必須 | 配列、1〜制限なし件、重複不可 |
| `nodes[].lanes[]` | 各要素 | 空でない文字列 |
| `nodes[].sub` | 任意 | 空でない文字列 |
| `links` | 必須 | 配列、1〜18件 |
| `links[]` | 各要素 | オブジェクト |
| `links[].from` | 必須 | 空でない文字列 |
| `links[].to` | 必須 | 空でない文字列 |
| `links[].kind` | 任意 | `access` / `trunk` / `routed` / `control` / `broadcast` / `blocked` |
| `links[].lanes` | 任意 | 配列、0〜制限なし件、重複不可 |
| `links[].lanes[]` | 各要素 | 空でない文字列 |
| `links[].label` | 任意 | 空でない文字列 |

## nw_protocol_flow

| フィールド | 指定 | 構造 |
|---|---|---|
| `type` | 必須 | 固定値 `nw_protocol_flow` |
| `title` | 必須 | 空でない文字列 |
| `kicker` | 必須 | 空でない文字列 |
| `footnote` | 任意 | オブジェクト |
| `footnote.text` | 必須 | 空でない文字列 |
| `footnote.label` | 任意 | 空でない文字列 |
| `title_nominal_review` | 任意 | オブジェクト |
| `title_nominal_review.title` | 必須 | 空でない文字列 |
| `title_nominal_review.reason` | 必須 | 空でない文字列 |
| `lead` | 任意 | 空でない文字列 |
| `stages` | 必須 | 配列、3〜6件 |
| `stages[]` | 各要素 | オブジェクト |
| `stages[].id` | 必須 | 空でない文字列 |
| `stages[].label` | 必須 | 空でない文字列 |
| `stages[].icon` | 必須 | 空でない文字列 |
| `stages[].role` | 任意 | `endpoint` / `processor` / `link` |
| `flows` | 必須 | 配列、1〜3件 |
| `flows[]` | 各要素 | オブジェクト |
| `flows[].label` | 必須 | 空でない文字列 |
| `flows[].states` | 必須 | 配列、0〜制限なし件 |
| `flows[].states[]` | 各要素 | オブジェクト |
| `flows[].states[].stage` | 必須 | 空でない文字列 |
| `flows[].states[].label` | 必須 | 空でない文字列 |
| `flows[].states[].detail` | 任意 | 空でない文字列 |
| `flows[].states[].appearance` | 任意 | `plain` / `encapsulated` / `internal` / `alert` |
| `flows[].states[].encapsulation` | 任意 | 空でない文字列 |
| `flows[].sub` | 任意 | 空でない文字列 |

## nw_frame_anatomy

| フィールド | 指定 | 構造 |
|---|---|---|
| `type` | 必須 | 固定値 `nw_frame_anatomy` |
| `title` | 必須 | 空でない文字列 |
| `kicker` | 必須 | 空でない文字列 |
| `footnote` | 任意 | オブジェクト |
| `footnote.text` | 必須 | 空でない文字列 |
| `footnote.label` | 任意 | 空でない文字列 |
| `title_nominal_review` | 任意 | オブジェクト |
| `title_nominal_review.title` | 必須 | 空でない文字列 |
| `title_nominal_review.reason` | 必須 | 空でない文字列 |
| `lead` | 任意 | 空でない文字列 |
| `frames` | 必須 | 配列、1〜3件 |
| `frames[]` | 各要素 | オブジェクト |
| `frames[].label` | 必須 | 空でない文字列 |
| `frames[].fields` | 必須 | 配列、3〜9件 |
| `frames[].fields[]` | 各要素 | オブジェクト |
| `frames[].fields[].id` | 必須 | 空でない文字列 |
| `frames[].fields[].name` | 必須 | 空でない文字列 |
| `frames[].fields[].bits` | 必須 | 整数、1〜65535 |
| `frames[].fields[].size_label` | 任意 | 空でない文字列 |
| `frames[].fields[].role` | 任意 | `standard` / `muted` / `highlight` / `alert` |
| `frames[].annotations` | 任意 | 配列、0〜4件 |
| `frames[].annotations[]` | 各要素 | オブジェクト |
| `frames[].annotations[].field` | 必須 | 空でない文字列 |
| `frames[].annotations[].text` | 必須 | 空でない文字列 |

## config_lab

| フィールド | 指定 | 構造 |
|---|---|---|
| `type` | 必須 | 固定値 `config_lab` |
| `title` | 必須 | 空でない文字列 |
| `kicker` | 必須 | 空でない文字列 |
| `footnote` | 任意 | オブジェクト |
| `footnote.text` | 必須 | 空でない文字列 |
| `footnote.label` | 任意 | 空でない文字列 |
| `title_nominal_review` | 任意 | オブジェクト |
| `title_nominal_review.title` | 必須 | 空でない文字列 |
| `title_nominal_review.reason` | 必須 | 空でない文字列 |
| `lead` | 任意 | 空でない文字列 |
| `sections` | 必須 | 配列、1〜2件 |
| `sections[]` | 各要素 | オブジェクト |
| `sections[].label` | 必須 | 空でない文字列 |
| `sections[].code` | 必須 | 空でない文字列 |
| `checks` | 必須 | 配列、2〜5件 |
| `checks[]` | 各要素 | 空でない文字列 |
| `check_label` | 任意 | 空でない文字列 |

## knowledge_check

| フィールド | 指定 | 構造 |
|---|---|---|
| `type` | 必須 | 固定値 `knowledge_check` |
| `title` | 必須 | 空でない文字列 |
| `kicker` | 必須 | 空でない文字列 |
| `footnote` | 任意 | オブジェクト |
| `footnote.text` | 必須 | 空でない文字列 |
| `footnote.label` | 任意 | 空でない文字列 |
| `title_nominal_review` | 任意 | オブジェクト |
| `title_nominal_review.title` | 必須 | 空でない文字列 |
| `title_nominal_review.reason` | 必須 | 空でない文字列 |
| `lead` | 任意 | 空でない文字列 |
| `mode` | 必須 | `questions` / `answers` |
| `questions` | 必須 | 配列、1〜3件 |
| `questions[]` | 各要素 | オブジェクト |
| `questions[].question` | 必須 | 空でない文字列 |
| `questions[].options` | 必須 | 配列、2〜4件 |
| `questions[].options[]` | 各要素 | 空でない文字列 |
| `questions[].answer` | 必須 | 整数 |
| `questions[].explanation` | 必須 | 空でない文字列 |

## org

| フィールド | 指定 | 構造 |
|---|---|---|
| `type` | 必須 | 固定値 `org` |
| `title` | 必須 | 空でない文字列 |
| `kicker` | 必須 | 空でない文字列 |
| `footnote` | 任意 | オブジェクト |
| `footnote.text` | 必須 | 空でない文字列 |
| `footnote.label` | 任意 | 空でない文字列 |
| `title_nominal_review` | 任意 | オブジェクト |
| `title_nominal_review.title` | 必須 | 空でない文字列 |
| `title_nominal_review.reason` | 必須 | 空でない文字列 |
| `lead` | 任意 | 空でない文字列 |
| `org` | 必須 | オブジェクト |
| `org.nodes` | 必須 | オブジェクト、1〜制限なし項目 |
| `org.nodes.<id>` | 名前付き要素 | オブジェクト |
| `org.nodes.<id>.name` | 必須 | 空でない文字列 |
| `org.nodes.<id>.sub` | 任意 | 空でない文字列 |
| `org.nodes.<id>.members` | 任意 | 配列、0〜4件 |
| `org.nodes.<id>.members[]` | 各要素 | 空でない文字列 |
| `org.nodes.<id>.style` | 任意 | `primary` / `accent` / `standard` / `external` |
| `org.levels` | 必須 | 配列、1〜6件 |
| `org.levels[]` | 各要素 | 配列、1〜5件 |
| `org.levels[][]` | 各要素 | 空でない文字列 |
| `org.edges` | 任意 | 配列、0〜40件 |
| `org.edges[]` | 各要素 | オブジェクト |
| `org.edges[].from` | 必須 | 空でない文字列 |
| `org.edges[].to` | 必須 | 空でない文字列 |
| `org.edges[].kind` | 任意 | `reporting` / `advice` / `collaboration` |
| `org.edges[].label` | 任意 | 空でない文字列 |
| `note` | 任意 | 空でない文字列 |

## diagram

| フィールド | 指定 | 構造 |
|---|---|---|
| `type` | 必須 | 固定値 `diagram` |
| `title` | 必須 | 空でない文字列 |
| `kicker` | 必須 | 空でない文字列 |
| `footnote` | 任意 | オブジェクト |
| `footnote.text` | 必須 | 空でない文字列 |
| `footnote.label` | 任意 | 空でない文字列 |
| `title_nominal_review` | 任意 | オブジェクト |
| `title_nominal_review.title` | 必須 | 空でない文字列 |
| `title_nominal_review.reason` | 必須 | 空でない文字列 |
| `lead` | 任意 | 空でない文字列 |
| `diagram` | 必須 | オブジェクト |
| `diagram.cols` | 必須 | 配列、1〜制限なし件、重複不可 |
| `diagram.cols[]` | 各要素 | 空でない文字列 |
| `diagram.rows` | 必須 | 配列、1〜制限なし件、重複不可 |
| `diagram.rows[]` | 各要素 | 空でない文字列 |
| `diagram.nodes` | 必須 | オブジェクト、1〜制限なし項目 |
| `diagram.nodes.<id>` | 名前付き要素 | オブジェクト |
| `diagram.nodes.<id>.col` | 必須 | 空でない文字列 |
| `diagram.nodes.<id>.row` | 必須 | 空でない文字列 |
| `diagram.nodes.<id>.title` | 必須 | 空でない文字列 |
| `diagram.nodes.<id>.icon` | 必須 | 空でない文字列 |
| `diagram.nodes.<id>.sub` | 任意 | 空でない文字列 |
| `diagram.nodes.<id>.service` | 任意 | 空でない文字列 |
| `diagram.edges` | 必須 | 配列、1〜制限なし件 |
| `diagram.edges[]` | 各要素 | オブジェクト |
| `diagram.edges[].from` | 必須 | 空でない文字列 |
| `diagram.edges[].to` | 必須 | 空でない文字列 |
| `diagram.edges[].label` | 任意 | 空でない文字列 |
| `diagram.edges[].exit` | 任意 | `left` / `right` / `top` / `bottom` |
| `diagram.edges[].enter` | 任意 | `left` / `right` / `top` / `bottom` |
| `diagram.edges[].via` | 任意 | 配列、0〜制限なし件 |
| `diagram.edges[].via[]` | 各要素 | 空でない文字列 |
| `diagram.edges[].dash` | 任意 | 固定値 `dash` |
| `diagram.edges[].both` | 任意 | 真偽値 |
| `diagram.edges[].from_row` | 任意 | 空でない文字列 |
| `diagram.containers` | 任意 | 配列、0〜制限なし件 |
| `diagram.containers[]` | 各要素 | オブジェクト |
| `diagram.containers[].name` | 必須 | 空でない文字列 |
| `diagram.containers[].label` | 必須 | 空でない文字列 |
| `diagram.containers[].members` | 必須 | 配列、1〜制限なし件 |
| `diagram.containers[].members[]` | 各要素 | 空でない文字列 |
| `diagram.containers[].color` | 任意 | `line` / `navy` / `accent` |
| `diagram.containers[].dash` | 任意 | 固定値 `dash` |
| `diagram.channels` | 任意 | オブジェクト、0〜制限なし項目 |
| `diagram.channels.<id>` | 名前付き要素 | 複数形式 |
| `diagram.channels.<id>（形式1）[0]` | 必須 | `left_of_col` / `right_of_col` / `above_row` / `below_row` |
| `diagram.channels.<id>（形式1）[1]` | 必須 | 空でない文字列 |
| `diagram.channels.<id>（形式2）[0]` | 必須 | 固定値 `outside_container` |
| `diagram.channels.<id>（形式2）[1]` | 必須 | 配列、2〜2件 |
| `diagram.channels.<id>（形式2）[1][0]` | 必須 | 複数形式 |
| `diagram.channels.<id>（形式2）[1][0]（形式2）[]` | 各要素 | 空でない文字列 |
| `diagram.channels.<id>（形式2）[1][1]` | 必須 | `left` / `right` / `top` / `bottom` / `top_inside` |
| `note` | 任意 | 空でない文字列 |

## aws_vpc_layout

| フィールド | 指定 | 構造 |
|---|---|---|
| `type` | 必須 | 固定値 `aws_vpc_layout` |
| `title` | 必須 | 空でない文字列 |
| `kicker` | 必須 | 空でない文字列 |
| `footnote` | 任意 | オブジェクト |
| `footnote.text` | 必須 | 空でない文字列 |
| `footnote.label` | 任意 | 空でない文字列 |
| `title_nominal_review` | 任意 | オブジェクト |
| `title_nominal_review.title` | 必須 | 空でない文字列 |
| `title_nominal_review.reason` | 必須 | 空でない文字列 |
| `lead` | 任意 | 空でない文字列 |
| `vpc` | 必須 | オブジェクト |
| `vpc.label` | 必須 | 空でない文字列 |
| `vpc.cidr` | 任意 | 空でない文字列 |
| `azs` | 必須 | 配列、1〜3件 |
| `azs[]` | 各要素 | オブジェクト |
| `azs[].id` | 必須 | 空でない文字列 |
| `azs[].label` | 必須 | 空でない文字列 |
| `azs[].subnets` | 必須 | 配列、1〜3件 |
| `azs[].subnets[]` | 各要素 | オブジェクト |
| `azs[].subnets[].id` | 必須 | 空でない文字列 |
| `azs[].subnets[].label` | 必須 | 空でない文字列 |
| `azs[].subnets[].cidr` | 任意 | 空でない文字列 |
| `azs[].subnets[].resources` | 任意 | 配列、0〜2件 |
| `azs[].subnets[].resources[]` | 各要素 | オブジェクト |
| `azs[].subnets[].resources[].id` | 必須 | 空でない文字列 |
| `azs[].subnets[].resources[].label` | 必須 | 空でない文字列 |
| `azs[].subnets[].resources[].icon` | 必須 | 空でない文字列 |
| `azs[].subnets[].resources[].sub` | 任意 | 空でない文字列 |
| `external` | 任意 | 配列、0〜2件 |
| `external[]` | 各要素 | オブジェクト |
| `external[].id` | 必須 | 空でない文字列 |
| `external[].label` | 必須 | 空でない文字列 |
| `external[].icon` | 必須 | 空でない文字列 |
| `external[].sub` | 任意 | 空でない文字列 |
| `flows` | 任意 | 配列、0〜10件 |
| `flows[]` | 各要素 | オブジェクト |
| `flows[].from` | 必須 | 空でない文字列 |
| `flows[].to` | 必須 | 空でない文字列 |
| `flows[].label` | 任意 | 空でない文字列 |
| `flows[].dash` | 任意 | 固定値 `dash` |
| `flows[].both` | 任意 | 真偽値 |
| `note` | 任意 | 空でない文字列 |

## split

| フィールド | 指定 | 構造 |
|---|---|---|
| `type` | 必須 | 固定値 `split` |
| `title` | 必須 | 空でない文字列 |
| `kicker` | 必須 | 空でない文字列 |
| `footnote` | 任意 | オブジェクト |
| `footnote.text` | 必須 | 空でない文字列 |
| `footnote.label` | 任意 | 空でない文字列 |
| `title_nominal_review` | 任意 | オブジェクト |
| `title_nominal_review.title` | 必須 | 空でない文字列 |
| `title_nominal_review.reason` | 必須 | 空でない文字列 |
| `lead` | 任意 | 空でない文字列 |
| `left` | 必須 | 半幅の子本文: diagram / cards / image / bullets / chart / table |
| `right` | 必須 | 半幅の子本文: diagram / cards / image / bullets / chart / table |
| `note` | 任意 | 空でない文字列 |
| `（形式1）.left` | 任意 | 複数形式 |
| `（形式1）.left.type` | 任意 | 固定値 `diagram` |
| `（形式1）.right` | 任意 | 複数形式 |
| `（形式1）.right.type` | 任意 | 固定値 `cards` |
| `（形式2）.left` | 任意 | 複数形式 |
| `（形式2）.left.type` | 任意 | 固定値 `image` |
| `（形式2）.right` | 任意 | 複数形式 |
| `（形式2）.right.type` | 任意 | 固定値 `bullets` |
| `（形式3）.left` | 任意 | 複数形式 |
| `（形式3）.left.type` | 任意 | 固定値 `chart` |
| `（形式3）.right` | 任意 | 複数形式 |
| `（形式3）.right.type` | 任意 | 固定値 `table` |
| `（形式4）.left` | 任意 | 複数形式 |
| `（形式4）.left.type` | 任意 | 固定値 `bullets` |
| `（形式4）.right` | 任意 | 複数形式 |
| `（形式4）.right.type` | 任意 | 固定値 `cards` |
| `（形式5）.left` | 任意 | 複数形式 |
| `（形式5）.left.type` | 任意 | 固定値 `cards` |
| `（形式5）.right` | 任意 | 複数形式 |
| `（形式5）.right.type` | 任意 | 固定値 `diagram` |
| `（形式6）.left` | 任意 | 複数形式 |
| `（形式6）.left.type` | 任意 | 固定値 `bullets` |
| `（形式6）.right` | 任意 | 複数形式 |
| `（形式6）.right.type` | 任意 | 固定値 `image` |
| `（形式7）.left` | 任意 | 複数形式 |
| `（形式7）.left.type` | 任意 | 固定値 `table` |
| `（形式7）.right` | 任意 | 複数形式 |
| `（形式7）.right.type` | 任意 | 固定値 `chart` |
| `（形式8）.left` | 任意 | 複数形式 |
| `（形式8）.left.type` | 任意 | 固定値 `cards` |
| `（形式8）.right` | 任意 | 複数形式 |
| `（形式8）.right.type` | 任意 | 固定値 `bullets` |
