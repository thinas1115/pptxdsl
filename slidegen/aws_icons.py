"""同梱AWS公式アイコンを名称検索する: python -m slidegen.aws_icons AppSync。"""
import argparse
import json
import re
from functools import lru_cache

from slidegen.asset_paths import AWS_ICON_DIR


@lru_cache(maxsize=1)
def catalog():
    return json.loads((AWS_ICON_DIR / 'catalog.json').read_text(encoding='utf-8'))['icons']


def normalize(value):
    return re.sub(r'[^a-z0-9]', '', value.casefold())


@lru_cache(maxsize=1)
def service_icons():
    result = {}
    for icon in catalog():
        if icon['format'] != 'png' or icon['kind'] != 'service':
            continue
        name = re.sub(r'^(?:AWS|Amazon)\s+', '', icon['label'])
        key = normalize(name)
        result.setdefault(key, []).append(icon['path'])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('query', nargs='?', default='')
    args = parser.parse_args()
    query = normalize(args.query)
    for icon in catalog():
        if query in normalize(icon['label']):
            print(f"{icon['label']}\t{icon['path']}")


if __name__ == '__main__':
    main()
