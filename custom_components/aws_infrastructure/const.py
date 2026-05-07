"""Constants for the AWS Infrastructure integration."""

DOMAIN = "aws_infrastructure"
# Service names
SERVICE_REFRESH_ACCOUNT = "refresh_account"
SERVICE_REFRESH_ALL = "refresh_all_accounts"

# Config/Options keys
CONF_ACCOUNT_NAME = "account_name"
CONF_AWS_ACCESS_KEY_ID = "aws_access_key_id"
CONF_AWS_SECRET_ACCESS_KEY = "aws_secret_access_key"
CONF_REGION_MODE = "region_mode"
CONF_REGIONS = "regions"
CONF_REFRESH_INTERVAL = "refresh_interval_minutes"
CONF_COST_REFRESH_INTERVAL = "cost_refresh_interval"
CONF_CREATE_INDIVIDUAL_COUNT_SENSORS = "create_individual_count_sensors"
CONF_SKIP_INITIAL_REFRESH = "skip_initial_refresh"
CONF_SERVICES = "services"

# Special select-all sentinel value
SELECT_ALL_SERVICES = "__select_all__"

# Region mode options
REGION_MODE_ALL = "all"
REGION_MODE_SELECT = "select"

# Default values
DEFAULT_REFRESH_INTERVAL = 5
DEFAULT_COST_REFRESH_INTERVAL = 1440  # 24 hours in minutes
DEFAULT_CREATE_INDIVIDUAL_COUNT_SENSORS = False
DEFAULT_SKIP_INITIAL_REFRESH = False

MIN_REFRESH_INTERVAL = 1
MAX_REFRESH_INTERVAL = 1440

# Maximum number of EBS snapshots to store in sensor attributes per region.
# Snapshots are sorted newest-first before truncation.
MAX_EBS_SNAPSHOTS = 50

# AWS Regions
AWS_REGIONS = {
    "us-east-1": "US East (N. Virginia) [us-east-1]",
    "us-east-2": "US East (Ohio) [us-east-2]",
    "us-west-1": "US West (N. California) [us-west-1]",
    "us-west-2": "US West (Oregon) [us-west-2]",
    "eu-west-1": "Europe (Ireland) [eu-west-1]",
    "eu-west-2": "Europe (London) [eu-west-2]",
    "eu-west-3": "Europe (Paris) [eu-west-3]",
    "eu-central-1": "Europe (Frankfurt) [eu-central-1]",
    "eu-north-1": "Europe (Stockholm) [eu-north-1]",
    "eu-south-1": "Europe (Milan) [eu-south-1]",
    "ap-south-1": "Asia Pacific (Mumbai) [ap-south-1]",
    "ap-northeast-1": "Asia Pacific (Tokyo) [ap-northeast-1]",
    "ap-northeast-2": "Asia Pacific (Seoul) [ap-northeast-2]",
    "ap-northeast-3": "Asia Pacific (Osaka) [ap-northeast-3]",
    "ap-southeast-1": "Asia Pacific (Singapore) [ap-southeast-1]",
    "ap-southeast-2": "Asia Pacific (Sydney) [ap-southeast-2]",
    "ca-central-1": "Canada (Central) [ca-central-1]",
    "sa-east-1": "South America (São Paulo) [sa-east-1]",
    "af-south-1": "Africa (Cape Town) [af-south-1]",
    "me-south-1": "Middle East (Bahrain) [me-south-1]",
}

# Coordinator names
COORDINATOR_COST = "cost"
COORDINATOR_EC2 = "ec2"
COORDINATOR_RDS = "rds"
COORDINATOR_LAMBDA = "lambda"
COORDINATOR_LOADBALANCER = "loadbalancer"
COORDINATOR_DYNAMODB = "dynamodb"
COORDINATOR_ELASTICACHE = "elasticache"
COORDINATOR_ECS = "ecs"
COORDINATOR_EKS = "eks"
COORDINATOR_EBS = "ebs"
COORDINATOR_SNS = "sns"
COORDINATOR_SQS = "sqs"
COORDINATOR_ASG = "asg"
COORDINATOR_S3 = "s3"
COORDINATOR_CLOUDWATCH_ALARMS = "cloudwatch_alarms"
COORDINATOR_ELASTIC_IPS = "elastic_ips"
COORDINATOR_CLASSIC_LB = "classic_lb"
COORDINATOR_EFS = "efs"
COORDINATOR_KINESIS = "kinesis"
COORDINATOR_BEANSTALK = "beanstalk"
COORDINATOR_ROUTE53 = "route53"
COORDINATOR_API_GATEWAY = "api_gateway"
COORDINATOR_CLOUDFRONT = "cloudfront"
COORDINATOR_VPC = "vpc"
COORDINATOR_ACM = "acm"
COORDINATOR_ECR = "ecr"
COORDINATOR_CLOUDTRAIL = "cloudtrail"
COORDINATOR_IAM = "iam"
COORDINATOR_REDSHIFT = "redshift"

# Attribution
ATTRIBUTION = "Data provided by Amazon Web Services"

# ============================================================================
# SERVICE DEFINITIONS
# ============================================================================

