# アイコン素材のクレジット表記

このディレクトリのアイコンは、スライド生成パイプラインがアーキテクチャ図・構成図を
描画するための素材であり、以下の出典・条件に基づいて同梱している。

## AWS Architecture Icons (`icons/aws/*.png`)

- 出典: [AWS Architecture Icons](https://aws.amazon.com/architecture/icons/)
  (AWS公式アイコンデッキまたは公式Icon packageから無改変抽出)
- ライセンス: [Creative Commons Attribution-NoDerivs 2.0](https://creativecommons.org/licenses/by-nd/2.0/legalcode)
- AWSによる同ライセンスでの公開配布例:
  [awslabs/aws-icons-for-plantuml](https://github.com/awslabs/aws-icons-for-plantuml)
- AWS公式ブログでの利用例:
  [Sequence Diagrams enrich your understanding of distributed architectures](https://aws.amazon.com/blogs/architecture/sequence-diagrams-enrich-your-understanding-of-distributed-architectures/)
- © Amazon Web Services, Inc. or its affiliates. AWS および関連アイコンは
  Amazon Web Services, Inc. の商標です
- アイコンデッキの利用ガイダンスに基づき、アーキテクチャ図の作成および技術資料への
  組み込み用途で使用する。**改変(比率・色・要素の追加削除)禁止**
- 準拠: [AWS商標ガイドラインおよびライセンス条項](https://d1.awsstatic.com/onedam/marketing-channels/website/public/legal/trademark-guidelines/AWS_Trademark_Guidelines_and_License_Terms_(2024-07-18)_JA-JP.pdf)
- 本リポジトリは AWS による後援・承認・提携を受けたものではありません
- 最新版・追加アイコンが必要な場合は公式デッキまたは公式Icon packageを入手し、
  必要なPNGを無改変で追加する
- 同梱時の帰属表示と条件: [`icons/aws/NOTICE.md`](icons/aws/NOTICE.md)

## Fluent UI System Icons (`icons/fluent/*.png`)

- 出典: [microsoft/fluentui-system-icons](https://github.com/microsoft/fluentui-system-icons)
- © Microsoft Corporation — [MIT License](https://github.com/microsoft/fluentui-system-icons/blob/main/LICENSE)
- `fetch_fluent_icons.py` でSVGを取得し、塗り色をスライド配色(#1F3864)に変更のうえ
  PNG化したもの(MITライセンスは改変・再配布を許諾)
- 同梱するライセンス全文: [`icons/fluent/LICENSE`](icons/fluent/LICENSE)
- 追加アイコンが必要な場合は `fetch_fluent_icons.py` の `ICONS` に追記して実行する

## 本文画像 (`images/*`)

`images/`へ追加する生成画像、手元の画像、Web画像は、各ファイルの利用者が公開・再配布・商用利用の
条件を確認する。外部由来の画像をGit管理へ含める場合は、この節へファイル名、取得元、権利者、
ライセンス、加工有無を追記する。機密情報、再配布できない素材、権利条件を確認できない画像はコミットしない。

- `pptxdsl-repository.png`: 公開中のpptxdslリポジトリ画面のスクリーンショット。
  画像加工なし。GitHubおよびGitHubロゴはGitHub, Inc.の商標であり、本リポジトリとの提携・承認を示さない。

## 表紙背景画像 (`cover/*`)

- `cover-background.png`: プロジェクト所有者がOpenAIのgpt-imageで生成した背景画像。
  外部から取得した画像ではなく、プロジェクト本体と同じMIT Licenseで提供する。
- OpenAIの[利用規約](https://openai.com/policies/terms-of-use/)では、適用法で認められる範囲で
  利用者がOutputを所有し、OpenAIがOutputについて持つ権利を利用者へ譲渡すると定めている。
- OpenAIおよびgpt-imageへの言及は生成元を示すものであり、OpenAIによる本プロジェクトの
  後援、承認、提携を示すものではない。
