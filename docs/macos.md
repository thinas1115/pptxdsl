# macOSでの生成・検証

## 対応範囲

macOSでは、`content.json`検証、PPTX生成、機械検証、PowerPoint for Macによる
PNG書き出しと目視確認を実行できます。特定のMac機種やCPUには依存しません。

WindowsとmacOSでは使用する日本語フォントが異なるため、完全なピクセル一致は保証しません。
各OSで生成したPPTXが、そのOSのPowerPointで溢れ・重なりなく表示されることを品質条件とします。

## セットアップ

```bash
git clone https://github.com/thinas1115/pptxdsl.git
cd pptxdsl
python3 -m pip install -r requirements.txt
```

macOSでは標準搭載のHiragino Sansを、Pillowの文字実測とPowerPointの描画へ使用します。
フォントが利用できない場合は生成を停止し、代替フォントへ黙って切り替えません。

別の日本語フォントを使う場合は、PowerPoint上のファミリー名と実測ファイルを環境変数で指定します。
`MEDIUM`と`BOLD`を省略した場合は`REGULAR`と同じファイルを使用します。

```bash
export PPTXDSL_FONT_FAMILY="<PowerPoint上のフォント名>"
export PPTXDSL_FONT_REGULAR="<regular-font-file>"
export PPTXDSL_FONT_MEDIUM="<medium-font-file>"
export PPTXDSL_FONT_BOLD="<bold-font-file>"
```

## 生成と機械検証

```bash
python3 slidegen/validate_content.py content.json
python3 slidegen/generate_from_json.py content.json out/deck.pptx
python3 slidegen/check_layout.py out/deck.pptx
```

## PowerPointでPNG化する

1. PowerPoint for Macで`out/deck.pptx`を開く。
2. `ファイル`から`エクスポート`を選ぶ。
3. ファイル形式を`PNG`、保存先を`out/png`にする。
4. すべてのスライドを書き出す。
5. 一覧画像を生成する。

```bash
python3 contact_sheet.py out/png
```

`out/png/sheet.png`の一覧と、各PNGの原寸を両方確認します。文字溢れ、要素重なり、
禁則違反、フォント置換、線の見え方を確認し、PowerPoint以外の描画結果で代替しません。

実機検証を共有するときは、macOS、CPU、Python、PowerPointの各バージョンを記録します。
