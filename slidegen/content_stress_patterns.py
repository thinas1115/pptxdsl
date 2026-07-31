"""段階的縮小が実際に発動する大規模入力の検証デッキ。"""


TABLE_ROWS = [
    [
        f"領域 {i + 1}",
        "運用部門と開発部門で確認する。" * 3,
        "運用部門と開発部門で確認する。" * 3,
        "運用部門と開発部門で確認する。" * 3,
    ]
    for i in range(5)
]


def _large_diagram():
    nodes = {
        "user": {"col": "external", "row": "north", "icon": "icons/fluent/people.png",
                 "title": "社内利用者"},
        "dns": {"col": "edge", "row": "north", "icon": "icons/fluent/globe.png",
                "title": "DNS"},
        "config": {"col": "security", "row": "north", "icon": "icons/fluent/settings.png",
                   "title": "構成管理"},
        "idp": {"col": "app", "row": "north", "icon": "icons/fluent/key.png",
                "title": "ID基盤"},
        "audit": {"col": "data", "row": "north", "icon": "icons/fluent/history.png",
                  "title": "監査サービス"},
        "cdn": {"col": "edge", "row": "web", "icon": "icons/fluent/cloud.png",
                "title": "CDN"},
        "waf": {"col": "security", "row": "web", "icon": "icons/fluent/shield.png",
                "title": "WAF"},
        "alb": {"col": "app", "row": "web", "icon": "icons/fluent/gateway.png",
                "title": "ロードバランサ"},
        "api": {"col": "service", "row": "web", "icon": "icons/fluent/app.png",
                "title": "業務API"},
        "portal": {"col": "data", "row": "web", "icon": "icons/fluent/browser.png",
                   "title": "業務ポータル"},
        "notify": {"col": "edge", "row": "async", "icon": "icons/fluent/mail.png",
                   "title": "通知サービス"},
        "queue": {"col": "security", "row": "async", "icon": "icons/fluent/task.png",
                  "title": "処理キュー"},
        "worker_a": {"col": "app", "row": "async", "icon": "icons/fluent/server.png",
                     "title": "ワーカーA"},
        "worker_b": {"col": "service", "row": "async", "icon": "icons/fluent/server.png",
                     "title": "ワーカーB"},
        "cache": {"col": "data", "row": "async", "icon": "icons/fluent/storage.png",
                  "title": "キャッシュ"},
        "archive": {"col": "edge", "row": "storage", "icon": "icons/fluent/archive.png",
                    "title": "長期保管"},
        "backup": {"col": "security", "row": "storage", "icon": "icons/fluent/sync.png",
                   "title": "バックアップ"},
        "db_a": {"col": "app", "row": "storage", "icon": "icons/fluent/database.png",
                 "title": "DB Primary"},
        "db_b": {"col": "service", "row": "storage", "icon": "icons/fluent/database.png",
                 "title": "DB Standby"},
        "monitor": {"col": "data", "row": "storage", "icon": "icons/fluent/monitor.png",
                    "title": "統合監視"},
    }
    return {
        "cols": ["external", "edge", "security", "app", "service", "data"],
        "rows": ["north", "web", "async", "storage"],
        "nodes": nodes,
        "containers": [
            {"name": "cloud", "label": "業務クラウド",
             "members": ["dns", "config", "idp", "audit", "cdn", "notify",
                         "archive", "@public", "@private"]},
            {"name": "public", "label": "公開サービス",
             "members": ["waf", "alb", "api", "portal"], "dash": "dash"},
            {"name": "private", "label": "非公開サービス",
             "members": ["queue", "worker_a", "worker_b", "cache", "backup",
                         "db_a", "db_b", "monitor"], "dash": "dash"},
        ],
        "channels": {
            "public_entry": ["outside_container", ["public", "top_inside"]],
            "private_entry": ["outside_container", ["private", "top_inside"]],
            "private_right": ["outside_container", ["private", "right"]],
            "cloud_right": ["outside_container", ["cloud", "right"]],
        },
        "edges": [
            {"from": "user", "to": "dns", "label": "DNS"},
            {"from": "user", "to": "cdn", "label": "HTTPS"},
            {"from": "dns", "to": "cdn", "exit": "bottom", "enter": "top",
             "via": ["public_entry"], "dash": "dash"},
            {"from": "cdn", "to": "waf", "label": "HTTPS"},
            {"from": "waf", "to": "alb"},
            {"from": "alb", "to": "api"},
            {"from": "api", "to": "portal"},
            {"from": "config", "to": "idp", "label": "ポリシー", "dash": "dash"},
            {"from": "idp", "to": "api", "exit": "bottom", "enter": "top",
             "via": ["public_entry"], "label": "認証", "dash": "dash"},
            {"from": "api", "to": "queue", "exit": "bottom", "enter": "top",
             "via": ["private_entry"]},
            {"from": "api", "to": "worker_a", "exit": "bottom", "enter": "top",
             "via": ["private_entry"]},
            {"from": "api", "to": "worker_b", "exit": "bottom", "enter": "top",
             "via": ["private_entry"]},
            {"from": "queue", "to": "notify"},
            {"from": "worker_b", "to": "cache"},
            {"from": "worker_a", "to": "db_a", "exit": "bottom", "enter": "top"},
            {"from": "worker_b", "to": "db_b", "exit": "bottom", "enter": "top"},
            {"from": "db_a", "to": "db_b", "both": True, "dash": "dash",
             "label": "同期"},
            {"from": "backup", "to": "db_a", "label": "復旧"},
            {"from": "backup", "to": "archive"},
            {"from": "audit", "to": "monitor", "exit": "right", "enter": "right",
             "via": ["cloud_right"], "dash": "dash"},
        ],
    }


