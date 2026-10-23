# ギャラリーPPTXはRelease・CIで配布する

ギャラリーを保守・配布する開発者向けの方針です。PPTXを取得するだけなら、
[ギャラリーの取得手順](../examples/gallery/README.md)を参照してください。

Gitには生成元と960px幅のtype別一覧を残し、PPTXと原寸PNGは追加しません。
renderer変更時の生成・機械検査・PNG目視QAは従来どおり必須です。変更するのは保存先です。

## 生成元・縮小一覧・検証結果を分ける

| 対象 | 保存先 | 更新方法 |
|---|---|---|
| renderer、テーマ、素材、回帰入力 | Git | ソースと対象テストを更新する。入力の正本は`tests/fixtures/gallery/` |
| 発見用の一覧PNG | Gitの`docs/pattern-gallery-by-type.png` | 960px幅、256KiB以下。type名と配置の概要を確認する |
| 編集可能なギャラリーPPTX | GitHub Release、CI成果物、ローカル`out/` | 同じコミットの生成元から生成・機械検査する |
| 原寸PNG、詳細一覧、環境情報、検証報告 | CI成果物、ローカル`out/` | backend・書体・コミットと合わせて確認する |

元の画面キャプチャや権利表示の必要な素材は生成物ではありません。`slidegen/assets/`の
必要素材とクレジットを削除しないでください。Skill・Pluginは従来どおりruntimeと素材を同梱し、
回帰入力・生成ツール・ギャラリーPPTXは同梱しません。

## Releaseは古いPPTXをコピーしない

`python -m tools.distribution.build --output-dir out/release`は、checkoutしたコードで
ギャラリーを生成し、機械検査に合格したPPTXをSkill・Pluginと一緒に出力します。
生成や検査が失敗した場合は配布を停止します。PPTX内のZIP日時は固定し、
同じソース・依存・書体・環境で再生成した配布物のSHA-256を比較します。
書体やOffice backendが異なる環境間の画素一致を保証するものではありません。

Release workflowはタグがmainに含まれることを検査する既存の手順を維持します。
forkやオフラインでは同じビルドをローカルで実行できます。GitHub権限が無くても生成は可能です。
安定版と開発中の版を混同しないよう、CI成果物は対象PR・コミットを確認して取得してください。
CI成果物には保存期限があるため、正式な配布はReleaseを使います。

## LFSへの移行より、今後の生成物を追跡しない

| 案 | 利点 | 採否と理由 |
|---|---|---|
| PPTXと大きなPNGを引き続き追跡 | clone直後に実物を開ける | 不採用。修正ごとにバイナリが増える |
| Git LFS | Gitには参照を置き、実体を別に保存する | 今回は不採用。生成できる成果物のためにLFS取得と保存先の運用を追加しない |
| Releaseだけを用意する | 通常コミットにPPTXが増えない | 一覧の発見性と開発版の確認を補う必要がある |
| 縮小一覧＋Release・CI＋ローカル生成 | READMEから見つけ、安定版・開発版・オフラインで使い分けられる | 採用。既存のPython依存と配布経路を使う |

Git LFSの参照方式は[GitHub公式説明](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage)に従います。
特定のプラン料金や保存枠を前提にした判断ではありません。

## 公開済み履歴は書き換えない

調査時のmainには、ギャラリーPPTXの異なるblobが51個、PNGが25個ありました。
未圧縮の実体サイズ合計はそれぞれ81,607,630バイトと13,705,860バイトです。
Gitの圧縮・転送量を表す数値ではありません。この変更は今後の増加を抑えるもので、
既存のcloneや過去履歴を小さくする処理は行いません。

既存clone・forkは通常のpullで新方針へ移れます。過去コミットのPPTXと公開済みReleaseは残ります。
旧パスへ手動生成したローカルPPTXはGit管理外となり、生成先は`out/`へ移してください。
履歴削減のための履歴書換え、強制push、既存タグの変更は別途明示承認が必要です。

取得やビルドの問題は[Issue](https://github.com/thinas1115/pptxdsl/issues)へ報告してください。
この文書でいうCI成果物はテスト実行に添付されたファイル、Releaseは正式版の配布、
blobはGitが保持するファイルの実体を指します。
