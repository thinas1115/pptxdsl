"""入力JSONを読み取り、端末固有パスを出さず修正方法を伝える。"""
import json
from pathlib import Path


def load_content_json(path):
    source = Path(path)
    try:
        raw = source.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SystemExit(
            f"NG: 入力JSONが見つかりません: {source.name}\n"
            "  AI_DECK_PROMPT.md と CONTENT_SCHEMA.md に従ってcontent.jsonを作成し、入力指定を確認してください。") from None
    except UnicodeDecodeError:
        raise SystemExit(f"NG: {source.name} はUTF-8で保存してください。") from None
    except OSError:
        raise SystemExit("NG: 入力JSONを読み取れません。通常のファイルか、読み取り権限があるか確認してください。") from None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as error:
        raise SystemExit(
            f"NG: {source.name} のJSON構文が不正です (行{error.lineno}, 列{error.colno})。"
            "指定位置の括弧、カンマ、引用符を修正して再実行してください。") from None
