"""回帰用文言の混入検出辞書を再生成・検証する。"""
import argparse
import json
from pathlib import Path

from slidegen.sample_content_guard import MIN_FINGERPRINT_LENGTH, _JAPANESE, _normalize, _strings
from tests.fixtures.gallery.content import DECK
from tests.fixtures.gallery.content_ext import EXTRA_SLIDES
from tests.fixtures.gallery.content_lead_patterns import LEAD_PATTERN_DECK
from tests.fixtures.gallery.content_patterns import PATTERN_DECK
from tests.fixtures.gallery.content_stress_patterns import STRESS_PATTERN_DECK
from tests.fixtures.gallery.diagram_specs import AWS_MULTIAZ_EXAMPLE, AWS_SIMPLE_EXAMPLE

OUTPUT = Path(__file__).resolve().parents[2] / "slidegen" / "data" / "sample_fingerprints.json"


def build():
    fingerprints = {}
    sources = (DECK, {"slides": EXTRA_SLIDES}, PATTERN_DECK, LEAD_PATTERN_DECK,
               STRESS_PATTERN_DECK, AWS_SIMPLE_EXAMPLE, AWS_MULTIAZ_EXAMPLE)
    for source in sources:
        for _, text in _strings(source):
            normalized = _normalize(text)
            if len(normalized) >= MIN_FINGERPRINT_LENGTH and _JAPANESE.search(normalized):
                fingerprints.setdefault(normalized, " ".join(text.split()))
    return fingerprints


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="辞書の更新漏れを検査する")
    args = parser.parse_args()
    expected = build()
    if args.check:
        if not OUTPUT.is_file() or json.loads(OUTPUT.read_text(encoding="utf-8")) != expected:
            raise SystemExit("NG: python -m tools.gallery.build_sample_fingerprints で辞書を更新してください。")
        print("OK: 混入検出辞書")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(expected, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8")
        print(f"OK: {len(expected)} 件の混入検出辞書を生成")


if __name__ == "__main__":
    main()
