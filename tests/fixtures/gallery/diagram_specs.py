"""公開diagramスキーマだけで記述した構成図サンプル。

書くのは:
  cols/rows   : グリッドの列・行の並び(名前だけ)
  nodes       : ノード = (列, 行, アイコン, ラベル)
  containers  : メンバー列挙(外側から順に。@名前 で子コンテナ参照)
  channels    : 配線レーン = ["left_of_col"|"right_of_col"|"above_row"|"below_row", 基準セル]
                  または ["outside_container", [コンテナ名 または [ノード名,...], 辺]]
                  — 後者は「そのコンテナ(またはノード群)のすぐ外側」を指す。同じ列/近い位置を
                  共有するノード間のローカルループ(例: 同一AZ内のFargate→RDS、隣接する
                  Route53↔CloudFrontの折り返し)は必ずこちらを使う。
                  列基準のチャネルを流用すると、無関係な隣接列まで大回りして他コンテナの
                  境界線を貫通する(実際に2箇所で発生した不具合。要注意)。
  edges       : from/to(+必要なら exit/enter 辺, via チャネル, label)
座標・描画領域・コンテナ余白は diagram_layout.py が構造から計算する。
これらは名前付きテンプレートではなく、content.json の diagram と同じ形式の
回帰試験用サンプルである。
"""

AWS_SIMPLE_EXAMPLE = {
    "cols": ["user", "alb", "ecs", "svc", "dept"],
    "rows": ["top", "mid", "bot"],
    "nodes": {
        "user": {"col": "user", "row": "mid", "icon": "icons/aws/users.png",
                 "title": "社内ユーザー", "sub": "ブラウザ"},
        "alb": {"col": "alb", "row": "mid", "icon": "icons/aws/alb.png",
                "title": "ALB", "sub": "内部LB"},
        "ecs": {"col": "ecs", "row": "mid", "icon": "icons/aws/fargate.png",
                "title": "ECS Fargate", "sub": "生成API (python-pptx)"},
        "bedrock": {"col": "svc", "row": "top", "icon": "icons/aws/bedrock.png",
                    "title": "Amazon Bedrock", "sub": "Claude (構成JSON生成)"},
        "s3": {"col": "svc", "row": "mid", "icon": "icons/aws/s3.png",
               "title": "Amazon S3", "sub": "テンプレート/成果物"},
        "cw": {"col": "svc", "row": "bot", "icon": "icons/aws/cloudwatch.png",
               "title": "CloudWatch", "sub": "ログ・監査証跡"},
        "dept": {"col": "dept", "row": "mid", "icon": "icons/aws/user.png",
                 "title": "利用部門", "sub": "ダウンロード"},
    },
    "containers": [
        {"name": "cloud", "label": "AWS Cloud",
         "members": ["@vpc", "bedrock", "s3", "cw"], "color": "line"},
        {"name": "vpc", "label": "VPC (private)", "members": ["alb", "ecs"],
         "color": "accent", "dash": "dash"},
    ],
    "channels": {},
    "edges": [
        {"from": "user", "to": "alb", "label": "HTTPS"},
        {"from": "alb", "to": "ecs"},
        {"from": "ecs", "to": "bedrock", "label": "構成生成"},
        {"from": "ecs", "to": "s3", "label": "読み書き"},
        {"from": "ecs", "to": "cw"},
        {"from": "s3", "to": "dept", "label": "署名URL"},
    ],
}