# Ordered list for UI — separators use "__sep_" prefix
SERVICE_UI_ORDER = [
    ("__sep_compute__",        "── Compute ─────────────────────────"),
    (COORDINATOR_EC2,          "EC2 Instances"),
    (COORDINATOR_LAMBDA,       "Lambda Functions"),
    (COORDINATOR_ASG,          "Auto Scaling Groups"),
    (COORDINATOR_ECS,          "ECS Clusters"),
    (COORDINATOR_EKS,          "EKS Clusters"),
    (COORDINATOR_BEANSTALK,    "Elastic Beanstalk"),
    ("__sep_data__",           "── Databases & Storage ─────────────"),
    (COORDINATOR_RDS,          "RDS Databases"),
    (COORDINATOR_REDSHIFT,     "Redshift"),
    (COORDINATOR_DYNAMODB,     "DynamoDB"),
    (COORDINATOR_ELASTICACHE,  "ElastiCache"),
    (COORDINATOR_S3,           "S3 Buckets"),
    (COORDINATOR_EBS,          "EBS Volumes"),
    (COORDINATOR_EFS,          "EFS File Systems"),
    (COORDINATOR_ECR,          "ECR Repositories"),
    ("__sep_network__",        "── Networking ──────────────────────"),
    (COORDINATOR_VPC,          "VPC"),
    (COORDINATOR_LOADBALANCER, "ALB / NLB Load Balancers"),
    (COORDINATOR_CLASSIC_LB,   "Classic Load Balancers"),
    (COORDINATOR_ELASTIC_IPS,  "Elastic IPs"),
    (COORDINATOR_API_GATEWAY,  "API Gateway"),
    (COORDINATOR_CLOUDFRONT,   "CloudFront (global)"),
    (COORDINATOR_ROUTE53,      "Route 53 (global)"),
    ("__sep_messaging__",      "── Messaging & Streaming ───────────"),
    (COORDINATOR_SNS,          "SNS Topics"),
    (COORDINATOR_SQS,          "SQS Queues"),
    (COORDINATOR_KINESIS,      "Kinesis Streams"),
    ("__sep_security__",       "── Security & Compliance ───────────"),
    (COORDINATOR_IAM,          "IAM (global)"),
    (COORDINATOR_ACM,          "ACM Certificates"),
    (COORDINATOR_CLOUDTRAIL,   "CloudTrail"),
    ("__sep_monitoring__",     "── Monitoring & Cost ───────────────"),
    (COORDINATOR_CLOUDWATCH_ALARMS, "CloudWatch Alarms"),
    (COORDINATOR_COST,         "Cost Explorer (global)"),
]

# All real service keys (excludes separators and select-all sentinel)
ALL_SERVICE_KEYS: list[str] = [
    key for key, _ in SERVICE_UI_ORDER
    if not key.startswith("__sep_") and key != SELECT_ALL_SERVICES
]

# Services selected by default
DEFAULT_SERVICES = {
    COORDINATOR_EC2,
    COORDINATOR_LAMBDA,
    COORDINATOR_ASG,
    COORDINATOR_RDS,
    COORDINATOR_S3,
    COORDINATOR_EBS,
    COORDINATOR_VPC,
    COORDINATOR_LOADBALANCER,
    COORDINATOR_ELASTIC_IPS,
    COORDINATOR_CLOUDWATCH_ALARMS,
    COORDINATOR_COST,
}

