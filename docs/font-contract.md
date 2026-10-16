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
生成時と検査時には同じフォント設定を使う。PPTXを開く側にも同じフォントが必要であり、
PPTXのfamily指定だけでは代替書体への置換を防げない。

診断コマンドはfamily、style、index、可変軸、SHA-256を返す。端末固有のパスは表示しない。

```text
python -m slidegen.font_config
python <Skill>/scripts/run.py fonts
```

## 安全係数と再現性

幅の実測はPillow/FreeTypeのadvance幅を96dpiへ換算し、游ゴシックでは`SAFETY = 1.08`、
Noto系では`SAFETY_BY_FAMILY`の1.10を掛ける。8.2〜42pt・通常/太字・和文/英文/混在文の
48条件を実描画と照合した最大比は、游ゴシック＋PowerPointで1.0749、Noto CJK/JP＋
LibreOfficeで1.0858だった。Notoの混在文では1.08を超えたため、書体別に余裕を確保する。
pt→pxの整数丸め、Officeの字送り・カーニング差を見込む幅方向の余裕であり、
行高、混在書体、未対応フォント、代替書体、任意のOffice版を保証する値ではない。
Pillowのfamily/styleと可変軸の扱いは[公式API](https://pillow.readthedocs.io/en/stable/reference/ImageFont.html)に従う。

同じ入力・renderer・依存バージョン・フォントファイルとindex・可変軸・設定で同じ配置を再現する。
異なるフォント間の同一改行、Office/OSをまたぐピクセル一致、ZIP日時を含むPPTXのバイト一致は保証しない。
測定値で収まることと、描画後に読みやすいことを分け、全ページのPNG確認を省略しない。
