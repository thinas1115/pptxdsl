# type選定ガイド

新しい資料のメッセージを、最小限の`type`へ割り当てるための判断基準。
この文書は`content.json`の値やスライド順を提示するサンプル集ではない。JSONのフィールド構造は
[CONTENT_SCHEMA.md](../CONTENT_SCHEMA.md)を参照する。

## typeカテゴリー

`type`は先に親カテゴリーで選ぶ。通常の業務資料はまず`Common`から選び、ネットワーク固有の物理/論理接続、フレーム/パケット構造、処理段階を説明する研修資料だけ`NW`を使う。

| category | type |
|---|---|
| Common | `title`, `bullets`, `cards`, `table`, `two_column`, `chart`, `image`, `process`, `program_roadmap`, `matrix`, `org`, `diagram`, `scope_boundary`, `decision_summary`, `paired_comparison`, `relationship_map`, `swimlane_flow`, `message_sequence`, `concept`, `config_lab`, `knowledge_check` |
| NW | `nw_topology`, `nw_protocol_flow`, `nw_frame_anatomy` |

## 参照情報の役割

| 情報 | 使う目的 | 内容作成への扱い |
|---|---|---|
| 資料要件・指定された情報源 | 主張、根拠、固有名詞、数値を決める | 内容の唯一の根拠 |
| `CONTENT_SCHEMA.md` | 許可フィールドとJSON構造を確認する | 値とページ順は流用しない |
| このガイド | メッセージに合う`type`を選ぶ | 選定基準だけを使う |
| `slidegen/content*.py`と`slidegen/diagram_specs.py` | rendererの回帰検証と目視QA | 題材、文言、数値、構成を参照しない |

## 選定手順

1. 資料要件から章立てと各章の到達目標を先に整理する。まだ`type`やページタイトルは決めない。
2. 各章へ必要なページの主題、結論、根拠を割り当てる。
3. ページタイトルは結論文にせず、主題を示す名詞句または短い疑問形へ変換する。結論は`lead`、
   根拠は本文へ分離する。文章型タイトルは回帰検証ギャラリー以外で使用しない。
4. 各ページの情報構造を、列挙、比較、推移、工程、期間、関係、階層、接続、画像のいずれかで捉える。
5. 次表から、その構造を過不足なく表せる最小限の`type`を選ぶ。同じ構造には同じ`type`を再利用する。
6. 適合する`type`がなければ、既存typeへの簡略化で失う情報と、新rendererで保持できる情報を示して
   利用者へ確認する。見た目が近いだけのtypeへ押し込まない。

## type一覧