LARGE_DIAGRAM = _large_diagram()


def _large_aws_diagram():
    return {
        "cols": ["external", "edge", "ingress", "compute_a", "compute_b", "data"],
        "rows": ["global", "web", "app", "data"],
        "nodes": {
            "user": {"col": "external", "row": "web", "icon": "icons/aws/users.png",
                     "title": "社内利用者"},
            "r53": {"col": "edge", "row": "global", "icon": "icons/aws/route53.png",
                    "title": "Route 53"},
            "ecr": {"col": "compute_a", "row": "global", "icon": "icons/aws/ecr.png",
                    "title": "Amazon ECR"},
            "bedrock": {"col": "compute_b", "row": "global", "icon": "icons/aws/bedrock.png",
                        "title": "Amazon Bedrock"},
            "knowledge": {"col": "data", "row": "global", "icon": "icons/aws/s3.png",
                          "title": "S3 Knowledge"},
            "cf": {"col": "edge", "row": "web", "icon": "icons/aws/cloudfront.png",
                   "title": "CloudFront"},
            "alb": {"col": "ingress", "row": "web", "icon": "icons/aws/alb.png",
                    "title": "ALB"},
            "api": {"col": "compute_a", "row": "web", "icon": "icons/aws/fargate.png",
                    "title": "API Fargate"},
            "queue": {"col": "ingress", "row": "app", "icon": "icons/aws/sqs.png",
                      "title": "Amazon SQS"},
            "worker_a": {"col": "compute_a", "row": "app", "icon": "icons/aws/fargate.png",
                         "title": "Worker A"},
            "worker_b": {"col": "compute_b", "row": "app", "icon": "icons/aws/fargate.png",
                         "title": "Worker B"},
            "ddb": {"col": "data", "row": "app", "icon": "icons/aws/dynamodb.png",
                    "title": "DynamoDB"},
            "cw": {"col": "edge", "row": "data", "icon": "icons/aws/cloudwatch.png",
                   "title": "CloudWatch"},
            "rds_a": {"col": "compute_a", "row": "data", "icon": "icons/aws/rds.png",
                      "title": "RDS Primary"},
            "rds_b": {"col": "compute_b", "row": "data", "icon": "icons/aws/rds.png",
                      "title": "RDS Standby"},
            "archive": {"col": "data", "row": "data", "icon": "icons/aws/s3.png",
                        "title": "S3 Archive"},
        },
        "containers": [
            {"name": "cloud", "label": "AWS Cloud",
             "members": ["r53", "ecr", "bedrock", "knowledge", "cf", "queue",
                         "ddb", "cw", "archive", "@public", "@private"]},
            {"name": "public", "label": "Public subnet",
             "members": ["alb"], "dash": "dash"},
            {"name": "private", "label": "Private subnets",
             "members": ["api", "worker_a", "worker_b", "rds_a", "rds_b"],
             "dash": "dash"},
        ],
        "channels": {
            "cloud_left": ["outside_container", ["cloud", "left"]],
            "public_right": ["outside_container", ["public", "right"]],
            "app_entry": ["above_row", "app"],
            "right_compute": ["right_of_col", "compute_a"],
            "cloud_right": ["outside_container", ["cloud", "right"]],
        },
        "edges": [
            {"from": "user", "to": "r53", "label": "DNS"},
            {"from": "user", "to": "cf", "label": "HTTPS"},
            {"from": "r53", "to": "cf", "dash": "dash"},
            {"from": "knowledge", "to": "bedrock", "label": "参照データ",
             "dash": "dash"},
            {"from": "cf", "to": "alb"},
            {"from": "alb", "to": "api"},
            {"from": "api", "to": "queue", "exit": "bottom", "enter": "top",
             "via": ["public_right", "app_entry"]},
            {"from": "queue", "to": "worker_a"},
            {"from": "worker_a", "to": "worker_b", "label": "並列処理"},
            {"from": "ecr", "to": "api", "exit": "bottom", "enter": "right",
             "via": ["right_compute"], "dash": "dash"},
            {"from": "bedrock", "to": "worker_b", "dash": "dash"},
            {"from": "worker_a", "to": "rds_a", "exit": "bottom", "enter": "top"},
            {"from": "worker_b", "to": "ddb"},
            {"from": "worker_b", "to": "rds_b", "exit": "bottom", "enter": "top"},
            {"from": "rds_a", "to": "rds_b", "both": True, "dash": "dash",
             "label": "同期"},
            {"from": "ddb", "to": "archive", "exit": "right", "enter": "right",
             "via": ["cloud_right"], "dash": "dash"},
            {"from": "queue", "to": "cw", "dash": "dash"},
        ],
    }


