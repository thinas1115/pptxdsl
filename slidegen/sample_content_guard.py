"""回帰検証用サンプルの文言が通常デッキへ混入するのを検出する。"""
import re
import json
import unicodedata
from functools import lru_cache
from pathlib import Path


MIN_FINGERPRINT_LENGTH = 14
_JAPANESE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
_SEPARATORS = re.compile(
    r"[\s\u3000、。，．・:：;；!?！？/\\|\-‐‑–—_()（）\[\]［］{}｛｝"
    r"「」『』【】〈〉《》]+"
)
_TECHNICAL_KEYS = {
    "type", "icon", "image", "fit", "style", "kind", "from", "to",
    "via", "col", "row", "from_row", "to_row", "channel",
}


def _normalize(text):
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return _SEPARATORS.sub("", normalized)


def _strings(value, path=""):
    if isinstance(value, str):
        yield path or "トップレベル", value
    elif isinstance(value, dict):
        for key, child in value.items():
            if key in _TECHNICAL_KEYS:
                continue
            child_path = f"{path}.{key}" if path else key
            yield from _strings(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _strings(child, f"{path}[{index}]")


@lru_cache(maxsize=1)
def sample_fingerprints():
    """同梱の混入検出辞書を読む。テスト専用の内容モジュールは読み込まない。"""
    path = Path(__file__).with_name("data") / "sample_fingerprints.json"
    return json.loads(path.read_text(encoding="utf-8"))


def sample_reuse_paths(deck):
    """通常デッキ内の、回帰サンプルと一致する文言を列挙する。"""
    fingerprints = sample_fingerprints()
    for path, text in _strings(deck):
        normalized = _normalize(text)
        if normalized in fingerprints:
            yield path, fingerprints[normalized]
