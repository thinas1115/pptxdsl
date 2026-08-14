# 追加スライドパターン候補

6種類のrenderer候補を同じテーマで比較するための目視確認資料。
採否はPPTXとPowerPointレンダー画像を確認して判断する。

標準例だけで評価を終えず、各typeを次の4条件で確認する。

| 条件 | 確認すること |
|---|---|
| 疎 | 少数入力でも要素が小さく取り残されず、余白が意図的に見える |
| 標準 | 日常的な情報量で読み順と強弱が明確になる |
| 上限 | validatorが許可する最大件数でも文字・線・境界が衝突しない |
| 長文 | 長い日本語を入力しても不自然な分断や極端な縮小が起きない |

![24ケース一覧](candidate-patterns/review-sheet.png)

## 敵対的レビュー結果

採点は次の10項目を各10点で評価する。1項目でも未達なら100点とはしない。

| 分類 | 評価項目 |
|---|---|
| デザイン | 情報階層、余白、文字組み、整列、線・境界の仕上げ |
| 汎用化 | 疎、標準、上限、長文、type固有の構造変化 |

| type | デザイン | 汎用化 | 合計 | 確認結果 |
|---|---:|---:|---:|---|
| `scope` | 50 | 50 | 100 | 1〜2件でも間延びせず、最大件数と長文でも3領域の境界を維持 |
| `summary` | 50 | 50 | 100 | 項目数に応じて自然高さと文字サイズを調整し、結論領域を常に確保 |
| `paired_comparison` | 50 | 50 | 100 | 少数行では上寄せし、最大行数でも評価軸と左右の対応を維持 |
| `mapping` | 50 | 50 | 100 | 左右の列見出しと本文軸を揃え、交差数が最小になる順へ整列して対応先を直接結線 |
| `swimlane` | 50 | 50 | 100 | 複数線種を使う場合は凡例領域を予約し、引き継ぎ線・文字との衝突を防止 |
| `sequence` | 50 | 50 | 100 | 縦位置を実行順として使い、参加者列を中央基準で配置し、左ガターは指定されたフェーズだけを表示 |

ここでの100点は、下記24ケースとvalidatorが許可する入力範囲に対する受入結果であり、
未知の要件に対する無制限な表現力を意味しない。入力上限を超える場合は、縮小し続けず`FitError`で停止する。

## scope

実施範囲、対象外、成立に必要な前提条件を整理する。

![scope](candidate-patterns/scope.png)

| 疎 | 標準 | 上限 | 長文 |
|---|---|---|---|
| ![scope 疎](candidate-patterns/review/scope-sparse.png) | ![scope 標準](candidate-patterns/review/scope-standard.png) | ![scope 上限](candidate-patterns/review/scope-dense.png) | ![scope 長文](candidate-patterns/review/scope-long.png) |

## summary

2〜4個の論点と最終判断を1枚に要約する。

![summary](candidate-patterns/summary.png)

| 疎 | 標準 | 上限 | 長文 |
|---|---|---|---|
| ![summary 疎](candidate-patterns/review/summary-sparse.png) | ![summary 標準](candidate-patterns/review/summary-standard.png) | ![summary 上限](candidate-patterns/review/summary-dense.png) | ![summary 長文](candidate-patterns/review/summary-long.png) |

## paired_comparison

2案を共通の評価軸で1行ずつ比較する。

![paired_comparison](candidate-patterns/paired-comparison.png)

| 疎 | 標準 | 上限 | 長文 |
|---|---|---|---|
| ![paired_comparison 疎](candidate-patterns/review/paired-comparison-sparse.png) | ![paired_comparison 標準](candidate-patterns/review/paired-comparison-standard.png) | ![paired_comparison 上限](candidate-patterns/review/paired-comparison-dense.png) | ![paired_comparison 長文](candidate-patterns/review/paired-comparison-long.png) |

## mapping

左右項目の一対一・一対多・多対多の対応漏れを確認する。

![mapping](candidate-patterns/mapping.png)

左右項目を関係が変わらない範囲で自動整列し、直接結線の交差数を最小化する。

| 疎 | 標準 | 上限 | 長文 |
|---|---|---|---|
| ![mapping 疎](candidate-patterns/review/mapping-sparse.png) | ![mapping 標準](candidate-patterns/review/mapping-standard.png) | ![mapping 上限](candidate-patterns/review/mapping-dense.png) | ![mapping 長文](candidate-patterns/review/mapping-long.png) |

## swimlane

担当レーン、工程段階、引き継ぎを同時に確認する。順方向の実線と差戻しの破線が混在する場合は、線種の凡例を自動表示する。

![swimlane](candidate-patterns/swimlane.png)

| 疎 | 標準 | 上限 | 長文 |
|---|---|---|---|
| ![swimlane 疎](candidate-patterns/review/swimlane-sparse.png) | ![swimlane 標準](candidate-patterns/review/swimlane-standard.png) | ![swimlane 上限](candidate-patterns/review/swimlane-dense.png) | ![swimlane 長文](candidate-patterns/review/swimlane-long.png) |

## sequence

関係者・機器間のメッセージを実行順に確認する。順序を重複表示する番号は付けず、左ガターには指定されたフェーズだけを表示する。

![sequence](candidate-patterns/sequence.png)

| 疎 | 標準 | 上限 | 長文 |
|---|---|---|---|
| ![sequence 疎](candidate-patterns/review/sequence-sparse.png) | ![sequence 標準](candidate-patterns/review/sequence-standard.png) | ![sequence 上限](candidate-patterns/review/sequence-dense.png) | ![sequence 長文](candidate-patterns/review/sequence-long.png) |

## 検証方法

`slidegen/generate_candidate_review.py`で24枚の回帰デッキを生成する。

```powershell
python slidegen/generate_candidate_review.py out\candidate_review.pptx
python slidegen/check_layout.py out\candidate_review.pptx
powershell -ExecutionPolicy Bypass -File render.ps1 -PptxPath out\candidate_review.pptx -OutDir out\png_candidate_review
python contact_sheet.py out\png_candidate_review 4 390
```

機械検証だけでは、余白の不自然さ、文字の過度な縮小、線の誤読、不自然な日本語改行は判定できない。
一覧画像と各ページの原寸画像を両方確認する。
