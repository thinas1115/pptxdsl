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
選び方は[type選定ガイド](../../docs/type-selection-guide.md)、
合否とbackend差の扱いは導入済みSkillの`references/visual-acceptance.md`を参照してください。
