# OS間の回帰検証

生成に対応する書体と、Office上の描画が一致するかは別の検証である。
CIでは以下を分け、PowerPointを利用していない検証を「PowerPoint確認済み」としない。

| 対象 | 実行環境 | 検証する内容 |
| --- | --- | --- |
| 游ゴシック | Windows、Python 3.10／3.13 | 全テスト、主要5デッキの生成と機械検査 |
| Noto Sans CJK JP | Ubuntu、Python 3.13 | 全テスト、主要5デッキ、LibreOffice描画、文字幅の校正 |
| Noto Sans JP可変400／700 | Ubuntu、Python 3.13 | 全テスト、主要5デッキ、LibreOffice描画、文字幅の校正 |
| 固定Noto Sans JP＋固定Noto Sans Mono CJK JP | Windows／Ubuntu、Python 3.13 | 全テスト、双方の主要5デッキを双方のOSで検査 |

主要5デッキは`basic`、`extended`、`patterns`、`lead_patterns`、`stress_patterns`である。
通常・太字だけでなくコード欄の書体も固定し、OSの既定コード書体の違いを比較へ持ち込まない。
フォントは公式配布のcommitとSHA256を固定し、検証時に取得する。GitやSkill・Pluginには同梱しない。

## 記録する値

`tools/quality/cross_platform.py`はデッキごとの成功／失敗、所要時間、PPTXのSHA256、ページ数、
文字枠数、各行の文言・矩形・行送り・役割、検査結果をJSONへ保存する。
いずれかのデッキが失敗しても残りを検査し、最後に非ゼロで終了する。
元PPTXの差し替え、基準値の欠落、書体ファイル・index・可変軸の不一致も不合格にする。

環境記録にはOS、Python、主要ライブラリ、FreeType、測定エンジン、書体family・style・SHA256を含める。
検査backendは`pptx-structure`、描画状態は`not_performed`と明記する。
LibreOfficeが見つかる場合は実際の`--version`を記録し、見つからなければ`not_detected`とする。
PowerPointはホストWindowsにあると仮定せず、この処理だけでは`not_probed`とする。
実描画側のLibreOfficeバージョンと校正結果は、別の描画・フォント契約ジョブの成果物へ保存する。

全テストの結果は、[テストランナー](../README.md)の`--report`でモジュール別に保存する。
CIの失敗時も基準値・照合結果を成果物として残す。1つ目の照合に失敗して2つ目が成功した場合も、
全体を成功扱いにしない。

## 一致させる項目と許容する差

同一PPTXを同一書体で検査した場合、行数、文言、診断コード、書体識別情報を一致させる。
矩形の数値許容差は[文字領域検査](text-metrics.md)と同じ0.00001インチとし、最大差と差の所在を記録する。
異なるOS名、Python・Office互換ソフトのバージョンは比較の除外項目だが、観測情報として残す。

PPTXのZIP作成時刻、異なるfamily間の改行、PowerPoint／LibreOffice間のピクセル一致は要求しない。
一方、同じ入力の検査診断がOSだけを理由に変わること、はみ出しや衝突の見逃しは回帰として扱う。
Officeの描画差はPNGでも確認し、差を「想定内」とするだけで文字切れ・読めないラベルを許可しない。

## 再実行

書体の選択は[フォント契約](font-contract.md)に従って環境変数で指定する。
クロス検査用の固定書体は次のコマンドで取得できる。

```sh
python -m tools.quality.cross_platform prepare-fonts out/cross-fonts
python -m tests --report out/regression/tests.json
python -m tools.quality.cross_platform build out/regression/decks
python -m tools.quality.cross_platform compare out/regression/decks out/regression/self-check
```

他環境の生成成果物を同じ書体設定で受け取り、`compare`で照合する。
GitHub ActionsではWindows／Ubuntu双方の成果物を取得して両方向を検査する。
実際の出力先やフォントの絶対パスは公開文書へ書かず、環境変数または引数で渡す。
