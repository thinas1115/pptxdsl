# AWSネットワーク資料の入力例

`content.json`は121ページの勉強資料の入力データ。章区切り、AWS VPC図、ネットワーク教材typeを組み合わせている。
本処理や回帰検証用の固定文言とは分離し、Pluginの実行コードには同梱しない。

リポジトリルートから生成する。

```sh
python slidegen/validate_content.py examples/training/aws-network/content.json
python slidegen/generate_from_json.py examples/training/aws-network/content.json out/aws-network.pptx
python slidegen/check_layout.py out/aws-network.pptx
```

AWS仕様の正確性・最新性を保証する教材ではない。実際に使う際は公式情報と照合し、実行環境でPNG化して全ページを目視確認する。
