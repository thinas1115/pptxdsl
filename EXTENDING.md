# EXTENDING.md — AI向け: renderer / エンジン拡張ガイド

対象読者: このリポジトリに**新しいスライド種別や図解機能を追加するAI**(Claude / Codex / Copilot 等)。
`content.json` を書くだけなら [AI_DECK_PROMPT.md](AI_DECK_PROMPT.md) + [CONTENT_SCHEMA.md](CONTENT_SCHEMA.md) を読む(このファイルは不要)。
既存rendererの配色・表紙・造形を変更する場合は [DESIGN_CUSTOMIZATION.md](DESIGN_CUSTOMIZATION.md) を読む。

このリポジトリは「生成→そのまま提出」を成立させるため、**AIとコードの分業線**を固定している:

- **AIが書くもの**: 離散的な構造(スライドの文言、type、グリッド仕様のセル名・メンバー列挙)
- **コードが決めるもの**: 座標・サイズ・余白・フォント・折り返し・描画順の**すべての数値**

拡張するときもこの線を動かさない。「contentに数値を書けば解決する」拡張は必ず設計ミス。

## レイヤーモデル — 何が再利用でき、何がジャンル専用か

拡張の設計判断はこの4層で考える。**再利用資産はL0/L2/L3であって、L1ではない。**

| レイヤー | 中身 | 再利用性 |
|---|---|---|
| L0 測定・描画プリミティブ | textfit(実測) / layout_fit(収容候補・停止) / add_text / add_rect / icon_node / add_arrow / arrow_label / container / route | ◎ 全typeで共有 |
| L1 レイアウト計算 | diagram_layout(グリッド図解) / org_layout(階層DAG) / timeline_layout(フェーズ・マルチトラック工程表) / image_slide(大判画像の比率維持・トリミング) / matrix(散布) / bullets・cards・twocol(縦詰め) / hub(放射) | **△ ジャンル内のみ** |
| L2 AI境界 | content.jsonスキーマ + validate_content + AI_DECK_PROMPT | ◎ typeが増えても同じ仕組み |
| L3 品質ゲート | check_layout + render.ps1 + contact_sheet + 目視ループ | ◎ 何を作っても同じゲート |

**L1に関する鉄則: レイアウトは1つの問題ではない。** グリッド配置・ツリー・放射・ガント・縦詰めは
別々の制約システムであり(graphviz/ELK/d3がジャンル別アルゴリズムの集合体なのと同じ理由)、
1つのエンジンに寄せようとするとエンジンの前提が壊れて複雑化だけが進む。

- **やること**: 新しいジャンルが必要になったら、L0部品の上に**小さな専用レイアウタ**を書く
  (ツリーなら50〜100行で足りる)。カタログの品目は「renderer関数」ではなく
  「ジャンル別レイアウタ」と考える。
