"""回帰検証用サンプルの文言が通常デッキへ混入するのを検出する。"""
import re
import unicodedata
from functools import lru_cache


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


def _sample_sources():
    # 遅延importにして、通常のschema検証起動時だけ回帰データを読み込む。
    from content import DECK
    from content_ext import EXTRA_SLIDES
    from content_lead_patterns import LEAD_PATTERN_DECK
    from content_patterns import PATTERN_DECK
    from content_stress_patterns import STRESS_PATTERN_DECK
    from diagram_specs import AWS_MULTIAZ_EXAMPLE, AWS_SIMPLE_EXAMPLE

    return (
        DECK,
        {"slides": EXTRA_SLIDES},
        PATTERN_DECK,
        LEAD_PATTERN_DECK,
        STRESS_PATTERN_DECK,
        AWS_SIMPLE_EXAMPLE,
        AWS_MULTIAZ_EXAMPLE,
    )


@lru_cache(maxsize=1)
def sample_fingerprints():
    """正規化したサンプル文言から、表示用の原文への辞書を返す。"""
    fingerprints = {}
    for source in _sample_sources():
        for _, text in _strings(source):
            normalized = _normalize(text)
            if (len(normalized) >= MIN_FINGERPRINT_LENGTH
                    and _JAPANESE.search(normalized)):
                fingerprints.setdefault(normalized, " ".join(text.split()))
    return fingerprints


def sample_reuse_paths(deck):
    """通常デッキ内の、回帰サンプルと一致する文言を列挙する。"""
    fingerprints = sample_fingerprints()
    for path, text in _strings(deck):
        normalized = _normalize(text)
        if normalized in fingerprints:
            yield path, fingerprints[normalized]
