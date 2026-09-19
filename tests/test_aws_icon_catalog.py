"""主要公式素材の一覧、重複除外、無改変ハッシュ、検索を確認する。"""
import hashlib

from slidegen.asset_paths import AWS_ICON_DIR, resolve_icon_path
from slidegen.aws_icons import catalog, service_icons
from slidegen.aws_icon_policy import icon_policy_error


def main():
    icons = catalog()
    assert 80 <= len(icons) <= 120
    assert all(icon['format'] == 'png' for icon in icons)
    assert all('Dark' not in icon['path'] and 'Light' not in icon['path'] for icon in icons)
    assert len({icon['sha256'] for icon in icons}) == len(icons)
    assert len({icon['path'] for icon in icons}) == len(icons)
    assert {resolve_icon_path(icon['path']) for icon in icons} == {path.resolve() for path in AWS_ICON_DIR.rglob('*.png')}
    assert not list(AWS_ICON_DIR.rglob('*.svg'))
    for icon in icons:
        path = resolve_icon_path(icon['path'])
        assert hashlib.sha256(path.read_bytes()).hexdigest() == icon['sha256'], icon['path']
    services = service_icons()
    assert services['appsync'] and services['ec2'] and services['lambda']
    assert not icon_policy_error('AWS AppSync', services['appsync'][0])
    assert icon_policy_error('Amazon EC2', 'icons/fluent/server.png')
    assert not icon_policy_error('実行環境', services['ec2'][0], 'ec2')
    assert 'braket' not in services and 'groundstation' not in services
    print(f'AWS公式素材: {len(icons)}PNGの無改変ハッシュ・重複除外・検索を確認')


if __name__ == '__main__':
    main()
