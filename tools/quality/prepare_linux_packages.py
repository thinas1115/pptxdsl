"""GitHub Actions Linux専用。遅延したAzureミラーを公式ミラーへ切替えて依存を導入する。"""
import argparse
import os
from pathlib import Path
import platform
import re
import subprocess


MIRROR_FILES = (Path("/etc/apt/apt-mirrors.txt"), Path("/etc/apt/sources.list"),
                Path("/etc/apt/sources.list.d/ubuntu.sources"))
APT_OPTIONS = ("-o", "Acquire::Retries=3", "-o", "Acquire::http::Timeout=30",
               "-o", "Acquire::https::Timeout=30")


def mirror_text(text: str) -> str:
    return text.replace("http://azure.archive.ubuntu.com/ubuntu", "https://archive.ubuntu.com/ubuntu").replace(
        "https://azure.archive.ubuntu.com/ubuntu", "https://archive.ubuntu.com/ubuntu")


def prepare(packages: list[str]) -> None:
    if platform.system() != "Linux" or os.environ.get("GITHUB_ACTIONS") != "true":
        raise ValueError("このツールはGitHub ActionsのLinuxジョブ専用です。ローカルでは実行しません")
    if not packages or any(not re.fullmatch(r"[a-z0-9][a-z0-9+.-]*", p) for p in packages):
        raise ValueError("導入するAPTパッケージ名を指定してください")
    changed = 0
    for path in MIRROR_FILES:
        if path.is_symlink() or not path.is_file():
            continue
        before = path.read_text(encoding="utf-8")
        after = mirror_text(before)
        if after != before:
            subprocess.run(["sudo", "tee", str(path)], input=after, text=True,
                           capture_output=True, check=True, timeout=15)
            changed += 1
    print(f"APTミラー設定: {changed}件を公式Ubuntuミラーへ切替え", flush=True)
    subprocess.run(["sudo", "apt-get", *APT_OPTIONS, "update"], check=True, timeout=480)
    subprocess.run(["sudo", "apt-get", *APT_OPTIONS, "install", "--no-install-recommends", "-y", *packages],
                   check=True, timeout=480)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packages", nargs="+")
    args = parser.parse_args()
    try:
        prepare(args.packages)
    except ValueError as error:
        raise SystemExit(f"NG: {error}") from None
    except (OSError, subprocess.SubprocessError):
        raise SystemExit("NG: Linux依存の準備に失敗しました。APTログを確認してください。検証は未完了です") from None


if __name__ == "__main__":
    main()
