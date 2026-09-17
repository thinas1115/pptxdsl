# Type選定

詳細な選定表は`docs/type-selection-guide.md`を正本とする。この文書は迷いやすい境界だけを補う。

## 選び方

見た目ではなく、読み手が追う関係で選ぶ。

- 文字中心の列挙は`bullets`。独立した根拠、選択肢、事例、KPIの比較は`cards`。
- 同じ評価軸で一覧するなら`table`。2案を行単位で対応させるなら`paired_comparison`。2つの状態や観点を大きく対比するなら`two_column`。
- 直線・分岐・差戻しを含む工程は`process`。担当レーンも必要なら`swimlane_flow`。関係者や機器間の送受信順が主役なら`message_sequence`。
- 期間と並行作業が主役なら`program_roadmap`。階層は`org`。要素間の接続や境界は`diagram`。
- 用語や判断基準の初出説明は`concept`。設定例と確認観点は`config_lab`。選択式の理解確認は`knowledge_check`。
- 物理機器と論理セグメント、Access・Trunk・L3接続を同時に示すなら`nw_topology`。
- 同一フレームまたはパケットの段階別状態変化は`nw_protocol_flow`。フィールド構造は`nw_frame_anatomy`。

## 選ばない理由も確認する

- 情報量が少ないだけで`cards`へしない。
- 見た目を変えるためだけに別typeへしない。
- 時系列、階層、接続、比較の意味を、単純な箇条書きへ落とさない。
- 適合するtypeがなければ、無理に近いtypeへ押し込まず利用者へ選択肢を示す。

選定後は`CONTENT_SCHEMA.md`の該当type節だけを読み、必須フィールドと件数制約を確認する。
