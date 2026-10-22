# macOSで生成し、PowerPointで目視確認する

MacでPPTXを生成・検査する利用者向けです。Python側の構造検査とPowerPoint for Macの描画は
別々に確認します。CIが成功しても、Mac版PowerPointの確認済みとは扱いません。

## 最初にPythonと対応フォントを用意する

Python 3.10以上と、[フォント契約](font-contract.md)に対応する書体が必要です。
Macの標準フォントやHiragino Sansへ黙って置き換えません。
本文はNoto Sans CJK JPまたはNoto Sans JPのRegular/Bold、コード欄はNoto Sans Mono CJK JPを使います。
書体の取得先は[Noto公式](https://github.com/notofonts/noto-cjk/blob/main/README.md)を参照してください。
フォント自体はSkill・Plugin・Gitに同梱しません。

フォントは[AppleのFont Book手順](https://support.apple.com/guide/font-book/install-and-validate-fonts-fntbk1000/mac)で導入し、
PowerPointからも同じfamilyを利用できることを確認します。fontconfigの`fc-match`が利用できれば
自動探索します。導入済みでも検出できない場合は、ローカル設定で実ファイルを指定してください。
次の値は作業フォルダへ用意したファイルの例です。実際の配置に合わせて変更し、公開ファイルへ個人パスを書かないでください。

```sh
export PPTXDSL_FONT_REGULAR="$(pwd)/out/fonts/NotoSansJP-VF.ttf"
export PPTXDSL_FONT_CODE="$(pwd)/out/fonts/NotoSansMonoCJKjp-Regular.otf"
python -m pip install -r requirements.txt
python -m slidegen.font_config
```

可変Noto Sans JPのWeight軸は400/700を選択します。静的フォントの場合は
`PPTXDSL_FONT_BOLD`も指定します。ファイルを直接指定して測定できても、PowerPointへ未導入なら
描画時に置換されます。配置やRegular/Boldの異常を無視して先へ進めないでください。

## 入力検証・生成・機械検査を順に実行する

cloneのルートで次を実行します。Skill・Plugin版は同梱の`run.py`の`validate`、`generate`、`check`を使い、
インストール先へ出力を保存しません。

```sh
python -m slidegen.validate_content content.json
python -m slidegen.generate_from_json content.json out/deck.pptx
python -m slidegen.check_layout out/deck.pptx
```

CIは固定Noto Sans JP・Noto Sans Mono CJK JPでmacOSの全テストと主要5デッキを実行します。
Windows・Ubuntu・macOSの生成物を全3OSで相互検査しますが、PowerPointはCIへ導入しません。
開発者向けの実行入口は`python -m tests`と`python -m tools.quality.cross_platform build out/regression/decks`です。
CIの固定書体は`python -m tools.quality.cross_platform prepare-fonts out/cross-fonts`で取得できます。
これらの開発ツールは配布版には同梱しません。

## PowerPoint for Macから全ページをPNGへ書き出す

`render.ps1`はWindows COM用です。現時点の`render_preview.py`はMac版PowerPointを自動操作しません。
MacではMicrosoftが案内する[画像書き出し](https://support.microsoft.com/en-au/powerpoint/export-your-powerpoint-for-mac-presentation-as-a-different-file-format)を使います。

1. PowerPoint for Macで`out/deck.pptx`を開き、書体が置換されていないか確認します。
2. 「ファイル」→「エクスポート」でPNG形式を選び、「すべてのスライド」を選択します。
3. 幅1600・高さ900を指定し、このデッキ専用の未使用フォルダへ書き出します。

cloneでは、手動出力を標準の連番へコピーし、一覧を生成できます。

```sh
python -m tools.quality.import_slide_pngs out/deck.pptx out/mac-export out/png
python contact_sheet.py out/png
```

取込ツールはPNG名末尾の番号、1からの連番、PPTXとの枚数一致、1600×900pxを検査します。
原本を変更せず、出力先が存在する場合は停止します。番号のない画像は推測で並べません。
配布版では、書出し原本を残して`slide_01.png`等へ別名コピーし、同梱`run.py sheet`で一覧を作れます。
一覧に加えて全ページ原寸と接続経路を確認します。取込成功は目視合格ではありません。

PowerPointが使えない場合はLibreOffice＋PDF画像化手段を調査します。代替backendの結果を
PowerPoint確認済みとは記録しません。使用製品・バージョンと未確認範囲を残してください。

## Mac実機の受入結果を残す

このWindows開発環境ではMac版PowerPointを実行していません。自動操作方式も実証していないため、
AppleScript等の未確認コードを正式手順へ入れません。Macの実機で主要5デッキを開き、全ページの
一覧・原寸・接続経路を確認する工程が受入条件として残ります。

記録にはmacOS・CPU・Python・PowerPointの各バージョン、コミット、フォントの診断結果、
デッキ名と枚数、機械検査、PNG書出し寸法、原寸確認範囲、NGと修正、確認者の役割を含めます。
個人パスや端末名は含めません。初回に使う機種だけを対応機種とするものでもありません。
問題は[Issue](https://github.com/thinas1115/pptxdsl/issues)へ、公開可能な情報だけを添えて報告してください。
