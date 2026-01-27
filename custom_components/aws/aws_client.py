"""AWS client wrapper for the AWS Infrastructure integration."""
from __future__ import annotations

import logging

import boto3

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

    def get_elb_client(self):
        """Get ELB client (for CLB)."""
        return self._session.client("elb")

    def get_autoscaling_client(self):
        """Get Auto Scaling client."""
        return self._session.client("autoscaling")

    def get_cloudwatch_client(self):
        """Get CloudWatch client."""
        return self._session.client("cloudwatch")

    @property
    def region(self) -> str:
        """Return the region."""
        return self._region
