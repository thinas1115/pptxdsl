# Pythonからのデッキ生成

## 公開入口

`slidegen.generate_from_json.build_presentation()`へJSON互換の辞書を渡すと、
入力検証済みの`Presentation`を返す。保存先の作成・保存・PNG化は呼び出し側が行う。
入力辞書とrenderer登録を呼び出し開始時にコピーするため、生成中に元データを書き換えても
生成対象のデッキへ混入しない。

```python
import json
from pathlib import Path
from slidegen.generate_from_json import build_presentation

deck = json.loads(Path("content.json").read_text(encoding="utf-8"))
presentation = build_presentation(deck, cover_footer_config="examples/cover_footer.json")
Path("out").mkdir(exist_ok=True)
presentation.save("out/deck.pptx")
```

`cover_footer_config`は設定JSONのパス、または検証済み`CoverFooterConfig`を受け取る。
省略時は毎回標準設定となり、以前の呼び出しの設定を引き継がない。
`renderers`は開発時のrenderer辞書の差し替え用であり、通常利用では省略する。
回帰ギャラリー以外で`allow_sample_content=True`を指定してはならない。

入力・設定が不正な場合は`ValueError`、収容できない場合はその派生の`FitError`を返す。
ライブラリから`SystemExit`は発生させない。CLIはこれらを利用者向けメッセージと終了コードへ変換する。
同一の`Presentation`を複数スレッドで編集する使い方は対象外だが、独立した入力から別々の
`Presentation`を並列生成する使い方は回帰テストで確認する。

## 状態の所有範囲

`GenerationContext`は、デッキのmetadata、総ページ数、表紙・フッター設定、標準テーマ、
現在の本文下端を保持する。metadataは入力の独立コピー、設定とテーマは不変値として扱う。
任意テーマを渡すAPIは公開しない。現時点では標準テーマだけを使用する。

rendererは`current_context()`で現在の読み取り専用状態を参照する。
生成入口だけが`bind_context()`で処理範囲を設定し、`finally`で必ず復元する。
補足欄は元のContextを変更せず、本文下端を予約した別Contextをそのスライドの処理中だけ設定する。
入れ子で別デッキを生成しても、正常・異常終了後は外側の状態へ戻る。
Contextはスレッド間で共有・再利用せず、各`build_presentation()`が作成する。

## 旧コードからの移行

CLIのコマンドと引数、Skill・Pluginからの生成方法は変更しない。
`generate.DECK`、`generate.COVER_FOOTER`、`configure_cover_footer()`による状態書き換えは廃止した。
デッキ全体を生成するコードは`build_presentation()`へ移行する。

1枚のrendererだけを検証する開発コードは、必要に応じて明示的なContextを使用する。

```python
from slidegen import generate
from slidegen.generation_context import bind_context, make_context

with bind_context(make_context(deck, "examples/cover_footer.json")):
    generate.render_slide(renderer, slide, spec, 1)
    generate.footer(slide, 1)
```

Contextを設定しない低水準呼び出しは、空metadata・総数0・標準設定となる。
デッキ単位の表紙・フッターが必要な場合、この既定値に依存しない。
