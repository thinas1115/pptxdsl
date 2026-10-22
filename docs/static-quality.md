# 静的検査と分岐coverage

通常の生成用依存と品質検査用依存は分ける。検査ツールと間接依存は
`requirements-quality.txt`へ固定し、ローカルとWindows／Ubuntu CIで同じ入口を使う。

```powershell
python -m pip install -r requirements.txt -r requirements-quality.txt
python -m tools.quality.static_gate
python -m tools.quality.static_gate --coverage
```

## 検査範囲と移行順

- Ruffの`E9`／`F`で`slidegen/`全体の構文・未定義名・未使用変数・未使用importを検査する。
  既存エラーを基準ファイルで黙認せず、最初に検出した5件を除去した。
- mypyのstrict検査は数値入力モデル`chart_model.py`と、renderer共通の収容API`layout_fit.py`から始め、
  共通設定、ネットワーク・担当フロー・プロトコル・工程表の配置計画、構成図の入力契約へ広げている。
  引数、戻り値、収容候補、計測callbackを型付けし、対象を`mypy.ini`へ明記する。
  `follow_imports = skip`は未移行の描画・フォントモジュールまで一括で型検査しないための境界であり、
  リポジトリ全体の型安全性を保証する設定ではない。
- Ruff formatterは型検査対象の8モジュールと検査の入口に適用する。
  大きなrendererや既存テストを一括整形し、機能差分へ混ぜない。

新規・変更runtimeには同じ基本lintを必須とする。新しい入力境界や純粋な配置計算は引数・戻り値を型付けし、
mypyとformatterの対象へ追加する。既存rendererの移行は、入力モデル、配置計算、描画adapterの順にモジュール単位で行う。
テスト・開発ツールも変更範囲を`python -m ruff check <対象>`で検査する。
例外は理由・対象・解消条件をPRへ記録し、ファイル全体への`noqa`や型検査の包括無効化で回避しない。

## coverageの読み方

`--coverage`は全テストを実行し、子Pythonプロセスも分岐計測して結合する。
実行結果は`out/coverage/tests.json`、欠落行・分岐はHTML／JSON／XMLへ保存する。
検査コマンドやテストの失敗はジョブ失敗とするが、初期導入時は全体の到達率だけを合否線にしない。

特に次を確認し、変更した失敗経路が未到達なら真値付きのテストを追加する。

| 対象 | 確認する経路 |
|---|---|
| `validate_content.py`、`generate_from_json.py` | 未知キー、型・件数、参照不整合、不正JSON、安全なエラー終了 |
| `check_layout.py`、`text_metrics.py` | 意図的な枠外・衝突・文字切れを拒否し、正常例を誤拒否しない |
| `layout_fit.py`、各renderer | 標準、余白圧縮、縮小、最小値でも収まらないFitError |

coverageは「実行された」範囲であり、検証の正確性・目視QA・人の承認とは別である。
OS固有処理や外部アプリの不在による未到達を無条件に除外せず、実行環境とskip理由を併記する。
除外を増やして数値だけを上げない。測定データ、キャッシュ、レポートはGitへ入れない。

初回のWindows／Python 3.13計測では全59テストモジュールが成功し、runtimeの行・分岐の合算は87%だった。
未到達だった「空の収容候補・空stack・改行判定の不合格」と「軸書式・非有限Decimalの拒否」へ
真値付き4試験を追加した。validatorは73%、文字矩形推定は78%であり、これらを完全検証済みとは扱わない。
構造schemaの移行・入力境界の変更時は、HTMLの欠落行・分岐を使って該当する不正入力を追加する。
テストを起動する親プロセスにruntime実行がない場合の`no-data-collected`警告と、子の結合後の実測結果は区別する。

設定の根拠は[Ruff](https://docs.astral.sh/ruff/configuration/)、
[mypy](https://mypy.readthedocs.io/en/stable/config_file.html)、
[coverageの子プロセス計測](https://coverage.readthedocs.io/en/latest/subprocess.html)を参照。
