# pptxdsl

「生成 → 検証 → そのまま提出」までを、決定論的に実行するPowerPoint生成パイプライン。

![パイプライン全体像](docs/pipeline-overview.png)

生成AIまたは人間が、スライドの内容と構造を`content.json`へ記述します。
座標・余白・文字サイズ・配線はrendererが決定し、PPTXを毎回同じ結果で生成します。

## 出力例

対応する27種類のtypeを、38枚の出力例で確認できます。

![TYPE別パターンギャラリー](docs/pattern-gallery-by-type.png)

PowerPointで確認・編集できる実物は
[パターンギャラリー](examples/gallery/pattern_gallery.pptx)に収録しています。
研修資料の構成例は[VLAN基礎研修](examples/training/vlan/README.md)で確認できます。
[AWSネットワーク資料の入力例](examples/training/aws-network/README.md)も収録しています。

## セットアップ

```powershell
git clone https://github.com/thinas1115/pptxdsl.git
cd pptxdsl
python -m pip install -r requirements.txt
```

- Python 3.10以上を前提とします。Windowsでは游ゴシック、非Windowsでは`fontconfig`から検出できる
  日本語sansフォントを使用します。Noto Sans CJKを推奨します。
- 生成結果を再現できるよう、直接・間接依存のバージョンを`requirements.txt`へ固定しています。
- PPTXの生成にPowerPointは不要です。PNG化と目視確認にだけ使用します。
- AWS・Fluentアイコンは`slidegen/assets/icons/`へ同梱済みです。

アイコンの出典とライセンスは[クレジット](slidegen/assets/CREDITS.md)を参照してください。

## 使い方

| 利用形態 | 向いている用途 | 実行に使うもの |
|---|---|---|
| Skill | このリポジトリ内で資料を作る、rendererや素材も編集する | `.agents/skills/pptxdsl/`とcloneした本処理 |
| Plugin | 任意の作業領域で資料を作る、他の利用者へ配布する | インストール済みPluginに同梱されたSkill・本処理・素材 |

どちらも、資料要件と情報源の確認、`content.json`の設計、PPTX生成、機械検証、PNG化、
全ページの目視QA、修正後の再確認までを1つの作業として実行します。

### Skillとして使う

