# content.jsonの意味検証と記述方針

`content.json`を書く人・生成AI向けの参照ガイド。最初に「資料の内容と見出し」を読み、
以降は使用するtypeだけを確認する。フィールド、型、件数、選択肢は自動生成の
[構造契約](../CONTENT_SCHEMA.md)を参照する。

## 資料の内容と見出し

文言・数値・ページ順は資料要件と情報源から新規に作る。回帰ギャラリーの文章は使わない。
`<...>`の入力欄や`TBD`・`TODO`・`要確認`・`未定`などを残すと検証エラーになる。
ギャラリー生成だけは`validate(..., allow_sample_content=True)`でサンプル保護と見出し方針を解除する。
型、件数、素材、参照の検証は解除しない。

`title`は名詞句または短い疑問形にする。疑問符・句読点・改行や述語で終わる文章は使わず、
結論・因果・行動は`lead`または本文へ書く。表紙の`subtitle`には対象範囲・目的を記す。
`title_nominal_review`は「こたつ」のような名詞の語尾誤検知に限る例外で、現在のタイトルと
名詞と判断した理由を記す。別のタイトルへの使い回しや文章型タイトルの許可には使えない。

`lead`は本文の読み方、`note`は対応type内の補足、`footnote`は全type共通の脚注。
必要な内容がない任意項目は省く。座標・余白・フォント・描画順はrendererが決めるため、JSONには書かない。
表紙や章扉は必要な位置にだけ置く。`section_divider.kicker`は指定値を表示し、章番号を自動補完しない。

## 画像とアイコンは同梱済みの素材から選ぶ

画像は`slidegen/assets/`基準の相対パスで、実在する有効なPNG/JPEGを指定する。
絶対パスやassets外への移動は拒否する。`image_compare`は左右を個別に検証する。
`fit=contain`は画像全体を保持し、`cover`は領域を埋めて周辺をトリミングする。
`alt`は代替説明、左右の`label`は比較軸として使い、レイアウト調整の文字を入れない。

アイコンのパスを推測しない。同梱ファイルを確認するか、開発時は
`python -m tools.assets.fetch_fluent_icons --list`で一覧を確認する。
AWSサービスは対応するAWS公式アイコンを無改変で使う。機能名だけの表示では`service`でAWSサービスを特定する。
たとえばAppSyncのEvent APIは`service: "appsync"`と`icons/aws/appsync.png`の組み合わせ。
人・組織・端末・一般概念にはFluentを使える。詳細は[AWSアイコンの選定](aws-icon-selection.md)を参照する。
追加素材の出典と利用条件は[素材の帰属表示](../slidegen/assets/CREDITS.md)へ記す。

## 基本typeで混同しやすい指定

| type | 値の意味と追加条件 |
|---|---|
| bullets | `checked`はchecklistだけ。旧`[本文, null]`は1.xで受理するが非推奨で、2.0.0で終了する |
| cards | metricsでは`value`が必須で、`emphasis`もmetricsだけ。editorialは独立した項目の説明に使う |
| table | 各行はcolumnsと同じセル数。空セルは許可。note_linkにはnoteも必要で、URLは認証情報・空白のない完全なHTTPS URL |
| chart | 各系列の値はcategoriesと同数。真偽値・NaN・Infinityは数値として受理しない。合計から百分率を推測せず、単位はnumber_formatで明示する |
| matrix | quadrantsを省く場合はtarget_labelが必須。象限ラベルの順序は左下・右下・左上・右上 |
| references | 同じページ内でidとURLを重複させない。URLは認証情報・空白のない完全なHTTP/HTTPS URL |
| config_lab | codeは構造契約の行数制限内に収める。checksはコードから読み取れる確認結果にする |
| knowledge_check | answerはoptionsの0始まりindex。questions/answersで同じ設問と選択肢を使う |

## 異なる構造を左右で読み合わせる

異なる構造を同じページで読み合わせる場合は[split](split-layout.md)を使える。
左右の本文は独立して検証・収容し、共通の見出し・注記・脚注は親だけに指定する。
未対応の組み合わせや再帰を避け、半幅で収まらない場合は内容を減らすかページを分ける。

## 工程とロードマップは位置の意味まで検証する

