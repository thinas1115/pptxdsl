"""主要サービスと基本リソースの公式PNGを1絵柄1件で同梱する。"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

from slidegen.asset_paths import AWS_ICON_DIR

# 基本構成・アプリ実装・データ基盤・運用の説明に使う収録対象。
# 利用頻度の統計ではなく、配布素材の編集方針として管理する。
SERVICES = set('''appsync apigateway lambda ec2 ec2autoscaling elasticcontainerservice
elasticcontainerregistry elastickubernetesservice fargate batch amplify aurora rds
dynamodb elasticache documentdb simplestorageservice efs elasticblockstore fsx
cloudfront route53 virtualprivatecloud elasticloadbalancing directconnect
transitgateway privatelink clientvpn sitetositevpn globalaccelerator networkfirewall
verifiedaccess cloudwan vpclattice simplequeueservice simplenotificationservice
eventbridge stepfunctions simpleemailservice cloudwatch cloudtrail xray config
systemsmanager cloudformation clouddevelopmentkit codebuild codedeploy codepipeline
identityandaccessmanagement iamidentitycenter cognito keymanagementservice
secretsmanager certificatemanager waf shield guardduty securityhub inspector
organizations controltower backup costexplorer budgets bedrock sagemakerai
athena glue redshift emr kinesisdatastreams datafirehose managedstreamingforapachekafka
opensearchservice lakeformation databasemigrationservice datasync transferfamily'''.split())
ALIASES = {
    'elasticcontainerservice': 'ecs', 'elasticcontainerregistry': 'ecr',
    'elastickubernetesservice': 'eks', 'simplestorageservice': 's3',
    'simplequeueservice': 'sqs', 'virtualprivatecloud': 'vpc',
    'directconnect': 'direct_connect', 'transitgateway': 'transit_gateway',
    'clientvpn': 'client_vpn', 'sitetositevpn': 'site_to_site_vpn',
    'globalaccelerator': 'global_accelerator', 'networkfirewall': 'network_firewall',
    'verifiedaccess': 'verified_access', 'cloudwan': 'cloud_wan', 'vpclattice': 'vpc_lattice',
}


def label_for(path):
    label = re.sub(r'_(?:16|32|48|64)(?:@\dx)?(?:_(?:Dark|Light))?$', '', path.stem)
    return re.sub(r'^(?:Arch|Res|Arch-Category)_', '', label).replace('-', ' ')


def service_key(label):
    return re.sub(r'[^a-z0-9]', '', re.sub(r'^(?:AWS|Amazon)\s+', '', label).casefold())


def import_package(source):
    source = Path(source)
    if not source.is_dir():
        raise ValueError('展開済みのAWS公式Icon packageを指定してください')
    files = sorted(p for p in source.rglob('*')
                   if p.is_file() and p.suffix.lower() == '.png'
                   and not any(part.startswith('.') or part == '__MACOSX'
                               for part in p.relative_to(source).parts))
    if not files:
        raise ValueError('公式PNG・SVGが見つかりません')
    selected = {}
    for path in files:
        relative = path.relative_to(source)
        if 'Dark' in relative.as_posix() or 'Light' in relative.as_posix():
            continue
        label = label_for(path)
        key = service_key(label)
        if not relative.parts[0].startswith('Architecture-Service-Icons_') or key not in SERVICES:
            continue
        score = ('64@5x' in path.stem, '_64' in path.stem)
        previous = selected.get(key)
        if previous is None or score > previous[0]:
            selected[key] = (score, path, label)
    missing = SERVICES - selected.keys()
    if missing:
        raise ValueError('指定サービスが公式パッケージにありません: ' + ', '.join(sorted(missing)))
    entries = []
    indexed = set()
    for key, (_, path, label) in sorted(selected.items()):
        alias = ALIASES.get(key, key)
        existing = AWS_ICON_DIR / f'{alias}.png'
        if existing.is_file():
            entries.append({'label': label, 'path': f'icons/aws/{alias}.png',
                            'source': f'existing/{alias}.png', 'kind': 'service', 'format': 'png',
                            'service': key, 'sha256': hashlib.sha256(existing.read_bytes()).hexdigest()})
            indexed.add(alias)
            continue
        relative = path.relative_to(source)
        target = AWS_ICON_DIR / 'official' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_bytes() != path.read_bytes():
            raise ValueError('既存素材と異なるファイルがあるため停止しました')
        shutil.copyfile(path, target)
        entries.append({'label': label, 'path': 'icons/aws/official/' + relative.as_posix(),
                        'source': relative.as_posix(), 'kind': 'service', 'service': key, 'format': 'png',
                        'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    for path in sorted(AWS_ICON_DIR.glob('*.png')):
        if path.stem in indexed:
            continue
        entries.append({'label': path.stem.replace('_', ' '), 'path': f'icons/aws/{path.name}',
                        'source': f'existing/{path.name}', 'kind': 'resource', 'format': 'png',
                        'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    catalog = {'source': 'https://aws.amazon.com/architecture/icons/',
               'package': sorted({p.relative_to(source).parts[0] for p in files}),
               'selection': {'services': sorted(SERVICES), 'variants': '1絵柄1PNG・明暗違いなし'},
               'icons': entries}
    (AWS_ICON_DIR / 'catalog.json').write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'主要サービス{len(SERVICES)}種と基本リソース、計{len(entries)}PNGを収録しました')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', help='展開済み公式Icon package')
    args = parser.parse_args()
    import_package(args.package)


if __name__ == '__main__':
    main()
