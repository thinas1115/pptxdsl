"""AWSサービスの識別名と同梱公式アイコンの対応。"""
import re
import unicodedata

from slidegen.asset_paths import AWS_ICON_DIR, resolve_icon_path
from slidegen.aws_icons import normalize, service_icons


_SERVICE_NAMES = {
    "appsync": ("AppSync", "AWS AppSync"),
    "lambda": ("Lambda", "AWS Lambda"),
    "dynamodb": ("DynamoDB", "Amazon DynamoDB"),
    "s3": ("S3", "Amazon S3"),
    "rds": ("RDS", "Amazon RDS"),
    "cloudfront": ("CloudFront", "Amazon CloudFront"),
    "cloudwatch": ("CloudWatch", "Amazon CloudWatch"),
    "sqs": ("SQS", "Amazon SQS"),
    "ecr": ("ECR", "Amazon ECR"),
    "ecs": ("ECS", "Amazon ECS"),
    "eks": ("EKS", "Amazon EKS"),
    "fargate": ("Fargate", "AWS Fargate"),
    "bedrock": ("Bedrock", "Amazon Bedrock"),
    "route53": ("Route 53", "Amazon Route 53"),
}
_CATALOG_KEYS = {"s3": "simplestorageservice"}


def _service_choices(value):
    key = normalize(re.sub(r"^(?:AWS|Amazon)\s+", "", value, flags=re.I))
    return service_icons().get(_CATALOG_KEYS.get(key, key), [])


def _normalize(value):
    return re.sub(r"[\s_-]+", "", unicodedata.normalize("NFKC", value).casefold())


def official_icon(label, service=None):
    """明示service、または曖昧でないサービス名から公式アイコンを返す。"""
    key = _normalize(service) if service else None
    if key:
        if not re.fullmatch(r"[a-z0-9]+", key):
            raise ValueError("serviceは同梱AWSアイコンの識別名にしてください")
        # ファイル名に含まれるアンダースコアは正規化前のserviceを使う。
        filename = service.strip().lower().replace("-", "_")
        path = AWS_ICON_DIR / f"{filename}.png"
        if path.is_file():
            return f"icons/aws/{filename}.png"
        choices = _service_choices(service)
        if choices:
            return max(choices, key=lambda value: ('64@5x' in value, '64' in value, value))
        raise ValueError("serviceに対応するAWS公式アイコンがありません。python -m slidegen.aws_iconsで一覧を確認してください")
    normalized = _normalize(label)
    for filename, names in _SERVICE_NAMES.items():
        if normalized in {_normalize(name) for name in names}:
            if (AWS_ICON_DIR / f"{filename}.png").is_file():
                return f"icons/aws/{filename}.png"
    # WAF、Backupなど一般製品にも使う語はAWS所属を名前だけで断定しない。
    choices = _service_choices(label) if re.match(r"^(?:AWS|Amazon)\s+", label, flags=re.I) else []
    return max(choices, key=lambda value: ('64@5x' in value, '64' in value, value)) if choices else None


def icon_policy_error(label, icon, service=None):
    expected = official_icon(label, service)
    choices = _service_choices(service or label)
    if expected and resolve_icon_path(icon) not in {resolve_icon_path(path) for path in [expected, *choices]}:
        return f'AWSサービスには公式アイコン "{expected}" を指定してください'
    return None
