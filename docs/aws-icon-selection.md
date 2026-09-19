# AWSアイコンの収録範囲

主要サービス79種と、構成図で使う基本リソースを合わせた103PNGを同梱する。
AppSync、API Gateway、Lambda、EC2、ECS、EKS、S3、RDS、DynamoDB、VPC、CloudFront、
認証・セキュリティ、監視・運用、データ分析など、一般的な構成説明で使う素材を収録する。
既存のAWSネットワーク研修例で使う接続・境界・エンドポイントの素材も含む。

これは利用頻度の統計順位ではなく、配布素材の編集方針である。用途が限定される量子、衛星、
医療、メディア専用サービスなどは標準セットに含めない。

- 同じ絵柄は1PNGだけ。サイズ・明暗・SVGとの重複を持たない。
- 同じサービスを既存ファイルで描ける場合は、そのファイルを一覧へ載せて追加コピーを作らない。
- 追加する場合は公式PNGを無改変で使い、元パッケージ内の相対パスとSHA-256を記録する。
- 一覧の`source: existing/...`は既に無改変抽出済みの同梱素材。出典と利用条件は
  [CREDITS.md](../slidegen/assets/CREDITS.md)を参照する。

名称検索は`python -m slidegen.aws_icons AppSync`。検索語を省略すると全件を表示する。
実行環境がPluginの場合は、同梱`project/`を作業ディレクトリにして検索する。
詳細一覧は[収録カタログ](../slidegen/assets/icons/aws/catalog.json)。

新しいサービスが資料要件に必要になった場合は、
`tools/assets/import_aws_icons.py`の`SERVICES`へ追加して、展開済み公式パッケージに対して
`python -m tools.assets.import_aws_icons <パッケージ>`を実行する。
新規素材の出典・ライセンス確認、重複検査、テスト、Plugin再梱包も行う。