LARGE_AWS_DIAGRAM = _large_aws_diagram()

PROGRAM_ROADMAP_STRESS = {
    "type": "program_roadmap",
    "kicker": "大規模プログラム工程表",
    "title": "5テーマ・15作業の同時進行を1枚で俯瞰する",
    "lead": "各テーマで3作業を重ね、自動レーン割当と要素縮小の発動を確認します。",
    "periods": ["4月", "5月", "6月", "7月", "8月", "9月",
                "10月", "11月", "12月", "1月", "2月", "3月"],
    "tracks": [
        {
            "name": f"改善テーマ{i + 1}",
            "activities": [
                {"label": f"要件整理{i + 1}", "start": "4月", "end": "7月"},
                {"label": f"実装検証{i + 1}", "start": "6月", "end": "10月"},
                {"label": f"展開準備{i + 1}", "start": "7月", "end": "2月",
                 "emph": i == 4},
            ],
        }
        for i in range(5)
    ],
}

IMAGE_STRESS = {
    "type": "image",
    "kicker": "大判画像",
    "title": "lead付きでも、画像の視認領域を最大限に確保する",
    "lead": "説明はleadへ集約し、画像全体を欠けなく表示するcontainの縮小耐性を確認します。",
    "image": "images/pptxdsl-repository.png",
    "fit": "contain",
    "alt": "GitHubで公開されているpptxdslリポジトリのトップ画面",
}

STRESS_PATTERN_DECK = {
    "meta": {
        "title": "段階的縮小ストレス検証",
        "footer": "段階的縮小ストレス検証",
        "date": "2026年7月",
        "organization": "業務企画本部\n業務改善推進部",
        "author": "業務改善検討チーム",
    },
    "slides": [
        {
            "type": "table",
            "kicker": "大規模表",
            "title": "5領域の責任分担と判断基準を一覧化する",
            "lead": "セル内の情報量を増やし、余白圧縮とフォント縮小の発動を確認します。",
            "columns": ["領域", "対象", "確認事項", "判断基準"],
            "rows": TABLE_ROWS,
        },
        {
            "type": "diagram",
            "kicker": "大規模構成図",
            "title": "20機能の同期・非同期・監視経路を1枚で俯瞰する",
            "lead": "分岐・合流・縦接続・外周迂回・入れ子境界を含む構成で縮小耐性を確認します。",
            "diagram": LARGE_DIAGRAM,
        },
        {
            "type": "diagram",
            "kicker": "大規模AWS構成図",
            "title": "AWSの同期・非同期・生成AI経路を1枚で俯瞰する",
            "lead": "AWS公式アイコンで分岐・冗長化・外周迂回を含む縮小耐性を確認します。",
            "diagram": LARGE_AWS_DIAGRAM,
        },
        PROGRAM_ROADMAP_STRESS,
        IMAGE_STRESS,
    ],
}
