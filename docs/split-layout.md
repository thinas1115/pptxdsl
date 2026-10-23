# 異なる情報構造を左右50:50で組み合わせる

`content.json`の作成者とrendererの保守者向けのガイド。
使うときは次の2節、実装を変更するときは「採用方式」以降を参照する。

## splitは共通の見出しを持つ1枚のスライド

構成図と判断材料、画像と説明、グラフと表など、相互に参照する異なる情報を同時に見せる場合に使う。
同じ評価軸で2案を比べるだけなら`two_column`、情報が多く読み合わせが不要なら別スライドへ分ける。

親にtype・kicker・titleと左右の本文を書く。lead、note、footnote、フッターは親で一度だけ表示する。
左右の本文へ共通見出し・注記を指定しない。splitの入れ子も検証で拒否する。
配置、幅比率、余白、フォントをJSONから指定する機能は持たない。

## 初期対応は4組で、左右の逆順も指定できる

| 組み合わせ | 読み合わせる内容 |
|---|---|
| diagram + cards | 構成・接続と、その判断材料や条件 |
| image + bullets | 画像・画面と、確認する点 |
| chart + table | 数量の傾向と、項目の定義や内訳 |
| bullets + cards | 読み順のある要点と、独立した比較項目 |

使用可能な組み合わせは構造スキーマが検査する。上記以外は受理せず、必要な構成をIssueへ記録する。
各子本文のフィールドは全幅typeと共通で、共通見出し・注記だけを除いている。
構造の詳細は[自動生成の契約](../CONTENT_SCHEMA.md#split)、入力時の注意点は[意味検証](content-semantics.md)を参照する。

構造を確認する最小例。新規資料の文言と画像は利用者の要件・情報源に合わせて置き換える。

```json
{
  "meta": {"title": "画面の確認"},
  "slides": [{
    "type": "split", "kicker": "確認", "title": "操作対象",
    "left": {"type": "image", "image": "images/pptxdsl-repository.png"},
    "right": {"type": "bullets", "style": "bullet", "bullets": [
      {"text": "表示する情報と操作対象を確認します。"}
    ]}
  }]
}
```

## 片側の不足を、もう片側の縮小や侵入で補わない

本文幅を等分し、中央に固定の間隔を置く。各子は既存の実測・余白圧縮・要素や文字の縮小を独立して行う。
たとえば右の箇条書きが増えても、左の画像を縮小しない。
全幅向けの内容がすべて半幅に入るという保証はなく、最小文字・最小列幅などの下限でも不足すれば`FitError`で停止する。
内容を短くする、項目を減らす、またはスライドを分ける。エラーには左右と子typeを表示する。

子の描画後にも領域外を検査し、切り取りや位置ずらしで隠さない。
失敗した場合は保存前に停止するため、途中まで描いたPPTXを提出物として保存しない。

## 採用方式はCで、対象を絞った領域APIを組み合わせる

| 方式 | 変更量・重複 | 既存出力への影響 | 組み合わせ追加 |
|---|---|---|---|
| A: 既存renderer全体を領域対応 | 対象外も含む多くの配置計算を変更する。本文処理の重複は少ない | 全typeへの回帰確認が必要 | 領域対応済みのtypeを組み合わせやすい |
| B: 半幅専用renderer | 全幅版を変更しにくい一方、実測・描画・収容が二重になる | 全幅版への直接影響は小さい | type追加ごとに専用実装の保守が増える |
| C: 複合層と選択対象の本文API | 親の共通部分と領域分割、子への委譲を追加する | 対象の本文APIは全幅の既定値を保持して確認する | 領域対応・検証済みの子だけを登録する |

Cを採用し、初期の6typeに限ってAの領域APIを導入した。本文処理をBとして複製せず、
既存の文字実測・収容・描画を使う。未対応rendererまで一括変更しない。
領域APIを追加した時点で、既存37枚のPPTX内部値・素材・描画順が変更前と完全一致することを確認した。
新しいギャラリーの追加によるページ数表示や表紙文言の変更とは区別している。

## 保守時の入口と検証

| 入口 | 責務 |
|---|---|
| split_layout.plan_split / DrawingRegion | 図形を作らず、左右の領域を確定する |
| split_renderer.s_split | 共通ヘッダー、本文への委譲、領域外の拒否、共通注記 |
| render_bullets_body / render_cards_body / render_table_body | 全幅・半幅で同じ本文処理を使う |
| render_image_body / render_chart / render_diagram | 領域内で各ジャンルの収容と描画を行う |
| schema_definition.split_block_schemas | 全幅の入力定義から子の本文契約を導出する |

新しい子typeを加える場合は、本文API・組み合わせのスキーマ・意味検証・通常と過密の試験を同時に追加する。
現在の組み合わせを変更せずrendererの許可だけを広げない。

```powershell
python -m unittest tests.test_split_layout
python -m tools.gallery.generate_split_cases out/split-cases.pptx
python slidegen/check_layout.py out/split-cases.pptx
python .agents/skills/pptxdsl/scripts/render_preview.py out/split-cases.pptx out/split-png
python contact_sheet.py out/split-png
```

全ページの一覧と原寸で、左右の視覚的な重さ、中央余白、見出し階層、接続経路、文字の収まりを確認する。
機械検査だけで目視確認や人の承認を完了にしない。描画手段がない場合は調査結果と未確認範囲を報告する。

このガイドで解決しない場合は、公開可能な入力・期待する組み合わせ・エラーを添えてIssueへ報告する。
「領域」はrenderer内部の描画範囲、「子本文」は左右に配置する構造、「複合層」はそれらをまとめる親の実装を指す。
