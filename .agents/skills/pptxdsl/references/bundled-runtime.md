# Release配布の実行環境

GitHub ReleaseのSkill ZIPを展開した場合、またはPluginとしてインストールされた場合に使用する。
Skillフォルダ内の`project/`へPPTX生成コード、素材、スキーマ、type選定ガイド、依存一覧、ライセンスを同梱している。
clone、GitHub認証、MCP接続は不要。資料作成のためにリポジトリを開発・変更しない。

## インストール先と作業領域

- 読み込んだ`SKILL.md`の場所からSkillフォルダを特定する。インストール先の固定パスを推測しない。
- 手順内の`CONTENT_SCHEMA.md`、`AI_DECK_PROMPT.md`、`docs/`、`slidegen/`は`project/`内を参照する。
- 利用者の作業領域に`content.json`と`out/`を作る。インストール先へ成果物やローカル設定を保存しない。
- 以下の`<Skill>/scripts/run.py`を実際のスクリプトパスへ置き換え、利用者の作業領域から実行する。
  参照文書にあるリポジトリ相対のコマンドも、Release配布版ではこの入口へ読み替える。

```text
python <Skill>/scripts/run.py validate content.json
python <Skill>/scripts/run.py generate content.json out/deck.pptx
python <Skill>/scripts/run.py check out/deck.pptx
python <Skill>/scripts/run.py probe
python <Skill>/scripts/run.py render out/deck.pptx out/png
python <Skill>/scripts/run.py sheet out/png
```

`generate`の出力先、`render`のPNG保存先は省略できない。`render`は`--backend`、`--width`、
`--slides`を、`generate`は`--cover-footer-config`を受け付ける。

## 前提条件と停止条件

Python 3.10以上、`project/requirements.txt`のPython依存、実行環境で利用できる日本語フォントが必要。
必要な依存だけでなくバージョンも確認し、環境への導入が許可されていれば同梱の依存一覧を使う。
ツールの配置やインターネット接続を仮定しない。導入できない場合は不足を報告して停止する。
非Windowsではfontconfigと日本語sansフォント、または`PPTXDSL_FONT_REGULAR`、
`PPTXDSL_FONT_MEDIUM`、`PPTXDSL_FONT_BOLD`で指定する利用可能なフォントファイルが必要。

PNG化にはPowerPoint、またはLibreOfficeとpdftoppm/PyMuPDFなどが必要。
`probe`の結果を確認し、未対応の環境では利用可能な代替手段を調査する。
Python実行ができない通常チャットやレンダリング手段のない環境では完了を約束しない。
PNG化できなければ目視QAを完了扱いにせず、不足と調査結果を報告する。
代替backendではPowerPointとの描画差が残る可能性を報告する。

追加画像や独自の配色が必要な場合は、利用者の作業領域へSkill全体をコピーし、コピー側の
`project/slidegen/assets/`とクレジットを更新して、コピー側の`run.py`を使用する。
インストールされた正本は変更しない。画像パスは引き続き同梱assets内の相対パスで指定する。
情報源の確認、全ページ一覧と原寸での目視QA、修正後の再確認は通常のSkill手順と同じ。
