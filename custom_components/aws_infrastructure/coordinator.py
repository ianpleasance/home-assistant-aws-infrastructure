"""Coordinators for AWS Infrastructure integration."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from botocore.exceptions import (
    ClientError,
    ConnectTimeoutError,
    EndpointConnectionError,
    NoCredentialsError,
    NoRegionError,
    ReadTimeoutError,
)
from homeassistant.components.persistent_notification import async_create as async_create_notification
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .aws_client import AwsClient

_LOGGER = logging.getLogger(__name__)

# Error codes that mean the IAM permission is missing for this service.
# We warn once and then suppress to avoid log spam on every refresh.
_PERMISSION_DENIED_CODES = {"AccessDenied", "AccessDeniedException", "UnauthorizedOperation"}

# Error codes that mean the service is simply not available in this region.
_NOT_AVAILABLE_CODES = {"OptInRequired", "InvalidClientTokenId", "SubscriptionRequiredException"}


def _classify_error(err: Exception) -> str:
    """Return a short classification string for a boto3/botocore exception."""
    if isinstance(err, NoCredentialsError):
        return "credentials"
    if isinstance(err, (ConnectTimeoutError, ReadTimeoutError)):
        return "timeout"
    if isinstance(err, EndpointConnectionError):
        return "endpoint"
    if isinstance(err, ClientError):
        code = err.response.get("Error", {}).get("Code", "")
        if code in _PERMISSION_DENIED_CODES:
            return "permission"
        if code in _NOT_AVAILABLE_CODES:
            return "not_available"
        if "Throttling" in code or "RequestLimitExceeded" in code:
            return "throttle"
        return f"client_error:{code}"
    return "unknown"


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
        # Track permission/availability errors so we only warn once per coordinator
        self._suppressed_error: str | None = None
        super().__init__(
            hass,
            _LOGGER,
            name=f"AWS {service_name} - {account_name} ({aws_client.region})",
            update_interval=timedelta(minutes=update_interval_minutes),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            result = await self.hass.async_add_executor_job(self._fetch_data)
            # If we had a suppressed error and the call succeeded, clear it and log recovery
            if self._suppressed_error:
                _LOGGER.info(
                    "%s [account=%s region=%s]: recovered successfully",
                    self.service_name, self.account_name, self.region,
                )
                self._suppressed_error = None
            return result
        except Exception as err:
            error_class = _classify_error(err)
            self._handle_error(error_class, err)
            # Return previous data if available, otherwise empty dict.
            # Never raise UpdateFailed — a single service error must not
            # mark the entire config entry as unavailable.
            return self.data if self.data is not None else {}

    def _handle_error(self, error_class: str, err: Exception) -> None:
        """Log errors appropriately — suppress repeated permission/availability errors."""
        if error_class == "credentials":
            # Credential errors affect all services — notify the user prominently
            _LOGGER.error(
                "%s [account=%s region=%s]: AWS credentials are invalid or expired. "
                "Please reconfigure the integration with valid credentials. Error: %s",
                self.service_name, self.account_name, self.region, err,
            )
            # Raise a HA persistent notification so it's visible in the UI
            try:
                async_create_notification(
                    self.hass,
                    f"AWS Infrastructure: credentials for account **{self.account_name}** "
                    f"are invalid or expired. Please reconfigure the integration.",
                    title="AWS Infrastructure — Credential Error",
                    notification_id=f"aws_infrastructure_credentials_{self.account_name}",
                )
            except Exception:
                pass  # Non-critical

        elif error_class == "permission":
            # Only warn once per coordinator — these won't self-resolve without IAM changes
            if self._suppressed_error != error_class:
                _LOGGER.warning(
                    "%s [account=%s region=%s]: IAM permission denied — "
                    "this service will show no data until the IAM policy is updated. "
                    "Error: %s",
                    self.service_name, self.account_name, self.region, err,
                )
                self._suppressed_error = error_class
            # else: silently skip — already warned

        elif error_class == "not_available":
            # Service not available in this region — warn once and suppress
            if self._suppressed_error != error_class:
                _LOGGER.warning(
                    "%s [account=%s region=%s]: service not available or not enabled "
                    "in this region — skipping. Error: %s",
                    self.service_name, self.account_name, self.region, err,
                )
                self._suppressed_error = error_class

        elif error_class == "throttle":
            # Throttling is transient — log at WARNING not ERROR
            _LOGGER.warning(
                "%s [account=%s region=%s]: request throttled by AWS, "
                "will retry on next interval. Error: %s",
                self.service_name, self.account_name, self.region, err,
            )

        elif error_class in ("timeout", "endpoint"):
            _LOGGER.error(
                "%s [account=%s region=%s]: connection %s — check network connectivity. "
                "Error: %s",
                self.service_name, self.account_name, self.region, error_class, err,
            )

        else:
            # Unexpected error — log at ERROR with full detail
            _LOGGER.error(
                "%s [account=%s region=%s]: %s",
                self.service_name, self.account_name, self.region, err,
            )

    def _fetch_data(self) -> dict[str, Any]:
        """Override this in subclasses - runs in executor."""
        raise NotImplementedError



class AwsCostCoordinator(AwsBaseCoordinator):
    """Coordinator for AWS Cost Explorer data."""

    def __init__(
        self, hass: HomeAssistant, aws_client, account_name: str, refresh_interval: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            aws_client,
            account_name,
            f"Cost Explorer ({aws_client.region})",
            refresh_interval,
        )

    def _fetch_data(self) -> dict:
        """Fetch cost data."""
        from datetime import datetime, timezone

        try:
            ce_client = self.aws_client.get_cost_explorer_client()
            
            # Get current date
            now = datetime.now(timezone.utc)
            
            # Yesterday's cost
            yesterday_start = (now - timedelta(days=1)).strftime("%Y-%m-%d")
            yesterday_end = now.strftime("%Y-%m-%d")
            
            cost_yesterday = ce_client.get_cost_and_usage(
                TimePeriod={"Start": yesterday_start, "End": yesterday_end},
                Granularity="DAILY",
                Metrics=["UnblendedCost"],
                GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
            )
            
            # Month-to-date cost
            month_start = now.replace(day=1).strftime("%Y-%m-%d")
            # End must be tomorrow — AWS rejects Start==End, and using tomorrow
            # captures today's partial costs (End is exclusive).
            tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")

            cost_mtd = ce_client.get_cost_and_usage(
                TimePeriod={"Start": month_start, "End": tomorrow},
                Granularity="MONTHLY",
                Metrics=["UnblendedCost"],
                GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
            )
            
            # Process service costs for yesterday
            service_costs = {}
            if cost_yesterday.get("ResultsByTime"):
                groups = cost_yesterday["ResultsByTime"][0].get("Groups", [])
                # Sort by cost descending
                sorted_groups = sorted(
                    groups,
                    key=lambda x: float(x["Metrics"]["UnblendedCost"]["Amount"]),
                    reverse=True,
                )
                
                # Get top 10 services
                total_cost = sum(
                    float(g["Metrics"]["UnblendedCost"]["Amount"]) for g in groups
                )
                
                for idx, group in enumerate(sorted_groups[:10], 1):
                    service_name = group["Keys"][0]
                    amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
                    percentage = (amount / total_cost * 100) if total_cost > 0 else 0
                    
                    # Create a slug for the service
                    service_slug = service_name.lower().replace(" ", "").replace("-", "")
                    
                    service_costs[service_slug] = {
                        "name": service_name,
                        "amount": amount,
                        "rank": idx,
                        "percentage": round(percentage, 2),
                    }
            
            return {
                "cost_yesterday": cost_yesterday,
                "cost_mtd": cost_mtd,
                "service_costs": service_costs,
            }
        except Exception as err:
            _LOGGER.error("%s [account=%s region=%s]: %s", "Error fetching Cost Explorer", self.account_name, self.region, err)
            return {"cost_yesterday": {}, "cost_mtd": {}, "service_costs": {}}


class AwsEc2Coordinator(AwsBaseCoordinator):
    """Coordinator for EC2 data."""

    def __init__(
        self, hass: HomeAssistant, aws_client, account_name: str, refresh_interval: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            aws_client,
            account_name,
            f"EC2 ({aws_client.region})",
            refresh_interval,
        )

    def _fetch_data(self) -> dict:
        """Fetch EC2 data."""
        try:
            ec2_client = self.aws_client.get_ec2_client()
            response = ec2_client.describe_instances()
            
            instances = []
            for reservation in response.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    # Get Name tag
                    tags = {tag["Key"]: tag["Value"] for tag in instance.get("Tags", [])}
                    
                    instances.append({
                        "instance_id": instance.get("InstanceId"),
                        "instance_type": instance.get("InstanceType"),
                        "state": instance.get("State", {}).get("Name"),
                        "launch_time": str(instance.get("LaunchTime", "")),
                        "public_ip": instance.get("PublicIpAddress"),
                        "private_ip": instance.get("PrivateIpAddress"),
                        "public_dns": instance.get("PublicDnsName"),
                        "vpc_id": instance.get("VpcId"),
                        "subnet_id": instance.get("SubnetId"),
                        "security_groups": [sg.get("GroupName") for sg in instance.get("SecurityGroups", [])],
                        "key_name": instance.get("KeyName"),
                        "platform": instance.get("Platform", "linux"),
                        "architecture": instance.get("Architecture"),
                        "iam_profile": instance.get("IamInstanceProfile", {}).get("Arn", "").split("/")[-1] or None,
                        "monitoring": instance.get("Monitoring", {}).get("State"),
                        "tags": tags,
                    })
            
            return {"instances": instances}
        except Exception as err:
            _LOGGER.error("%s [account=%s region=%s]: %s", "Error fetching EC2", self.account_name, self.region, err)
            return {"instances": []}


class AwsRdsCoordinator(AwsBaseCoordinator):
    """Coordinator for RDS data."""

    def __init__(
        self, hass: HomeAssistant, aws_client, account_name: str, refresh_interval: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            aws_client,
            account_name,
            f"RDS ({aws_client.region})",
            refresh_interval,
        )

    def _fetch_data(self) -> dict:
        """Fetch RDS data."""
        try:
            rds_client = self.aws_client.get_rds_client()
            response = rds_client.describe_db_instances()
            
            instances = []
            for db in response.get("DBInstances", []):
                    endpoint = db.get("Endpoint", {})
                    instances.append({
                        "db_instance_identifier": db.get("DBInstanceIdentifier"),
                        "db_instance_class": db.get("DBInstanceClass"),
                        "engine": db.get("Engine"),
                        "engine_version": db.get("EngineVersion"),
                        "status": db.get("DBInstanceStatus"),
                        "allocated_storage": db.get("AllocatedStorage"),
                        "storage_type": db.get("StorageType"),
                        "multi_az": db.get("MultiAZ", False),
                        "publicly_accessible": db.get("PubliclyAccessible", False),
                        "deletion_protection": db.get("DeletionProtection", False),
                        "backup_retention_days": db.get("BackupRetentionPeriod", 0),
                        "performance_insights": db.get("PerformanceInsightsEnabled", False),
                        "endpoint": endpoint.get("Address"),
                        "port": endpoint.get("Port"),
                        "vpc_id": db.get("DBSubnetGroup", {}).get("VpcId"),
                        "availability_zone": db.get("AvailabilityZone"),
                        "ca_certificate": db.get("CACertificateIdentifier"),
                    })
            
            return {"instances": instances}
        except Exception as err:
            _LOGGER.error("%s [account=%s region=%s]: %s", "Error fetching RDS", self.account_name, self.region, err)
            return {"instances": []}


class AwsLambdaCoordinator(AwsBaseCoordinator):
    """Coordinator for Lambda data."""

    def __init__(
        self, hass: HomeAssistant, aws_client, account_name: str, refresh_interval: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            aws_client,
            account_name,
            f"Lambda ({aws_client.region})",
            refresh_interval,
        )

    def _fetch_data(self) -> dict:
        """Fetch Lambda data."""
        try:
            lambda_client = self.aws_client.get_lambda_client()
            
            functions = []
            paginator = lambda_client.get_paginator('list_functions')
            for page in paginator.paginate():
                for func in page.get("Functions", []):
                    functions.append({
                        "function_name": func.get("FunctionName"),
                        "runtime": func.get("Runtime"),
                        "memory_size": func.get("MemorySize"),
                        "timeout": func.get("Timeout"),
                        "code_size": func.get("CodeSize"),
                        "last_modified": func.get("LastModified"),
                        "description": func.get("Description", ""),
                        "handler": func.get("Handler"),
                        "role": func.get("Role", "").split("/")[-1],
                        "package_type": func.get("PackageType", "Zip"),
                        "architectures": func.get("Architectures", ["x86_64"]),
                        "ephemeral_storage_mb": func.get("EphemeralStorage", {}).get("Size", 512),
                        "layers_count": len(func.get("Layers", [])),
                    })
            
            return {"functions": functions}
        except Exception as err:
            _LOGGER.error("%s [account=%s region=%s]: %s", "Error fetching Lambda", self.account_name, self.region, err)
            return {"functions": []}


class AwsLoadBalancerCoordinator(AwsBaseCoordinator):
    """Coordinator for Load Balancer data."""

    def __init__(
        self, hass: HomeAssistant, aws_client, account_name: str, refresh_interval: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            aws_client,
            account_name,
            f"Load Balancers ({aws_client.region})",
            refresh_interval,
        )

    def _fetch_data(self) -> dict:
        """Fetch Load Balancer data."""
        try:
            elbv2_client = self.aws_client.get_elbv2_client()
            
            load_balancers = []
            paginator = elbv2_client.get_paginator('describe_load_balancers')
            for page in paginator.paginate():
                for lb in page.get("LoadBalancers", []):
                    load_balancers.append({
                        "name": lb.get("LoadBalancerName"),
                        "dns_name": lb.get("DNSName"),
                        "type": lb.get("Type"),
                        "scheme": lb.get("Scheme"),
                        "state": lb.get("State", {}).get("Code"),
                        "vpc_id": lb.get("VpcId"),
                    })
            
            return {"load_balancers": load_balancers}
        except Exception as err:
            _LOGGER.error("%s [account=%s region=%s]: %s", "Error fetching Load Balancers", self.account_name, self.region, err)
            return {"load_balancers": []}


class AwsAutoScalingCoordinator(AwsBaseCoordinator):
    """Coordinator for Auto Scaling data."""

    def __init__(
        self, hass: HomeAssistant, aws_client, account_name: str, refresh_interval: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            aws_client,
            account_name,
            f"Auto Scaling ({aws_client.region})",
            refresh_interval,
        )

    def _fetch_data(self) -> dict:
        """Fetch Auto Scaling data."""
        try:
            asg_client = self.aws_client.get_autoscaling_client()
            
            auto_scaling_groups = []
            paginator = asg_client.get_paginator('describe_auto_scaling_groups')
            for page in paginator.paginate():
                for asg in page.get("AutoScalingGroups", []):
                    lt = asg.get("LaunchTemplate", {})
                    lc = asg.get("LaunchConfigurationName", "")
                    suspended = [p.get("ProcessName") for p in asg.get("SuspendedProcesses", [])]
                    auto_scaling_groups.append({
                        "name": asg.get("AutoScalingGroupName"),
                        "desired_capacity": asg.get("DesiredCapacity"),
                        "min_size": asg.get("MinSize"),
                        "max_size": asg.get("MaxSize"),
                        "instances": len(asg.get("Instances", [])),
                        "health_check_type": asg.get("HealthCheckType"),
                        "availability_zones": asg.get("AvailabilityZones", []),
                        "launch_template": lt.get("LaunchTemplateName") or lc or None,
                        "launch_template_version": lt.get("Version"),
                        "suspended_processes": suspended,
                        "vpc_zone_identifier": asg.get("VPCZoneIdentifier", ""),
                        "termination_policies": asg.get("TerminationPolicies", []),
                        "created_time": str(asg.get("CreatedTime", "")),
                    })
            
            return {"auto_scaling_groups": auto_scaling_groups}
        except Exception as err:
            _LOGGER.error("%s [account=%s region=%s]: %s", "Error fetching Auto Scaling Groups", self.account_name, self.region, err)
            return {"auto_scaling_groups": []}


class AwsDynamoDBCoordinator(AwsBaseCoordinator):
    """Coordinator for DynamoDB data."""

    def __init__(
        self, hass: HomeAssistant, aws_client, account_name: str, refresh_interval: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            aws_client,
            account_name,
            f"DynamoDB ({aws_client.region})",
            refresh_interval,
        )

    def _fetch_data(self) -> dict:
        """Fetch DynamoDB data."""
        try:
            dynamodb_client = self.aws_client.get_dynamodb_client()
            
            # List all tables
            tables = []
            paginator = dynamodb_client.get_paginator('list_tables')
            for page in paginator.paginate():
                tables.extend(page.get('TableNames', []))
            
            # Get details for each table
            table_details = []
            for table_name in tables:
                try:
                    response = dynamodb_client.describe_table(TableName=table_name)
                    table = response['Table']
                    billing = table.get('BillingModeSummary', {})
                    ptp = table.get('ProvisionedThroughput', {})
                    table_details.append({
                        'name': table_name,
                        'status': table.get('TableStatus'),
                        'item_count': table.get('ItemCount', 0),
                        'size_bytes': table.get('TableSizeBytes', 0),
                        'creation_date': str(table.get('CreationDateTime', '')),
                        'billing_mode': billing.get('BillingMode', 'PROVISIONED'),
                        'read_capacity_units': ptp.get('ReadCapacityUnits', 0),
                        'write_capacity_units': ptp.get('WriteCapacityUnits', 0),
                        'stream_enabled': table.get('StreamSpecification', {}).get('StreamEnabled', False),
                        'encryption_type': table.get('SSEDescription', {}).get('Status', 'DISABLED'),
                        'global_indexes': len(table.get('GlobalSecondaryIndexes', [])),
                        'local_indexes': len(table.get('LocalSecondaryIndexes', [])),
                        'table_class': table.get('TableClassSummary', {}).get('TableClass', 'STANDARD'),
                    })
                except Exception as err:
                    _LOGGER.warning(f"Error describing DynamoDB table {table_name}: {err}")
            
            return {"tables": table_details}
        except Exception as err:
            _LOGGER.error("%s [account=%s region=%s]: %s", "Error fetching DynamoDB", self.account_name, self.region, err)
            return {"tables": []}


class AwsElastiCacheCoordinator(AwsBaseCoordinator):
    """Coordinator for ElastiCache data."""

    def __init__(
        self, hass: HomeAssistant, aws_client, account_name: str, refresh_interval: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            aws_client,
            account_name,
            f"ElastiCache ({aws_client.region})",
            refresh_interval,
        )

    def _fetch_data(self) -> dict:
        """Fetch ElastiCache data."""
        try:
            elasticache_client = self.aws_client.get_elasticache_client()
            
            # Get cache clusters
            clusters = []
            paginator = elasticache_client.get_paginator('describe_cache_clusters')
            for page in paginator.paginate():
                for cluster in page.get('CacheClusters', []):
                    clusters.append({
                        'id': cluster.get('CacheClusterId'),
                        'status': cluster.get('CacheClusterStatus'),
                        'engine': cluster.get('Engine'),
                        'engine_version': cluster.get('EngineVersion'),
                        'node_type': cluster.get('CacheNodeType'),
                        'num_nodes': cluster.get('NumCacheNodes', 0),
                        'preferred_az': cluster.get('PreferredAvailabilityZone'),
                        'parameter_group': cluster.get('CacheParameterGroup', {}).get('CacheParameterGroupName'),
                        'snapshot_retention_days': cluster.get('SnapshotRetentionLimit', 0),
                        'at_rest_encryption': cluster.get('AtRestEncryptionEnabled', False),
                        'in_transit_encryption': cluster.get('TransitEncryptionEnabled', False),
                        'replication_group_id': cluster.get('ReplicationGroupId'),
                        'auto_minor_version_upgrade': cluster.get('AutoMinorVersionUpgrade', False),
                    })
            
            return {"clusters": clusters}
        except Exception as err:
            _LOGGER.error("%s [account=%s region=%s]: %s", "Error fetching ElastiCache", self.account_name, self.region, err)
            return {"clusters": []}


class AwsECSCoordinator(AwsBaseCoordinator):
    """Coordinator for ECS data."""

    def __init__(
        self, hass: HomeAssistant, aws_client, account_name: str, refresh_interval: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            aws_client,
            account_name,
            f"ECS ({aws_client.region})",
            refresh_interval,
        )

    def _fetch_data(self) -> dict:
        """Fetch ECS data."""
        try:
            ecs_client = self.aws_client.get_ecs_client()
            
            # List clusters
            cluster_arns = []
            paginator = ecs_client.get_paginator('list_clusters')
            for page in paginator.paginate():
                cluster_arns.extend(page.get('clusterArns', []))
            
            # Get cluster details
            clusters = []
            if cluster_arns:
                response = ecs_client.describe_clusters(clusters=cluster_arns, include=['STATISTICS'])
                for cluster in response.get('clusters', []):
                    clusters.append({
                        'name': cluster.get('clusterName'),
                        'arn': cluster.get('clusterArn'),
                        'status': cluster.get('status'),
                        'running_tasks': cluster.get('runningTasksCount', 0),
                        'pending_tasks': cluster.get('pendingTasksCount', 0),
                        'active_services': cluster.get('activeServicesCount', 0),
                        'registered_instances': cluster.get('registeredContainerInstancesCount', 0),
                    })
            
            return {"clusters": clusters}
        except Exception as err:
            _LOGGER.error("%s [account=%s region=%s]: %s", "Error fetching ECS", self.account_name, self.region, err)
            return {"clusters": []}


class AwsEKSCoordinator(AwsBaseCoordinator):
    """Coordinator for EKS data."""

    def __init__(
        self, hass: HomeAssistant, aws_client, account_name: str, refresh_interval: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            aws_client,
            account_name,
            f"EKS ({aws_client.region})",
            refresh_interval,
        )

    def _fetch_data(self) -> dict:
        """Fetch EKS data."""
        try:
            eks_client = self.aws_client.get_eks_client()
            
            # List clusters
            cluster_names = []
            paginator = eks_client.get_paginator('list_clusters')
            for page in paginator.paginate():
                cluster_names.extend(page.get('clusters', []))
            
            # Get cluster details
            clusters = []
            for cluster_name in cluster_names:
                try:
                    response = eks_client.describe_cluster(name=cluster_name)
                    cluster = response['cluster']
                    clusters.append({
                        'name': cluster.get('name'),
                        'arn': cluster.get('arn'),
                        'status': cluster.get('status'),
                        'version': cluster.get('version'),
                        'endpoint': cluster.get('endpoint'),
                        'created_at': str(cluster.get('createdAt', '')),
                    })
                except Exception as err:
                    _LOGGER.warning(f"Error describing EKS cluster {cluster_name}: {err}")
            
            return {"clusters": clusters}
        except Exception as err:
            _LOGGER.error("%s [account=%s region=%s]: %s", "Error fetching EKS", self.account_name, self.region, err)
            return {"clusters": []}


class AwsEBSCoordinator(AwsBaseCoordinator):
    """Coordinator for EBS volumes data."""

    def __init__(
        self, hass: HomeAssistant, aws_client, account_name: str, refresh_interval: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            aws_client,
            account_name,
            f"EBS ({aws_client.region})",
            refresh_interval,
        )

    def _fetch_data(self) -> dict:
        """Fetch EBS volumes and snapshots data."""
        from .const import MAX_EBS_SNAPSHOTS

        ec2_client = self.aws_client.get_ec2_client()

        # ----------------------------------------------------------------
        # Volumes
        # ----------------------------------------------------------------
        volumes = []
        try:
            paginator = ec2_client.get_paginator('describe_volumes')
            for page in paginator.paginate():
                for volume in page.get('Volumes', []):
                    attachments = volume.get('Attachments', [])
                    attached_to = attachments[0].get('InstanceId') if attachments else None
                    volumes.append({
                        'id': volume.get('VolumeId'),
                        'size': volume.get('Size', 0),
                        'type': volume.get('VolumeType'),
                        'iops': volume.get('Iops'),
                        'throughput': volume.get('Throughput'),
                        'state': volume.get('State'),
                        'az': volume.get('AvailabilityZone'),
                        'attached_to': attached_to,
                        'encrypted': volume.get('Encrypted', False),
                        'created': str(volume.get('CreateTime', '')),
                    })
        except Exception as err:
            _LOGGER.error(
                "%s [account=%s region=%s]: %s",
                "Error fetching EBS volumes", self.account_name, self.region, err,
            )

        # ----------------------------------------------------------------
        # Snapshots — owner filter is mandatory; without it the API returns
        # every public snapshot on AWS (millions of entries).
        # Results are sorted newest-first and truncated to MAX_EBS_SNAPSHOTS
        # before storage to keep HA attribute payloads bounded.
        # ----------------------------------------------------------------
        snapshots = []
        snapshots_truncated = False
        total_snapshot_size_gb = 0
        try:
            all_snapshots = []
            paginator = ec2_client.get_paginator('describe_snapshots')
            for page in paginator.paginate(OwnerIds=['self']):
                for snap in page.get('Snapshots', []):
                    tags = {t['Key']: t['Value'] for t in snap.get('Tags', [])}
                    all_snapshots.append({
                        'snapshot_id': snap.get('SnapshotId'),
                        'volume_id': snap.get('VolumeId'),
                        'volume_size': snap.get('VolumeSize', 0),
                        'start_time': str(snap.get('StartTime', '')),
                        'state': snap.get('State'),
                        'progress': snap.get('Progress', ''),
                        'description': snap.get('Description', ''),
                        'name': tags.get('Name', ''),
                        'encrypted': snap.get('Encrypted', False),
                    })
                    total_snapshot_size_gb += snap.get('VolumeSize', 0)

            # Sort newest-first using the ISO start_time string (lexicographic
            # sort works correctly for ISO 8601 timestamps).
            all_snapshots.sort(key=lambda s: s['start_time'], reverse=True)

            if len(all_snapshots) > MAX_EBS_SNAPSHOTS:
                snapshots_truncated = True
            snapshots = all_snapshots[:MAX_EBS_SNAPSHOTS]

        except Exception as err:
            _LOGGER.error(
                "%s [account=%s region=%s]: %s",
                "Error fetching EBS snapshots", self.account_name, self.region, err,
            )

        return {
            "volumes": volumes,
            "snapshots": snapshots,
            "snapshots_truncated": snapshots_truncated,
            "total_snapshot_size_gb": total_snapshot_size_gb,
        }


class AwsSNSCoordinator(AwsBaseCoordinator):
    """Coordinator for SNS topics data."""

    def __init__(
        self, hass: HomeAssistant, aws_client, account_name: str, refresh_interval: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            aws_client,
            account_name,
            f"SNS ({aws_client.region})",
            refresh_interval,
        )

    def _fetch_data(self) -> dict:
        """Fetch SNS topics data."""
        try:
            sns_client = self.aws_client.get_sns_client()
            
            # List topics
            topics = []
            paginator = sns_client.get_paginator('list_topics')
            for page in paginator.paginate():
                for topic in page.get('Topics', []):
                    topic_arn = topic['TopicArn']
                    topic_name = topic_arn.split(':')[-1]
                    
                    # Get topic attributes
                    try:
                        attrs = sns_client.get_topic_attributes(TopicArn=topic_arn)
                        attributes = attrs.get('Attributes', {})
                        topics.append({
                            'name': topic_name,
                            'arn': topic_arn,
                            'subscriptions': int(attributes.get('SubscriptionsConfirmed', 0)),
                            'display_name': attributes.get('DisplayName', topic_name),
                        })
                    except Exception as err:
                        _LOGGER.warning(f"Error getting SNS topic attributes for {topic_name}: {err}")
            
            return {"topics": topics}
        except Exception as err:
            _LOGGER.error("%s [account=%s region=%s]: %s", "Error fetching SNS", self.account_name, self.region, err)
            return {"topics": []}


class AwsSQSCoordinator(AwsBaseCoordinator):
    """Coordinator for SQS queues data."""

    def __init__(
        self, hass: HomeAssistant, aws_client, account_name: str, refresh_interval: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            aws_client,
            account_name,
            f"SQS ({aws_client.region})",
            refresh_interval,
        )

    def _fetch_data(self) -> dict:
        """Fetch SQS queues data."""
        try:
            sqs_client = self.aws_client.get_sqs_client()
            
            # List queues
            queues = []
            paginator = sqs_client.get_paginator('list_queues')
            for page in paginator.paginate():
                for queue_url in page.get('QueueUrls', []):
                    queue_name = queue_url.split('/')[-1]
                    
                    # Get queue attributes
                    try:
                        attrs = sqs_client.get_queue_attributes(
                            QueueUrl=queue_url,
                            AttributeNames=['All']
                        )
                        attributes = attrs.get('Attributes', {})
                        queues.append({
                            'name': queue_name,
                            'url': queue_url,
                            'messages_available': int(attributes.get('ApproximateNumberOfMessages', 0)),
                            'messages_in_flight': int(attributes.get('ApproximateNumberOfMessagesNotVisible', 0)),
                            'messages_delayed': int(attributes.get('ApproximateNumberOfMessagesDelayed', 0)),
                            'created': attributes.get('CreatedTimestamp'),
                            'visibility_timeout_seconds': int(attributes.get('VisibilityTimeout', 30)),
                            'message_retention_seconds': int(attributes.get('MessageRetentionPeriod', 345600)),
                            'max_message_size_bytes': int(attributes.get('MaximumMessageSize', 262144)),
                            'delay_seconds': int(attributes.get('DelaySeconds', 0)),
                            'fifo': queue_name.endswith('.fifo'),
                            'kms_key': attributes.get('KmsMasterKeyId', ''),
                        })
                    except Exception as err:
                        _LOGGER.warning(f"Error getting SQS queue attributes for {queue_name}: {err}")
            
            return {"queues": queues}
        except Exception as err:
            _LOGGER.error("%s [account=%s region=%s]: %s", "Error fetching SQS", self.account_name, self.region, err)
            return {"queues": []}


class AwsS3Coordinator(AwsBaseCoordinator):
    """Coordinator for S3 buckets data."""

    def __init__(
        self, hass: HomeAssistant, aws_client, account_name: str, refresh_interval: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            aws_client,
            account_name,
            f"S3 ({aws_client.region})",
            refresh_interval,
        )

    def _fetch_data(self) -> dict:
        """Fetch S3 buckets data."""
        try:
            s3_client = self.aws_client.get_s3_client()
            
            # List all buckets (this is account-wide)
            response = s3_client.list_buckets()
            buckets = []
            
            for bucket in response.get('Buckets', []):
                bucket_name = bucket['Name']
                
                # Get bucket location
                try:
                    location_response = s3_client.get_bucket_location(Bucket=bucket_name)
                    location = location_response.get('LocationConstraint')
                    # None means us-east-1
                    bucket_region = location if location else 'us-east-1'
                    
                    # Only include buckets in this region
                    if bucket_region == self.aws_client.region:
                        buckets.append({
                            'name': bucket_name,
                            'region': bucket_region,
                            'created': str(bucket.get('CreationDate', '')),
                        })
                except Exception as err:
                    _LOGGER.warning(f"Error getting S3 bucket location for {bucket_name}: {err}")
            
            return {"buckets": buckets}
        except Exception as err:
            _LOGGER.error("%s [account=%s region=%s]: %s", "Error fetching S3", self.account_name, self.region, err)
            return {"buckets": []}


class AwsCloudWatchAlarmsCoordinator(AwsBaseCoordinator):
    """Coordinator for CloudWatch alarms data."""

    def __init__(
        self, hass: HomeAssistant, aws_client, account_name: str, refresh_interval: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            aws_client,
            account_name,
            f"CloudWatch Alarms ({aws_client.region})",
            refresh_interval,
        )

    def _fetch_data(self) -> dict:
        """Fetch CloudWatch alarms data."""
        try:
            cloudwatch_client = self.aws_client.get_cloudwatch_client()
            
            # Get all alarms
            alarms = []
            paginator = cloudwatch_client.get_paginator('describe_alarms')
            for page in paginator.paginate():
                for alarm in page.get('MetricAlarms', []):
                    alarms.append({
                        'name': alarm.get('AlarmName'),
                        'state': alarm.get('StateValue'),
                        'reason': alarm.get('StateReason'),
                        'metric': alarm.get('MetricName'),
                        'namespace': alarm.get('Namespace'),
                        'enabled': alarm.get('ActionsEnabled', False),
                    })
            
            return {"alarms": alarms}
        except Exception as err:
            _LOGGER.error("%s [account=%s region=%s]: %s", "Error fetching CloudWatch Alarms", self.account_name, self.region, err)
            return {"alarms": []}


class AwsElasticIPsCoordinator(AwsBaseCoordinator):
    """Coordinator for Elastic IPs data."""

    def __init__(
        self, hass: HomeAssistant, aws_client, account_name: str, refresh_interval: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            aws_client,
            account_name,
            f"Elastic IPs ({aws_client.region})",
            refresh_interval,
        )

    def _fetch_data(self) -> dict:
        """Fetch Elastic IPs data."""
        try:
            ec2_client = self.aws_client.get_ec2_client()
            
            # Get all Elastic IPs
            response = ec2_client.describe_addresses()
            addresses = []
            
            for address in response.get('Addresses', []):
                addresses.append({
                    'ip': address.get('PublicIp'),
                    'allocation_id': address.get('AllocationId'),
                    'associated_with': address.get('InstanceId') or address.get('NetworkInterfaceId'),
                    'domain': address.get('Domain'),
                    'attached': 'InstanceId' in address or 'NetworkInterfaceId' in address,
                })
            
            return {"addresses": addresses}
        except Exception as err:
            _LOGGER.error("%s [account=%s region=%s]: %s", "Error fetching Elastic IPs", self.account_name, self.region, err)
            return {"addresses": []}


class AwsClassicLBCoordinator(AwsBaseCoordinator):
    """Coordinator for Classic Load Balancer (ELB v1) data."""

    def __init__(
        self, hass: HomeAssistant, aws_client, account_name: str, refresh_interval: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            aws_client,
            account_name,
            f"Classic Load Balancers ({aws_client.region})",
            refresh_interval,
        )

    def _fetch_data(self) -> dict:
        """Fetch Classic Load Balancer data."""
        try:
            elb_client = self.aws_client.get_elb_client()

            load_balancers = []
            paginator = elb_client.get_paginator('describe_load_balancers')
            for page in paginator.paginate():
                for lb in page.get('LoadBalancerDescriptions', []):
                    hc = lb.get('HealthCheck', {})
                    listeners = [
                        {
                            'lb_port': l.get('Listener', {}).get('LoadBalancerPort'),
                            'lb_protocol': l.get('Listener', {}).get('Protocol'),
                            'instance_port': l.get('Listener', {}).get('InstancePort'),
                            'instance_protocol': l.get('Listener', {}).get('InstanceProtocol'),
                        }
                        for l in lb.get('ListenerDescriptions', [])
                    ]
                    instances = [i.get('InstanceId') for i in lb.get('Instances', [])]
                    load_balancers.append({
                        'name': lb.get('LoadBalancerName'),
                        'dns_name': lb.get('DNSName'),
                        'scheme': lb.get('Scheme'),
                        'vpc_id': lb.get('VPCId'),
                        'availability_zones': lb.get('AvailabilityZones', []),
                        'subnets': lb.get('Subnets', []),
                        'security_groups': lb.get('SecurityGroups', []),
                        'instances': instances,
                        'instance_count': len(instances),
                        'listeners': listeners,
                        'health_check_target': hc.get('Target'),
                        'health_check_interval': hc.get('Interval'),
                        'created_time': str(lb.get('CreatedTime', '')),
                    })

            return {"load_balancers": load_balancers}
        except Exception as err:
            _LOGGER.error("%s [account=%s region=%s]: %s", "Error fetching Classic Load Balancers", self.account_name, self.region, err)
            return {"load_balancers": []}


class AwsEFSCoordinator(AwsBaseCoordinator):
    """Coordinator for EFS file system data."""

    def __init__(
        self, hass: HomeAssistant, aws_client, account_name: str, refresh_interval: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            aws_client,
            account_name,
            f"EFS ({aws_client.region})",
            refresh_interval,
        )

    def _fetch_data(self) -> dict:
        """Fetch EFS file system data."""
        try:
            efs_client = self.aws_client.get_efs_client()

            file_systems = []
            paginator = efs_client.get_paginator('describe_file_systems')
            for page in paginator.paginate():
                for fs in page.get('FileSystems', []):
                    name = None
                    for tag in fs.get('Tags', []):
                        if tag.get('Key') == 'Name':
                            name = tag.get('Value')
                            break
                    size_bytes = fs.get('SizeInBytes', {}).get('Value', 0)
                    file_systems.append({
                        'id': fs.get('FileSystemId'),
                        'name': name or fs.get('FileSystemId'),
                        'state': fs.get('LifeCycleState'),
                        'size_bytes': size_bytes,
                        'size_gb': round(size_bytes / (1024 ** 3), 2) if size_bytes else 0,
                        'number_of_mount_targets': fs.get('NumberOfMountTargets', 0),
                        'performance_mode': fs.get('PerformanceMode'),
                        'throughput_mode': fs.get('ThroughputMode'),
                        'encrypted': fs.get('Encrypted', False),
                        'availability_zone': fs.get('AvailabilityZoneName'),
                        'created_time': str(fs.get('CreationTime', '')),
                        'tags': {t['Key']: t['Value'] for t in fs.get('Tags', [])},
                    })

            return {"file_systems": file_systems}
        except Exception as err:
            _LOGGER.error("%s [account=%s region=%s]: %s", "Error fetching EFS", self.account_name, self.region, err)
            return {"file_systems": []}


class AwsKinesisCoordinator(AwsBaseCoordinator):
    """Coordinator for Kinesis stream data."""

    def __init__(
        self, hass: HomeAssistant, aws_client, account_name: str, refresh_interval: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            aws_client,
            account_name,
            f"Kinesis ({aws_client.region})",
            refresh_interval,
        )

    def _fetch_data(self) -> dict:
        """Fetch Kinesis stream data."""
        try:
            kinesis_client = self.aws_client.get_kinesis_client()

            streams = []
            paginator = kinesis_client.get_paginator('list_streams')
            for page in paginator.paginate():
                for summary in page.get('StreamSummaries', []):
                    name = summary.get('StreamName')
                    arn = summary.get('StreamARN')
                    status = summary.get('StreamStatus')
                    stream_mode = summary.get('StreamModeDetails', {}).get('StreamMode', 'PROVISIONED')

                    # Get full stream details
                    shard_count = None
                    retention_hours = None
                    consumer_count = None
                    try:
                        detail = kinesis_client.describe_stream_summary(StreamName=name)
                        sd = detail.get('StreamDescriptionSummary', {})
                        shard_count = sd.get('OpenShardCount')
                        retention_hours = sd.get('RetentionPeriodHours')
                        consumer_count = sd.get('ConsumerCount', 0)
                    except Exception:
                        pass

                    streams.append({
                        'name': name,
                        'arn': arn,
                        'status': status,
                        'stream_mode': stream_mode,
                        'shard_count': shard_count,
                        'retention_hours': retention_hours,
                        'consumer_count': consumer_count,
                    })

            return {"streams": streams}
        except Exception as err:
            _LOGGER.error("%s [account=%s region=%s]: %s", "Error fetching Kinesis", self.account_name, self.region, err)
            return {"streams": []}


class AwsBeanstalkCoordinator(AwsBaseCoordinator):
    """Coordinator for Elastic Beanstalk environment data."""

    def __init__(
        self, hass: HomeAssistant, aws_client, account_name: str, refresh_interval: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            aws_client,
            account_name,
            f"Elastic Beanstalk ({aws_client.region})",
            refresh_interval,
        )

    def _fetch_data(self) -> dict:
        """Fetch Elastic Beanstalk environment data."""
        try:
            eb_client = self.aws_client.get_beanstalk_client()

            environments = []
            paginator = eb_client.get_paginator('describe_environments')
            for page in paginator.paginate():
                for env in page.get('Environments', []):
                    environments.append({
                        'name': env.get('EnvironmentName'),
                        'id': env.get('EnvironmentId'),
                        'application_name': env.get('ApplicationName'),
                        'status': env.get('Status'),
                        'health': env.get('Health'),
                        'health_status': env.get('HealthStatus'),
                        'platform_arn': env.get('PlatformArn'),
                        'solution_stack': env.get('SolutionStackName'),
                        'tier_name': env.get('Tier', {}).get('Name'),
                        'tier_type': env.get('Tier', {}).get('Type'),
                        'cname': env.get('CNAME'),
                        'endpoint_url': env.get('EndpointURL'),
                        'date_created': str(env.get('DateCreated', '')),
                        'date_updated': str(env.get('DateUpdated', '')),
                    })

            return {"environments": environments}
        except Exception as err:
            _LOGGER.error("%s [account=%s region=%s]: %s", "Error fetching Elastic Beanstalk", self.account_name, self.region, err)
            return {"environments": []}


class AwsRoute53Coordinator(AwsBaseCoordinator):
    """Coordinator for Route 53 hosted zone data (global service, fetched via us-east-1)."""

    def __init__(
        self, hass: HomeAssistant, aws_client, account_name: str, refresh_interval: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            aws_client,
            account_name,
            "Route 53 (global)",
            refresh_interval,
        )

    def _fetch_data(self) -> dict:
        """Fetch Route 53 hosted zone data."""
        try:
            r53_client = self.aws_client.get_route53_client()

            zones = []
            paginator = r53_client.get_paginator('list_hosted_zones')
            for page in paginator.paginate():
                for zone in page.get('HostedZones', []):
                    config = zone.get('Config', {})
                    zone_id = zone.get('Id', '').split('/')[-1]
                    zones.append({
                        'id': zone_id,
                        'name': zone.get('Name', '').rstrip('.'),
                        'private': config.get('PrivateZone', False),
                        'record_count': zone.get('ResourceRecordSetCount', 0),
                        'comment': config.get('Comment', ''),
                    })

            return {"zones": zones}
        except Exception as err:
            _LOGGER.error("%s [account=%s region=%s]: %s", "Error fetching Route 53", self.account_name, self.region, err)
            return {"zones": []}


class AwsApiGatewayCoordinator(AwsBaseCoordinator):
    """Coordinator for API Gateway (v1 REST and v2 HTTP/WebSocket) data."""

    def __init__(
        self, hass: HomeAssistant, aws_client, account_name: str, refresh_interval: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            aws_client,
            account_name,
            f"API Gateway ({aws_client.region})",
            refresh_interval,
        )

    def _fetch_data(self) -> dict:
        """Fetch API Gateway data from both v1 and v2."""
        apis = []

        # v1 REST APIs
        try:
            apigw1_client = self.aws_client.get_apigateway_client()
            paginator = apigw1_client.get_paginator('get_rest_apis')
            for page in paginator.paginate():
                for api in page.get('items', []):
                    apis.append({
                        'id': api.get('id'),
                        'name': api.get('name'),
                        'type': 'REST',
                        'description': api.get('description', ''),
                        'endpoint_type': ', '.join(
                            api.get('endpointConfiguration', {}).get('types', [])
                        ),
                        'created_date': str(api.get('createdDate', '')),
                        'api_endpoint': None,
                    })
        except Exception as err:
            _LOGGER.error("%s [account=%s region=%s]: %s", "Error fetching API Gateway v1", self.account_name, self.region, err)

        # v2 HTTP/WebSocket APIs
        try:
            apigw2_client = self.aws_client.get_apigatewayv2_client()
            paginator = apigw2_client.get_paginator('get_apis')
            for page in paginator.paginate():
                for api in page.get('Items', []):
                    apis.append({
                        'id': api.get('ApiId'),
                        'name': api.get('Name'),
                        'type': api.get('ProtocolType', 'HTTP'),
                        'description': api.get('Description', ''),
                        'endpoint_type': None,
                        'created_date': str(api.get('CreatedDate', '')),
                        'api_endpoint': api.get('ApiEndpoint'),
                    })
        except Exception as err:
            _LOGGER.error("%s [account=%s region=%s]: %s", "Error fetching API Gateway v2", self.account_name, self.region, err)

        return {"apis": apis}


class AwsCloudFrontCoordinator(AwsBaseCoordinator):
    """Coordinator for CloudFront distribution data (global service, fetched via us-east-1)."""

    def __init__(
        self, hass: HomeAssistant, aws_client, account_name: str, refresh_interval: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            aws_client,
            account_name,
            "CloudFront (global)",
            refresh_interval,
        )

    def _fetch_data(self) -> dict:
        """Fetch CloudFront distribution data."""
        try:
            cf_client = self.aws_client.get_cloudfront_client()

            distributions = []
            paginator = cf_client.get_paginator('list_distributions')
            for page in paginator.paginate():
                dist_list = page.get('DistributionList', {})
                for dist in dist_list.get('Items', []):
                    config = dist.get('DefaultCacheBehavior', {})
                    aliases = dist.get('Aliases', {}).get('Items', [])
                    origins = [
                        o.get('DomainName')
                        for o in dist.get('Origins', {}).get('Items', [])
                    ]
                    distributions.append({
                        'id': dist.get('Id'),
                        'domain_name': dist.get('DomainName'),
                        'status': dist.get('Status'),
                        'enabled': dist.get('Enabled', False),
                        'http_version': dist.get('HttpVersion'),
                        'price_class': dist.get('PriceClass'),
                        'origins': origins,
                        'aliases': aliases,
                        'comment': dist.get('Comment', ''),
                        'last_modified': str(dist.get('LastModifiedTime', '')),
                    })

            return {"distributions": distributions}
        except Exception as err:
            _LOGGER.error("%s [account=%s region=%s]: %s", "Error fetching CloudFront", self.account_name, self.region, err)
            return {"distributions": []}


class AwsVPCCoordinator(AwsBaseCoordinator):
    """Coordinator for VPC data including subnets, gateways and peering."""

    def __init__(
        self, hass: HomeAssistant, aws_client, account_name: str, refresh_interval: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            aws_client,
            account_name,
            f"VPC ({aws_client.region})",
            refresh_interval,
        )

    def _fetch_data(self) -> dict:
        """Fetch VPC data with subnets and gateway info."""
        try:
            ec2_client = self.aws_client.get_ec2_client()

            # Fetch all VPCs
            vpcs_response = ec2_client.describe_vpcs()
            vpc_list = vpcs_response.get('Vpcs', [])

            # Fetch subnets (all at once, then group by VPC)
            subnets_response = ec2_client.describe_subnets()
            subnets_by_vpc: dict = {}
            for subnet in subnets_response.get('Subnets', []):
                vpc_id = subnet.get('VpcId')
                if vpc_id not in subnets_by_vpc:
                    subnets_by_vpc[vpc_id] = []
                name = next(
                    (t['Value'] for t in subnet.get('Tags', []) if t['Key'] == 'Name'), None
                )
                subnets_by_vpc[vpc_id].append({
                    'subnet_id': subnet.get('SubnetId'),
                    'name': name,
                    'cidr_block': subnet.get('CidrBlock'),
                    'availability_zone': subnet.get('AvailabilityZone'),
                    'available_ips': subnet.get('AvailableIpAddressCount'),
                    'public': subnet.get('MapPublicIpOnLaunch', False),
                    'state': subnet.get('State'),
                })

            # Fetch internet gateways (grouped by VPC)
            igw_response = ec2_client.describe_internet_gateways()
            igw_by_vpc: dict = {}
            for igw in igw_response.get('InternetGateways', []):
                for attachment in igw.get('Attachments', []):
                    vpc_id = attachment.get('VpcId')
                    if vpc_id:
                        igw_by_vpc[vpc_id] = igw.get('InternetGatewayId')

            # Fetch NAT gateways (grouped by VPC)
            nat_response = ec2_client.describe_nat_gateways(
                Filters=[{'Name': 'state', 'Values': ['available', 'pending']}]
            )
            nat_by_vpc: dict = {}
            for nat in nat_response.get('NatGateways', []):
                vpc_id = nat.get('VpcId')
                if vpc_id not in nat_by_vpc:
                    nat_by_vpc[vpc_id] = []
                nat_by_vpc[vpc_id].append(nat.get('NatGatewayId'))

            # Fetch VPC peering connections (grouped by VPC)
            peering_response = ec2_client.describe_vpc_peering_connections(
                Filters=[{'Name': 'status-code', 'Values': ['active', 'pending-acceptance']}]
            )
            peering_by_vpc: dict = {}
            for peering in peering_response.get('VpcPeeringConnections', []):
                for vpc_id in [
                    peering.get('RequesterVpcInfo', {}).get('VpcId'),
                    peering.get('AccepterVpcInfo', {}).get('VpcId'),
                ]:
                    if vpc_id:
                        peering_by_vpc[vpc_id] = peering_by_vpc.get(vpc_id, 0) + 1

            # Fetch VPN connections (grouped by VPC via attached gateway)
            vpn_response = ec2_client.describe_vpn_connections(
                Filters=[{'Name': 'state', 'Values': ['available', 'pending']}]
            )
            vpn_by_vpc: dict = {}
            for vpn in vpn_response.get('VpnConnections', []):
                vpc_id = vpn.get('VpcId')
                if vpc_id:
                    vpn_by_vpc[vpc_id] = vpn_by_vpc.get(vpc_id, 0) + 1

            # Assemble VPC objects
            vpcs = []
            for vpc in vpc_list:
                vpc_id = vpc.get('VpcId')
                name = next(
                    (t['Value'] for t in vpc.get('Tags', []) if t['Key'] == 'Name'), None
                )
                subnets = subnets_by_vpc.get(vpc_id, [])
                public_subnets = [s for s in subnets if s['public']]
                private_subnets = [s for s in subnets if not s['public']]

                # Truncate subnet list if it would exceed HA attribute limits
                MAX_SUBNETS = 40
                truncated = len(subnets) > MAX_SUBNETS
                subnet_list = subnets[:MAX_SUBNETS]

                vpcs.append({
                    'vpc_id': vpc_id,
                    'name': name or vpc_id,
                    'state': vpc.get('State'),
                    'cidr_block': vpc.get('CidrBlock'),
                    'is_default': vpc.get('IsDefault', False),
                    'tenancy': vpc.get('InstanceTenancy'),
                    'dhcp_options_id': vpc.get('DhcpOptionsId'),
                    'internet_gateway': igw_by_vpc.get(vpc_id),
                    'nat_gateways': nat_by_vpc.get(vpc_id, []),
                    'nat_gateway_count': len(nat_by_vpc.get(vpc_id, [])),
                    'peering_connection_count': peering_by_vpc.get(vpc_id, 0),
                    'vpn_connection_count': vpn_by_vpc.get(vpc_id, 0),
                    'subnet_count': len(subnets),
                    'public_subnet_count': len(public_subnets),
                    'private_subnet_count': len(private_subnets),
                    'subnets': subnet_list,
                    'subnets_truncated': truncated,
                })

            return {"vpcs": vpcs}
        except Exception as err:
            _LOGGER.error("%s [account=%s region=%s]: %s", "Error fetching VPC", self.account_name, self.region, err)
            return {"vpcs": []}


class AwsACMCoordinator(AwsBaseCoordinator):
    """Coordinator for ACM certificate data."""

    def __init__(
        self, hass: HomeAssistant, aws_client, account_name: str, refresh_interval: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            aws_client,
            account_name,
            f"ACM ({aws_client.region})",
            refresh_interval,
        )

    def _fetch_data(self) -> dict:
        """Fetch ACM certificate data."""
        try:
            acm_client = self.aws_client.get_acm_client()

            certificates = []
            paginator = acm_client.get_paginator('list_certificates')
            for page in paginator.paginate():
                for cert_summary in page.get('CertificateSummaryList', []):
                    arn = cert_summary.get('CertificateArn')
                    try:
                        detail = acm_client.describe_certificate(CertificateArn=arn)
                        cert = detail.get('Certificate', {})
                        not_after = cert.get('NotAfter')
                        not_before = cert.get('NotBefore')
                        days_until_expiry = None
                        if not_after:
                            from datetime import datetime, timezone
                            now = datetime.now(timezone.utc)
                            if hasattr(not_after, 'tzinfo') and not_after.tzinfo:
                                days_until_expiry = (not_after - now).days
                            else:
                                days_until_expiry = (not_after.replace(tzinfo=timezone.utc) - now).days

                        certificates.append({
                            'arn': arn,
                            'domain_name': cert.get('DomainName'),
                            'subject_alternative_names': cert.get('SubjectAlternativeNames', []),
                            'status': cert.get('Status'),
                            'type': cert.get('Type'),
                            'issuer': cert.get('Issuer'),
                            'key_algorithm': cert.get('KeyAlgorithm'),
                            'not_before': str(not_before) if not_before else None,
                            'not_after': str(not_after) if not_after else None,
                            'days_until_expiry': days_until_expiry,
                            'renewal_eligibility': cert.get('RenewalEligibility'),
                            'in_use_by': cert.get('InUseBy', []),
                        })
                    except Exception as err:
                        _LOGGER.warning(
                            "ACM [account=%s region=%s]: could not describe cert %s: %s",
                            self.account_name, self.region, arn, err,
                        )

            return {"certificates": certificates}
        except Exception as err:
            _LOGGER.error("%s [account=%s region=%s]: %s", "Error fetching ACM", self.account_name, self.region, err)
            return {"certificates": []}


class AwsECRCoordinator(AwsBaseCoordinator):
    """Coordinator for ECR repository data."""

    def __init__(
        self, hass: HomeAssistant, aws_client, account_name: str, refresh_interval: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            aws_client,
            account_name,
            f"ECR ({aws_client.region})",
            refresh_interval,
        )

    def _fetch_data(self) -> dict:
        """Fetch ECR repository data."""
        try:
            ecr_client = self.aws_client.get_ecr_client()

            repositories = []
            paginator = ecr_client.get_paginator('describe_repositories')
            for page in paginator.paginate():
                for repo in page.get('repositories', []):
                    repo_name = repo.get('repositoryName')
                    image_count = 0
                    try:
                        img_paginator = ecr_client.get_paginator('describe_images')
                        for img_page in img_paginator.paginate(repositoryName=repo_name):
                            image_count += len(img_page.get('imageDetails', []))
                    except Exception:
                        pass

                    repositories.append({
                        'name': repo_name,
                        'arn': repo.get('repositoryArn'),
                        'uri': repo.get('repositoryUri'),
                        'image_count': image_count,
                        'image_tag_mutability': repo.get('imageTagMutability'),
                        'scan_on_push': repo.get('imageScanningConfiguration', {}).get('scanOnPush', False),
                        'encryption_type': repo.get('encryptionConfiguration', {}).get('encryptionType'),
                        'created_at': str(repo.get('createdAt', '')),
                    })

            return {"repositories": repositories}
        except Exception as err:
            _LOGGER.error("%s [account=%s region=%s]: %s", "Error fetching ECR", self.account_name, self.region, err)
            return {"repositories": []}



class AwsCloudTrailCoordinator(AwsBaseCoordinator):
    """Coordinator for CloudTrail trail data."""

    def __init__(
        self, hass: HomeAssistant, aws_client, account_name: str, refresh_interval: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            aws_client,
            account_name,
            f"CloudTrail ({aws_client.region})",
            refresh_interval,
        )

    def _fetch_data(self) -> dict:
        """Fetch CloudTrail trail data."""
        try:
            ct_client = self.aws_client.get_cloudtrail_client()

            # includeShadowTrails=False still returns trails homed in other
            # regions when queried from a different region. Filter explicitly
            # to only trails whose HomeRegion matches the current region so
            # each trail is counted exactly once.
            trails_response = ct_client.describe_trails(includeShadowTrails=False)
            trails = []

            for trail in trails_response.get('trailList', []):
                # Skip trails not homed in this region
                if trail.get('HomeRegion') != self.region:
                    continue
                trail_arn = trail.get('TrailARN')
                name = trail.get('Name')

                # Get trail status
                is_logging = False
                latest_delivery = None
                latest_error = None
                latest_digest = None
                try:
                    status = ct_client.get_trail_status(Name=trail_arn)
                    is_logging = status.get('IsLogging', False)
                    latest_delivery = str(status.get('LatestDeliveryTime', '') or '')
                    latest_error = status.get('LatestDeliveryError') or ''
                    latest_digest = str(status.get('LatestDigestDeliveryTime', '') or '')
                except Exception:
                    pass

                # Get event selectors
                management_events = False
                data_event_count = 0
                try:
                    selectors = ct_client.get_event_selectors(TrailName=trail_arn)
                    for selector in selectors.get('EventSelectors', []):
                        if selector.get('ReadWriteType') in ('All', 'WriteOnly', 'ReadOnly'):
                            management_events = True
                        data_event_count += len(selector.get('DataResources', []))
                except Exception:
                    pass

                trails.append({
                    'name': name,
                    'arn': trail_arn,
                    'home_region': trail.get('HomeRegion'),
                    'is_logging': is_logging,
                    'is_multi_region': trail.get('IsMultiRegionTrail', False),
                    'is_organization': trail.get('IsOrganizationTrail', False),
                    'log_file_validation': trail.get('LogFileValidationEnabled', False),
                    's3_bucket': trail.get('S3BucketName'),
                    'cloudwatch_logs_arn': trail.get('CloudWatchLogsLogGroupArn'),
                    'kms_key_id': trail.get('KMSKeyId'),
                    'has_custom_event_selectors': trail.get('HasCustomEventSelectors', False),
                    'management_events': management_events,
                    'data_event_count': data_event_count,
                    'latest_delivery': latest_delivery,
                    'latest_error': latest_error,
                    'latest_digest': latest_digest,
                })

            return {"trails": trails}
        except Exception as err:
            _LOGGER.error("%s [account=%s region=%s]: %s", "Error fetching CloudTrail", self.account_name, self.region, err)
            return {"trails": []}


class AwsIAMCoordinator(AwsBaseCoordinator):
    """Coordinator for IAM data (global service, fetched via us-east-1).
    
    Covers:
    - Users via credential report (last login, password age, MFA, access key age/usage)
    - Customer-managed roles (last used, trust policy, permissions boundary)
    - Account summary (root account status, MFA, totals)
    - Password policy
    """

    def __init__(
        self, hass: HomeAssistant, aws_client, account_name: str, refresh_interval: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            aws_client,
            account_name,
            "IAM (global)",
            refresh_interval,
        )

    def _fetch_data(self) -> dict:
        """Fetch IAM data."""
        try:
            from datetime import datetime, timezone, timedelta
            import csv
            import io

            iam_client = self.aws_client.get_iam_client()
            now = datetime.now(timezone.utc)

            # ----------------------------------------------------------------
            # Users via credential report
            # ----------------------------------------------------------------
            users = []
            try:
                # Generate report — AWS may need a moment to prepare it
                iam_client.generate_credential_report()
                import time
                report = None
                for attempt in range(10):
                    try:
                        report = iam_client.get_credential_report()
                        break
                    except iam_client.exceptions.CredentialReportNotReadyException:
                        time.sleep(2)

                if report is None:
                    _LOGGER.warning("IAM [account=%s]: credential report not ready after 20s", self.account_name)
                else:
                    content = report['Content'].decode('utf-8')
                    reader = csv.DictReader(io.StringIO(content))

                    def days_since(val):
                        if not val or val in ('N/A', 'no_information', 'not_supported'):
                            return None
                        try:
                            dt = datetime.fromisoformat(val.replace('Z', '+00:00'))
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            return (now - dt).days
                        except Exception:
                            return None

                    for row in reader:
                        username = row.get('user', '')
                        if username == '<root_account>':
                            continue  # handled separately in account summary

                        pw_last_changed = days_since(row.get('password_last_changed'))
                        pw_last_used = days_since(row.get('password_last_used'))
                        key1_last_rotated = days_since(row.get('access_key_1_last_rotated'))
                        key2_last_rotated = days_since(row.get('access_key_2_last_rotated'))
                        key1_last_used = days_since(row.get('access_key_1_last_used_date'))
                        key2_last_used = days_since(row.get('access_key_2_last_used_date'))

                        key1_active = row.get('access_key_1_active', 'false').lower() == 'true'
                        key2_active = row.get('access_key_2_active', 'false').lower() == 'true'
                        mfa_active = row.get('mfa_active', 'false').lower() == 'true'
                        pw_enabled = row.get('password_enabled', 'false').lower() == 'true'

                        active_key_ages = [a for a in [
                            key1_last_rotated if key1_active else None,
                            key2_last_rotated if key2_active else None,
                        ] if a is not None]
                        oldest_key_age = max(active_key_ages) if active_key_ages else None

                        users.append({
                            'username': username,
                            'arn': row.get('arn'),
                            'password_enabled': pw_enabled,
                            'mfa_active': mfa_active,
                            'password_last_changed_days': pw_last_changed,
                            'password_last_used_days': pw_last_used,
                            'key1_active': key1_active,
                            'key1_age_days': key1_last_rotated,
                            'key1_last_used_days': key1_last_used,
                            'key2_active': key2_active,
                            'key2_age_days': key2_last_rotated,
                            'key2_last_used_days': key2_last_used,
                            'oldest_key_age_days': oldest_key_age,
                            'active_key_count': sum([key1_active, key2_active]),
                        })
            except Exception as err:
                _LOGGER.warning("IAM [account=%s]: credential report error: %s", self.account_name, err)

            # ----------------------------------------------------------------
            # Customer-managed roles
            # ----------------------------------------------------------------
            roles = []
            try:
                paginator = iam_client.get_paginator('list_roles')
                for page in paginator.paginate():
                    for role in page.get('Roles', []):
                        path = role.get('Path', '/')
                        name = role.get('RoleName', '')

                        # Skip service-linked and AWS-reserved roles by path
                        if (path.startswith('/aws-service-role/')
                                or path.startswith('/aws-reserved/')
                                or path.startswith('/service-role/')):
                            continue

                        # Skip well-known AWS-created role name patterns
                        # These are created automatically by AWS services and are
                        # not customer-managed even if they have path "/"
                        aws_name_prefixes = (
                            'aws-',           # aws-elasticbeanstalk-*, aws-opsworks-*, etc.
                            'AWS',            # AWSServiceRole*, AmazonEKS*, etc.
                            'Amazon',         # AmazonEKSAutoClusterRole, etc.
                        )
                        if name.startswith(aws_name_prefixes):
                            continue

                        # Skip auto-created Lambda/CodeBuild execution roles
                        # These follow patterns like: FunctionName-role-xxxxxxxx
                        # or ServiceName-region-service-role
                        import re
                        if re.search(r'-role-[a-z0-9]{8,}$', name, re.IGNORECASE):
                            continue
                        if name.endswith('-service-role') and '-' in name:
                            # e.g. codebuild-ProjectName-service-role
                            continue

                        last_used = role.get('RoleLastUsed', {})
                        last_used_date = last_used.get('LastUsedDate')
                        days_since_used = None
                        if last_used_date:
                            if hasattr(last_used_date, 'tzinfo') and last_used_date.tzinfo:
                                days_since_used = (now - last_used_date).days
                            else:
                                days_since_used = (now - last_used_date.replace(tzinfo=timezone.utc)).days

                        roles.append({
                            'name': role.get('RoleName'),
                            'arn': role.get('Arn'),
                            'path': path,
                            'created_days_ago': (now - role['CreateDate'].replace(tzinfo=timezone.utc) if role.get('CreateDate') and not role['CreateDate'].tzinfo else now - role['CreateDate']).days if role.get('CreateDate') else None,
                            'last_used_days': days_since_used,
                            'last_used_region': last_used.get('Region'),
                            'description': role.get('Description', ''),
                            'max_session_duration': role.get('MaxSessionDuration'),
                            'has_permissions_boundary': 'PermissionsBoundary' in role,
                        })
            except Exception as err:
                _LOGGER.warning("IAM [account=%s]: roles error: %s", self.account_name, err)

            # ----------------------------------------------------------------
            # Account summary
            # ----------------------------------------------------------------
            account_summary = {}
            try:
                summary = iam_client.get_account_summary()
                s = summary.get('SummaryMap', {})
                account_summary = {
                    'users': s.get('Users', 0),
                    'groups': s.get('Groups', 0),
                    'roles': s.get('Roles', 0),
                    'policies': s.get('Policies', 0),
                    'mfa_devices': s.get('MFADevices', 0),
                    'mfa_devices_in_use': s.get('MFADevicesInUse', 0),
                    'root_mfa_enabled': s.get('AccountMFAEnabled', 0) == 1,
                    'access_keys_present': s.get('AccountAccessKeysPresent', 0),
                }
            except Exception as err:
                _LOGGER.warning("IAM [account=%s]: account summary error: %s", self.account_name, err)

            # ----------------------------------------------------------------
            # Password policy
            # ----------------------------------------------------------------
            password_policy = {}
            try:
                pp = iam_client.get_account_password_policy()
                p = pp.get('PasswordPolicy', {})
                password_policy = {
                    'min_length': p.get('MinimumPasswordLength'),
                    'require_uppercase': p.get('RequireUppercaseCharacters', False),
                    'require_lowercase': p.get('RequireLowercaseCharacters', False),
                    'require_numbers': p.get('RequireNumbers', False),
                    'require_symbols': p.get('RequireSymbols', False),
                    'allow_users_to_change': p.get('AllowUsersToChangePassword', False),
                    'expire_passwords': p.get('ExpirePasswords', False),
                    'max_password_age': p.get('MaxPasswordAge'),
                    'password_reuse_prevention': p.get('PasswordReusePrevention'),
                    'hard_expiry': p.get('HardExpiry', False),
                }
            except iam_client.exceptions.NoSuchEntityException:
                # No password policy set — using AWS defaults
                password_policy = {'configured': False}
            except Exception as err:
                _LOGGER.warning("IAM [account=%s]: password policy error: %s", self.account_name, err)

            return {
                "users": users,
                "roles": roles,
                "account_summary": account_summary,
                "password_policy": password_policy,
            }

        except Exception as err:
            _LOGGER.error("%s [account=%s region=%s]: %s", "Error fetching IAM", self.account_name, self.region, err)
            return {"users": [], "roles": [], "account_summary": {}, "password_policy": {}}


class AwsRedshiftCoordinator(AwsBaseCoordinator):
    """Coordinator for Redshift cluster data."""

    def __init__(
        self, hass: HomeAssistant, aws_client, account_name: str, refresh_interval: int
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            aws_client,
            account_name,
            f"Redshift ({aws_client.region})",
            refresh_interval,
        )

    def _fetch_data(self) -> dict:
        """Fetch Redshift cluster data."""
        try:
            rs_client = self.aws_client.get_redshift_client()

            clusters = []
            paginator = rs_client.get_paginator('describe_clusters')
            for page in paginator.paginate():
                for cluster in page.get('Clusters', []):
                    endpoint = cluster.get('Endpoint', {})
                    clusters.append({
                        'identifier': cluster.get('ClusterIdentifier'),
                        'status': cluster.get('ClusterStatus'),
                        'node_type': cluster.get('NodeType'),
                        'number_of_nodes': cluster.get('NumberOfNodes', 1),
                        'db_name': cluster.get('DBName'),
                        'endpoint': endpoint.get('Address'),
                        'port': endpoint.get('Port'),
                        'vpc_id': cluster.get('VpcId'),
                        'availability_zone': cluster.get('AvailabilityZone'),
                        'encrypted': cluster.get('Encrypted', False),
                        'publicly_accessible': cluster.get('PubliclyAccessible', False),
                        'cluster_version': cluster.get('ClusterVersion'),
                        'engine_version': cluster.get('EngineFullVersion'),
                        'master_username': cluster.get('MasterUsername'),
                        'created_time': str(cluster.get('ClusterCreateTime', '')),
                    })

            return {"clusters": clusters}
        except Exception as err:
            _LOGGER.error("%s [account=%s region=%s]: %s", "Error fetching Redshift", self.account_name, self.region, err)
            return {"clusters": []}
