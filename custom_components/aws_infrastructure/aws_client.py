"""AWS client wrapper for the AWS Infrastructure integration."""
from __future__ import annotations

import logging

import boto3
from botocore.config import Config

_LOGGER = logging.getLogger(__name__)


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

    def get_cost_explorer_client(self):
        """Get Cost Explorer client."""
        return self._session.client("ce")

    def get_ec2_client(self):
        """Get EC2 client."""
        return self._session.client("ec2")

    def get_rds_client(self):
        """Get RDS client."""
        return self._session.client("rds")

    def get_lambda_client(self):
        """Get Lambda client."""
        return self._session.client("lambda")

    def get_elbv2_client(self):
        """Get ELBv2 client (for ALB/NLB)."""
        return self._session.client("elbv2")

    def get_autoscaling_client(self):
        """Get Auto Scaling client."""
        return self._session.client("autoscaling")

    def get_cloudwatch_client(self):
        """Get CloudWatch client."""
        return self._session.client("cloudwatch")

    def get_dynamodb_client(self):
        """Get DynamoDB client."""
        return self._session.client("dynamodb")

    def get_elasticache_client(self):
        """Get ElastiCache client."""
        return self._session.client("elasticache")

    def get_ecs_client(self):
        """Get ECS client."""
        return self._session.client("ecs")

    def get_eks_client(self):
        """Get EKS client."""
        return self._session.client("eks")

    def get_sns_client(self):
        """Get SNS client."""
        return self._session.client("sns")

    def get_sqs_client(self):
        """Get SQS client."""
        return self._session.client("sqs")

    def get_s3_client(self):
        """Get S3 client.

        boto3 >= 1.35.74 defaults to sending checksums on all S3 requests,
        which requires DEFAULT_CHECKSUM_ALGORITHM from botocore.httpchecksum.
        Passing explicit config opts out of that behaviour and keeps
        compatibility across the supported botocore range.
        """
        return self._session.client(
            "s3",
            config=Config(
                request_checksum_calculation="when_required",
                response_checksum_validation="when_supported",
            ),
        )

    @property
    def region(self) -> str:
        """Return the region."""
        return self._region
