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
                instances.append({
                    "db_instance_identifier": db.get("DBInstanceIdentifier"),
                    "db_instance_class": db.get("DBInstanceClass"),
                    "engine": db.get("Engine"),
                    "engine_version": db.get("EngineVersion"),
                    "status": db.get("DBInstanceStatus"),
                    "allocated_storage": db.get("AllocatedStorage"),
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
                    auto_scaling_groups.append({
                        "name": asg.get("AutoScalingGroupName"),
                        "desired_capacity": asg.get("DesiredCapacity"),
                        "min_size": asg.get("MinSize"),
                        "max_size": asg.get("MaxSize"),
                        "instances": len(asg.get("Instances", [])),
                        "health_check_type": asg.get("HealthCheckType"),
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
                    table_details.append({
                        'name': table_name,
                        'status': table.get('TableStatus'),
                        'item_count': table.get('ItemCount', 0),
                        'size_bytes': table.get('TableSizeBytes', 0),
                        'creation_date': str(table.get('CreationDateTime', '')),
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
        """Fetch EBS volumes data."""
        try:
            ec2_client = self.aws_client.get_ec2_client()
            
            # Get all volumes
            volumes = []
            paginator = ec2_client.get_paginator('describe_volumes')
            for page in paginator.paginate():
                for volume in page.get('Volumes', []):
                    # Check if attached
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
            
            return {"volumes": volumes}
        except Exception as err:
            _LOGGER.error("%s [account=%s region=%s]: %s", "Error fetching EBS", self.account_name, self.region, err)
            return {"volumes": []}


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
