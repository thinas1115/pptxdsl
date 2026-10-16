"""主要5デッキで文字幅キャッシュの導入前と試作を比較する。"""
import argparse
from functools import lru_cache
import gc
import hashlib
import importlib
import json
from pathlib import Path
import statistics
import time
import tracemalloc
from zipfile import ZipFile

from slidegen import textfit


def deck_digest(path):
    """ZIP日時ではなく全内部パーツを照合する。"""
    digest = hashlib.sha256()
    with ZipFile(path) as package:
        for name in sorted(package.namelist()):
            digest.update(name.encode("utf-8"))
            digest.update(b"\0")
            digest.update(package.read(name))
    return digest.hexdigest()


def benchmark(output, mode, repeats):
    original = textfit.text_width_in
    counters = {"calls": 0, "measurements": 0}

    def measure(text, size, weight):
        counters["measurements"] += bool(text)
        return original(text, size, weight)

    @lru_cache(maxsize=4096)
    def prototype(text, size, weight, face, safety):
        return measure(text, size, weight)

    def measured(text, size, weight="regular"):
        counters["calls"] += 1
        if mode == "prototype" and text and len(text) <= 1024:
            return prototype(text, size, weight, textfit.font_face(weight), textfit.width_safety(weight))
        return measure(text, size, weight)

    # rendererが関数をimportする前に差し替え、checkerも同じ条件で測る。
    textfit.text_width_in = measured
    from slidegen.check_layout import check
    from tools.quality.cross_platform import DECKS, environment
    from slidegen.font_config import describe
    builders = [(name, importlib.import_module(f"tools.gallery.generate_{name}").main) for name in DECKS]
    for weight in ("regular", "bold", "code"):
        textfit._font(weight, 12)

    def run(directory):
        directory.mkdir(parents=True, exist_ok=True)
        decks = []
        for name, build in builders:
            path = directory / f"{name}.pptx"
            build(path)
            findings = check(path)
            if findings:
                raise ValueError(f"{name}の機械検査が不合格です")
            decks.append({"name": name, "parts_sha256": deck_digest(path), "findings": findings})
        return decks

    rows = []
    for index in range(repeats):
        gc.collect()
        prototype.cache_clear()
        counters.update(calls=0, measurements=0)
        started = time.perf_counter()
        decks = run(output / f"run-{index + 1}")
        rows.append({"seconds": time.perf_counter() - started, **counters,
                     "cache": prototype.cache_info()._asdict(), "decks": decks})
    # 時間とメモリを別実行にし、tracemalloc自体の負荷を速度測定へ混ぜない。
    gc.collect()
    prototype.cache_clear()
    tracemalloc.start()
    run(output / "memory")
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    result = {"mode": mode, "environment": environment(), "fonts": describe(),
              "median_seconds": statistics.median(row["seconds"] for row in rows),
              "tracemalloc_current_bytes": current, "tracemalloc_peak_bytes": peak,
              "cache_max_entries": 4096, "cache_max_text_characters": 1024, "runs": rows}
    (output / "benchmark.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{mode}: 中央値{result['median_seconds']:.3f}秒、Python割当peak {peak / 1024 / 1024:.2f}MiB")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("current", "prototype"))
    parser.add_argument("output", type=Path)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("repeatsは1以上にしてください")
    benchmark(args.output, args.mode, args.repeats)