AWS_MULTIAZ_EXAMPLE = {
    "cols": ["user", "edge", "fg_a", "alb", "fg_c", "svc"],
    "rows": ["north", "web", "fg", "rds"],
    "nodes": {
        "user": {"col": "user", "row": "web", "icon": "icons/aws/users.png",
                 "title": "社内ユーザー"},
        "r53": {"col": "edge", "row": "north", "icon": "icons/aws/route53.png",
                "title": "Route 53"},
        "cf": {"col": "edge", "row": "web", "icon": "icons/aws/cloudfront.png",
               "title": "CloudFront"},
        "alb": {"col": "alb", "row": "web", "icon": "icons/aws/alb.png", "title": "ALB"},
        "fg_a": {"col": "fg_a", "row": "fg", "icon": "icons/aws/fargate.png",
                 "title": "Fargate"},
        "fg_c": {"col": "fg_c", "row": "fg", "icon": "icons/aws/fargate.png",
                 "title": "Fargate"},
        "rds_a": {"col": "fg_a", "row": "rds", "icon": "icons/aws/rds.png",
                  "title": "RDS (primary)"},
        "rds_c": {"col": "fg_c", "row": "rds", "icon": "icons/aws/rds.png",
                  "title": "RDS (standby)"},
        "s3": {"col": "svc", "row": "web", "icon": "icons/aws/s3.png",
               "title": "Amazon S3", "sub": "成果物/静的配信"},
        "cw": {"col": "svc", "row": "rds", "icon": "icons/aws/cloudwatch.png",
               "title": "CloudWatch", "sub": "監視・ログ"},
    },
    "containers": [
        {"name": "cloud", "label": "AWS Cloud",
         "members": ["@vpc", "r53", "cf", "s3", "cw"]},
        {"name": "vpc", "label": "VPC (private subnets)",
         "members": ["alb", "@az_a", "@az_c"], "color": "navy"},
        {"name": "az_a", "label": "AZ-a", "members": ["fg_a", "rds_a"],
         "dash": "dash"},
        {"name": "az_c", "label": "AZ-c", "members": ["fg_c", "rds_c"],
         "dash": "dash"},
    ],
    "channels": {
        "loop_a": ["outside_container", ["az_a", "left"]],
        "loop_c": ["outside_container", ["az_c", "right"]],
        # 同じ辺の2本目はエンジンが外側へ離し、S3向け専用レーンにする。
        "s3_lane": ["outside_container", ["az_c", "right"]],
        # ALB→Fargateの横方向ジョグをAZコンテナのラベル帯のすぐ下(内側)で
        # 行い、ラベルの文字帯を横切らないようにする(自動Zルート任せだと
        # ジョグ位置がラベル帯の高さと重なることがあった。実際に発生した不具合)。
        "above_az_a": ["outside_container", ["az_a", "top_inside"]],
        "above_az_c": ["outside_container", ["az_c", "top_inside"]],
    },
    "edges": [
        {"from": "user", "to": "cf"},
        # r53とcfは同じ列(edge)で真上・真下に並ぶので側面迂回させず素直に縦接続する
        {"from": "r53", "to": "cf", "dash": "dash", "label": "名前解決"},
        {"from": "cf", "to": "alb", "label": "HTTPS"},
        # ALBからは真下に分岐させる(HTTPSの着信ポート[左辺]と衝突させない)
        {"from": "alb", "to": "fg_a", "exit": "bottom", "enter": "top",
         "via": ["above_az_a"]},
        {"from": "alb", "to": "fg_c", "exit": "bottom", "enter": "top",
         "via": ["above_az_c"]},
        {"from": "fg_a", "to": "rds_a", "exit": "left", "enter": "left",
         "via": ["loop_a"]},
        {"from": "fg_c", "to": "rds_c", "exit": "bottom", "enter": "right",
         "via": ["loop_c"]},
        {"from": "rds_a", "to": "rds_c", "both": True, "dash": "dash",
         "label": "同期"},
        # VPC境界のすぐ外や自動Zの中央へ通すと、VPC/AZ境界またはRDS側
        # ループと近接する。専用レーンで両者の間を通し、Fargate右辺から
        # S3左辺へ垂直に接続する。
        {"from": "fg_c", "to": "s3", "exit": "right", "enter": "left",
         "via": ["s3_lane"], "label": "成果物"},
        {"from": "@vpc", "to": "cw", "from_row": "rds", "dash": "dash"},
    ],
}
