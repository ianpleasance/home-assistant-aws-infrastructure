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

# Attribution
ATTRIBUTION = "Data provided by Amazon Web Services"

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
    # Check exact matches first
    if service_name in SERVICE_SLUG_MAP:
        return SERVICE_SLUG_MAP[service_name]
    
    # Fallback: create slug from name
    slug = service_name.lower()
    slug = slug.replace("amazon ", "").replace("aws ", "")
    slug = slug.split(" - ")[0]  # Take first part before dash
    slug = "".join(c for c in slug if c.isalnum())
    return slug[:20]  # Limit length
