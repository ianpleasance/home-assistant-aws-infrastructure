"""Coordinators for AWS Infrastructure integration."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .aws_client import AwsClient

_LOGGER = logging.getLogger(__name__)


class AwsBaseCoordinator(DataUpdateCoordinator):
    """Base coordinator for AWS services."""

    def __init__(
        self,
        hass: HomeAssistant,
        aws_client: AwsClient,
        account_name: str,
        service_name: str,
        update_interval_minutes: int,
    ) -> None:
        """Initialize coordinator."""
        self.aws_client = aws_client
        self.account_name = account_name
        self.service_name = service_name
        self.region = aws_client.region

        super().__init__(
            hass,
            _LOGGER,
            name=f"AWS {service_name} - {account_name} ({aws_client.region})",
            update_interval=timedelta(minutes=update_interval_minutes),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            return await self._fetch_data()
        except Exception as err:
            raise UpdateFailed(
                f"Error fetching {self.service_name} data: {err}"
            ) from err

    async def _fetch_data(self) -> dict[str, Any]:
        """Override this in subclasses."""
        raise NotImplementedError


class AwsCostCoordinator(AwsBaseCoordinator):
    """Coordinator for AWS cost data."""

    def __init__(
        self,
        hass: HomeAssistant,
        aws_client: AwsClient,
        account_name: str,
        update_interval_minutes: int,
    ) -> None:
        """Initialize coordinator."""
        super().__init__(hass, aws_client, account_name, "Cost", update_interval_minutes)

    async def _fetch_data(self) -> dict[str, Any]:
        """Fetch cost data."""
        if self.region != "us-east-1":
            return {"message": "Cost data only available in us-east-1"}

        return await self.hass.async_add_executor_job(self._fetch_cost_data_sync)

    def _fetch_cost_data_sync(self) -> dict[str, Any]:
        """Sync method to fetch cost data."""
        try:
            ce_client = self.aws_client.get_cost_explorer_client()

            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            start_of_month = today.replace(day=1)

            response_yesterday = ce_client.get_cost_and_usage(
                TimePeriod={"Start": str(yesterday), "End": str(today)},
                Granularity="DAILY",
                Metrics=["UnblendedCost"],
                GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
            )

            response_mtd = ce_client.get_cost_and_usage(
                TimePeriod={"Start": str(start_of_month), "End": str(today)},
                Granularity="MONTHLY",
                Metrics=["UnblendedCost"],
                GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
            )

            return {
                "cost_yesterday": response_yesterday,
                "cost_mtd": response_mtd,
                "last_update": datetime.now().isoformat(),
            }

        except Exception as err:
            _LOGGER.error("Error fetching cost data: %s", err)
            return {}


class AwsEc2Coordinator(AwsBaseCoordinator):
    """Coordinator for EC2 data."""

    def __init__(
        self,
        hass: HomeAssistant,
        aws_client: AwsClient,
        account_name: str,
        update_interval_minutes: int,
    ) -> None:
        """Initialize coordinator."""
        super().__init__(hass, aws_client, account_name, "EC2", update_interval_minutes)

    async def _fetch_data(self) -> dict[str, Any]:
        """Fetch EC2 instances."""
        return await self.hass.async_add_executor_job(self._fetch_ec2_data_sync)

    def _fetch_ec2_data_sync(self) -> dict[str, Any]:
        """Sync method to fetch EC2 data."""
        try:
            ec2_client = self.aws_client.get_ec2_client()
            response = ec2_client.describe_instances()

            instances = {}
            for reservation in response.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    instance_id = instance["InstanceId"]
                    instances[instance_id] = {
                        "state": instance["State"]["Name"],
                        "instance_type": instance["InstanceType"],
                        "launch_time": instance.get("LaunchTime", "").isoformat()
                        if instance.get("LaunchTime")
                        else None,
                        "private_ip": instance.get("PrivateIpAddress"),
                        "public_ip": instance.get("PublicIpAddress"),
                        "tags": {
                            tag["Key"]: tag["Value"]
                            for tag in instance.get("Tags", [])
                        },
                        "volumes": [
                            {"device": bdm["DeviceName"], "volume_id": bdm["Ebs"]["VolumeId"]}
                            for bdm in instance.get("BlockDeviceMappings", [])
                            if "Ebs" in bdm
                        ],
                    }

            return {"instances": instances, "last_update": datetime.now().isoformat()}

        except Exception as err:
            _LOGGER.error("Error fetching EC2 data: %s", err)
            return {"instances": {}}


class AwsRdsCoordinator(AwsBaseCoordinator):
    """Coordinator for RDS data."""

    def __init__(
        self,
        hass: HomeAssistant,
        aws_client: AwsClient,
        account_name: str,
        update_interval_minutes: int,
    ) -> None:
        """Initialize coordinator."""
        super().__init__(hass, aws_client, account_name, "RDS", update_interval_minutes)

    async def _fetch_data(self) -> dict[str, Any]:
        """Fetch RDS instances."""
        return await self.hass.async_add_executor_job(self._fetch_rds_data_sync)

    def _fetch_rds_data_sync(self) -> dict[str, Any]:
        """Sync method to fetch RDS data."""
        try:
            rds_client = self.aws_client.get_rds_client()
            response = rds_client.describe_db_instances()

            instances = {}
            for db_instance in response.get("DBInstances", []):
                db_id = db_instance["DBInstanceIdentifier"]
                instances[db_id] = {
                    "status": db_instance["DBInstanceStatus"],
                    "engine": db_instance["Engine"],
                    "engine_version": db_instance["EngineVersion"],
                    "instance_class": db_instance["DBInstanceClass"],
                    "allocated_storage": db_instance["AllocatedStorage"],
                    "multi_az": db_instance.get("MultiAZ", False),
                    "publicly_accessible": db_instance.get("PubliclyAccessible", False),
                    "endpoint": db_instance.get("Endpoint", {}).get("Address"),
                    "port": db_instance.get("Endpoint", {}).get("Port"),
                }

            return {"instances": instances, "last_update": datetime.now().isoformat()}

        except Exception as err:
            _LOGGER.error("Error fetching RDS data: %s", err)
            return {"instances": {}}


class AwsLambdaCoordinator(AwsBaseCoordinator):
    """Coordinator for Lambda data."""

    def __init__(
        self,
        hass: HomeAssistant,
        aws_client: AwsClient,
        account_name: str,
        update_interval_minutes: int,
    ) -> None:
        """Initialize coordinator."""
        super().__init__(hass, aws_client, account_name, "Lambda", update_interval_minutes)

    async def _fetch_data(self) -> dict[str, Any]:
        """Fetch Lambda functions."""
        return await self.hass.async_add_executor_job(self._fetch_lambda_data_sync)

    def _fetch_lambda_data_sync(self) -> dict[str, Any]:
        """Sync method to fetch Lambda data."""
        try:
            lambda_client = self.aws_client.get_lambda_client()
            response = lambda_client.list_functions()

            functions = {}
            for function in response.get("Functions", []):
                function_name = function["FunctionName"]
                functions[function_name] = {
                    "runtime": function.get("Runtime"),
                    "handler": function.get("Handler"),
                    "memory_size": function.get("MemorySize"),
                    "timeout": function.get("Timeout"),
                    "last_modified": function.get("LastModified"),
                    "code_size": function.get("CodeSize"),
                    "state": function.get("State"),
                }

            return {"functions": functions, "last_update": datetime.now().isoformat()}

        except Exception as err:
            _LOGGER.error("Error fetching Lambda data: %s", err)
            return {"functions": {}}


class AwsLoadBalancerCoordinator(AwsBaseCoordinator):
    """Coordinator for Load Balancer data."""

    def __init__(
        self,
        hass: HomeAssistant,
        aws_client: AwsClient,
        account_name: str,
        update_interval_minutes: int,
    ) -> None:
        """Initialize coordinator."""
        super().__init__(hass, aws_client, account_name, "LoadBalancer", update_interval_minutes)

    async def _fetch_data(self) -> dict[str, Any]:
        """Fetch load balancers."""
        return await self.hass.async_add_executor_job(self._fetch_lb_data_sync)

    def _fetch_lb_data_sync(self) -> dict[str, Any]:
        """Sync method to fetch load balancer data."""
        try:
            elbv2_client = self.aws_client.get_elbv2_client()
            response = elbv2_client.describe_load_balancers()

            load_balancers = {}
            for lb in response.get("LoadBalancers", []):
                lb_name = lb["LoadBalancerName"]
                load_balancers[lb_name] = {
                    "type": lb["Type"],
                    "scheme": lb["Scheme"],
                    "state": lb["State"]["Code"],
                    "dns_name": lb["DNSName"],
                    "vpc_id": lb.get("VpcId"),
                    "availability_zones": [
                        az["ZoneName"] for az in lb.get("AvailabilityZones", [])
                    ],
                    "created_time": lb.get("CreatedTime", "").isoformat()
                    if lb.get("CreatedTime")
                    else None,
                }

            return {"load_balancers": load_balancers, "last_update": datetime.now().isoformat()}

        except Exception as err:
            _LOGGER.error("Error fetching load balancer data: %s", err)
            return {"load_balancers": {}}


class AwsAutoScalingCoordinator(AwsBaseCoordinator):
    """Coordinator for Auto Scaling data."""

    def __init__(
        self,
        hass: HomeAssistant,
        aws_client: AwsClient,
        account_name: str,
        update_interval_minutes: int,
    ) -> None:
        """Initialize coordinator."""
        super().__init__(hass, aws_client, account_name, "AutoScaling", update_interval_minutes)

    async def _fetch_data(self) -> dict[str, Any]:
        """Fetch Auto Scaling groups."""
        return await self.hass.async_add_executor_job(self._fetch_asg_data_sync)

    def _fetch_asg_data_sync(self) -> dict[str, Any]:
        """Sync method to fetch ASG data."""
        try:
            asg_client = self.aws_client.get_autoscaling_client()
            response = asg_client.describe_auto_scaling_groups()

            groups = {}
            for asg in response.get("AutoScalingGroups", []):
                asg_name = asg["AutoScalingGroupName"]
                groups[asg_name] = {
                    "desired_capacity": asg["DesiredCapacity"],
                    "min_size": asg["MinSize"],
                    "max_size": asg["MaxSize"],
                    "instances": len(asg.get("Instances", [])),
                    "healthy_instances": sum(
                        1
                        for i in asg.get("Instances", [])
                        if i.get("HealthStatus") == "Healthy"
                    ),
                    "availability_zones": asg.get("AvailabilityZones", []),
                }

            return {"auto_scaling_groups": groups, "last_update": datetime.now().isoformat()}

        except Exception as err:
            _LOGGER.error("Error fetching Auto Scaling data: %s", err)
            return {"auto_scaling_groups": {}}
