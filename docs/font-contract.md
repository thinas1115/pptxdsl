# 実測と描画のフォント契約

## 対応範囲

日本語の通常書体はYu Gothic、Noto Sans CJK JP、Noto Sans JPに対応する。
Regular/Boldの実ファイル・face index・family・styleを確認し、同じfamilyをPPTXの
Latin/東アジア/複合文字の指定へ使用する。コード欄はWindowsでConsolas、非Windowsで
Noto Sans Mono CJK JPを測定・指定する。Consolasに含まれない日本語のコードコメントには
Noto Sans Mono CJK JPを明示指定するか、コメントをコード欄の外へ出す。

対応外family、family混在、Bold不足、Regularへの誤置換、未対応の可変軸は停止条件。
任意のフォントへ黙ってフォールバックしない。対応フォントを増やす際は、実測・生成・検査・
実レンダリングの回帰検証を追加する。フォント自体はリポジトリやSkill・Pluginへ同梱しない。

## 選択順と設定

1. `PPTXDSL_FONT_REGULAR`と`PPTXDSL_FONT_BOLD`の明示指定を優先する。
   静的フォントでは両方必要。NotoのWeight軸だけを持つ可変フォントでは、REGULARだけを
   指定しても同じファイルから400/700を明示選択する。Thinなどの既定インスタンスでは測らない。
2. 指定がなければ、WindowsではOSのFonts内の游ゴシックRegular/Boldを使用する。
3. 非WindowsではfontconfigからNoto Sans CJK JP、次にNoto Sans JPのRegular/Boldを探す。
   `fc-match`の代替候補を無条件には受理せず、返されたファイルのfamily/styleを再確認する。

TTCの面を指定する場合は`PPTXDSL_FONT_REGULAR_INDEX`、`PPTXDSL_FONT_BOLD_INDEX`へ
0以上のface indexを設定する。fontconfigによる探索では返されたindexを保持する。
コード欄も明示する場合は`PPTXDSL_FONT_CODE`と任意の`PPTXDSL_FONT_CODE_INDEX`を使う。
ファイルパスはローカルの環境変数で渡し、公開JSONやIssueへ書かない。

PPTXのrunは通常/太字の二値であり、Mediumの500を表現できない。
従来の内部`medium`はRegularの別名へ統一する。`PPTXDSL_FONT_MEDIUM`は未指定、または
Regularと同じfaceだけを受理し、別のMedium面を指定した場合は移行方法を示して停止する。

同一プロセスで環境変数を変えた場合は別のキャッシュキーで解決する。
読み込み済みフォントファイルの差し替えはプロセス再起動後に行う。
文字幅の再利用条件と導入前後の測定は[文字幅キャッシュ](text-width-cache.md)を参照する。
生成時と検査時には同じフォント設定を使う。PPTXを開く側にも同じフォントが必要であり、
PPTXのfamily指定だけでは代替書体への置換を防げない。

診断コマンドはfamily、style、index、可変軸、SHA-256を返す。端末固有のパスは表示しない。

```text
python -m slidegen.font_config
python <Skill>/scripts/run.py fonts
```

## 安全係数と再現性

