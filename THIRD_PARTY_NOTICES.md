# 第三者素材に関する通知

本リポジトリには、プロジェクト本体のMIT Licenseとは異なる条件が適用される第三者素材が
含まれます。本プロジェクトのMIT Licenseは、以下の素材、商標、ロゴへ適用されません。

## AWS Architecture Icons

- 対象: `slidegen/assets/icons/aws/*.png`およびこれらを含む配布サンプル
- 出典: [AWS Architecture Icons](https://aws.amazon.com/architecture/icons/)
- 権利者: Amazon Web Services, Inc.またはその関連会社
- ライセンス: [Creative Commons Attribution-NoDerivs 2.0](https://creativecommons.org/licenses/by-nd/2.0/legalcode)
- AWSによる同ライセンスでの公開配布例:
  [awslabs/aws-icons-for-plantuml](https://github.com/awslabs/aws-icons-for-plantuml)
- AWS公式ブログでの利用例:
  [Sequence Diagrams enrich your understanding of distributed architectures](https://aws.amazon.com/blogs/architecture/sequence-diagrams-enrich-your-understanding-of-distributed-architectures/)
- 配布条件: 無改変で使用し、帰属表示とライセンスURIを維持する。詳細は
  [`slidegen/assets/icons/aws/NOTICE.md`](slidegen/assets/icons/aws/NOTICE.md)を参照
- 備考: AWSおよび関連アイコンはAmazon Web Services, Inc.の商標です。本プロジェクトは
  AWSによる後援、承認、提携を受けたものではありません

## Fluent UI System Icons

- 対象: `slidegen/assets/icons/fluent/*.png`
- 出典: [microsoft/fluentui-system-icons](https://github.com/microsoft/fluentui-system-icons)
- 権利者: Microsoft Corporation
- ライセンス: MIT License
- 加工: SVGの塗り色を変更し、PNGへ変換
- ライセンス全文: [`slidegen/assets/icons/fluent/LICENSE`](slidegen/assets/icons/fluent/LICENSE)

## GitHub画面のスクリーンショット

- 対象: `slidegen/assets/images/pptxdsl-repository.png`
- 内容: 公開中のpptxdslリポジトリ画面の無加工スクリーンショット
- 備考: GitHubおよびGitHubロゴはGitHub, Inc.の商標です。本プロジェクトとの提携や承認を
  示すものではありません

## Python依存パッケージ

`requirements.txt`の実行時依存と、開発用`requirements-assets.txt`の素材取得依存は、
本リポジトリへ複製しておらず、インストール時に各配布元から取得します。
パッケージ別の区分とライセンスは[依存関係](docs/dependencies.md)を参照してください。
Skill・Pluginには実行時の依存一覧だけを同梱し、素材取得用ライブラリの導入を要求しません。
各パッケージとそのバイナリに含まれるライブラリには、配布元のライセンス通知が適用されます。
