"""AWSサービス名・識別名と公式アイコンの一致を検証する。"""
from copy import deepcopy

from slidegen.aws_icon_policy import icon_policy_error
from slidegen.validate_content import validate
from tests.fixtures.gallery.content_patterns import PATTERN_DECK


def main():
    assert icon_policy_error('AppSync', 'icons/fluent/cloud.png')
    assert icon_policy_error('AWS AppSync', 'icons/aws/s3.png')
    assert not icon_policy_error('AppSync', 'icons/aws/appsync.png')
    assert icon_policy_error('Event API', 'icons/fluent/cloud.png', 'appsync')
    assert not icon_policy_error('Event API', 'icons/aws/appsync.png', 'appsync')
    assert not icon_policy_error('データソース', 'icons/fluent/database.png')
    assert not icon_policy_error('WAF', 'icons/fluent/shield.png')
    assert icon_policy_error('AWS WAF', 'icons/fluent/shield.png')
    spec = deepcopy(next(s for s in PATTERN_DECK['slides'] if s['type'] == 'diagram'))
    node = next(iter(spec['diagram']['nodes'].values()))
    node.update(title='Event API', service='appsync', icon='icons/aws/appsync.png')
    deck = {'meta': {'title': '検証'}, 'slides': [spec]}
    assert not validate(deck, allow_sample_content=True)
    node['icon'] = 'icons/fluent/cloud.png'
    assert any('icons/aws/appsync.png' in error for error in validate(deck, allow_sample_content=True))
    for service in ('../appsync', 'unknown', [], ''):
        node['service'] = service
        assert any('service' in error for error in validate(deck, allow_sample_content=True))
    print('AWS公式アイコン: サービス名・明示識別名・一般概念の検証を確認')


if __name__ == '__main__':
    main()