- **やらないこと**: 既存レイアウタに別ジャンルを混ぜる拡張。例えば diagram_layout の機構
  (ポート計算・行間のラベル深さ・コンテナ外接)は「正方形アイコン+下ラベルのノードを
  グリッドに置く」前提に張り付いており、幅広ボックスや放射配置を入れるのは汎用化ではなく
  前提破壊になる(体制図・ハブ図をdiagram_layoutに統合しない判断の理由。#8参照)。
- **判断に迷ったら**: そのジャンルのレイアウトを2〜3枚、既存レイアウタの仕様語彙だけで
  書けるか小規模に実証する。書けないものが多ければ別レイアウタに分ける。

## アーキテクチャ

```
content.json ──→ validate_content.py ──→ generate_from_json.py ──→ PPTX
 (AIが作る)      (schema機械検証)          RENDER[type] で分岐         │
                                              │                        ▼
                 diagram type のみ:            │              check_layout.py (機械検知)
                 diagram_layout.py エンジン ←──┘              render.ps1 (PNG化)
                 (座標計算+自己検証)                          contact_sheet.py (俯瞰)
                                                              → 人間/AIの目視
```

| ファイル | 役割 |
|---|---|
| `slidegen/generate.py` | 基本renderer (title/bullets/cards/table/twocol/chart) + 共通ヘルパー + ページ定数 |
| `slidegen/diagrams.py` | hub renderer + 図解部品 (icon_node/add_arrow/arrow_label/container) |
| `slidegen/org_layout.py` | 体制図の階層DAG配置、直角配線、段階的収容 |
| `slidegen/diagrams2.py` | process/roadmap/program_roadmap/matrix renderer |
| `slidegen/timeline_layout.py` | 期間ラベル解決、重複作業の自動レーン割当、roadmap系の段階的収容 |
| `slidegen/image_slide.py` | 大判画像の比率維持・中央トリミング・右下影・段階的収容 |
| `slidegen/split_layout.py` | 左右50:50の合成領域と、対応済み子typeの独立収容 |
| `slidegen/diagrams3.py` | route() 直角配線 |
| `slidegen/diagram_layout.py` | 宣言的レイアウトエンジン (グリッド仕様→座標。diagram type の本体) |
| `slidegen/diagram_specs.py` | 公開diagramスキーマだけで書いた構成図の回帰試験用サンプル |
| `slidegen/validate_content.py` | content.json の生成前検証。typeごとの `_v_*` 関数 |
| `slidegen/generate_from_json.py` | content.json→PPTX。**新規資料の正式経路** |
| `slidegen/generate_patterns.py` + `content_patterns.py` | 全typeの検証ギャラリー |
| `slidegen/check_layout.py` | 生成済みPPTXの重なり・はみ出し機械検知 |
| `slidegen/textfit.py` | フォント実測 (游ゴシックをPillowで測る) |
| `slidegen/layout_fit.py` | 標準→裁量余白圧縮→要素縮小→明示停止の共通契約 |
| `slidegen/fetch_fluent_icons.py` / `extract_aws_icons.py` | アイコン素材の追加取得 (`slidegen/assets/icons/fluent/`・`slidegen/assets/icons/aws/` に同梱済み。条件は `slidegen/assets/CREDITS.md`。Fluentは要 svglib+reportlab+rlPyCairo) |

## 絶対に守る不変条件(全て実際の不具合から学んだもの)

1. **置く前に測る**: テキストは textfit.py で折り返し・必要高さを計算してから置く。
   PowerPointの自動調整に頼らない(頼った結果が「溢れ・重なり」の常習化)。
2. **収容順序を固定する**: 標準配置→裁量余白の圧縮→ジャンル固有要素の縮小→`FitError`で停止、
   の順を崩さない。必須間隔を先に潰したり、最小値へ黙って固定して描画したりしない。
3. **数値はrenderer/エンジンの中だけ**: content側スキーマに座標・サイズを要求するフィールドを
   作らない。ラベル衝突など個別調整が必要に見える場合も、入力へオフセットを追加せず
   レイアウタの候補探索と明示停止で解決する。
4. **均等分散しない**: 要素は自然高さ+一定gapで詰めて、やや上寄りに置く
   (均等分散は間延びして「AIっぽい」見た目になりやすい)。
5. **配線はウェイポイント明示**: プリセットのカギ線コネクタは折れ位置を制御できず
   ノードを貫通する。route() に点列を渡す。
6. **同じ行のノードは中心Yを完全に揃える**(1pxのズレが斜め線になる)。
7. **日本語runは set_run() 経由で作る**(lang="ja-JP" を自動設定。忘れると行頭に「、。」が来る)。
8. **同じ意味の値を2箇所で定義しない**: 行間計算と描画で別々の余白値を持つと
   「計算上は収まるのに実際は重なる」状態になる。
9. **エラーメッセージは日本語+対処方法つき**: このリポジトリのエラーは「生成AIに
   そのまま渡して直させる」前提。スタックトレースを見せない
   (validate_content.py / diagram_layout.py の既存メッセージの粒度に合わせる)。
10. **入力仕様を公開schemaへ限定する**: typeとフィールドは`CONTENT_SCHEMA.md`へ掲載し、
   validatorとrendererへ同時に登録する。diagramには名前付きサンプル参照を設けず、常にインライン仕様を渡す。
11. **カードは情報構造として使う**: 独立項目の比較・選択・事例提示にはカードを使ってよい。
   短い文を埋めるためだけの反復白箱や、タイムラインのフェーズ名など別構造に属する要素の
   カード化は避ける。カードを使う場合は、余白・文字階層・視覚的な焦点まで設計する。
12. **別エッジを接触させない**: 同一ノードからの分岐・同一ノードへの合流を除き、経路同士の
   重なり、T字接触、交差を描画前に検出して停止する。入出力を同じノード辺で往復させず、
   接続辺または専用チャネルを分離する。見た目で偶然つながる経路をcontent側の微調整で黙認しない。
13. **接続点はノード辺へ垂直にする**: `exit="bottom"`なら最初の区間は下向き、`enter="right"`
   なら最後の区間は左向きにする。接続直後に辺と平行な線を引くと、隣のノードやラベルへ接続した
   ように見える。viaが接線方向から始まる場合はPORT_STUBを挿入し、開始・終了方向を自己検証する。
14. **コネクタを先に描き、ラベルは実測外形だけをマスクする**: 上下線はアイコン外周から出し、
   ノード名・補足文の背後を直進させる。ラベルの塗りは背景色とし、実測文字幅・行高へ最小限の余白だけを
   加える。固定幅の大きな白箱で周囲の線を消さない。マスクを理由にアイコン貫通や不正経路を許可せず、
   `validate_edges()`を描画前に必ず通す。
15. **カタログ網羅を資料構成の目的にしない**: AIが新しい資料を作るときは、意味に合う最小限の
   typeだけを使う。既存typeに意味を損なわず収まらない場合は、簡略化する案と新rendererを追加する案を
   利用者へ示し、後者が選ばれた場合だけ拡張する。見た目の変化だけを理由にtypeを追加しない。
16. **split子typeは半幅で独立検証する**: `split`へ子typeを追加するときは、既存の全幅rendererを
   そのまま縮小呼び出ししない。割り当てられた`ContentArea`だけを使う半幅レイアウタを用意し、
   標準配置、余白圧縮、要素縮小、`FitError`の全段階をテストする。反対側への侵入、入れ子、
   未対応typeはvalidatorで生成前に拒否する。

## 共通部品カタログ(車輪の再発明をしない)

```python
# textfit.py — フォント実測
text_width_in(text, size_pt, weight="regular") -> float      # 1行の実測幅(インチ)
wrap_text(text, width_in, size_pt, weight="regular") -> list # 禁則込み折り返し
line_height_in(size_pt, spacing=1.3) -> float
fit_font_size(text, box_w, box_h, start_pt, min_pt=..., ...) -> (size, lines)

# layout_fit.py — renderer共通の収容契約
stepped(start, minimum, step) -> iterator
select_fit(renderer, available, candidates, *, guidance) -> FitResult
fit_text_or_raise(renderer, field, text, box_w, box_h, max_pt, *, min_pt, ...) -> (size, lines)
ensure_within(renderer, used, available, *, guidance) -> FitResult

# generate.py — ページ部品と定数
SLIDE_W=13.333, SLIDE_H=7.5, MARGIN=0.55, BODY_W=12.233, BODY_TOP=1.58, BODY_BOTTOM=6.85
NAVY / ACCENT / CORAL / TEXT / GRAY / LIGHT / ZEBRA / WHITE / CANVAS / RULE
add_text(slide, x, y, w, h, text, size, *, bold, color, align, anchor, spacing)
add_rect(slide, x, y, w, h, fill, *, line=None, round_=False)
header(slide, kicker, title, lead=None) -> ContentArea / footer(slide, page) / note_line(slide, note)
ContentArea.top / bottom / height / map_y(y)  # lead指定時だけ縮小された本文領域

# diagrams.py — 図解部品
icon_node(slide, cx, cy, img, title, sub)   # アイコン+下ラベル(外形0.62角)
add_arrow(slide, x1, y1, x2, y2, *, both, dash) / arrow_label(slide, cx, cy, text, w, size)
container(slide, x, y, w, h, label, color, dash)
ICON_R=0.31, EDGE_GAP=0.06

# diagrams3.py
route(slide, pts, *, dash, width)   # 直角折れ線+終端矢印

# diagram_layout.py
Layout(spec, reserve_note=False, content_area=None)  # グリッド仕様→座標(port/channel/route_edges/validate_edges)
render_diagram(slide, spec, note, content_area=None) # 描画一式
```

## 必須の収容ポリシー

新しいrendererは、描画前に次の候補をこの順で評価する。これは推奨ではなくマージ条件である。

1. **標準**: デザイン上の標準余白、標準文字サイズ、標準図形サイズ。
2. **裁量余白の圧縮**: 要素間gap、セルpaddingなど、読みやすさを損なわず縮められる余白だけ。
3. **ジャンル固有要素の縮小**: 本文フォント、行高、アイコンなどを、rendererが定めた最小値まで。
   画像・アイコンは縦横比を変えない。タイトル階層や必須の配線間隔を安易に縮めない。
4. **明示停止**: 最小値でも不足する場合は`FitError`を投げ、不足量と、文言短縮・項目削減・分割など
   利用者が取れる対処を日本語で示す。最小値のまま描画を続行しない。

`select_fit()`へ渡す候補順が、そのrendererの収容ポリシーになる。共通化するのは候補選択と停止の
契約までであり、圧縮可能な余白と縮小対象・最小値はジャンルごとに定義する。通常入力、余白圧縮が
必要な入力、要素縮小が必要な入力、最小値でも収まらない入力をそれぞれテストする。

## レシピA: 新しいスライドtypeを追加する

**8点セットを必ず揃える**(1つでも欠けたらマージ不可):

1. **renderer関数**: シグネチャは `def s_xxx(slide, spec, page)`。配置場所は内容で選ぶ
   (テキスト系→generate.py、図解系→diagrams*.py)。数値はすべて関数内に閉じ込める。
   冒頭で `area = header(slide, spec["kicker"], spec["title"], spec.get("lead"))` を呼び、
   本文のY座標・利用可能高さは必ず `area.top` / `area.bottom` / `area.height` から計算する。
   固定構図は `area.map_y()` で標準本文領域の座標を写像する。`BODY_TOP` / `BODY_BOTTOM` を直接参照して
   leadと本文を重ねる実装は不可。lead未指定時は標準配置を維持する。
2. **RENDER登録**: `generate_from_json.py` と `generate_patterns.py` の両方。
   同じtypeを使う別generatorがある場合は、その登録も更新する。
3. **validator**: `validate_content.py` に `_v_xxx` を追加し `VALIDATORS` に登録。
   件数上限は「最小設定でも収まらない値」を**生成して確かめてから**決める。
   標準設定で収まらないだけの入力をvalidatorで拒否せず、段階的収容へ回す。
   note を描画するなら `NOTE_TYPES` にも追加。`_TYPE_KEYS`へslide直下の許可キーを登録し、
   入れ子objectごとに`allow_keys()`を呼ぶ。未知フィールドを黙って無視するrendererはマージ不可。
4. **CONTENT_SCHEMA.md**: 必須/任意フィールド・制約・JSON例のセクションを追加。
5. **AI_DECK_PROMPT.md**: 対応済みtype一覧に追加。
6. **ギャラリー**: `content_patterns.py` に検証スライドを1枚追加
   (これが将来のリグレッション検知網になる)。
7. **収容ポリシー**: 標準→裁量余白圧縮→ジャンル固有要素縮小→`FitError`停止を実装し、
   各段階と最小値超過の過密入力テストを追加する。
8. **品質ゲート**(下記)を全部通し、全PNGを一覧と原寸で目視してから完了報告。

## レシピB: diagram エンジン(diagram_layout.py)を拡張する

構造マップ:

| 場所 | 役割 |
|---|---|
| モジュール定数 | AREA/GAP/MIN_SEG/LABEL_ROW_GAP/SLOT_PITCH 等。**コメントに設計理由と実不具合の記録あり。必読** |
| `Layout._auto_rows()` | 行位置の自動計算。行間=必須分(圧縮禁止)+裁量分(圧縮可)の2階建て |
| `Layout.port()` | ノードの矢印接続点(辺+オフセット) |
| `Layout.channel()` | 配線レーンの座標解決(列間/行間/コンテナ外側) |
| `Layout.route_edges()` | エッジ→直角経路。同一辺の多重エッジをSLOT_PITCHで分離 |
| `Layout.validate_edges()` | 意味レベル自己検証(接続辺への垂直性・境界貫通・逆走・非直角/短すぎる区間・別エッジの接触) |
| `render_diagram()` | コンテナ→配線→ノード(実測マスク付きラベル)→配線ラベルの順に描画 |

拡張の作法:

- **語彙を増やす方向で拡張する**: 新しい配置要件は「チャネル種類の追加」「ノード形状の追加」
  「コンテナ属性の追加」のような離散的な仕様語彙として設計する。
  仕様側に数値を書かせる逃げ道を作らない(「9.55と書きたくなったらエンジンの制約計算不足」)。
- **行間計算に影響する変更は必須分/裁量分の区別を維持する**: 必須分まで圧縮すると
  ラベルがアイコンに食い込む。上下線はアイコン外周からラベルマスクの背後を通すため、
  ラベル深さ自体を可視長として利用できる。ラベル下端から線を出す前提の直結線専用余白は設けない。
- **新しい描画パターンには対応する自己検証を足す**: check_layout.py は色・Z順・線同士の
  接触が見えない。エンジンが意味を知っている検証(validate_edges系)はエンジンに入れる。
  経路を追加したら、異なるエッジの重なり・T字接触・交差がなく、同一始点の分岐と同一終点への
  合流だけが許可されることを正常系・異常系の両方でテストする。
- **少量入力の位置基準も数値で固定する**: 収まることだけをテストせず、通常版とlead版の双方で
  本文上端からの開始位置、同一段の整列、下端へ張り付かないことを回帰テストする。
- **エラーは行数削減・sub削除・ラベル短縮など「AIが取れる対処」を必ず添える**。

## 品質ゲート(マージ条件)

```powershell
python slidegen/validate_content.py content.json                       # 新typeのschema検証
python slidegen/test_layout_fit.py                                     # 共通収容契約
python slidegen/test_ai_content_contract.py                            # AI入力の未知キー・任意表紙・未確定文言
python slidegen/test_generate_errors.py                                # JSON構文エラーの安全な診断
python slidegen/test_check_layout.py                                   # 壊れた表・グラフ・可変サイズPPTXの検出
python slidegen/test_sample_content_guard.py                           # 回帰サンプル文言の通常入力への混入防止
python slidegen/test_timeline_layout.py                               # roadmap系の期間解決・レーン割当・段階的収容
python slidegen/test_image_slide.py                                   # 大判画像の比率維持・crop・schema・収容停止
python slidegen/test_org_layout.py                                    # 体制図の階層DAG・配線・段階的収容
python slidegen/test_renderer_fit.py                                   # 通常・圧縮・縮小・停止
python slidegen/test_generalized_renderers.py                         # 件数・構造・種類の汎用化回帰
python slidegen/test_diagram_examples.py                               # 図解の配置・配線・縮小
python slidegen/test_lead_layout.py                                    # 全rendererのlead領域・停止
python slidegen/test_shrink_behavior.py                                # 大規模表・20ノード図の縮小発動
python slidegen/generate_from_json.py content.json out\deck.pptx       # 新規資料経路
python slidegen/generate_patterns.py out\pattern_gallery.pptx          # ギャラリー(全type)
python slidegen/generate_lead_patterns.py out\lead_gallery.pptx        # lead指定時の全type
python slidegen/generate_stress_patterns.py out\stress_gallery.pptx    # 段階的縮小の境界ケース
python slidegen\check_layout.py out\pattern_gallery.pptx               # exit 0 必須
python slidegen\check_layout.py out\lead_gallery.pptx                  # exit 0 必須
python slidegen\check_layout.py out\stress_gallery.pptx                # exit 0 必須
powershell -ExecutionPolicy Bypass -File render.ps1 -PptxPath out\pattern_gallery.pptx -OutDir out\png_pg
python contact_sheet.py out\png_pg                                      # → sheet.png を目視
```

- チェッカーの限界: グラフ内部のラベル衝突、白マスクラベルの枠線またぎ、線同士の交差、色/Z順は検知できない。
  **PNG目視は省略不可**。全ページを一覧とフル解像度(`render.ps1` 既定1600px)の両方で確認する。
- Pull RequestではWindows CIが全テストと主要デッキの生成・機械検査を実行する。CIが失敗した変更は
  マージせず、PowerPointでのPNG目視結果もPull Requestへ記録する。
- 出力先pptxをPowerPointで開いたままだと PermissionError。閉じてから実行。
- コンソールの日本語はcp932で文字化けすることがある。判定に使う出力は
  ファイルにリダイレクトしてから読む(**読めない出力を根拠に成功と報告しない**)。
- `slidegen/content*.py`と`slidegen/diagram_specs.py`の内容は回帰検証専用。ギャラリー生成器は
  `validate(..., allow_sample_content=True)`を明示し、通常の`content.json`生成経路へこの許可を渡さない。

## 既知の落とし穴

症状ごとの原因と対策は、次の実装箇所とその周辺コメントを参照する。

| 症状 | 原因と対策の場所 |
|---|---|
| 要素が間延びして不自然 | 均等分散をやめ自然高さパッキングに (generate.py s_bullets) |
| 行頭に「、。」 | set_run の lang="ja-JP" (generate.py) |
| ラベルが次行アイコンに食い込む | 行間の必須分/裁量分の分離 (diagram_layout._auto_rows) |
| 縦線がアイコン縁と平行に走る | top/bottom辺をSLOT_PITCHオフセット対象から除外 (route_edges) |
| 矢印が逆向きに見える | MIN_SEG_CLAMP と最終区間の向き検証 (_validate_segment_lengths) |
| 隣接ノード間の線が消える | 上下ポートをアイコン外周に置き、実測マスク付きラベルの背後へ通す (port/icon_node) |
| GAPを増やしても行間が広がらない | 圧縮モードでは裁量分が等比で潰される。必須分か構造別の自動余白を見直す |
| 2つの線が繋がって見える | 接続辺またはチャネルを分離し、validate_edgesの接触検出を通す (_validate_edge_contacts) |
| 線がどのノードへ接続したか曖昧 | 始点・終点をノード辺へ垂直にし、PORT_STUBと開始/終了方向検証を通す (_validate_segment_lengths) |
| コンテナ境界を線が貫通 | outside_container チャネル + validate_edges (diagram_layout) |
| 兄弟コンテナで縦余白が過大 | 入れ子マージンは1チェーンのみ積算 (chain_stack) |

## 開発フロー

Issue、ブランチ、品質検証、Pull Requestの扱いは[AGENTS.md](AGENTS.md)に従う。
この文書の8点セットと品質ゲートを満たしてから変更を提出する。
