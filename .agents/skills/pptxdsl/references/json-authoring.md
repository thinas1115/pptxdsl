# JSON成形

`content.json`を作成・修正するときに使用する。正確な許可フィールド、必須項目、件数制約はリポジトリルートの`CONTENT_SCHEMA.md`を正本とする。

## 成形手順

1. 資料全体の章立てと各章の到達目標を決める。
2. 各ページについて、主題、結論、根拠、情報構造を整理する。
3. `docs/type-selection-guide.md`に従って、情報構造を保てる最小限のtypeを選ぶ。
4. schemaに存在するフィールドだけでJSONへ落とす。資料要件にない任意フィールドは省略する。
5. `python slidegen/validate_content.py content.json`を実行し、エラー位置と理由に沿って直す。

## 守る境界

- `slides[*].title`は名詞句または短い疑問形にし、句点、改行、結論・因果・行動を言い切る文章を使わない。
- 結論・前提・読み方が必要な場合だけ`lead`へ1〜2行で書く。本文の繰り返しなら省略する。
- `meta.date`、`meta.organization`、`meta.author`、`meta.footer`、`note`、`actor`、`attribute`、`emphasis`は、必要性と値が資料要件にある場合だけ使う。
- 座標、寸法、余白、フォント、色、描画順、表の列幅、ラベル位置をJSONへ書かない。
- 表紙が必要な場合だけ`title`を使う。typeは同梱のschemaにあるものだけを選び、ギャラリーのページ順やtype順を流用しない。
- 章区切りは`section_divider`を使い、章番号・章ラベルを`kicker`に書く。自動採番を前提にしない。
- システムやネットワーク図のノード・エッジには意味だけを書き、配置はrendererへ任せる。存在しないアイコン名を発明しない。
- 画像typeでは、実在して利用可能なリポジトリ相対パスだけを書く。追加素材の出典とライセンスは`slidegen/assets/CREDITS.md`へ記録する。
- `tests/fixtures/gallery/content*.py`と`tests/fixtures/gallery/diagram_specs.py`から題材、文言、数値、ページ構成をコピーしない。

## 収容エラーの直し方

優先順位は、文言短縮、項目削減、ページ分割、必要なら新rendererの検討とする。座標指定、最小値を下回る文字縮小、意味の合わないtypeへの置換で回避しない。
