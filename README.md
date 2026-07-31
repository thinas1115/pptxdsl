# pptxdsl

「生成 → 検証 → そのまま提出」までを、決定論的に実行するPowerPoint生成パイプライン。

![パイプライン全体像](docs/pipeline-overview.png)

生成AIまたは人間が、スライドの内容と構造を`content.json`へ記述します。
座標・余白・文字サイズ・配線はrendererが決定し、PPTXを毎回同じ結果で生成します。

## 出力例

対応する14種類のtypeを、23枚の出力例で確認できます。

![TYPE別パターンギャラリー](docs/pattern-gallery-by-type.png)

PowerPointで確認・編集できる実物は
[パターンギャラリー](examples/gallery/pattern_gallery.pptx)に収録しています。

## セットアップ

```powershell
git clone https://github.com/thinas1115/pptxdsl.git
cd pptxdsl
python -m pip install -r requirements.txt
```

- Python 3.10以上、Windows、游ゴシックを前提とします。
- 生成結果を再現できるよう、直接・間接依存のバージョンを`requirements.txt`へ固定しています。
- PPTXの生成にPowerPointは不要です。PNG化と目視確認にだけ使用します。
- AWS・Fluentアイコンは`slidegen/assets/icons/`へ同梱済みです。

アイコンの出典とライセンスは[クレジット](slidegen/assets/CREDITS.md)を参照してください。

## 使い方

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
powershell -ExecutionPolicy Bypass -File render.ps1 -PptxPath out\deck.pptx -OutDir out\png
python contact_sheet.py out\png
```

`generate_from_json.py`は生成前にschemaを検証し、不正な入力ではPPTXを生成しません。
エラーが出た場合は、表示された`slides[番号] (type=種別)`の内容を修正して再実行します。

PowerPointを利用できる場合は、`out\png\sheet.png`の一覧と各ページの原寸画像を確認してください。
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
| `slidegen/` | renderer、レイアウトエンジン、validator、テスト |
| `slidegen/assets/icons/` | 同梱済みのAWS・Fluentアイコン |
| `slidegen/assets/images/` | 本文で使用する画像 |
| `slidegen/assets/cover/` | 利用者が差し替える表紙背景画像 |
| `out/` | PPTX、PNG、検証結果などの生成物。Git管理外 |

実行時の生成物はすべて`out/`へ保存します。`docs/`には保守対象の説明文書と、
その文書から参照する掲載素材だけを置きます。

`examples/gallery/pattern_gallery.pptx`はclone後に人間が確認する配布用サンプルです。
新しい資料を作る生成AIには渡さず、内容・文言・ページ順の参考資料にも使用しません。

## ライセンス

本リポジトリのオリジナルコードおよび文書は、[MIT License](LICENSE)で提供します。

`slidegen/assets/`以下には、AWS Architecture Icons、Fluent UI System Icons、商標、ロゴなど、
第三者が権利を持つ素材が含まれます。これらの素材には本プロジェクトのMIT Licenseを適用せず、
各素材の利用条件が適用されます。出典と条件は[第三者素材に関する通知](THIRD_PARTY_NOTICES.md)と
[クレジット](slidegen/assets/CREDITS.md)を参照してください。

本ソフトウェアを使用して利用者が作成した`content.json`やPPTXには、本プロジェクトの
MIT Licenseを適用しません。ただし、出力へ含まれる第三者素材には各素材の利用条件が適用されます。
