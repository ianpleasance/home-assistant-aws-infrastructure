"""Constants for the AWS Infrastructure integration."""

DOMAIN = "aws"
PLATFORMS = ["sensor", "binary_sensor"]

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

# Region mode options
REGION_MODE_ALL = "all"
REGION_MODE_SELECT = "select"

# Default values
DEFAULT_REFRESH_INTERVAL = 5
MIN_REFRESH_INTERVAL = 1
MAX_REFRESH_INTERVAL = 1440

# AWS Regions
AWS_REGIONS = {
    "us-east-1": "US East (N. Virginia)",
    "us-east-2": "US East (Ohio)",
    "us-west-1": "US West (N. California)",
    "us-west-2": "US West (Oregon)",
    "eu-west-1": "Europe (Ireland)",
    "eu-west-2": "Europe (London)",
    "eu-west-3": "Europe (Paris)",
    "eu-central-1": "Europe (Frankfurt)",
    "eu-north-1": "Europe (Stockholm)",
    "eu-south-1": "Europe (Milan)",
    "ap-south-1": "Asia Pacific (Mumbai)",
    "ap-northeast-1": "Asia Pacific (Tokyo)",
    "ap-northeast-2": "Asia Pacific (Seoul)",
    "ap-northeast-3": "Asia Pacific (Osaka)",
    "ap-southeast-1": "Asia Pacific (Singapore)",
    "ap-southeast-2": "Asia Pacific (Sydney)",
    "ca-central-1": "Canada (Central)",
    "sa-east-1": "South America (São Paulo)",
    "af-south-1": "Africa (Cape Town)",
    "me-south-1": "Middle East (Bahrain)",
}

# Coordinator names
COORDINATOR_COST = "cost"
COORDINATOR_EC2 = "ec2"
COORDINATOR_RDS = "rds"
COORDINATOR_LAMBDA = "lambda"
COORDINATOR_LOAD_BALANCER = "load_balancer"
COORDINATOR_AUTO_SCALING = "auto_scaling"

# Attribution
ATTRIBUTION = "Data provided by Amazon Web Services"
