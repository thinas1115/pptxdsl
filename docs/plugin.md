# ChatGPT・Codex向けPlugin

pptxdslをskills-only Pluginとして配布する。資料要件と情報源の確認から、JSON成形、PPTX生成、
機械検証、実行環境のPNGレンダリング、全ページの目視QAまでを1つのSkillで扱う。
外部MCPサーバーやGitHub認証は必要ない。Python実行ができるChatGPT WorkまたはCodexが対象であり、
通常チャットにZIPを添付するだけでPluginとしてインストールされるわけではない。

## 配布物の作成

ビルドにはPython 3.10以上とGitが必要。リポジトリルートで実行する。

```text
python -m tools.plugin.build
```

- `out/plugins/pptxdsl/`: インストール対象の自己完結したPluginフォルダ
- `out/plugins/pptxdsl-0.1.0.zip`: フォルダと同じ内容の配布ZIP。ZIP直下がPluginルート

既存出力を上書きしない。再ビルド時は`--output-dir out/plugins-next`など、未使用の出力先を指定する。
生成済みのPluginフォルダとZIPはGitへコミットしない。

追跡する正本は`.agents/skills/pptxdsl/`、`slidegen/`、公開スキーマと説明文書、
`plugins/pptxdsl/.codex-plugin/plugin.json`。Plugin専用のrendererやSkill複製を管理しない。
ビルド時に正本を集め、`skills/pptxdsl/project/`へ必要な本処理・素材・依存一覧・ライセンスを同梱する。
テスト、回帰入力、開発ツール、ローカル設定、生成デッキは配布へ含めない。
本処理・素材はGit追跡対象だけを同梱し、未追跡の利用者画像などは公開しない。

Portable形式の`plugin.json`を生成し、`.codex-plugin/plugin.json`も互換用に同梱する。
表示情報は互換manifestを正本としてPortable側の`extensions.com.openai.interface`へ反映する。
形式と固定の`skills/`検出については[公式のPluginパッケージ仕様](https://developers.openai.com/plugins/build/plugins)を参照する。

## 導入と受け入れ確認

開発時は、ビルドした`out/plugins/pptxdsl/`を個人のlocal marketplaceへ登録し、
ChatGPT WorkまたはCodexを再読み込みしてPlugins Directoryからインストールする。
登録は`@plugin-creator`または`$plugin-creator`へ、Pluginフォルダと個人marketplaceへの追加希望を指定して依頼できる。
公開ディレクトリへの公開や組織の導入は、利用者・管理者が選んだ公開経路で別途行う。
このビルドはアカウント設定、個人marketplace、組織ポリシーを変更しない。
具体的な導入経路と対象アカウントの制約は
[ChatGPT WorkのPluginガイド](https://learn.chatgpt.com/docs/build-plugins)と
[公式の接続・テスト手順](https://developers.openai.com/plugins/deploy/connect-chatgpt)を確認する。

導入後はPluginを有効にした新しい会話で、資料要件・情報源を渡してPPTX作成を依頼する。
次を確認する。

1. `pptxdsl` Skillが読み込まれ、同梱のスキーマとtype選定ガイドが参照される。
2. cloneせず、新規JSONから利用者の作業領域にPPTXを生成できる。
3. 機械検証後、環境を探索して全ページのPNGと一覧画像を生成する。
4. 全ページを原寸でも確認し、成果物と使用backend、残る制約を報告する。
5. Python依存・日本語フォント・レンダリング手段が不足する場合は、未確認を完了扱いにしない。

PluginがPython依存、フォント、Office互換ソフトを自動的に提供するわけではない。
同梱Skillの[Plugin実行環境](../.agents/skills/pptxdsl/references/plugin-runtime.md)に前提条件と
インストール先を変更せずに実行する入口を記載している。

## 自動検証

```text
python -m tests.test_plugin_package
```

配布ZIPを別ディレクトリへ展開し、リポジトリをimportできない独立プロセスで、
JSON検証、PPTX生成、配置検査、backend探索を実行する。配布物の再現性、素材の同一性、
リンク、ライセンス、インストール先に成果物を書かないこと、不正入力の終了も確認する。

CIのLinux環境では`PPTXDSL_PLUGIN_REQUIRE_RENDER=1`を指定し、展開したPluginからLibreOfficeで
PNG化と一覧画像生成まで実行する。これは配布物の実行試験であり、ChatGPT Work内の
Plugin選択・有効化・Skill自動選択そのものの試験とは区別する。
