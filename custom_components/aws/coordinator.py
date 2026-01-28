"""Coordinators for AWS Infrastructure integration."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .aws_client import AwsClient
from .const import slugify_service_name

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
    """Coordinator for Cost Explorer data."""

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
        return await self.hass.async_add_executor_job(self._fetch_cost_data_sync)

    def _fetch_cost_data_sync(self) -> dict[str, Any]:
        """Sync method to fetch cost data."""
        try:
            from datetime import date

            ce_client = self.aws_client.get_ce_client()

            # Get yesterday's cost
            today = date.today()
            yesterday = today - timedelta(days=1)
            response_yesterday = ce_client.get_cost_and_usage(
                TimePeriod={
                    "Start": yesterday.isoformat(),
                    "End": today.isoformat(),
                },
                Granularity="DAILY",
                Metrics=["UnblendedCost"],
                GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
            )

            # Get month-to-date cost
            month_start = date(today.year, today.month, 1)
            response_mtd = ce_client.get_cost_and_usage(
                TimePeriod={
                    "Start": month_start.isoformat(),
                    "End": today.isoformat(),
                },
                Granularity="MONTHLY",
                Metrics=["UnblendedCost"],
            )

            # Parse service costs for individual sensors
            service_costs = {}
            results_yesterday = response_yesterday.get("ResultsByTime", [])
            if results_yesterday and "Groups" in results_yesterday[0]:
                rank = 1
                total_cost = 0
                
                # First pass: calculate total for percentages
                for group in results_yesterday[0]["Groups"]:
                    amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
                    total_cost += amount
                
                # Second pass: create service entries
                for group in results_yesterday[0]["Groups"]:
                    service_name = group["Keys"][0]
                    amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
                    if amount > 0:
                        service_slug = slugify_service_name(service_name)
                        percentage = (amount / total_cost * 100) if total_cost > 0 else 0
                        service_costs[service_slug] = {
                            "amount": round(amount, 2),
                            "name": service_name,
                            "rank": rank,
                            "percentage": round(percentage, 1),
                        }
                        rank += 1

            # Sort by amount and take top 10
            sorted_services = sorted(
                service_costs.items(),
                key=lambda x: x[1]["amount"],
                reverse=True
            )[:10]
            service_costs = dict(sorted_services)

            return {
                "cost_yesterday": response_yesterday,
                "cost_mtd": response_mtd,
                "service_costs": service_costs,
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
                    "state": function.get("State", "Active"),
                    "runtime": function.get("Runtime"),
                    "handler": function.get("Handler"),
                    "memory_size": function.get("MemorySize"),
                    "timeout": function.get("Timeout"),
                    "code_size": function.get("CodeSize"),
                    "last_modified": function.get("LastModified"),
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
        super().__init__(
            hass, aws_client, account_name, "LoadBalancer", update_interval_minutes
        )

    async def _fetch_data(self) -> dict[str, Any]:
        """Fetch load balancers."""
        return await self.hass.async_add_executor_job(self._fetch_lb_data_sync)

    def _fetch_lb_data_sync(self) -> dict[str, Any]:
        """Sync method to fetch load balancer data."""
        try:
            elb_client = self.aws_client.get_elb_client()
            response = elb_client.describe_load_balancers()

            load_balancers = {}
            for lb in response.get("LoadBalancers", []):
                lb_name = lb["LoadBalancerName"]
                load_balancers[lb_name] = {
                    "state": lb.get("State", {}).get("Code", "unknown"),
                    "type": lb.get("Type"),
                    "scheme": lb.get("Scheme"),
                    "dns_name": lb.get("DNSName"),
                    "vpc_id": lb.get("VpcId"),
                    "availability_zones": [
                        az.get("ZoneName") for az in lb.get("AvailabilityZones", [])
                    ],
                    "created_time": lb.get("CreatedTime", "").isoformat()
                    if lb.get("CreatedTime")
                    else None,
                }

            return {
                "load_balancers": load_balancers,
                "last_update": datetime.now().isoformat(),
            }

        except Exception as err:
            _LOGGER.error("Error fetching load balancer data: %s", err)
            return {"load_balancers": {}}


class AwsAutoScalingCoordinator(AwsBaseCoordinator):
    """Coordinator for Auto Scaling Group data."""

    def __init__(
        self,
        hass: HomeAssistant,
        aws_client: AwsClient,
        account_name: str,
        update_interval_minutes: int,
    ) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass, aws_client, account_name, "AutoScaling", update_interval_minutes
        )

    async def _fetch_data(self) -> dict[str, Any]:
        """Fetch auto scaling groups."""
        return await self.hass.async_add_executor_job(self._fetch_asg_data_sync)

    def _fetch_asg_data_sync(self) -> dict[str, Any]:
        """Sync method to fetch ASG data."""
        try:
            asg_client = self.aws_client.get_asg_client()
            response = asg_client.describe_auto_scaling_groups()

            auto_scaling_groups = {}
            for asg in response.get("AutoScalingGroups", []):
                asg_name = asg["AutoScalingGroupName"]
                instances = asg.get("Instances", [])
                auto_scaling_groups[asg_name] = {
                    "instances": len(instances),
                    "desired_capacity": asg.get("DesiredCapacity", 0),
                    "min_size": asg.get("MinSize", 0),
                    "max_size": asg.get("MaxSize", 0),
                    "healthy_instances": sum(
                        1 for i in instances if i.get("HealthStatus") == "Healthy"
                    ),
                    "availability_zones": asg.get("AvailabilityZones", []),
                }

            return {
                "auto_scaling_groups": auto_scaling_groups,
                "last_update": datetime.now().isoformat(),
            }

        except Exception as err:
            _LOGGER.error("Error fetching ASG data: %s", err)
            return {"auto_scaling_groups": {}}