1. [セットアップ](#セットアップ)を完了し、Codexでこのリポジトリのルートを開く。
2. 新しいタスクで`$pptxdsl`を明示して依頼する。Codexは作業ディレクトリからリポジトリルートまでの
   `.agents/skills/`を探索するため、別の場所へSkillをコピーする必要はない。

```text
$pptxdsl
次の要件と情報源から、目視確認済みのPPTXを作成してください。

- テーマ: AWS AppSyncの設計と運用
- 想定読者: 導入を検討するアプリケーション開発者
- 目的: 採用判断に必要な構成、制約、費用を説明する
- 必須内容: Pipeline resolver、Merged API、認証、監視、料金
- 情報源: ここにURLまたは入力ファイルを書く
- 枚数目安: 30〜40枚
```

Skillは[pptxdsl Skill](.agents/skills/pptxdsl/SKILL.md)を入口に、必要なスキーマ、type選定、
renderer、検証手順を読み込みます。通常は利用者が生成コマンドを個別に指示する必要はありません。
CodexでSkillが候補に出ない場合は、`/skills`で一覧を確認するか、`$`に続けて`pptxdsl`を検索します。

### Pluginとして使う

Plugin版はSkill・本処理・素材を同梱するため、利用時にこのリポジトリをcloneする必要がありません。
Python 3.10以上、日本語フォント、PowerPointまたはLibreOfficeなどのレンダリング手段は実行環境側に必要です。

#### 1. 配布物を作る

リポジトリを持つ作成者が、未使用の出力先を指定してビルドします。

```powershell
python -m tools.plugin.build --output-dir out\plugins
```

インストール対象は`out/plugins/pptxdsl/`です。`out/plugins/pptxdsl-0.1.0.zip`を渡す場合は、
展開後に`plugin.json`が直下にあるフォルダをPluginルートとして使います。

#### 2. Codexへ登録・インストールする

Codexの新しいタスクで、ビルド済みPluginフォルダを指定して依頼します。

```text
$plugin-creator
このビルド済みpptxdsl Pluginを個人marketplaceへ登録してください。
Pluginフォルダ: out/plugins/pptxdsl
```

登録後、Plugins Directoryの個人marketplaceから`pptxdsl`をインストールします。
CLIを使う場合は、実際のmarketplace名を指定します。標準の個人marketplace名は`personal`です。

```text
codex plugin add pptxdsl@personal
```

標準の個人marketplaceは暗黙に検出されるため、`codex plugin marketplace add`は不要です。
インストール後は新しいタスクを開始し、Pluginに含まれるSkillを明示して依頼します。

```text
$pptxdsl
添付資料と以下の要件から、目視確認済みのPPTXを作成してください。
```

ChatGPTでは`@pptxdsl`、Codexでは`$pptxdsl`で明示選択できます。目的に合う依頼であれば、
名前を付けずに依頼して自動選択させることもできます。登録、更新、ChatGPT Workでの導入、
隔離実行の確認方法は[Pluginガイド](docs/plugin.md)を参照してください。

OpenAI公式の基本仕様は[Skills](https://developers.openai.com/docs/build-skills)と
[Pluginパッケージ](https://developers.openai.com/plugins/build/plugins)を参照してください。

## CLIで直接使う

AIエージェントを使わず、自分で`content.json`を作成して生成・検証する場合の手順です。

### 1. content.jsonを作る

生成AIに作らせる場合:

1. [AI_DECK_PROMPT.md](AI_DECK_PROMPT.md)の入力欄へ、テーマ・想定読者・目的・必須内容・情報源・枚数目安を記入する。
2. 記入した依頼文、[CONTENT_SCHEMA.md](CONTENT_SCHEMA.md)、[type選定ガイド](docs/type-selection-guide.md)を生成AIへ渡す。
3. 返されたJSONを、プロジェクト直下の`content.json`として保存する。

手動で作る場合は、[CONTENT_SCHEMA.md](CONTENT_SCHEMA.md)に沿って`content.json`を記述します。

入力時は次の4点だけ先に確認してください。

- `content.json`は資料ごとに新規作成し、過去資料や回帰ギャラリーの文言を残さない。
- 不明な任意項目は、仮文言や空文字を入れずフィールド自体を省略する。
- 資料の情報構造に合うtypeだけを使い、対応typeがなければ生成AIから利用者へ確認する。
- 座標・余白・文字サイズなどのレイアウト値は記述しない。

typeごとのフィールド、件数、構成図、画像、`lead`の指定方法は
[CONTENT_SCHEMA.md](CONTENT_SCHEMA.md)に集約しています。

### 2. 生成・検証する

```powershell
python slidegen/generate_from_json.py content.json out\deck.pptx
python slidegen/check_layout.py out\deck.pptx
python .agents/skills/pptxdsl/scripts/render_preview.py --probe
python .agents/skills/pptxdsl/scripts/render_preview.py out\deck.pptx out\png
python contact_sheet.py out\png
```

`generate_from_json.py`は生成前にschemaを検証し、不正な入力ではPPTXを生成しません。
エラーが出た場合は、表示された`slides[番号] (type=種別)`の内容を修正して再実行します。

`out\png\sheet.png`の一覧と各ページの原寸画像を確認してください。レンダリング補助スクリプトは、
WindowsではPowerPointを優先し、それ以外ではLibreOfficeとPDF画像化手段の組み合わせを探索します。
機械検証だけでは、文字の読みやすさ、内容の正確性、余白や配線の印象までは判断できません。

Pull Requestと`main`へのpushでは、Windows CIがPython 3.10・3.13の全テスト、主要デッキ生成、
`check_layout.py`を実行します。PowerPointによるPNG化と目視確認はCIで代替せず、提出前に実施します。

## 目的別ガイド

| やりたいこと | 参照先 |
|---|---|
| `content.json`のフィールドと制約を確認する | [CONTENT_SCHEMA.md](CONTENT_SCHEMA.md) |
| 内容に合うtypeを選ぶ | [docs/type-selection-guide.md](docs/type-selection-guide.md) |
| 生成AIへの依頼文を作る | [AI_DECK_PROMPT.md](AI_DECK_PROMPT.md) |
| 対応レイアウトを人間が見て確認する | [サンプルスライドギャラリー](examples/gallery/pattern_gallery.pptx) |
| 新しいtypeやレイアウタを追加する | [EXTENDING.md](EXTENDING.md) |
| 配色・フォント・表紙デザインを変更する | [DESIGN_CUSTOMIZATION.md](DESIGN_CUSTOMIZATION.md) |
| 表紙・フッターだけを利用者別に変更する | [docs/cover-footer-customization.md](docs/cover-footer-customization.md) |
| rendererと品質ゲートの設計を確認する | [docs/architecture.md](docs/architecture.md) |

## 主なディレクトリ

| パス | 内容 |
|---|---|
| `.agents/skills/pptxdsl/` | AIエージェント向けのPPTX作成Skill |
| `slidegen/` | renderer、レイアウトエンジン、validator、PPTX検査の本処理 |
| `slidegen/data/` | 通常入力へのサンプル混入を防ぐ生成済み辞書 |
| `tests/` | 契約・回帰テスト。全件実行は`python -m tests` |
| `tests/fixtures/gallery/` | 回帰専用の内容データ・構成図仕様 |
| `tools/gallery/` | 回帰ギャラリーの生成・検証・掲載画像作成 |
| `tools/assets/` | 素材の取得・点検。通常生成には不要 |
| `tools/plugin/` | Skillと本処理を同梱するPlugin配布用ビルド |
| `plugins/pptxdsl/` | Pluginの表示情報・配布metadataの正本 |
| `slidegen/assets/icons/` | 同梱済みのAWS・Fluentアイコン |
| `slidegen/assets/images/` | 本文で使用する画像 |
| `slidegen/assets/cover/` | 利用者が差し替える表紙背景画像 |
| `out/` | PPTX、PNG、検証結果などの生成物。Git管理外 |

実行時の生成物はすべて`out/`へ保存します。`docs/`には保守対象の説明文書と、
その文書から参照する掲載素材だけを置きます。

`examples/gallery/pattern_gallery.pptx`はclone後に人間が確認する配布用サンプルです。
新しい資料を作る生成AIには渡さず、内容・文言・ページ順の参考資料にも使用しません。

テストや開発ツールはリポジトリルートからmoduleとして実行します。
単体実行例は`python -m tests.test_check_layout`、ギャラリー生成は
`python -m tools.gallery.generate_patterns out/pattern_gallery.pptx`です。
通常のJSON生成・検証は従来のファイル実行とmodule実行の両方に対応します。

## ライセンス

本リポジトリのオリジナルコードおよび文書は、[MIT License](LICENSE)で提供します。

`slidegen/assets/`以下には、AWS Architecture Icons、Fluent UI System Icons、商標、ロゴなど、
第三者が権利を持つ素材が含まれます。これらの素材には本プロジェクトのMIT Licenseを適用せず、
各素材の利用条件が適用されます。出典と条件は[第三者素材に関する通知](THIRD_PARTY_NOTICES.md)と
[クレジット](slidegen/assets/CREDITS.md)を参照してください。

本ソフトウェアを使用して利用者が作成した`content.json`やPPTXには、本プロジェクトの
MIT Licenseを適用しません。ただし、出力へ含まれる第三者素材には各素材の利用条件が適用されます。
