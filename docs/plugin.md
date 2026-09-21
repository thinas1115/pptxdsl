# ChatGPT・Codex・Claude Code向けPlugin

pptxdslをskills-only Pluginとして配布する。資料要件と情報源の確認から、JSON成形、PPTX生成、
機械検証、実行環境のPNGレンダリング、全ページの目視QAまでを1つのSkillで扱う。
外部MCPサーバーやGitHub認証は必要ない。Python実行ができるChatGPT WorkまたはCodexが対象であり、
通常チャットにZIPを添付するだけでPluginとしてインストールされるわけではない。

## 配布物の作成

正式配布は[GitHub Releases](https://github.com/thinas1115/pptxdsl/releases)の
`pptxdsl-plugin-v<version>.zip`を使用する。同じReleaseにある
`pptxdsl-skill-v<version>.zip`はSkillとして直接導入する配布物であり、Plugin manifestを含まない。

ビルドにはPython 3.10以上とGitが必要。リポジトリルートで実行する。

```text
python -m tools.plugin.build
```

- `out/plugins/pptxdsl/`: インストール対象の自己完結したPluginフォルダ
- `out/plugins/pptxdsl-plugin-v<version>.zip`: フォルダと同じ内容の配布ZIP。ZIP直下がPluginルート

既存出力を上書きしない。再ビルド時は`--output-dir out/plugins-next`など、未使用の出力先を指定する。
生成済みのPluginフォルダとZIPはGitへコミットしない。

Skill ZIP、Plugin ZIP、パターンギャラリー、SHA-256一覧をRelease候補としてまとめる場合は次を実行する。

```text
python -m tools.distribution.build --output-dir out/release
```

Release workflowはタグとmanifestのバージョンが一致しない場合に停止する。
`v<version>`タグのpushでは`.github/workflows/release.yml`が全テストを実行し、
タグがmainに含まれることを確認してからReleaseを公開する。

追跡する正本は`.agents/skills/pptxdsl/`、`slidegen/`、公開スキーマと説明文書、
`plugins/pptxdsl/.codex-plugin/plugin.json`、`plugins/pptxdsl/.claude-plugin/plugin.json`。
Plugin専用のrendererやSkill複製を管理しない。
ビルド時に正本を集め、`skills/pptxdsl/project/`へ必要なPPTX生成コード・素材・依存一覧・ライセンスを同梱する。
テスト、回帰入力、開発ツール、ローカル設定、生成デッキは配布へ含めない。
PPTX生成コードと素材はGit追跡対象だけを同梱し、未追跡の利用者画像などは公開しない。

Portable形式の`plugin.json`を生成し、`.codex-plugin/plugin.json`と`.claude-plugin/plugin.json`も同梱する。
表示情報は互換manifestを正本としてPortable側の`extensions.com.openai.interface`へ反映する。
形式と固定の`skills/`検出については[公式のPluginパッケージ仕様](https://developers.openai.com/plugins/build/plugins)を参照する。

## 導入と受け入れ確認

### Codexでの導入

ChatGPT向けとCodex向けでSkillやrendererを分岐させない。同じ配布物にCodex用の
`.codex-plugin/plugin.json`と`skills/pptxdsl/`が入っている。
リポジトリの`plugins/pptxdsl/`はmetadataの正本だけなので、そのままインストールせず、
ビルド済みの`out/plugins/pptxdsl/`またはZIPを展開したPluginルートを使用する。

1. Codexへ次のように依頼し、個人設定を変更する承認を与える。
   「`$plugin-creator`で、このビルド済みpptxdsl Pluginを個人marketplaceへ登録してください。
   同梱SkillとPPTX生成コードを保持し、既存Plugin・marketplace項目は上書きしないでください。」
2. 登録後、Codexを再読み込みし、Plugins Directoryの個人タブからpptxdslをインストールする。
   CLIが利用できる場合は、登録済みmarketplaceの実際の名前で以下を実行して確認できる。

   ```text
   codex plugin list --marketplace <marketplace名> --available --json
   codex plugin add pptxdsl@<marketplace名> --json
   codex plugin list --marketplace <marketplace名> --json
   ```

3. 新しいタスクで「pptxdsl Pluginで、添付資料と要件から目視確認済みのPPTXを作って」と依頼する。
   リポジトリ内のSkillを直接読ませる試験と混同しないよう、cloneを開いていない作業領域でも確認する。

標準の個人marketplaceは暗黙に検出されるため、`codex plugin marketplace add`は不要。
利用者が別のmarketplaceを指定した場合だけ、その配布元の登録が必要になる。
更新時は登録元のPluginを更新し、plugin-creatorのcachebuster・再インストール手順を使って
新しいタスクで確認する。生成物だけでなくCodexのPlugin一覧でインストール済みか確認する。
個人設定への登録・インストールは、配布ビルドとは別の操作であり、ビルド時に自動実行しない。
Pluginの導入と新しい会話での利用は[公式のPlugin利用ガイド](https://learn.chatgpt.com/docs/plugins)を参照する。

### Claude Codeでの導入

`.claude-plugin/marketplace.json`は、GitHub ReleaseのPlugin ZIPをバージョン付きURLとSHA-256で固定する。
Claude Code 2.1.224以上で次を実行する。

```text
/plugin marketplace add thinas1115/pptxdsl
/plugin install pptxdsl@pptxdsl-marketplace
```

Plugin ZIPの直下には`.claude-plugin/plugin.json`と`skills/pptxdsl/`がある。
Claude Codeが再読み込みを求めた場合は`/reload-plugins`を実行する。
Skillを明示する場合は`/pptxdsl:pptxdsl`を使う。個人用Skillとして導入する場合は、
同じReleaseのSkill ZIPを`~/.claude/skills/`へ展開し、`/pptxdsl`で呼び出す。

Marketplaceの`version`、Plugin manifestの`version`、Releaseタグ、ZIP名は同じ版にそろえる。
`sha256`には、その版のPlugin ZIPをビルドして得た値を記録する。値が違う場合、Claude Codeは導入を拒否する。
仕様は[Claude Code Plugins](https://code.claude.com/docs/en/plugins)と
[Plugin Marketplace](https://code.claude.com/docs/en/plugin-marketplaces)を参照する。

### ChatGPT Workでの導入

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
同梱Skillの[Release配布の実行環境](../.agents/skills/pptxdsl/references/bundled-runtime.md)に前提条件と
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
Codexでも同様に、配布物の隔離実行が成功しただけでPluginの登録・インストール済みとは扱わない。
