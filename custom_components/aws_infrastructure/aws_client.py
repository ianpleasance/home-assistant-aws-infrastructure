"""AWS client wrapper for the AWS Infrastructure integration."""
from __future__ import annotations

import logging

import boto3
from botocore.config import Config

_LOGGER = logging.getLogger(__name__)

# Apply a connect and read timeout to all boto3 clients.
# Without this, a hung or slow AWS endpoint can block a coordinator
# indefinitely, producing no log output and keeping all sensors unavailable.
_BOTO_CONFIG = Config(
    connect_timeout=10,
    read_timeout=30,
    retries={"max_attempts": 2, "mode": "standard"},
)


class AwsClient:
    """AWS client wrapper."""

    def __init__(
        self,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        region: str,
    ) -> None:
        """Initialize the AWS client."""
        self._aws_access_key_id = aws_access_key_id
        self._aws_secret_access_key = aws_secret_access_key
        self._region = region
        self._session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region,
        )

    def _client(self, service: str, **kwargs):
        """Create a boto3 client with standard timeouts."""
        return self._session.client(service, config=_BOTO_CONFIG, **kwargs)

    def get_cost_explorer_client(self):
        """Get Cost Explorer client."""
        return self._client("ce")

    def get_ec2_client(self):
        """Get EC2 client."""
        return self._client("ec2")

    def get_rds_client(self):
        """Get RDS client."""
        return self._client("rds")

    def get_lambda_client(self):
        """Get Lambda client."""
        return self._client("lambda")

    def get_elbv2_client(self):
        """Get ELBv2 client (for ALB/NLB)."""
        return self._client("elbv2")

    def get_elb_client(self):
        """Get ELB client (for Classic Load Balancers)."""
        return self._client("elb")

    def get_efs_client(self):
        """Get EFS client."""
        return self._client("efs")

    def get_kinesis_client(self):
        """Get Kinesis client."""
        return self._client("kinesis")

    def get_beanstalk_client(self):
        """Get Elastic Beanstalk client."""
        return self._client("elasticbeanstalk")

    def get_autoscaling_client(self):
        """Get Auto Scaling client."""
        return self._client("autoscaling")

    def get_cloudwatch_client(self):
        """Get CloudWatch client."""
        return self._client("cloudwatch")

    def get_dynamodb_client(self):
        """Get DynamoDB client."""
        return self._client("dynamodb")

    def get_elasticache_client(self):
        """Get ElastiCache client."""
        return self._client("elasticache")

    def get_ecs_client(self):
        """Get ECS client."""
        return self._client("ecs")

    def get_eks_client(self):
        """Get EKS client."""
        return self._client("eks")

    def get_sns_client(self):
        """Get SNS client."""
        return self._client("sns")

    def get_sqs_client(self):
        """Get SQS client."""
        return self._client("sqs")

    def get_s3_client(self):
        """Get S3 client."""
        return self._client("s3")

    @property
    def region(self) -> str:
        """Return the region."""
        return self._region
