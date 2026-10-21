# 情報構造に合わせたtypeの記述例

[type-selection.json](type-selection.json)は、架空の受付方式の試行を題材にした4ページの例です。
実在組織の運用や効果を示すものではありません。新規資料では値やページ順を流用せず、
利用者の要件と情報源から内容を作ってください。

| ページ | type | 確認する情報構造 |
|---|---|---|
| 1 | `paired_comparison` | 同じ評価軸で2案を行ごとに比較 |
| 2 | `two_column` | 評価軸を揃えない、担当ごとの独立した準備事項 |
| 3 | `scope_boundary` | 左右共通の前提を`lead`へ置き、対象・対象外を分離 |
| 4 | `bullets` | 判断依頼と今回決めない範囲を`lead`へ置き、判断材料を本文へ分離 |

2ページ目は項目数も異なり、左右の同じ行が対応する意味はありません。
3ページ目では条件を左右へ複製せず、「左右共通の前提」と明記しています。
4ページ目の判断依頼は入力に明記した内容であり、rendererによる結論の生成ではありません。
廃止済みの`decision_summary`、`conclusion`、`preconditions`は使いません。

リポジトリルートから生成・検査します。

```powershell
python slidegen/validate_content.py examples/authoring/type-selection.json
python slidegen/generate_from_json.py examples/authoring/type-selection.json out/authoring/type-selection.pptx
python slidegen/check_layout.py out/authoring/type-selection.pptx
```

提出品質の確認にはPNG化と全ページの一覧・原寸確認も必要です。

## 画像の表示範囲

[image-reading.json](image-reading.json)は、全体の位置を示す図と、操作文字を読む図を分けた4ページ例です。

| ページ | 表示範囲と用途 |
|---|---|
| 1 | 架空画面全体を`contain`で表示し、緑枠①の位置を確認 |
| 2 | 同じ緑枠①の別画像を`contain`で拡大し、Target・Event・Saveを確認 |
| 3 | 抽象画像を`contain`で表示し、端を残す |
| 4 | 同じ抽象画像を`cover`で表示し、枠を埋める代わりに上下が切れることを確認 |

`cover`は中央基準のトリミングであり、操作対象へ自動的に寄る機能ではありません。
必須の文字やボタンが端にある画像には使わず、注目領域を含む画像を別途用意します。
切り抜きで操作の前提が消えないよう全体図と対応記号を残し、原寸で必要な文字が読めるか確認してください。
画面はコードで作った図版であり、実在サービスの仕様や操作手順を示しません。
再生成元は`tools/assets/build_image_examples.py`です。実行には開発用の`rlPyCairo`が必要ですが、
生成済みPNGは同梱され、通常のPPTX生成に追加依存は不要です。

```powershell
python slidegen/validate_content.py examples/authoring/image-reading.json
python slidegen/generate_from_json.py examples/authoring/image-reading.json out/authoring/image-reading.pptx
python slidegen/check_layout.py out/authoring/image-reading.pptx
```

## 設定箇所と確認事項の対応

[config-checks.json](config-checks.json)は、Pythonの設定キー・期待値・確認コードを対応づけた1ページ例です。
左の`replicas`、`health_path`、`timeout_s`を右の同名キーで追えます。
上の区画から下の区画へ続けて実行すると3つの`assert`が成功します。
これは設定値の照合例であり、サービスの稼働数・疎通・応答時間を実測した証拠ではありません。

`sections[].code`と`checks[]`に同じ識別子と期待値を書き、行位置や色だけで対応を伝えないようにします。
新たな座標・行強調フィールドは使いません。コード内の改行・インデントを保ち、
9.5ptでも収まらない長文は分割案内付きの`FitError`で停止します。
区画ごとに16行以内でも横幅や高さに収まるとは限らないため、長い実習は別ページへ分けます。

```powershell
python slidegen/validate_content.py examples/authoring/config-checks.json
python slidegen/generate_from_json.py examples/authoring/config-checks.json out/authoring/config-checks.pptx
python slidegen/check_layout.py out/authoring/config-checks.pptx
```

選び方は[type選定ガイド](../../docs/type-selection-guide.md)、
合否とbackend差の扱いは導入済みSkillの`references/visual-acceptance.md`を参照してください。
