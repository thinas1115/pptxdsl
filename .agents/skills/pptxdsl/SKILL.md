---
name: pptxdsl
description: pptxdslで資料要件と情報源からcontent.jsonを設計し、PPTX生成、機械検証、実環境でのPNGレンダリング、目視QA、修正まで完了する。新規デッキ作成や既存content.jsonから提出品質のPPTXを作る依頼で使用する。renderer自体の開発・保守だけの依頼には使用しない。
---

# pptxdsl

利用者へ渡せるPPTXを完成させる。`content.json`の作成だけで終了せず、生成、機械検証、全ページの目視確認、修正後の再確認まで行う。

## 前提

- cloneではリポジトリルートから作業し、最初に`AGENTS.md`を読む。
  Pluginとして読み込まれた場合は[Plugin実行環境](references/plugin-runtime.md)を先に読み、
  同梱の`project/`を本処理・文書のルート、利用者の作業領域を入出力先として区別する。
- 主張、固有名詞、数値、画像の根拠は、利用者の資料要件と指定された情報源だけに限定する。
- `tests/fixtures/gallery/content*.py`、`tests/fixtures/gallery/diagram_specs.py`、ギャラリーは回帰検証用であり、新規資料の内容やページ構成の参考にしない。
- 正確な資料を作るために不足している情報があれば、不足を埋める質問だけを行い、仮の内容で先へ進めない。

## 完成までの流れ

1. テーマ、想定読者、目的、必須内容、使用可能な情報源、枚数目安を確認する。内容の根拠と網羅性を点検するときは[内容QA](references/content-qa.md)を読む。
2. 章立てと各ページの主題・結論・根拠を整理してからtypeを決める。選定時は`docs/type-selection-guide.md`と[Type選定](references/type-selection.md)を読む。
3. `CONTENT_SCHEMA.md`と[JSON成形](references/json-authoring.md)に従って`content.json`を新規作成または修正する。座標、余白、フォント、色、描画順をJSONへ書かない。
4. 次の順で検証・生成する。`FitError`では極小文字化や不適切なtypeへの置換をせず、文言短縮、項目削減、スライド分割を優先する。

   ```text
   python slidegen/validate_content.py content.json
   python slidegen/generate_from_json.py content.json out/deck.pptx
   python slidegen/check_layout.py out/deck.pptx
   ```

5. [レンダリングと目視QA](references/render-and-visual-qa.md)を読み、実行環境で利用可能なbackendを探索して全ページをPNG化する。コンタクトシートと原寸画像を確認し、問題があれば2へ戻る。
6. 修正後は、影響した工程以降を再実行する。最終報告にはPPTXの場所、実行した検証、使用したレンダリングbackend、目視確認結果、残る制約を記載する。

## 停止条件

- 必須情報や画像がなく、根拠のない補完が必要になる場合は利用者へ確認する。
- 適合するtypeがない場合は、既存typeへ簡略化して失う情報と、新rendererで保持できる情報を示し、どちらにするか確認する。
- 利用可能なレンダリング方法を調査してもPNG化できない場合は、目視QAを完了扱いにしない。調査結果と不足する前提条件を報告する。
