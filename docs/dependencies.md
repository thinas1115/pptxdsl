# 依存関係

## 用途別の導入

| 用途 | 導入コマンド | 内容 |
|---|---|---|
| PPTX生成・検査・PNG一覧作成、Skill・Plugin | `python -m pip install -r requirements.txt` | 実行時10パッケージ。構造検証用jsonschemaと間接依存を含め固定 |
| テスト・ギャラリー生成・Skill/Plugin/Releaseビルド | 同上 | 実行時依存とPython標準ライブラリ。配布ビルドにはGitも必要 |
| 素材の取得・SVG→PNG変換 | `python -m pip install -r requirements-assets.txt` | 実行時依存と素材取得用9パッケージ |
| 静的検査・分岐coverage | `python -m pip install -r requirements.txt -r requirements-quality.txt` | 実行時依存と検査専用依存。対象範囲は[静的品質ゲート](static-quality.md)を参照 |
| 全開発ツール | `python -m pip install -r requirements-dev.txt` | 素材取得・静的検査を含む全依存。追加のテストframeworkは不要 |

コマンドはcloneしたリポジトリのルートから実行する。Release版Skill・Pluginでは、
同梱された`project/requirements.txt`だけを使う。素材は変換済みPNGを同梱しており、
利用者の環境でSVG変換ライブラリを導入する必要はない。開発用の依存一覧はReleaseへ含めない。

用途別の依存一覧は`-r`で共通定義を参照する。実行時依存のバージョンを開発用一覧へ重複記載しない。
更新時は間接依存を含めて固定し、`python -m pip check`、最小環境での全テストと隔離配布試験、
素材変換試験を実施する。Python依存の固定だけではフォントやOfficeの描画差までは固定できない。

## OS側の前提

- Python 3.10以上と、日本語フォント。非Windowsの自動検出にはfontconfigが必要。
- PPTXのPNG化にはPowerPoint、またはLibreOfficeとPopplerの`pdftoppm`などが必要。
  これらはPythonの依存一覧では導入しない。実行環境の管理手順で用意する。
- 素材取得にはネットワーク接続が必要。SVGからPNGへの変換にはCairoの利用可能な共有ライブラリが必要。
  Linuxでpycairoをソースから導入する場合はCairo開発ヘッダー、pkg-config、Cコンパイラー、
  Python開発ヘッダーも必要になる。Debian/Ubuntuの例は`libcairo2-dev pkg-config python3-dev`。
  Windowsでは利用するPythonに対応したwheelとCairoを用意し、DLLの検索パスは環境側で設定する。
  特定のインストール先は前提にしない。

ReportLabのPNG描画backendは[公式導入ガイド](https://docs.reportlab.com/install/open_source_installation/)を、
Cairoの導入は[pycairo公式ガイド](https://pycairo.readthedocs.io/en/latest/getting_started.html)を参照する。
本プロジェクトではbackendの依存も固定するため、ReportLabのextraを無固定で追加しない。

## パッケージとライセンス

以下は固定したPythonパッケージの区分。ライセンス全文・権利表示は各配布物を参照する。
Pillow、lxmlなどのwheelに同梱されるネイティブライブラリの追加通知も各配布物に含まれる。

| パッケージ | 区分 | ライセンス | 配布元 |
|---|---|---|---|
| python-pptx | 実行時・直接 | MIT | [PyPI](https://pypi.org/project/python-pptx/) |
| Pillow | 実行時・直接 | MIT-CMU | [PyPI](https://pypi.org/project/Pillow/) |
| lxml | 実行時・直接 | BSD-3-Clause | [PyPI](https://pypi.org/project/lxml/) |
| XlsxWriter | 実行時・間接 | BSD-2-Clause | [PyPI](https://pypi.org/project/XlsxWriter/) |
| typing_extensions | 実行時・間接 | PSF-2.0 | [PyPI](https://pypi.org/project/typing-extensions/) |
| jsonschema | 実行時・直接 | MIT | [PyPI](https://pypi.org/project/jsonschema/) |
| attrs | 実行時・間接 | MIT | [PyPI](https://pypi.org/project/attrs/) |
| jsonschema-specifications | 実行時・間接 | MIT | [PyPI](https://pypi.org/project/jsonschema-specifications/) |
| referencing | 実行時・間接 | MIT | [PyPI](https://pypi.org/project/referencing/) |
| rpds-py | 実行時・間接 | MIT | [PyPI](https://pypi.org/project/rpds-py/) |
| reportlab | 素材取得・直接 | BSD | [PyPI](https://pypi.org/project/reportlab/) |
| svglib | 素材取得・直接 | LGPL-3.0-or-later | [PyPI](https://pypi.org/project/svglib/) |
| charset-normalizer | 素材取得・間接 | MIT | [PyPI](https://pypi.org/project/charset-normalizer/) |
| cssselect2 | 素材取得・間接 | BSD-3-Clause | [PyPI](https://pypi.org/project/cssselect2/) |
| tinycss2 | 素材取得・間接 | BSD-3-Clause | [PyPI](https://pypi.org/project/tinycss2/) |
| webencodings | 素材取得・間接 | BSD | [PyPI](https://pypi.org/project/webencodings/) |
| rlPyCairo | 素材取得・PNG backend | BSD | [PyPI](https://pypi.org/project/rlPyCairo/) |
| pycairo | 素材取得・間接 | LGPL-2.1-only OR MPL-1.1 | [PyPI](https://pypi.org/project/pycairo/) |
| freetype-py | 素材取得・間接 | BSD | [PyPI](https://pypi.org/project/freetype-py/) |
| ruff | 静的検査・直接 | MIT | [PyPI](https://pypi.org/project/ruff/) |
| mypy | 静的検査・直接 | MIT | [PyPI](https://pypi.org/project/mypy/) |
| mypy_extensions | 静的検査・間接 | MIT | [PyPI](https://pypi.org/project/mypy-extensions/) |
| types-jsonschema | 静的検査・型定義 | Apache-2.0 | [PyPI](https://pypi.org/project/types-jsonschema/) |
| pathspec | 静的検査・間接 | MPL-2.0 | [PyPI](https://pypi.org/project/pathspec/) |
| coverage | 分岐coverage・直接 | Apache-2.0 | [PyPI](https://pypi.org/project/coverage/) |
