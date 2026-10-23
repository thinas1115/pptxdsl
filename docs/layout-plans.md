# 配置計算を描画から分離する

対象はrendererや入力検証を保守する開発者である。初回は次の「変更の入口」を読み、
寸法を変更するときは「共通設定とジャンル固有寸法」、提出前は「検証」を参照する。

## 変更の入口

ネットワーク図、担当フロー、プロトコル図、プログラム工程表は、
検証済みの構造入力を正規化し、図形を作らず配置計画を求めてから描画する。
計画は位置、接続経路、収容段階を保持するデータであり、`Presentation`や`slide.shapes`を受け取らない。

| type | 配置計画の入口 | 描画側の入口 |
|---|---|---|
| `nw_topology` | `network_layout.plan_network` | `training_renderers.s_network` |
| `swimlane_flow` | `swimlane_layout.plan_swimlane` | `candidate_renderers.s_swimlane` |
| `nw_protocol_flow` | `protocol_state_layout.plan_protocol_state_flow` | `training_renderers.s_protocol_state_flow` |
| `program_roadmap` | `timeline_layout.plan_program_roadmap` | `diagrams2.s_program_roadmap` |

座標や配線の修正は計画側へ、色、図形の作成、描画順の修正は描画側へ入れる。
入力の参照切れを座標計算で補わない。型・フィールド・件数は`schema_validation`で検査し、
合格した構成図の軸、ノード、コンテナ、チャネル、辺の参照を`diagram_contract.validate_diagram`で検査する。
収まるか、配線が成立するかは従来どおり`diagram_layout`が判定する。

`layout_fit.select_fit`は数値だけの候補、`select_payload_fit`は行高の配列などを含む型付き候補を選ぶ。
候補順は標準、裁量余白の圧縮、要素・文字の縮小とし、最小値でも不足する場合は`FitError`で停止する。
プロトコル図の`icon`段階はアイコン縮小を表す。黙って状態や辺を省略しない。

## 共通設定とジャンル固有寸法

標準ページ、余白、本文上下端は`layout_settings.PAGE`を正本とし、`generation_context.Theme`の既定値から参照する。
今回分離した4ジャンルのレール幅、本文内の予約領域、最小文字サイズも同モジュールに名前付きで集約した。
配色は従来のテーマを使う。入力JSONへ寸法を追加しない。

| 設定 | 既定値 | 扱い |
|---|---|---|
| 標準ページ・本文 | 13.333×7.5in、左右余白0.55in、本文1.58〜6.85in | ページ共通の基準 |
| ネットワーク図 | 標準本文幅、上部予約0.46in、右内側0.16in | セグメントと凡例の配置に使用 |
| 担当フロー | 左0.37in、幅12.59in、下端6.48in | 担当名レールと差戻し経路を持つ既存の広幅フレーム |
| 工程表 | 左0.72in、テーマ欄2.78in、時間軸9.09in | テーマ名と狙いを専用列へ、作業を時間軸へ分離 |
| プロトコル図 | 左レール1.42in、凡例高さ0.36in | トラック名と状態変化の列に使用 |

カードの枠付きパネル化と工程表のバー起点配置は受入時に撤回し、レビュー開始時の旧デザインへ戻した。
工程表は専用テーマ列と従来の時間軸幅を維持する。他の項目は分離前の寸法を保持している。
工程表の外枠11.87inを一般図解の11.89inへ丸めるような変更は行っていない。
同じ数値という理由で統合すると、ジャンル固有の接続や文字収容まで同時に変わる。
変更時は、共通の意味を持つかと影響範囲を先に確認する。

工程表のテーマ名と任意のgoalは左の専用列へ置く。作業名は各バーの中央へ置き、
名称を開始月に沿って移動させない。文字・線・ラベル幅の既定値も旧デザインへ戻している。
最小文字サイズでも収まらない場合は生成を停止する。

## 検証

配置モデルだけを確認するときは、図形を作らない次の試験を使う。

```powershell
python -m tests.test_layout_plans
python -m tests.test_diagram_contract
python -m tests.test_card_roadmap_design
python -m tools.quality.static_gate
```

試験は全4計画の入力非破壊性、決定性、幹線・一斉送信・停止点、差戻し経路、
状態の段階順と変化判定、工程の重なりとマイルストーン、圧縮・縮小・明示停止を確認する。
この計算境界はstrict型検査とformatterの対象である。

カードと工程表の15枚は`python -m tools.gallery.generate_card_roadmap_cases out/card-roadmap.pptx`で生成する。
説明カードは枠付きパネルを使わず、番号・見出し・本文を並べる旧配置を維持する。
KPIとの階層差、通常・lead・過密な工程表も一覧と原寸で確認する。
横幅拡張でのみ収容できた長い工程名の入力は短縮せず、旧幅での`FitError`を確認する負例として残す。

提出時は全テスト、対象ギャラリーの再生成、`check_layout`、実環境でのPNG化と目視確認まで行う。
分離だけの変更では、分離前後のPPTX内部の座標・文字・素材・描画順も比較する。
差がない場合でも、レンダリング条件と既確認画像の再利用根拠を検証記録に残す。
細則は[PNGの合否基準](../.agents/skills/pptxdsl/references/visual-acceptance.md)に従う。
このガイドで説明できない変更は、再現入力と期待する配置を添えてIssueへ記録する。

用語: 「配置計画」は描画前の確定値、「描画側」はその値から図形を作る処理、
「収容段階」は標準・圧縮・縮小のうち選択された設定を指す。