幅の実測はPillow/FreeTypeのadvance幅を96dpiへ換算する。Noto系では、LibreOfficeが加える
和欧間隔を見込み、日本語と英数字が直接隣接する境界ごとに1/4emを確保したうえで、
共通の`SAFETY = 1.08`を掛ける。係数だけを増やして境界数の影響を吸収しない。
初回48条件の実描画／Pillow advanceの最大比は、游ゴシック＋PowerPointで1.0749、
Noto CJK/JP＋LibreOfficeで1.0858だった。このNotoの差を受けて和欧間隔をモデルへ加え、
和英交互の文を含む64条件へ校正を拡張した。advance幅と字間込み推定幅を別々に記録する。
和欧間隔の機能は[LibreOfficeのAsian Typography](https://help.libreoffice.org/latest/en-US/text/shared/01/05020700.html)を参照する。
pt→pxの整数丸め、Officeの字送り・カーニング差を見込む幅方向の余裕であり、
行高、混在書体、未対応フォント、代替書体、任意のOffice版を保証する値ではない。
Pillowのfamily/styleと可変軸の扱いは[公式API](https://pillow.readthedocs.io/en/stable/reference/ImageFont.html)に従う。

同じ入力・renderer・依存バージョン・フォントファイルとindex・可変軸・設定で同じ配置を再現する。
異なるフォント間の同一改行、Office/OSをまたぐピクセル一致、ZIP日時を含むPPTXのバイト一致は保証しない。
測定値で収まることと、描画後に読みやすいことを分け、全ページのPNG確認を省略しない。

## 実レンダリングによる校正記録

2026-10-16に、8.2／9／10.5／11／13.5／16／24／42pt、通常／太字、
日本語・英数字・和英混在・和英交互文の64条件を各環境で照合した。
「推定幅」は安全係数を掛ける前の値であり、合格条件は実描画幅／推定幅が1.08以下である。

| 測定書体 | 描画環境 | 実描画幅／advance幅の最大値 | 実描画幅／推定幅の最大値 |
| --- | --- | ---: | ---: |
| Yu Gothic Regular/Bold | Windows、PowerPoint 16.0 build 20430 | 1.074859 | 1.074859 |
| Noto Sans CJK JP Regular/Bold | Ubuntu、LibreOffice 24.2.7.2 420(Build:2)、Poppler | 1.271585 | 1.012383 |
| Noto Sans JP Weight軸400/700 | Ubuntu、LibreOffice 24.2.7.2 420(Build:2)、Poppler | 1.271585 | 1.012383 |

Notoで和欧間隔を無視すると、和英交互文の実描画幅はadvance幅より最大27.16%広い。
境界ごとの間隔を加えた最終モデルでは、3書体とも共通の安全係数内に収まった。
この結果は上記64条件の観測であり、未検証の文字列や描画環境すべての保証ではない。

各書体で通常41ページ・lead付き40ページ・過密入力5ページを生成・機械検査し、
計234ページのPNGを一覧と原寸で確認した。フォント変更による新しい文字切れ・欠字・
重なりは見つからず、可変フォントも通常／太字の描き分けを確認した。
LibreOfficeではPowerPointと異なる線・図形の影が見られるため、ピクセル一致とは扱わない。
既存の画像比較、グラフ、パケット図、ギャラリー文言などの課題は別Issueの対象であり、
この校正はそれらのデザイン・内容の完成を意味しない。

OS間の検査では、同じPillow版とフォントでも既定エンジンが異なることが分かった。
WindowsのBASICとUbuntuのRAQMによる18文字枠の照合で、幅の差は最大約0.027インチだった。
以後、測定用フォントは`ImageFont.Layout.BASIC`を明示し、RAQMの有無で測定方法を変えない。
上表のNoto校正値は変更前のRAQMでの観測であり、BASICの実描画校正はCIの構造化記録で別途確認する。

Notoの全テスト、測定値、フォントSHA-256、PPTX、PNGは
[検証実行38851559009](https://github.com/thinas1115/pptxdsl/actions/runs/38851559009)の
`font-contract-noto-cjk`／`font-contract-noto-jp-variable`成果物に保存している。
成果物の保持期限後も、同じ検証は次のコマンドとCIから再実行できる。
Noto Sans JPの取得元commitとSHA-256はCIで固定・照合する。
PDFのPostScript名にThinが残る場合があるため、その名前だけで可変軸の選択を判定しない。

```powershell
python -m tools.quality.font_metrics build out/font-metrics
powershell -NoProfile -File tools/quality/font_metrics.ps1 -PptxPath out/font-metrics/metrics.pptx -Output out/font-metrics/actual.json
python -m tools.quality.font_metrics compare out/font-metrics/expected.json out/font-metrics/actual.json --backend powerpoint --report out/font-metrics/report.json
```

LibreOffice環境では、同じフォントを描画側にも導入してからPDF内のfamilyも照合する。
必要なツールはLibreOffice Impress、Popplerの`pdftotext`と`pdffonts`である。

```sh
python -m tools.quality.font_metrics build out/font-metrics
soffice --headless --convert-to pdf --outdir out/font-metrics out/font-metrics/metrics.pptx
pdftotext -bbox-layout out/font-metrics/metrics.pdf out/font-metrics/actual.xhtml
python -m tools.quality.font_metrics compare out/font-metrics/expected.json out/font-metrics/actual.xhtml --backend poppler --pdf out/font-metrics/metrics.pdf --report out/font-metrics/report.json
```
