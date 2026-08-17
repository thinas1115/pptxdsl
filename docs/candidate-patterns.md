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

## レビュー観点

各typeは採点値ではなく、次の観点を満たしているかを画像とテストで確認する。

| 観点 | 受入条件 |
|---|---|
| 情報階層 | 見出し、`lead`、本文、注記の優先順位を一目で判別できる |
| 余白 | 少数入力でも小さく沈まず、高密度入力でも詰め込み感がない |
| 文字組み | 不自然な単語分割や過度な縮小がなく、読み順が明確である |
| 整列 | 見出し、本文、接続点、線の基準位置が揃っている |
| 線と境界 | 接続先を誤読せず、異なる線種には凡例がある |
| 汎用化 | 疎、標準、上限、長文の4条件で構造と視認性を維持する |
| 安定性 | 最小値でも収まらない入力は、崩れたまま出力せず`FitError`で停止する |

この受入条件は下記24ケースとvalidatorが許可する入力範囲へ適用する。未知の用途や入力上限を超える
情報量まで保証するものではないため、用途が合わない場合は別typeまたはスライド分割を選ぶ。

## scope_boundary

実施範囲と対象外を整理する。成立条件や前提が必要な場合は`lead`へ記載する。

![scope](candidate-patterns/scope.png)

| 疎 | 標準 | 上限 | 長文 |
|---|---|---|---|
| ![scope 疎](candidate-patterns/review/scope-sparse.png) | ![scope 標準](candidate-patterns/review/scope-standard.png) | ![scope 上限](candidate-patterns/review/scope-dense.png) | ![scope 長文](candidate-patterns/review/scope-long.png) |

## decision_summary

2〜4個の論点を1枚に要約する。最終判断が必要な場合は`lead`へ記載する。

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

## relationship_map

左右項目の一対一・一対多・多対多の対応漏れを確認する。

![mapping](candidate-patterns/mapping.png)

左右項目を関係が変わらない範囲で自動整列し、直接結線の交差数を最小化する。

| 疎 | 標準 | 上限 | 長文 |
|---|---|---|---|
| ![mapping 疎](candidate-patterns/review/mapping-sparse.png) | ![mapping 標準](candidate-patterns/review/mapping-standard.png) | ![mapping 上限](candidate-patterns/review/mapping-dense.png) | ![mapping 長文](candidate-patterns/review/mapping-long.png) |

## swimlane_flow

担当レーン、工程段階、引き継ぎを同時に確認する。順方向の実線と差戻しの破線が混在する場合は、線種の凡例を自動表示する。

![swimlane](candidate-patterns/swimlane.png)

| 疎 | 標準 | 上限 | 長文 |
|---|---|---|---|
| ![swimlane 疎](candidate-patterns/review/swimlane-sparse.png) | ![swimlane 標準](candidate-patterns/review/swimlane-standard.png) | ![swimlane 上限](candidate-patterns/review/swimlane-dense.png) | ![swimlane 長文](candidate-patterns/review/swimlane-long.png) |

## message_sequence

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