`process`はstepsかflowの一方だけを使う。stepsのemphは工程の0始まりindex。
actorとattributeは同じ工程に併記しない。flowは全ノードをlevelsへ一度ずつ配置し、
定義済みノード間だけを接続する。自分自身や同じ接続の重複は不可。
同じ列・前の列へ戻す接続には`kind: "feedback"`を付ける。

`program_roadmap`の期間ラベルは重複不可。start/endは期間ラベルまたは期間位置を指定し、
期間内で開始が終了を超えないようにする。milestoneは同じテーマの作業期間内の位置を指定する。
期間位置は四分の一単位で表現する。作業の合計上限は構造契約の`x-maxActivities`で管理する。

## 接続図はIDと向きを確認する

| type | 参照・重複・方向の条件 |
|---|---|
| relationship_map | 左右それぞれのidは一意。links.fromはleft_items、toはright_itemsを参照し、対応を重複させない |
| swimlane_flow | lane/stage/stepのidと工程番号は一意。stepsは定義済みlane/stageを参照する。同じセルの工程数を制限し、前フェーズへ戻る線はfeedback |
| message_sequence | participant/messageのidは一意。messagesは定義済みparticipantを参照する。phasesは定義済みmessageの順序に沿ってfrom/toを指定する |
| org | 全ノードをlevelsへ一度ずつ配置する。reportingは上位から下位へ接続し、線上labelはadvice/collaborationだけ。自己接続・同一関係の重複は不可 |
| nw_topology | lane/column/nodeのidは一意。ノードのcolumn/lanesと接続先は定義済みIDを使う。同じ所属・列の機器数を制限し、向きを問わず同じ接続を重複させない |
| nw_protocol_flow | stageのidと正規化後のflow.labelは一意。各flow.statesは全stageを一度ずつ指定する。encapsulationはappearance=encapsulatedだけで必須 |
| nw_frame_anatomy | fieldのidは同じframe内で一意。annotations.fieldはそのframe内の定義済みfieldを参照する |
| aws_vpc_layout | AZ・subnet・resource・externalのidは全体で一意。flowsはresource/externalだけを参照し、自己接続・同じ接続の重複は不可 |

nw_topologyのtrunkには複数lane、access/broadcast/blockedには単一laneを指定する。
通常の接続で運ぶlaneは両端の機器が所属するものに限る。
blockedは接続元だけが所属し、接続先が所属しないlaneを示す。

## diagramの名前付き参照

nodesのcol/rowはcols/rowsの名前を参照する。containers.membersにはノード名か
`@コンテナ名`を指定する。edgesのfrom/toも同じ参照形式で、viaは定義済みchannels名の配列。
コンテナを始点にする場合だけfrom_rowで接続行を指定し、それ以外ではfrom_rowを書かない。

channelsは`[種類, 基準]`。left_of_col/right_of_colは列名、above_row/below_rowは行名を参照する。
outside_containerの基準は`[コンテナ名またはノード名配列, 辺]`で、名前は定義済みのものを使う。
領域や余白はエンジンが決めるため、area・pad・pad_xや数値のラベル位置は入力できない。

## 廃止項目は表示を失わないように移行する

下部注記帯のassumptions/takeawayはleadへ移す。image.captionもleadへ移し、
image.sourceの権利情報はCREDITSへ記す。旧orgのtop/pm/teams/externalは
org.nodes/levels/edgesへ置き換える。diagram.specによるサンプル図の名前参照は使わず、構造をインラインで書く。

## エラーと提出品質の確認

`python slidegen/validate_content.py content.json`でスライドとフィールドの位置を確認する。
構造が壊れたスライドは参照・素材の検証へ渡さないため、まず構造エラーを直して再実行する。
合格は入力契約の確認であり、内容の事実性や収容可能性の保証ではない。
生成後はレイアウト検査、利用環境でのPNG化、全ページの一覧・原寸確認まで行う。
解決できない場合は、個人情報と絶対パスを除いた入力とエラーを添えてリポジトリのIssueへ報告する。

## 用語

| 用語 | 意味 |
|---|---|
| 構造検証 | フィールド、型、必須条件、件数、選択肢の検査 |
| 意味検証 | ID参照、素材の実在、値同士の関係や記述方針の検査 |
| renderer | 入力から配置・描画を決めるtype別の実装 |
| backend | PowerPointやLibreOfficeなど、PPTXを画像へ描画する実行系 |