| type | 選ぶ場面 | 選ばない場面 | 主な代替 |
|---|---|---|---|
| `title` | 表紙、章扉 | 本文の見出しだけを強調したい | 通常スライドの`title` |
| `bullets` | 手順、順序を持たない要点、完了状態付きタスクを文字中心で示す | 数値比較、工程、階層を表す | `table`、`process`、`org` |
| `cards` | 主結論と複数の独立した根拠、選択肢、事例、KPIを比較する | 読み順のある要点、情報が少ないだけ、工程や図の要素を並べる | `bullets`、`process`、`diagram` |
| `table` | 同じ評価軸で複数項目を比較・一覧する | 時系列の推移や関係を見せる | `chart`、`program_roadmap` |
| `two_column` | 2つの状態・案・観点を対比する | 3つ以上の選択肢や多軸比較 | `cards`、`table` |
| `chart` | 数値の大小、推移、構成を視覚比較する。`bar` / `column` / `line` / `stacked_bar` / `stacked_column`に対応 | 数値根拠がない概念比較 | `table`、`bullets` |
| `image` | 写真、画面、イラスト自体を主メッセージにする | 複数要素の関係を描く | `diagram`、`cards` |
| `process` | 直線工程、分岐、合流、差戻しを示す | 日付・期間が主役、組織階層を示す | `program_roadmap`、`org` |
| `program_roadmap` | 少数フェーズ、判定点、複数テーマの並行作業を時間軸で示す | 工程間の分岐・差戻しが主役 | `process` |
| `matrix` | 2軸上の位置関係や優先度を示す | 正確な値の比較や時系列 | `chart`、`table` |
| `scope_boundary` | 実施範囲と対象外を分け、成立条件を`lead`で示す | 2案の優劣や施策の比較 | `two_column`、`paired_comparison` |
| `decision_summary` | 2〜4個の論点を読み順に並べ、最終判断を`lead`で示す | 独立項目の比較や詳細な箇条書き | `cards`、`bullets` |
| `paired_comparison` | 2案を同じ評価軸で1行ずつ対応させて比較する | 評価軸が揃わない比較、3案以上の比較 | `table`、`two_column` |
| `relationship_map` | 課題と施策、要件と機能などの対応漏れ・多対多関係を示す | 工程順、システム境界、時系列を示す | `diagram`、`process` |
| `swimlane_flow` | 担当レーンと工程段階を同時に示し、引き継ぎを確認する | 厳密な時間間隔や機器間メッセージが主役 | `message_sequence`、`program_roadmap` |
| `message_sequence` | 関係者・機器間のメッセージを上から時系列に追う | 担当別の作業箱や分岐工程が主役 | `swimlane_flow`、`process` |
| `org` | 複数トップ、多段階層、複数親、横連携を示す | システムやデータの接続を示す | `diagram` |
| `diagram` | システム、クラウド、業務要素の接続・境界・データフローを示す | VLANなど論理セグメントと物理リンク種別の対応を示す | `nw_topology`、`process` |
| `concept` | 専門用語や判断基準を初めて定義し、要点と誤解しやすい境界を説明する | 複数案の比較、要素間の接続、単なる箇条書き | `bullets`、`diagram` |
| `nw_topology` | 物理機器、論理セグメント、Access・Trunk・L3接続を同時に示す | 一般的なシステム構成や業務フローを示す | `diagram`、`process` |
| `nw_protocol_flow` | 同じフレームやパケットの状態が、端末・装置内部・伝送区間ごとにどう変わるかを追跡する | 物理構成全体、単なるメッセージ順、ビット配置を示す | `nw_topology`、`message_sequence`、`nw_frame_anatomy` |
| `nw_frame_anatomy` | フレームやパケットのフィールド構成、ビット長、注目箇所を示す | 通信順序や機器間の流れを示す | `message_sequence`、`table` |
| `config_lab` | 設定例やコードと、その確認観点・検証コマンドを同じページで示す | 概念説明や工程だけを示す | `process`、`image` |
| `knowledge_check` | 選択式の設問と、対応する正答・解説を研修資料へ組み込む | 通常の要点整理や結論を示す | `bullets`、`decision_summary` |

### `nw_protocol_flow`の選択境界

- 同じ対象の属性が処理段階ごとに変わることを追う場合だけ使う。例は、タグの有無、送信元IP、暗号化状態、認証状態。
- 先に追跡単位を決め、L2なら「フレーム」、L3なら「IPパケット」のように`lead`と状態説明の用語を統一する。
- `stages`は場所または処理段階、`flows`は比較する属性、`states`は各段階での値または状態として分ける。
- 機器の接続関係が主役なら`nw_topology`、送受信順が主役なら`message_sequence`、ヘッダー構造が主役なら`nw_frame_anatomy`を選ぶ。
- `appearance`は色分け指定ではない。タグやヘッダーの付与、装置内部処理、異常状態を意味に沿って指定する。
- `appearance: "encapsulated"`では、付加されたタグまたはヘッダーを`encapsulation`へ短く明記する。VLAN以外の題材へ`TAG`を流用しない。

### `bullets` / `cards`で迷う場合

- 文を同じ重要度で並べる、順番を示す、完了状態を示す場合は`bullets`。
- 各項目に独立した見出しと説明があり、主結論と根拠または選択肢を比較する場合は`cards`。
- 要素間の接続や関係名を示す場合は、見た目を近づけず`diagram`または`org`を使う。
- 上記のどれにも収まらない情報構造は、新rendererを検討する。

## アンチパターン

- 対応typeを一通り使うために、同じ情報を別形式で繰り返す。
- ギャラリーと同じページ順、同じtype順、同じ項目数を採用する。
- ギャラリーの題材、見出し、本文、固有名詞、組織名、数値を資料要件へ関係なく流用する。
- 情報量が少ないという理由だけで`cards`を使う。
- 任意の`lead`、`note`、属性、日付、作成者を、値が指定されていないまま追加する。
- 結論・示唆・前提を本文下部の独立した帯やカードへ置く。必要な内容は`lead`へ書く。
- 適合するtypeがないのに、見た目が近い既存typeへ意味を変えて押し込む。
- 見た目を変えるためだけに、同じ情報構造へ別typeを割り当てる。

## 検証の範囲

通常の`validate_content.py`は、回帰検証サンプルにある正規化後14文字以上の日本語文言と一致する入力を拒否する。
空白・改行・句読点の差は同一として扱う。短い一般語や製品名の誤検知を避けるため、短文と英語だけの
名称は対象外である。言い換えたサンプル文脈や、資料要件に合わないページ構成までは機械判定できないため、
PNG目視時に内容の根拠とページごとの役割も確認する。