# IAM actions required per service
SERVICE_IAM_ACTIONS: dict[str, list[str]] = {
    COORDINATOR_EC2: [
        "ec2:DescribeInstances",
        "ec2:DescribeRegions",
    ],
    COORDINATOR_LAMBDA: [
        "lambda:ListFunctions",
    ],
    COORDINATOR_ASG: [
        "autoscaling:DescribeAutoScalingGroups",
    ],
    COORDINATOR_ECS: [
        "ecs:DescribeClusters",
        "ecs:ListClusters",
    ],
    COORDINATOR_EKS: [
        "eks:DescribeCluster",
        "eks:ListClusters",
    ],
    COORDINATOR_BEANSTALK: [
        "elasticbeanstalk:DescribeEnvironments",
    ],
    COORDINATOR_RDS: [
        "rds:DescribeDBInstances",
    ],
    COORDINATOR_REDSHIFT: [
        "redshift:DescribeClusters",
    ],
    COORDINATOR_DYNAMODB: [
        "dynamodb:DescribeTable",
        "dynamodb:ListTables",
    ],
    COORDINATOR_ELASTICACHE: [
        "elasticache:DescribeCacheClusters",
    ],
    COORDINATOR_S3: [
        "s3:GetBucketLocation",
        "s3:ListAllMyBuckets",
    ],
    COORDINATOR_EBS: [
        "ec2:DescribeSnapshots",
        "ec2:DescribeVolumes",
    ],
    COORDINATOR_EFS: [
        "elasticfilesystem:DescribeFileSystems",
    ],
    COORDINATOR_ECR: [
        "ecr:DescribeImages",
        "ecr:DescribeRepositories",
    ],
    COORDINATOR_VPC: [
        "ec2:DescribeInternetGateways",
        "ec2:DescribeNatGateways",
        "ec2:DescribeSubnets",
        "ec2:DescribeVpcPeeringConnections",
        "ec2:DescribeVpcs",
        "ec2:DescribeVpnConnections",
    ],
    COORDINATOR_LOADBALANCER: [
        "elasticloadbalancing:DescribeLoadBalancers",
    ],
    COORDINATOR_CLASSIC_LB: [
        "elasticloadbalancing:DescribeLoadBalancers",
    ],
    COORDINATOR_ELASTIC_IPS: [
        "ec2:DescribeAddresses",
    ],
    COORDINATOR_API_GATEWAY: [
        "apigateway:GET",
    ],
    COORDINATOR_CLOUDFRONT: [
        "cloudfront:ListDistributions",
    ],
    COORDINATOR_ROUTE53: [
        "route53:ListHostedZones",
    ],
    COORDINATOR_SNS: [
        "sns:GetTopicAttributes",
        "sns:ListTopics",
    ],
    COORDINATOR_SQS: [
        "sqs:GetQueueAttributes",
        "sqs:ListQueues",
    ],
    COORDINATOR_KINESIS: [
        "kinesis:DescribeStreamSummary",
        "kinesis:ListStreams",
    ],
    COORDINATOR_IAM: [
        "iam:GenerateCredentialReport",
        "iam:GetAccountPasswordPolicy",
        "iam:GetAccountSummary",
        "iam:GetCredentialReport",
        "iam:ListRoles",
    ],
    COORDINATOR_ACM: [
        "acm:DescribeCertificate",
        "acm:ListCertificates",
    ],
    COORDINATOR_CLOUDTRAIL: [
        "cloudtrail:DescribeTrails",
        "cloudtrail:GetEventSelectors",
        "cloudtrail:GetTrailStatus",
    ],
    COORDINATOR_CLOUDWATCH_ALARMS: [
        "cloudwatch:DescribeAlarms",
    ],
    COORDINATOR_COST: [
        "ce:GetCostAndUsage",
    ],
}

# Always required regardless of service selection
ALWAYS_REQUIRED_IAM_ACTIONS = [
    "sts:GetCallerIdentity",
]


def get_iam_policy(selected_services: set[str]) -> dict:
    """Generate minimum IAM policy JSON for the given service selection."""
    actions: set[str] = set(ALWAYS_REQUIRED_IAM_ACTIONS)
    for svc in selected_services:
        actions.update(SERVICE_IAM_ACTIONS.get(svc, []))
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "HomeAssistantAWSMonitoring",
                "Effect": "Allow",
                "Action": sorted(actions),
                "Resource": "*",
            }
        ],
    }


def get_new_iam_actions(old_services: set[str], new_services: set[str]) -> list[str]:
    """Return IAM actions needed for newly added services (not in old set)."""
    added = new_services - old_services
    old_actions: set[str] = set(ALWAYS_REQUIRED_IAM_ACTIONS)
    for svc in old_services:
        old_actions.update(SERVICE_IAM_ACTIONS.get(svc, []))
    new_actions: set[str] = set()
    for svc in added:
        for action in SERVICE_IAM_ACTIONS.get(svc, []):
            if action not in old_actions:
                new_actions.add(action)
    return sorted(new_actions)


# AWS Service name to slug mapping for cost sensors
SERVICE_SLUG_MAP = {
    "Amazon Elastic Compute Cloud - Compute": "ec2",
    "AWS Lambda": "lambda",
    "Amazon Relational Database Service": "rds",
    "Amazon Simple Storage Service": "s3",
    "Amazon DynamoDB": "dynamodb",
    "Amazon CloudWatch": "cloudwatch",
    "Amazon Virtual Private Cloud": "vpc",
    "AWS Key Management Service": "kms",
    "AWS CloudTrail": "cloudtrail",
    "AWS Config": "config",
    "Amazon CloudFront": "cloudfront",
    "Amazon Route 53": "route53",
    "AWS Secrets Manager": "secretsmanager",
    "Amazon Elastic Container Service": "ecs",
    "Amazon Elastic Kubernetes Service": "eks",
    "Amazon ElastiCache": "elasticache",
    "AWS Data Transfer": "datatransfer",
    "Amazon API Gateway": "apigateway",
    "AWS Systems Manager": "systemsmanager",
    "Amazon Simple Notification Service": "sns",
    "Amazon Simple Queue Service": "sqs",
    "Amazon Elastic Load Balancing": "elb",
    "Amazon EC2 Container Registry (ECR)": "ecr",
    "AWS Step Functions": "stepfunctions",
    "Amazon Kinesis": "kinesis",
    "AWS Glue": "glue",
    "Amazon Athena": "athena",
}


def slugify_service_name(service_name: str) -> str:
    """Convert AWS service name to slug."""
    if service_name in SERVICE_SLUG_MAP:
        return SERVICE_SLUG_MAP[service_name]
    slug = service_name.lower()
    slug = slug.replace("amazon ", "").replace("aws ", "")
    slug = slug.split(" - ")[0]
    slug = "".join(c for c in slug if c.isalnum())
    return slug[:20]
