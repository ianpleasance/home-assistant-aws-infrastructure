"""Sensor platform for AWS Infrastructure integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    ATTRIBUTION,
    CONF_ACCOUNT_NAME,
    CONF_CREATE_INDIVIDUAL_COUNT_SENSORS,
    COORDINATOR_ASG,
    COORDINATOR_CLOUDWATCH_ALARMS,
    COORDINATOR_COST,
    COORDINATOR_DYNAMODB,
    COORDINATOR_EBS,
    COORDINATOR_EC2,
    COORDINATOR_ECS,
    COORDINATOR_EKS,
    COORDINATOR_ELASTICACHE,
    COORDINATOR_ELASTIC_IPS,
    COORDINATOR_LAMBDA,
    COORDINATOR_LOADBALANCER,
    COORDINATOR_RDS,
    COORDINATOR_S3,
    COORDINATOR_SNS,
    COORDINATOR_SQS,
    COORDINATOR_CLASSIC_LB,
    COORDINATOR_API_GATEWAY,
    COORDINATOR_CLOUDFRONT,
    COORDINATOR_EFS,
    COORDINATOR_ROUTE53,
    COORDINATOR_KINESIS,
    COORDINATOR_BEANSTALK,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def _make_device_info(account_name: str, region: str) -> DeviceInfo:
    """Create DeviceInfo for a regional device."""
    return DeviceInfo(
        entry_type=DeviceEntryType.SERVICE,
        identifiers={(DOMAIN, f"{account_name}_{region}")},
        name=f"AWS {account_name} ({region})",
        manufacturer="Amazon Web Services",
        model=region,
    )


def _make_global_device_info(account_name: str) -> DeviceInfo:
    """Create DeviceInfo for the global device."""
    return DeviceInfo(
        entry_type=DeviceEntryType.SERVICE,
        identifiers={(DOMAIN, f"{account_name}_global")},
        name=f"AWS {account_name} (Global)",
        manufacturer="Amazon Web Services",
        model="Global",
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AWS Infrastructure sensors."""
    all_coordinators = hass.data[DOMAIN][entry.entry_id]["coordinators"]
    account_name = entry.data[CONF_ACCOUNT_NAME].lower()
    create_individual = entry.data.get(CONF_CREATE_INDIVIDUAL_COUNT_SENSORS, False)

    entities = []

    # Global summary sensor (aggregates all regions)
    if "global" in hass.data[DOMAIN][entry.entry_id]:
        global_coordinator_data = hass.data[DOMAIN][entry.entry_id]["global"]
        entities.append(
            AwsGlobalSummarySensor(
                hass,
                account_name,
                global_coordinator_data["coordinators"],
            )
        )

    # Create sensors for each region
    for region, coordinators in all_coordinators.items():
        # Regional summary sensor
        entities.append(AwsRegionSummarySensor(coordinators, account_name, region))

        # Cost sensors (only in us-east-1)
        if COORDINATOR_COST in coordinators:
            cost_coordinator = coordinators[COORDINATOR_COST]

            entities.extend([
                AwsCostYesterdaySensor(cost_coordinator, account_name),
                AwsCostMonthToDateSensor(cost_coordinator, account_name),
            ])

            # Per-service cost sensors (top 10 services by cost)
            if cost_coordinator.data and "service_costs" in cost_coordinator.data:
                for service_slug, service_data in cost_coordinator.data["service_costs"].items():
                    entities.append(
                        AwsServiceCostSensor(
                            cost_coordinator,
                            account_name,
                            service_slug,
                            service_data,
                        )
                    )

        # EC2 sensors
        if COORDINATOR_EC2 in coordinators:
            ec2_coordinator = coordinators[COORDINATOR_EC2]

            if create_individual:
                entities.append(AwsEc2CountSensor(ec2_coordinator, account_name, region))

            if ec2_coordinator.data and "instances" in ec2_coordinator.data:
                for instance in ec2_coordinator.data["instances"]:
                    entities.append(
                        AwsEc2InstanceSensor(
                            ec2_coordinator,
                            account_name,
                            region,
                            instance["instance_id"],
                        )
                    )

        # RDS sensors
        if COORDINATOR_RDS in coordinators:
            rds_coordinator = coordinators[COORDINATOR_RDS]

            if create_individual:
                entities.append(AwsRdsCountSensor(rds_coordinator, account_name, region))

            if rds_coordinator.data and "instances" in rds_coordinator.data:
                for instance in rds_coordinator.data["instances"]:
                    entities.append(
                        AwsRdsInstanceSensor(
                            rds_coordinator,
                            account_name,
                            region,
                            instance["db_instance_identifier"],
                        )
                    )

        # Lambda sensors
        if COORDINATOR_LAMBDA in coordinators:
            lambda_coordinator = coordinators[COORDINATOR_LAMBDA]

            if create_individual:
                entities.append(AwsLambdaCountSensor(lambda_coordinator, account_name, region))

            if lambda_coordinator.data and "functions" in lambda_coordinator.data:
                for function in lambda_coordinator.data["functions"]:
                    entities.append(
                        AwsLambdaFunctionSensor(
                            lambda_coordinator,
                            account_name,
                            region,
                            function["function_name"],
                        )
                    )

        # Load Balancer sensors
        if COORDINATOR_LOADBALANCER in coordinators:
            lb_coordinator = coordinators[COORDINATOR_LOADBALANCER]

            if lb_coordinator.data and "load_balancers" in lb_coordinator.data:
                for lb in lb_coordinator.data["load_balancers"]:
                    entities.append(
                        AwsLoadBalancerSensor(
                            lb_coordinator,
                            account_name,
                            region,
                            lb["name"],
                        )
                    )

        # Auto Scaling Group sensors
        if COORDINATOR_ASG in coordinators:
            asg_coordinator = coordinators[COORDINATOR_ASG]

            if asg_coordinator.data and "auto_scaling_groups" in asg_coordinator.data:
                for asg in asg_coordinator.data["auto_scaling_groups"]:
                    entities.append(
                        AwsAsgSensor(
                            asg_coordinator,
                            account_name,
                            region,
                            asg["name"],
                        )
                    )

        # DynamoDB sensors
        if COORDINATOR_DYNAMODB in coordinators:
            dynamodb_coordinator = coordinators[COORDINATOR_DYNAMODB]

            if create_individual:
                entities.append(AwsDynamoDBCountSensor(dynamodb_coordinator, account_name, region))

            if dynamodb_coordinator.data and "tables" in dynamodb_coordinator.data:
                for table in dynamodb_coordinator.data["tables"]:
                    entities.append(
                        AwsDynamoDBTableSensor(
                            dynamodb_coordinator,
                            account_name,
                            region,
                            table["name"],
                        )
                    )

        # ElastiCache sensors
        if COORDINATOR_ELASTICACHE in coordinators:
            elasticache_coordinator = coordinators[COORDINATOR_ELASTICACHE]

            if create_individual:
                entities.append(AwsElastiCacheCountSensor(elasticache_coordinator, account_name, region))

            if elasticache_coordinator.data and "clusters" in elasticache_coordinator.data:
                for cluster in elasticache_coordinator.data["clusters"]:
                    entities.append(
                        AwsElastiCacheClusterSensor(
                            elasticache_coordinator,
                            account_name,
                            region,
                            cluster["id"],
                        )
                    )

        # ECS sensors
        if COORDINATOR_ECS in coordinators:
            ecs_coordinator = coordinators[COORDINATOR_ECS]

            if create_individual:
                entities.append(AwsECSCountSensor(ecs_coordinator, account_name, region))

            if ecs_coordinator.data and "clusters" in ecs_coordinator.data:
                for cluster in ecs_coordinator.data["clusters"]:
                    entities.append(
                        AwsECSClusterSensor(
                            ecs_coordinator,
                            account_name,
                            region,
                            cluster["name"],
                        )
                    )

        # EKS sensors
        if COORDINATOR_EKS in coordinators:
            eks_coordinator = coordinators[COORDINATOR_EKS]

            if create_individual:
                entities.append(AwsEKSCountSensor(eks_coordinator, account_name, region))

            if eks_coordinator.data and "clusters" in eks_coordinator.data:
                for cluster in eks_coordinator.data["clusters"]:
                    entities.append(
                        AwsEKSClusterSensor(
                            eks_coordinator,
                            account_name,
                            region,
                            cluster["name"],
                        )
                    )

        # EBS Volume sensors
        if COORDINATOR_EBS in coordinators:
            ebs_coordinator = coordinators[COORDINATOR_EBS]

            if create_individual:
                entities.append(AwsEBSCountSensor(ebs_coordinator, account_name, region))

            if ebs_coordinator.data and "volumes" in ebs_coordinator.data:
                for volume in ebs_coordinator.data["volumes"]:
                    entities.append(
                        AwsEBSVolumeSensor(
                            ebs_coordinator,
                            account_name,
                            region,
                            volume["id"],
                        )
                    )

        # SNS sensors
        if COORDINATOR_SNS in coordinators:
            sns_coordinator = coordinators[COORDINATOR_SNS]

            if create_individual:
                entities.append(AwsSNSCountSensor(sns_coordinator, account_name, region))

            if sns_coordinator.data and "topics" in sns_coordinator.data:
                for topic in sns_coordinator.data["topics"]:
                    entities.append(
                        AwsSNSTopicSensor(
                            sns_coordinator,
                            account_name,
                            region,
                            topic["name"],
                        )
                    )

        # SQS sensors
        if COORDINATOR_SQS in coordinators:
            sqs_coordinator = coordinators[COORDINATOR_SQS]

            if create_individual:
                entities.append(AwsSQSCountSensor(sqs_coordinator, account_name, region))

            if sqs_coordinator.data and "queues" in sqs_coordinator.data:
                for queue in sqs_coordinator.data["queues"]:
                    entities.append(
                        AwsSQSQueueSensor(
                            sqs_coordinator,
                            account_name,
                            region,
                            queue["name"],
                        )
                    )

        # S3 sensors
        if COORDINATOR_S3 in coordinators:
            s3_coordinator = coordinators[COORDINATOR_S3]

            if create_individual:
                entities.append(AwsS3CountSensor(s3_coordinator, account_name, region))

            if s3_coordinator.data and "buckets" in s3_coordinator.data:
                for bucket in s3_coordinator.data["buckets"]:
                    entities.append(
                        AwsS3BucketSensor(
                            s3_coordinator,
                            account_name,
                            region,
                            bucket["name"],
                        )
                    )

        # CloudWatch Alarms sensors
        if COORDINATOR_CLOUDWATCH_ALARMS in coordinators:
            cloudwatch_coordinator = coordinators[COORDINATOR_CLOUDWATCH_ALARMS]

            if create_individual:
                entities.append(AwsCloudWatchAlarmsCountSensor(cloudwatch_coordinator, account_name, region))

            if cloudwatch_coordinator.data and "alarms" in cloudwatch_coordinator.data:
                for alarm in cloudwatch_coordinator.data["alarms"]:
                    entities.append(
                        AwsCloudWatchAlarmSensor(
                            cloudwatch_coordinator,
                            account_name,
                            region,
                            alarm["name"],
                        )
                    )

        # Elastic IP sensors
        if COORDINATOR_ELASTIC_IPS in coordinators:
            eip_coordinator = coordinators[COORDINATOR_ELASTIC_IPS]

            if create_individual:
                entities.append(AwsElasticIPsCountSensor(eip_coordinator, account_name, region))

            if eip_coordinator.data and "addresses" in eip_coordinator.data:
                for address in eip_coordinator.data["addresses"]:
                    entities.append(
                        AwsElasticIPSensor(
                            eip_coordinator,
                            account_name,
                            region,
                            address["ip"],
                        )
                    )

        # Classic Load Balancers
        if COORDINATOR_CLASSIC_LB in coordinators:
            clb_coordinator = coordinators[COORDINATOR_CLASSIC_LB]

            if create_individual:
                entities.append(AwsClassicLBCountSensor(clb_coordinator, account_name, region))

            if clb_coordinator.data and "load_balancers" in clb_coordinator.data:
                for lb in clb_coordinator.data["load_balancers"]:
                    entities.append(
                        AwsClassicLBSensor(clb_coordinator, account_name, region, lb["name"])
                    )

        # API Gateway
        if COORDINATOR_API_GATEWAY in coordinators:
            apigw_coordinator = coordinators[COORDINATOR_API_GATEWAY]

            if create_individual:
                entities.append(AwsApiGatewayCountSensor(apigw_coordinator, account_name, region))

            if apigw_coordinator.data and "apis" in apigw_coordinator.data:
                for api in apigw_coordinator.data["apis"]:
                    entities.append(
                        AwsApiGatewaySensor(apigw_coordinator, account_name, region, api["id"], api["name"])
                    )

        # EFS
        if COORDINATOR_EFS in coordinators:
            efs_coordinator = coordinators[COORDINATOR_EFS]

            if create_individual:
                entities.append(AwsEFSCountSensor(efs_coordinator, account_name, region))

            if efs_coordinator.data and "file_systems" in efs_coordinator.data:
                for fs in efs_coordinator.data["file_systems"]:
                    entities.append(
                        AwsEFSSensor(efs_coordinator, account_name, region, fs["id"])
                    )

        # Kinesis
        if COORDINATOR_KINESIS in coordinators:
            kinesis_coordinator = coordinators[COORDINATOR_KINESIS]

            if create_individual:
                entities.append(AwsKinesisCountSensor(kinesis_coordinator, account_name, region))

            if kinesis_coordinator.data and "streams" in kinesis_coordinator.data:
                for stream in kinesis_coordinator.data["streams"]:
                    entities.append(
                        AwsKinesisStreamSensor(kinesis_coordinator, account_name, region, stream["name"])
                    )

        # Elastic Beanstalk
        if COORDINATOR_BEANSTALK in coordinators:
            beanstalk_coordinator = coordinators[COORDINATOR_BEANSTALK]

            if create_individual:
                entities.append(AwsBeanstalkCountSensor(beanstalk_coordinator, account_name, region))

            if beanstalk_coordinator.data and "environments" in beanstalk_coordinator.data:
                for env in beanstalk_coordinator.data["environments"]:
                    entities.append(
                        AwsBeanstalkEnvironmentSensor(beanstalk_coordinator, account_name, region, env["name"])
                    )

        # CloudFront (global — only in us-east-1 coordinator)
        if COORDINATOR_CLOUDFRONT in coordinators:
            cf_coordinator = coordinators[COORDINATOR_CLOUDFRONT]

            if create_individual:
                entities.append(AwsCloudFrontCountSensor(cf_coordinator, account_name, region))

            if cf_coordinator.data and "distributions" in cf_coordinator.data:
                for dist in cf_coordinator.data["distributions"]:
                    entities.append(
                        AwsCloudFrontDistributionSensor(cf_coordinator, account_name, region, dist["id"])
                    )

        # Route 53 (global — only in us-east-1 coordinator)
        if COORDINATOR_ROUTE53 in coordinators:
            r53_coordinator = coordinators[COORDINATOR_ROUTE53]

            if create_individual:
                entities.append(AwsRoute53CountSensor(r53_coordinator, account_name, region))

            if r53_coordinator.data and "zones" in r53_coordinator.data:
                for zone in r53_coordinator.data["zones"]:
                    entities.append(
                        AwsRoute53ZoneSensor(r53_coordinator, account_name, region, zone["id"], zone["name"])
                    )

    async_add_entities(entities)


# ============================================================================
# SENSORS - Region & Global Summaries
# ============================================================================


class AwsRegionSummarySensor(CoordinatorEntity, SensorEntity):
    """Sensor that summarizes all resources in a region."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        coordinators: dict,
        account_name: str,
        region: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinators.get(COORDINATOR_EC2) or list(coordinators.values())[0])
        self._coordinators = coordinators
        self._account_name = account_name
        self._region = region

        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_summary"
        self._attr_name = f"{region} summary"
        self._attr_icon = "mdi:aws"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> int:
        """Return total resource count for this region."""
        total = 0
        for key, data_key in [
            (COORDINATOR_EC2, "instances"),
            (COORDINATOR_RDS, "instances"),
            (COORDINATOR_LAMBDA, "functions"),
            (COORDINATOR_LOADBALANCER, "load_balancers"),
            (COORDINATOR_CLASSIC_LB, "load_balancers"),
            (COORDINATOR_ASG, "auto_scaling_groups"),
            (COORDINATOR_DYNAMODB, "tables"),
            (COORDINATOR_ELASTICACHE, "clusters"),
            (COORDINATOR_ECS, "clusters"),
            (COORDINATOR_EKS, "clusters"),
            (COORDINATOR_EBS, "volumes"),
            (COORDINATOR_SNS, "topics"),
            (COORDINATOR_SQS, "queues"),
            (COORDINATOR_S3, "buckets"),
            (COORDINATOR_CLOUDWATCH_ALARMS, "alarms"),
            (COORDINATOR_ELASTIC_IPS, "addresses"),
            (COORDINATOR_API_GATEWAY, "apis"),
            (COORDINATOR_EFS, "file_systems"),
            (COORDINATOR_KINESIS, "streams"),
            (COORDINATOR_BEANSTALK, "environments"),
            (COORDINATOR_CLOUDFRONT, "distributions"),
            (COORDINATOR_ROUTE53, "zones"),
        ]:
            if key in self._coordinators and self._coordinators[key].data:
                total += len(self._coordinators[key].data.get(data_key, []))
        return total

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return resource breakdown."""
        attrs: dict[str, Any] = {
            "region": self._region,
            "last_updated": dt_util.now(),
        }

        if COORDINATOR_EC2 in self._coordinators and self._coordinators[COORDINATOR_EC2].data:
            instances = self._coordinators[COORDINATOR_EC2].data.get("instances", [])
            attrs["ec2_total"] = len(instances)
            attrs["ec2_running"] = sum(1 for i in instances if i.get("state") == "running")
            attrs["ec2_stopped"] = sum(1 for i in instances if i.get("state") == "stopped")

        if COORDINATOR_RDS in self._coordinators and self._coordinators[COORDINATOR_RDS].data:
            attrs["rds_instances"] = len(self._coordinators[COORDINATOR_RDS].data.get("instances", []))

        if COORDINATOR_LAMBDA in self._coordinators and self._coordinators[COORDINATOR_LAMBDA].data:
            attrs["lambda_functions"] = len(self._coordinators[COORDINATOR_LAMBDA].data.get("functions", []))

        if COORDINATOR_LOADBALANCER in self._coordinators and self._coordinators[COORDINATOR_LOADBALANCER].data:
            attrs["load_balancers"] = len(self._coordinators[COORDINATOR_LOADBALANCER].data.get("load_balancers", []))

        if COORDINATOR_ASG in self._coordinators and self._coordinators[COORDINATOR_ASG].data:
            attrs["auto_scaling_groups"] = len(self._coordinators[COORDINATOR_ASG].data.get("auto_scaling_groups", []))

        if COORDINATOR_DYNAMODB in self._coordinators and self._coordinators[COORDINATOR_DYNAMODB].data:
            attrs["dynamodb_tables"] = len(self._coordinators[COORDINATOR_DYNAMODB].data.get("tables", []))

        if COORDINATOR_ELASTICACHE in self._coordinators and self._coordinators[COORDINATOR_ELASTICACHE].data:
            attrs["elasticache_clusters"] = len(self._coordinators[COORDINATOR_ELASTICACHE].data.get("clusters", []))

        if COORDINATOR_ECS in self._coordinators and self._coordinators[COORDINATOR_ECS].data:
            attrs["ecs_clusters"] = len(self._coordinators[COORDINATOR_ECS].data.get("clusters", []))

        if COORDINATOR_EKS in self._coordinators and self._coordinators[COORDINATOR_EKS].data:
            attrs["eks_clusters"] = len(self._coordinators[COORDINATOR_EKS].data.get("clusters", []))

        if COORDINATOR_EBS in self._coordinators and self._coordinators[COORDINATOR_EBS].data:
            volumes = self._coordinators[COORDINATOR_EBS].data.get("volumes", [])
            attached = sum(1 for v in volumes if v.get("attached_to"))
            attrs["ebs_volumes"] = len(volumes)
            attrs["ebs_attached"] = attached
            attrs["ebs_unattached"] = len(volumes) - attached

        if COORDINATOR_SNS in self._coordinators and self._coordinators[COORDINATOR_SNS].data:
            attrs["sns_topics"] = len(self._coordinators[COORDINATOR_SNS].data.get("topics", []))

        if COORDINATOR_SQS in self._coordinators and self._coordinators[COORDINATOR_SQS].data:
            attrs["sqs_queues"] = len(self._coordinators[COORDINATOR_SQS].data.get("queues", []))

        if COORDINATOR_S3 in self._coordinators and self._coordinators[COORDINATOR_S3].data:
            attrs["s3_buckets"] = len(self._coordinators[COORDINATOR_S3].data.get("buckets", []))

        if COORDINATOR_CLOUDWATCH_ALARMS in self._coordinators and self._coordinators[COORDINATOR_CLOUDWATCH_ALARMS].data:
            alarms = self._coordinators[COORDINATOR_CLOUDWATCH_ALARMS].data.get("alarms", [])
            attrs["cloudwatch_alarms"] = len(alarms)
            attrs["cloudwatch_alarms_alarm"] = sum(1 for a in alarms if a.get("state") == "ALARM")

        if COORDINATOR_ELASTIC_IPS in self._coordinators and self._coordinators[COORDINATOR_ELASTIC_IPS].data:
            addresses = self._coordinators[COORDINATOR_ELASTIC_IPS].data.get("addresses", [])
            attrs["elastic_ips"] = len(addresses)
            attrs["elastic_ips_unattached"] = sum(1 for a in addresses if not a.get("attached"))

        if COORDINATOR_CLASSIC_LB in self._coordinators and self._coordinators[COORDINATOR_CLASSIC_LB].data:
            attrs["classic_load_balancers"] = len(self._coordinators[COORDINATOR_CLASSIC_LB].data.get("load_balancers", []))

        if COORDINATOR_API_GATEWAY in self._coordinators and self._coordinators[COORDINATOR_API_GATEWAY].data:
            attrs["api_gateways"] = len(self._coordinators[COORDINATOR_API_GATEWAY].data.get("apis", []))

        if COORDINATOR_EFS in self._coordinators and self._coordinators[COORDINATOR_EFS].data:
            attrs["efs_file_systems"] = len(self._coordinators[COORDINATOR_EFS].data.get("file_systems", []))

        if COORDINATOR_KINESIS in self._coordinators and self._coordinators[COORDINATOR_KINESIS].data:
            attrs["kinesis_streams"] = len(self._coordinators[COORDINATOR_KINESIS].data.get("streams", []))

        if COORDINATOR_BEANSTALK in self._coordinators and self._coordinators[COORDINATOR_BEANSTALK].data:
            attrs["beanstalk_environments"] = len(self._coordinators[COORDINATOR_BEANSTALK].data.get("environments", []))

        if COORDINATOR_CLOUDFRONT in self._coordinators and self._coordinators[COORDINATOR_CLOUDFRONT].data:
            attrs["cloudfront_distributions"] = len(self._coordinators[COORDINATOR_CLOUDFRONT].data.get("distributions", []))

        if COORDINATOR_ROUTE53 in self._coordinators and self._coordinators[COORDINATOR_ROUTE53].data:
            attrs["route53_zones"] = len(self._coordinators[COORDINATOR_ROUTE53].data.get("zones", []))

        return attrs


class AwsGlobalSummarySensor(CoordinatorEntity, SensorEntity):
    """Sensor for global AWS summary across all regions."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:earth"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        hass: HomeAssistant,
        account_name: str,
        all_coordinators: dict,
    ) -> None:
        """Initialize the sensor."""
        # Bind to the first available coordinator so HA triggers updates
        primary_coordinator = None
        for region_coordinators in all_coordinators.values():
            primary_coordinator = (
                region_coordinators.get(COORDINATOR_EC2)
                or next(iter(region_coordinators.values()), None)
            )
            if primary_coordinator:
                break
        super().__init__(primary_coordinator)

        self._hass = hass
        self._account_name = account_name
        self._all_coordinators = all_coordinators

        self._attr_unique_id = f"aws_{account_name}_global_summary"
        self._attr_name = f"{account_name} Global Summary"
        self._attr_device_info = _make_global_device_info(account_name)

    @property
    def native_value(self) -> int:
        """Return total resource count across all regions."""
        total = 0
        for region_coordinators in self._all_coordinators.values():
            for key, data_key in [
                (COORDINATOR_EC2, "instances"),
                (COORDINATOR_RDS, "instances"),
                (COORDINATOR_LAMBDA, "functions"),
                (COORDINATOR_LOADBALANCER, "load_balancers"),
                (COORDINATOR_CLASSIC_LB, "load_balancers"),
                (COORDINATOR_ASG, "auto_scaling_groups"),
                (COORDINATOR_DYNAMODB, "tables"),
                (COORDINATOR_ELASTICACHE, "clusters"),
                (COORDINATOR_ECS, "clusters"),
                (COORDINATOR_EKS, "clusters"),
                (COORDINATOR_EBS, "volumes"),
                (COORDINATOR_SNS, "topics"),
                (COORDINATOR_SQS, "queues"),
                (COORDINATOR_S3, "buckets"),
                (COORDINATOR_CLOUDWATCH_ALARMS, "alarms"),
                (COORDINATOR_ELASTIC_IPS, "addresses"),
                (COORDINATOR_API_GATEWAY, "apis"),
                (COORDINATOR_EFS, "file_systems"),
                (COORDINATOR_KINESIS, "streams"),
                (COORDINATOR_BEANSTALK, "environments"),
                (COORDINATOR_CLOUDFRONT, "distributions"),
                (COORDINATOR_ROUTE53, "zones"),
            ]:
                if key in region_coordinators and region_coordinators[key].data:
                    total += len(region_coordinators[key].data.get(data_key, []))
        return total

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return aggregated attributes across all regions."""
        totals = {
            "ec2_running": 0, "ec2_stopped": 0, "lambda_functions": 0,
            "rds_instances": 0, "load_balancers": 0, "classic_load_balancers": 0,
            "auto_scaling_groups": 0,
            "dynamodb_tables": 0, "elasticache_clusters": 0, "ecs_clusters": 0,
            "eks_clusters": 0, "ebs_volumes": 0, "ebs_attached": 0,
            "ebs_unattached": 0, "sns_topics": 0, "sqs_queues": 0,
            "s3_buckets": 0, "cloudwatch_alarms": 0, "cloudwatch_alarms_alarm": 0,
            "elastic_ips": 0, "elastic_ips_unattached": 0,
            "api_gateways": 0, "efs_file_systems": 0, "kinesis_streams": 0,
            "beanstalk_environments": 0, "cloudfront_distributions": 0, "route53_zones": 0,
        }
        active_regions = 0

        for region_coordinators in self._all_coordinators.values():
            region_has_resources = False

            if COORDINATOR_EC2 in region_coordinators and region_coordinators[COORDINATOR_EC2].data:
                instances = region_coordinators[COORDINATOR_EC2].data.get("instances", [])
                if instances:
                    region_has_resources = True
                totals["ec2_running"] += sum(1 for i in instances if i.get("state") == "running")
                totals["ec2_stopped"] += sum(1 for i in instances if i.get("state") == "stopped")

            if COORDINATOR_RDS in region_coordinators and region_coordinators[COORDINATOR_RDS].data:
                instances = region_coordinators[COORDINATOR_RDS].data.get("instances", [])
                if instances:
                    region_has_resources = True
                totals["rds_instances"] += len(instances)

            if COORDINATOR_LAMBDA in region_coordinators and region_coordinators[COORDINATOR_LAMBDA].data:
                functions = region_coordinators[COORDINATOR_LAMBDA].data.get("functions", [])
                if functions:
                    region_has_resources = True
                totals["lambda_functions"] += len(functions)

            if COORDINATOR_LOADBALANCER in region_coordinators and region_coordinators[COORDINATOR_LOADBALANCER].data:
                lbs = region_coordinators[COORDINATOR_LOADBALANCER].data.get("load_balancers", [])
                if lbs:
                    region_has_resources = True
                totals["load_balancers"] += len(lbs)

            if COORDINATOR_ASG in region_coordinators and region_coordinators[COORDINATOR_ASG].data:
                asgs = region_coordinators[COORDINATOR_ASG].data.get("auto_scaling_groups", [])
                if asgs:
                    region_has_resources = True
                totals["auto_scaling_groups"] += len(asgs)

            if COORDINATOR_DYNAMODB in region_coordinators and region_coordinators[COORDINATOR_DYNAMODB].data:
                tables = region_coordinators[COORDINATOR_DYNAMODB].data.get("tables", [])
                if tables:
                    region_has_resources = True
                totals["dynamodb_tables"] += len(tables)

            if COORDINATOR_ELASTICACHE in region_coordinators and region_coordinators[COORDINATOR_ELASTICACHE].data:
                clusters = region_coordinators[COORDINATOR_ELASTICACHE].data.get("clusters", [])
                if clusters:
                    region_has_resources = True
                totals["elasticache_clusters"] += len(clusters)

            if COORDINATOR_ECS in region_coordinators and region_coordinators[COORDINATOR_ECS].data:
                clusters = region_coordinators[COORDINATOR_ECS].data.get("clusters", [])
                if clusters:
                    region_has_resources = True
                totals["ecs_clusters"] += len(clusters)

            if COORDINATOR_EKS in region_coordinators and region_coordinators[COORDINATOR_EKS].data:
                clusters = region_coordinators[COORDINATOR_EKS].data.get("clusters", [])
                if clusters:
                    region_has_resources = True
                totals["eks_clusters"] += len(clusters)

            if COORDINATOR_EBS in region_coordinators and region_coordinators[COORDINATOR_EBS].data:
                volumes = region_coordinators[COORDINATOR_EBS].data.get("volumes", [])
                if volumes:
                    region_has_resources = True
                totals["ebs_volumes"] += len(volumes)
                totals["ebs_attached"] += sum(1 for v in volumes if v.get("attached_to"))
                totals["ebs_unattached"] += sum(1 for v in volumes if not v.get("attached_to"))

            if COORDINATOR_SNS in region_coordinators and region_coordinators[COORDINATOR_SNS].data:
                topics = region_coordinators[COORDINATOR_SNS].data.get("topics", [])
                if topics:
                    region_has_resources = True
                totals["sns_topics"] += len(topics)

            if COORDINATOR_SQS in region_coordinators and region_coordinators[COORDINATOR_SQS].data:
                queues = region_coordinators[COORDINATOR_SQS].data.get("queues", [])
                if queues:
                    region_has_resources = True
                totals["sqs_queues"] += len(queues)

            if COORDINATOR_S3 in region_coordinators and region_coordinators[COORDINATOR_S3].data:
                buckets = region_coordinators[COORDINATOR_S3].data.get("buckets", [])
                if buckets:
                    region_has_resources = True
                totals["s3_buckets"] += len(buckets)

            if COORDINATOR_CLOUDWATCH_ALARMS in region_coordinators and region_coordinators[COORDINATOR_CLOUDWATCH_ALARMS].data:
                alarms = region_coordinators[COORDINATOR_CLOUDWATCH_ALARMS].data.get("alarms", [])
                if alarms:
                    region_has_resources = True
                totals["cloudwatch_alarms"] += len(alarms)
                totals["cloudwatch_alarms_alarm"] += sum(1 for a in alarms if a.get("state") == "ALARM")

            if COORDINATOR_ELASTIC_IPS in region_coordinators and region_coordinators[COORDINATOR_ELASTIC_IPS].data:
                addresses = region_coordinators[COORDINATOR_ELASTIC_IPS].data.get("addresses", [])
                if addresses:
                    region_has_resources = True
                totals["elastic_ips"] += len(addresses)
                totals["elastic_ips_unattached"] += sum(1 for a in addresses if not a.get("attached"))

            if COORDINATOR_CLASSIC_LB in region_coordinators and region_coordinators[COORDINATOR_CLASSIC_LB].data:
                clbs = region_coordinators[COORDINATOR_CLASSIC_LB].data.get("load_balancers", [])
                if clbs:
                    region_has_resources = True
                totals["classic_load_balancers"] += len(clbs)

            if COORDINATOR_API_GATEWAY in region_coordinators and region_coordinators[COORDINATOR_API_GATEWAY].data:
                apis = region_coordinators[COORDINATOR_API_GATEWAY].data.get("apis", [])
                if apis:
                    region_has_resources = True
                totals["api_gateways"] += len(apis)

            if COORDINATOR_EFS in region_coordinators and region_coordinators[COORDINATOR_EFS].data:
                fss = region_coordinators[COORDINATOR_EFS].data.get("file_systems", [])
                if fss:
                    region_has_resources = True
                totals["efs_file_systems"] += len(fss)

            if COORDINATOR_KINESIS in region_coordinators and region_coordinators[COORDINATOR_KINESIS].data:
                streams = region_coordinators[COORDINATOR_KINESIS].data.get("streams", [])
                if streams:
                    region_has_resources = True
                totals["kinesis_streams"] += len(streams)

            if COORDINATOR_BEANSTALK in region_coordinators and region_coordinators[COORDINATOR_BEANSTALK].data:
                envs = region_coordinators[COORDINATOR_BEANSTALK].data.get("environments", [])
                if envs:
                    region_has_resources = True
                totals["beanstalk_environments"] += len(envs)

            if COORDINATOR_CLOUDFRONT in region_coordinators and region_coordinators[COORDINATOR_CLOUDFRONT].data:
                dists = region_coordinators[COORDINATOR_CLOUDFRONT].data.get("distributions", [])
                if dists:
                    region_has_resources = True
                totals["cloudfront_distributions"] += len(dists)

            if COORDINATOR_ROUTE53 in region_coordinators and region_coordinators[COORDINATOR_ROUTE53].data:
                zones = region_coordinators[COORDINATOR_ROUTE53].data.get("zones", [])
                if zones:
                    region_has_resources = True
                totals["route53_zones"] += len(zones)

            if region_has_resources:
                active_regions += 1

        return {
            "active_regions": active_regions,
            "last_updated": dt_util.now(),
            **totals,
        }


# ============================================================================
# SENSORS - Graphable Cost Sensors
# ============================================================================


class AwsCostYesterdaySensor(CoordinatorEntity, SensorEntity):
    """Sensor for yesterday's AWS cost."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = "USD"
    _attr_icon = "mdi:cash"

    def __init__(self, coordinator, account_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._attr_unique_id = f"aws_{account_name}_cost_yesterday"
        self._attr_name = "Cost Yesterday"
        self._attr_device_info = _make_global_device_info(account_name)

    @property
    def native_value(self) -> float | None:
        """Return yesterday's cost."""
        if not self.coordinator.data or "cost_yesterday" not in self.coordinator.data:
            return None
        results = self.coordinator.data["cost_yesterday"].get("ResultsByTime", [])
        if not results:
            return None
        try:
            groups = results[0].get("Groups", [])
            if groups:
                return round(sum(float(g["Metrics"]["UnblendedCost"]["Amount"]) for g in groups), 2)
            amount = results[0]["Total"]["UnblendedCost"]["Amount"]
            return round(float(amount), 2)
        except (KeyError, ValueError, TypeError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        from datetime import date, timedelta
        yesterday = date.today() - timedelta(days=1)
        return {
            "date": yesterday.isoformat(),
            "account_name": self._account_name,
            "last_updated": dt_util.now(),
        }


class AwsCostMonthToDateSensor(CoordinatorEntity, SensorEntity):
    """Sensor for month-to-date AWS cost."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = "USD"
    _attr_icon = "mdi:calendar-cash"

    def __init__(self, coordinator, account_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._attr_unique_id = f"aws_{account_name}_cost_month_to_date"
        self._attr_name = "Cost Month to Date"
        self._attr_device_info = _make_global_device_info(account_name)

    @property
    def native_value(self) -> float | None:
        """Return month-to-date cost."""
        if not self.coordinator.data or "cost_mtd" not in self.coordinator.data:
            return None
        results = self.coordinator.data["cost_mtd"].get("ResultsByTime", [])
        if not results:
            return None
        try:
            groups = results[0].get("Groups", [])
            if groups:
                return round(sum(float(g["Metrics"]["UnblendedCost"]["Amount"]) for g in groups), 2)
            amount = results[0]["Total"]["UnblendedCost"]["Amount"]
            return round(float(amount), 2)
        except (KeyError, ValueError, TypeError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        from datetime import date
        return {
            "month": date.today().strftime("%Y-%m"),
            "account_name": self._account_name,
            "last_updated": dt_util.now(),
        }


class AwsServiceCostSensor(CoordinatorEntity, SensorEntity):
    """Sensor for per-service AWS cost."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = "USD"
    _attr_icon = "mdi:cash-multiple"

    def __init__(self, coordinator, account_name: str, service_slug: str, cost_data: dict) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._service_slug = service_slug
        self._service_name = cost_data.get("name", service_slug)
        self._attr_unique_id = f"aws_{account_name}_cost_service_{service_slug}"
        self._attr_name = f"Cost {self._service_name}"
        self._attr_device_info = _make_global_device_info(account_name)

    @property
    def native_value(self) -> float | None:
        """Return service cost."""
        if not self.coordinator.data or "service_costs" not in self.coordinator.data:
            return None
        service_costs = self.coordinator.data["service_costs"]
        if self._service_slug in service_costs:
            return service_costs[self._service_slug]["amount"]
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        attrs: dict[str, Any] = {
            "service_name": self._service_name,
            "account_name": self._account_name,
            "last_updated": dt_util.now(),
        }
        if self.coordinator.data and "service_costs" in self.coordinator.data:
            cost_data = self.coordinator.data["service_costs"].get(self._service_slug, {})
            attrs["rank"] = cost_data.get("rank", 0)
            attrs["percentage"] = cost_data.get("percentage", 0)
        return attrs


# ============================================================================
# SENSORS - EC2
# ============================================================================


class AwsEc2CountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for EC2 instance count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:server"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, account_name: str, region: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_ec2_total"
        self._attr_name = "EC2 Instances"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> int:
        """Return the total count of instances."""
        if not self.coordinator.data or "instances" not in self.coordinator.data:
            return 0
        return len(self.coordinator.data["instances"])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return breakdown by state."""
        if not self.coordinator.data or "instances" not in self.coordinator.data:
            return {"last_updated": dt_util.now()}
        instances = self.coordinator.data["instances"]
        return {
            "running": sum(1 for i in instances if i.get("state") == "running"),
            "stopped": sum(1 for i in instances if i.get("state") == "stopped"),
            "last_updated": dt_util.now(),
        }


class AwsEc2InstanceSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual EC2 instance."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:server"

    def __init__(self, coordinator, account_name: str, region: str, instance_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._instance_id = instance_id
        region_normalized = region.replace("-", "_")
        instance_normalized = instance_id.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_ec2_{instance_normalized}"
        self._attr_name = f"EC2 {instance_id}"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> str:
        """Return the instance state."""
        if self.coordinator.data and "instances" in self.coordinator.data:
            for instance in self.coordinator.data["instances"]:
                if instance.get("instance_id") == self._instance_id:
                    return instance.get("state", "unknown")
        return "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if self.coordinator.data and "instances" in self.coordinator.data:
            for instance in self.coordinator.data["instances"]:
                if instance.get("instance_id") == self._instance_id:
                    tags = instance.get("tags", {})
                    return {
                        "instance_id": instance.get("instance_id"),
                        "instance_type": instance.get("instance_type"),
                        "state": instance.get("state"),
                        "launch_time": instance.get("launch_time"),
                        "name": tags.get("Name", "Unnamed"),
                        "tags": tags,
                        "last_updated": dt_util.now(),
                    }
        return {"last_updated": dt_util.now()}


# ============================================================================
# SENSORS - RDS
# ============================================================================


class AwsRdsCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for RDS instance count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:database"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, account_name: str, region: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_rds_total_instances"
        self._attr_name = "RDS Instances"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> int:
        """Return the count of instances."""
        if not self.coordinator.data or "instances" not in self.coordinator.data:
            return 0
        return len(self.coordinator.data["instances"])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {"last_updated": dt_util.now()}


class AwsRdsInstanceSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual RDS instance."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:database"

    def __init__(self, coordinator, account_name: str, region: str, db_identifier: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._db_identifier = db_identifier
        region_normalized = region.replace("-", "_")
        db_normalized = db_identifier.replace("-", "_").replace(".", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_rds_{db_normalized}"
        self._attr_name = f"RDS {db_identifier}"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> str:
        """Return the database status."""
        if self.coordinator.data and "instances" in self.coordinator.data:
            for instance in self.coordinator.data["instances"]:
                if instance.get("db_instance_identifier") == self._db_identifier:
                    return instance.get("status", "unknown")
        return "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if self.coordinator.data and "instances" in self.coordinator.data:
            for instance in self.coordinator.data["instances"]:
                if instance.get("db_instance_identifier") == self._db_identifier:
                    return {
                        "db_instance_identifier": instance.get("db_instance_identifier"),
                        "db_instance_class": instance.get("db_instance_class"),
                        "engine": instance.get("engine"),
                        "engine_version": instance.get("engine_version"),
                        "status": instance.get("status"),
                        "allocated_storage": instance.get("allocated_storage"),
                        "last_updated": dt_util.now(),
                    }
        return {"last_updated": dt_util.now()}


# ============================================================================
# SENSORS - Lambda
# ============================================================================


class AwsLambdaCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Lambda function count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:lambda"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, account_name: str, region: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_lambda_total_functions"
        self._attr_name = "Lambda Functions"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> int:
        """Return the count of functions."""
        if not self.coordinator.data or "functions" not in self.coordinator.data:
            return 0
        return len(self.coordinator.data["functions"])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {"last_updated": dt_util.now()}


class AwsLambdaFunctionSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual Lambda function."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:lambda"

    def __init__(self, coordinator, account_name: str, region: str, function_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._function_name = function_name
        region_normalized = region.replace("-", "_")
        function_normalized = function_name.replace("-", "_").replace(".", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_lambda_{function_normalized}"
        self._attr_name = f"Lambda {function_name}"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> str:
        """Return the runtime."""
        if self.coordinator.data and "functions" in self.coordinator.data:
            for function in self.coordinator.data["functions"]:
                if function.get("function_name") == self._function_name:
                    return function.get("runtime", "unknown")
        return "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if self.coordinator.data and "functions" in self.coordinator.data:
            for function in self.coordinator.data["functions"]:
                if function.get("function_name") == self._function_name:
                    return {
                        "function_name": function.get("function_name"),
                        "runtime": function.get("runtime"),
                        "memory_size": function.get("memory_size"),
                        "timeout": function.get("timeout"),
                        "code_size": function.get("code_size"),
                        "last_modified": function.get("last_modified"),
                        "last_updated": dt_util.now(),
                    }
        return {"last_updated": dt_util.now()}


# ============================================================================
# SENSORS - Load Balancer
# ============================================================================


class AwsLoadBalancerSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual load balancer."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:scale-balance"

    def __init__(self, coordinator, account_name: str, region: str, lb_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._lb_name = lb_name
        region_normalized = region.replace("-", "_")
        lb_normalized = lb_name.replace("-", "_").replace(".", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_lb_{lb_normalized}"
        self._attr_name = f"Load Balancer {lb_name}"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> str:
        """Return the load balancer state."""
        if self.coordinator.data and "load_balancers" in self.coordinator.data:
            for lb in self.coordinator.data["load_balancers"]:
                if lb.get("name") == self._lb_name:
                    return lb.get("state", "unknown")
        return "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if self.coordinator.data and "load_balancers" in self.coordinator.data:
            for lb in self.coordinator.data["load_balancers"]:
                if lb.get("name") == self._lb_name:
                    return {
                        "name": lb.get("name"),
                        "dns_name": lb.get("dns_name"),
                        "type": lb.get("type"),
                        "scheme": lb.get("scheme"),
                        "state": lb.get("state"),
                        "vpc_id": lb.get("vpc_id"),
                        "last_updated": dt_util.now(),
                    }
        return {"last_updated": dt_util.now()}


# ============================================================================
# SENSORS - Auto Scaling Group
# ============================================================================


class AwsAsgSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual Auto Scaling Group."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:server-network"

    def __init__(self, coordinator, account_name: str, region: str, asg_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._asg_name = asg_name
        region_normalized = region.replace("-", "_")
        asg_normalized = asg_name.replace("-", "_").replace(".", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_asg_{asg_normalized}"
        self._attr_name = f"Auto Scaling Group {asg_name}"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> int:
        """Return the number of instances."""
        if self.coordinator.data and "auto_scaling_groups" in self.coordinator.data:
            for asg in self.coordinator.data["auto_scaling_groups"]:
                if asg.get("name") == self._asg_name:
                    return asg.get("instances", 0)
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if self.coordinator.data and "auto_scaling_groups" in self.coordinator.data:
            for asg in self.coordinator.data["auto_scaling_groups"]:
                if asg.get("name") == self._asg_name:
                    return {
                        "name": asg.get("name"),
                        "desired_capacity": asg.get("desired_capacity"),
                        "min_size": asg.get("min_size"),
                        "max_size": asg.get("max_size"),
                        "instances": asg.get("instances"),
                        "health_check_type": asg.get("health_check_type"),
                        "last_updated": dt_util.now(),
                    }
        return {"last_updated": dt_util.now()}


# ============================================================================
# SENSORS - DynamoDB
# ============================================================================


class AwsDynamoDBCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for DynamoDB table count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:database"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, account_name: str, region: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_dynamodb_count"
        self._attr_name = "DynamoDB Tables"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> int:
        """Return the number of DynamoDB tables."""
        if self.coordinator.data:
            return len(self.coordinator.data.get("tables", []))
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {"last_updated": dt_util.now()}


class AwsDynamoDBTableSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual DynamoDB table."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:database"

    def __init__(self, coordinator, account_name: str, region: str, table_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._table_name = table_name
        region_normalized = region.replace("-", "_")
        table_normalized = table_name.replace("-", "_").replace(".", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_dynamodb_{table_normalized}"
        self._attr_name = f"DynamoDB {table_name}"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> str:
        """Return the table status."""
        if self.coordinator.data:
            for table in self.coordinator.data.get("tables", []):
                if table["name"] == self._table_name:
                    return table.get("status", "unknown")
        return "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if self.coordinator.data:
            for table in self.coordinator.data.get("tables", []):
                if table["name"] == self._table_name:
                    return {
                        "table_name": table.get("name"),
                        "status": table.get("status"),
                        "item_count": table.get("item_count"),
                        "size_bytes": table.get("size_bytes"),
                        "created": table.get("creation_date"),
                        "last_updated": dt_util.now(),
                    }
        return {"last_updated": dt_util.now()}


# ============================================================================
# SENSORS - ElastiCache
# ============================================================================


class AwsElastiCacheCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for ElastiCache cluster count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:memory"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, account_name: str, region: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_elasticache_count"
        self._attr_name = "ElastiCache Clusters"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> int:
        """Return the number of ElastiCache clusters."""
        if self.coordinator.data:
            return len(self.coordinator.data.get("clusters", []))
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {"last_updated": dt_util.now()}


class AwsElastiCacheClusterSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual ElastiCache cluster."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:memory"

    def __init__(self, coordinator, account_name: str, region: str, cluster_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._cluster_id = cluster_id
        region_normalized = region.replace("-", "_")
        cluster_normalized = cluster_id.replace("-", "_").replace(".", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_elasticache_{cluster_normalized}"
        self._attr_name = f"ElastiCache {cluster_id}"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> str:
        """Return the cluster status."""
        if self.coordinator.data and "clusters" in self.coordinator.data:
            for cluster in self.coordinator.data["clusters"]:
                if cluster.get("id") == self._cluster_id:
                    return cluster.get("status", "unknown")
        return "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if self.coordinator.data and "clusters" in self.coordinator.data:
            for cluster in self.coordinator.data["clusters"]:
                if cluster.get("id") == self._cluster_id:
                    return {
                        "cluster_id": cluster.get("id"),
                        "status": cluster.get("status"),
                        "engine": cluster.get("engine"),
                        "engine_version": cluster.get("engine_version"),
                        "node_type": cluster.get("node_type"),
                        "num_nodes": cluster.get("num_nodes"),
                        "last_updated": dt_util.now(),
                    }
        return {"last_updated": dt_util.now()}


# ============================================================================
# SENSORS - ECS
# ============================================================================


class AwsECSCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for ECS cluster count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:docker"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, account_name: str, region: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_ecs_count"
        self._attr_name = "ECS Clusters"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> int:
        """Return the number of ECS clusters."""
        if self.coordinator.data:
            return len(self.coordinator.data.get("clusters", []))
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {"last_updated": dt_util.now()}


class AwsECSClusterSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual ECS cluster."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:docker"

    def __init__(self, coordinator, account_name: str, region: str, cluster_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._cluster_name = cluster_name
        region_normalized = region.replace("-", "_")
        cluster_normalized = cluster_name.replace("-", "_").replace(".", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_ecs_{cluster_normalized}"
        self._attr_name = f"ECS {cluster_name}"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> int:
        """Return the number of running tasks."""
        if self.coordinator.data and "clusters" in self.coordinator.data:
            for cluster in self.coordinator.data["clusters"]:
                if cluster.get("name") == self._cluster_name:
                    return cluster.get("running_tasks", 0)
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if self.coordinator.data and "clusters" in self.coordinator.data:
            for cluster in self.coordinator.data["clusters"]:
                if cluster.get("name") == self._cluster_name:
                    return {
                        "cluster_name": cluster.get("name"),
                        "status": cluster.get("status"),
                        "running_tasks": cluster.get("running_tasks"),
                        "pending_tasks": cluster.get("pending_tasks"),
                        "active_services": cluster.get("active_services"),
                        "registered_instances": cluster.get("registered_instances"),
                        "last_updated": dt_util.now(),
                    }
        return {"last_updated": dt_util.now()}


# ============================================================================
# SENSORS - EKS
# ============================================================================


class AwsEKSCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for EKS cluster count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:kubernetes"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, account_name: str, region: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_eks_count"
        self._attr_name = "EKS Clusters"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> int:
        """Return the number of EKS clusters."""
        if self.coordinator.data:
            return len(self.coordinator.data.get("clusters", []))
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {"last_updated": dt_util.now()}


class AwsEKSClusterSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual EKS cluster."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:kubernetes"

    def __init__(self, coordinator, account_name: str, region: str, cluster_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._cluster_name = cluster_name
        region_normalized = region.replace("-", "_")
        cluster_normalized = cluster_name.replace("-", "_").replace(".", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_eks_{cluster_normalized}"
        self._attr_name = f"EKS {cluster_name}"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> str:
        """Return the cluster status."""
        if self.coordinator.data and "clusters" in self.coordinator.data:
            for cluster in self.coordinator.data["clusters"]:
                if cluster.get("name") == self._cluster_name:
                    return cluster.get("status", "unknown")
        return "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if self.coordinator.data and "clusters" in self.coordinator.data:
            for cluster in self.coordinator.data["clusters"]:
                if cluster.get("name") == self._cluster_name:
                    return {
                        "cluster_name": cluster.get("name"),
                        "status": cluster.get("status"),
                        "version": cluster.get("version"),
                        "endpoint": cluster.get("endpoint"),
                        "created_at": cluster.get("created_at"),
                        "last_updated": dt_util.now(),
                    }
        return {"last_updated": dt_util.now()}


# ============================================================================
# SENSORS - EBS Volumes
# ============================================================================


class AwsEBSCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for EBS volume count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:harddisk"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, account_name: str, region: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_ebs_count"
        self._attr_name = "EBS Volumes"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> int:
        """Return the number of EBS volumes."""
        if self.coordinator.data:
            return len(self.coordinator.data.get("volumes", []))
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return breakdown by state."""
        if self.coordinator.data:
            volumes = self.coordinator.data.get("volumes", [])
            attached = sum(1 for v in volumes if v.get("attached_to"))
            return {
                "total_volumes": len(volumes),
                "attached": attached,
                "unattached": len(volumes) - attached,
                "total_size_gb": sum(v.get("size", 0) for v in volumes),
                "last_updated": dt_util.now(),
            }
        return {"last_updated": dt_util.now()}


class AwsEBSVolumeSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual EBS volume."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:harddisk"

    def __init__(self, coordinator, account_name: str, region: str, volume_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._volume_id = volume_id
        region_normalized = region.replace("-", "_")
        volume_normalized = volume_id.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_ebs_{volume_normalized}"
        self._attr_name = f"EBS {volume_id}"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> str:
        """Return the volume state."""
        if self.coordinator.data and "volumes" in self.coordinator.data:
            for volume in self.coordinator.data["volumes"]:
                if volume.get("id") == self._volume_id:
                    return volume.get("state", "unknown")
        return "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if self.coordinator.data and "volumes" in self.coordinator.data:
            for volume in self.coordinator.data["volumes"]:
                if volume.get("id") == self._volume_id:
                    return {
                        "volume_id": volume.get("id"),
                        "size_gb": volume.get("size"),
                        "type": volume.get("type"),
                        "iops": volume.get("iops"),
                        "throughput": volume.get("throughput"),
                        "state": volume.get("state"),
                        "availability_zone": volume.get("az"),
                        "attached_to": volume.get("attached_to"),
                        "encrypted": volume.get("encrypted"),
                        "created": volume.get("created"),
                        "last_updated": dt_util.now(),
                    }
        return {"last_updated": dt_util.now()}


# ============================================================================
# SENSORS - SNS
# ============================================================================


class AwsSNSCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for SNS topic count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:bell"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, account_name: str, region: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_sns_count"
        self._attr_name = "SNS Topics"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> int:
        """Return the number of SNS topics."""
        if self.coordinator.data:
            return len(self.coordinator.data.get("topics", []))
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {"last_updated": dt_util.now()}


class AwsSNSTopicSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual SNS topic."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:bell"

    def __init__(self, coordinator, account_name: str, region: str, topic_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._topic_name = topic_name
        region_normalized = region.replace("-", "_")
        topic_normalized = topic_name.replace("-", "_").replace(".", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_sns_{topic_normalized}"
        self._attr_name = f"SNS {topic_name}"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> int:
        """Return the number of subscriptions."""
        if self.coordinator.data and "topics" in self.coordinator.data:
            for topic in self.coordinator.data["topics"]:
                if topic.get("name") == self._topic_name:
                    return topic.get("subscriptions", 0)
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if self.coordinator.data and "topics" in self.coordinator.data:
            for topic in self.coordinator.data["topics"]:
                if topic.get("name") == self._topic_name:
                    return {
                        "topic_name": topic.get("name"),
                        "arn": topic.get("arn"),
                        "subscriptions": topic.get("subscriptions"),
                        "display_name": topic.get("display_name"),
                        "last_updated": dt_util.now(),
                    }
        return {"last_updated": dt_util.now()}


# ============================================================================
# SENSORS - SQS
# ============================================================================


class AwsSQSCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for SQS queue count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:format-list-bulleted"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, account_name: str, region: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_sqs_count"
        self._attr_name = "SQS Queues"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> int:
        """Return the number of SQS queues."""
        if self.coordinator.data:
            return len(self.coordinator.data.get("queues", []))
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {"last_updated": dt_util.now()}


class AwsSQSQueueSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual SQS queue."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:format-list-bulleted"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, account_name: str, region: str, queue_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._queue_name = queue_name
        region_normalized = region.replace("-", "_")
        queue_normalized = queue_name.replace("-", "_").replace(".", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_sqs_{queue_normalized}"
        self._attr_name = f"SQS {queue_name}"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> int:
        """Return the number of available messages."""
        if self.coordinator.data and "queues" in self.coordinator.data:
            for queue in self.coordinator.data["queues"]:
                if queue.get("name") == self._queue_name:
                    return queue.get("messages_available", 0)
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if self.coordinator.data and "queues" in self.coordinator.data:
            for queue in self.coordinator.data["queues"]:
                if queue.get("name") == self._queue_name:
                    return {
                        "queue_name": queue.get("name"),
                        "url": queue.get("url"),
                        "messages_available": queue.get("messages_available"),
                        "messages_in_flight": queue.get("messages_in_flight"),
                        "messages_delayed": queue.get("messages_delayed"),
                        "created": queue.get("created"),
                        "last_updated": dt_util.now(),
                    }
        return {"last_updated": dt_util.now()}


# ============================================================================
# SENSORS - S3
# ============================================================================


class AwsS3CountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for S3 bucket count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:bucket"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, account_name: str, region: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_s3_count"
        self._attr_name = "S3 Buckets"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> int:
        """Return the number of S3 buckets."""
        if self.coordinator.data:
            return len(self.coordinator.data.get("buckets", []))
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {"last_updated": dt_util.now()}


class AwsS3BucketSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual S3 bucket."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:bucket"

    def __init__(self, coordinator, account_name: str, region: str, bucket_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._bucket_name = bucket_name
        region_normalized = region.replace("-", "_")
        bucket_normalized = bucket_name.replace("-", "_").replace(".", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_s3_{bucket_normalized}"
        self._attr_name = f"S3 {bucket_name}"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> str:
        """Return the bucket region."""
        if self.coordinator.data and "buckets" in self.coordinator.data:
            for bucket in self.coordinator.data["buckets"]:
                if bucket.get("name") == self._bucket_name:
                    return bucket.get("region", "unknown")
        return "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if self.coordinator.data and "buckets" in self.coordinator.data:
            for bucket in self.coordinator.data["buckets"]:
                if bucket.get("name") == self._bucket_name:
                    return {
                        "bucket_name": bucket.get("name"),
                        "region": bucket.get("region"),
                        "created": bucket.get("created"),
                        "last_updated": dt_util.now(),
                    }
        return {"last_updated": dt_util.now()}


# ============================================================================
# SENSORS - CloudWatch Alarms
# ============================================================================


class AwsCloudWatchAlarmsCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for CloudWatch alarm count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:alarm-light"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, account_name: str, region: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_cloudwatch_alarms_count"
        self._attr_name = "CloudWatch Alarms"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> int:
        """Return the number of CloudWatch alarms."""
        if self.coordinator.data:
            return len(self.coordinator.data.get("alarms", []))
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return breakdown by state."""
        if self.coordinator.data:
            alarms = self.coordinator.data.get("alarms", [])
            return {
                "total_alarms": len(alarms),
                "ok": sum(1 for a in alarms if a.get("state") == "OK"),
                "alarm": sum(1 for a in alarms if a.get("state") == "ALARM"),
                "insufficient_data": sum(1 for a in alarms if a.get("state") == "INSUFFICIENT_DATA"),
                "last_updated": dt_util.now(),
            }
        return {"last_updated": dt_util.now()}


class AwsCloudWatchAlarmSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual CloudWatch alarm."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:alarm-light"

    def __init__(self, coordinator, account_name: str, region: str, alarm_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._alarm_name = alarm_name
        region_normalized = region.replace("-", "_")
        alarm_normalized = alarm_name.replace("-", "_").replace(".", "_").replace(" ", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_alarm_{alarm_normalized}"
        self._attr_name = f"CloudWatch Alarm {alarm_name}"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> str:
        """Return the alarm state."""
        if self.coordinator.data and "alarms" in self.coordinator.data:
            for alarm in self.coordinator.data["alarms"]:
                if alarm.get("name") == self._alarm_name:
                    return alarm.get("state", "unknown")
        return "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if self.coordinator.data and "alarms" in self.coordinator.data:
            for alarm in self.coordinator.data["alarms"]:
                if alarm.get("name") == self._alarm_name:
                    return {
                        "alarm_name": alarm.get("name"),
                        "state": alarm.get("state"),
                        "reason": alarm.get("reason"),
                        "metric": alarm.get("metric"),
                        "namespace": alarm.get("namespace"),
                        "enabled": alarm.get("enabled"),
                        "last_updated": dt_util.now(),
                    }
        return {"last_updated": dt_util.now()}


# ============================================================================
# SENSORS - Elastic IPs
# ============================================================================


class AwsElasticIPsCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Elastic IP count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:ip-network"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, account_name: str, region: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_elastic_ips_count"
        self._attr_name = "Elastic IPs"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> int:
        """Return the number of Elastic IPs."""
        if self.coordinator.data:
            return len(self.coordinator.data.get("addresses", []))
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return breakdown by attachment status."""
        if self.coordinator.data:
            addresses = self.coordinator.data.get("addresses", [])
            attached = sum(1 for a in addresses if a.get("attached"))
            return {
                "total_ips": len(addresses),
                "attached": attached,
                "unattached": len(addresses) - attached,
                "last_updated": dt_util.now(),
            }
        return {"last_updated": dt_util.now()}


class AwsElasticIPSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual Elastic IP."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:ip-network"

    def __init__(self, coordinator, account_name: str, region: str, ip_address: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._ip_address = ip_address
        region_normalized = region.replace("-", "_")
        ip_normalized = ip_address.replace(".", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_eip_{ip_normalized}"
        self._attr_name = f"Elastic IP {ip_address}"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> str:
        """Return attached or unattached."""
        if self.coordinator.data and "addresses" in self.coordinator.data:
            for address in self.coordinator.data["addresses"]:
                if address.get("ip") == self._ip_address:
                    return "attached" if address.get("attached") else "unattached"
        return "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if self.coordinator.data and "addresses" in self.coordinator.data:
            for address in self.coordinator.data["addresses"]:
                if address.get("ip") == self._ip_address:
                    return {
                        "ip_address": address.get("ip"),
                        "allocation_id": address.get("allocation_id"),
                        "associated_with": address.get("associated_with"),
                        "domain": address.get("domain"),
                        "attached": address.get("attached"),
                        "last_updated": dt_util.now(),
                    }
        return {"last_updated": dt_util.now()}


# ============================================================================
# SENSORS - Classic Load Balancers
# ============================================================================


class AwsClassicLBCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Classic Load Balancer count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:scale-balance"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, account_name: str, region: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_classic_lb_count"
        self._attr_name = "Classic Load Balancers"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> int:
        """Return the count of classic load balancers."""
        if self.coordinator.data:
            return len(self.coordinator.data.get("load_balancers", []))
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {"last_updated": dt_util.now()}


class AwsClassicLBSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual Classic Load Balancer."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:scale-balance"

    def __init__(self, coordinator, account_name: str, region: str, lb_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._lb_name = lb_name
        region_normalized = region.replace("-", "_")
        lb_normalized = lb_name.replace("-", "_").replace(".", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_classic_lb_{lb_normalized}"
        self._attr_name = f"Classic LB {lb_name}"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> int:
        """Return the number of registered instances."""
        if self.coordinator.data and "load_balancers" in self.coordinator.data:
            for lb in self.coordinator.data["load_balancers"]:
                if lb.get("name") == self._lb_name:
                    return lb.get("instance_count", 0)
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if self.coordinator.data and "load_balancers" in self.coordinator.data:
            for lb in self.coordinator.data["load_balancers"]:
                if lb.get("name") == self._lb_name:
                    return {
                        "name": lb.get("name"),
                        "dns_name": lb.get("dns_name"),
                        "scheme": lb.get("scheme"),
                        "vpc_id": lb.get("vpc_id"),
                        "availability_zones": lb.get("availability_zones"),
                        "subnets": lb.get("subnets"),
                        "security_groups": lb.get("security_groups"),
                        "instances": lb.get("instances"),
                        "instance_count": lb.get("instance_count"),
                        "listeners": lb.get("listeners"),
                        "health_check_target": lb.get("health_check_target"),
                        "health_check_interval": lb.get("health_check_interval"),
                        "created_time": lb.get("created_time"),
                        "last_updated": dt_util.now(),
                    }
        return {"last_updated": dt_util.now()}


# ============================================================================
# SENSORS - API Gateway
# ============================================================================


class AwsApiGatewayCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for API Gateway count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:api"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, account_name: str, region: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_api_gateway_count"
        self._attr_name = "API Gateways"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> int:
        """Return the count of APIs."""
        if self.coordinator.data:
            return len(self.coordinator.data.get("apis", []))
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {"last_updated": dt_util.now()}


class AwsApiGatewaySensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual API Gateway."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:api"

    def __init__(self, coordinator, account_name: str, region: str, api_id: str, api_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._api_id = api_id
        self._api_name = api_name
        region_normalized = region.replace("-", "_")
        id_normalized = api_id.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_apigw_{id_normalized}"
        self._attr_name = f"API Gateway {api_name}"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> str:
        """Return the API type."""
        if self.coordinator.data and "apis" in self.coordinator.data:
            for api in self.coordinator.data["apis"]:
                if api.get("id") == self._api_id:
                    return api.get("type", "unknown")
        return "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if self.coordinator.data and "apis" in self.coordinator.data:
            for api in self.coordinator.data["apis"]:
                if api.get("id") == self._api_id:
                    return {
                        "api_id": api.get("id"),
                        "name": api.get("name"),
                        "type": api.get("type"),
                        "description": api.get("description"),
                        "endpoint_type": api.get("endpoint_type"),
                        "api_endpoint": api.get("api_endpoint"),
                        "created_date": api.get("created_date"),
                        "last_updated": dt_util.now(),
                    }
        return {"last_updated": dt_util.now()}


# ============================================================================
# SENSORS - CloudFront
# ============================================================================


class AwsCloudFrontCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for CloudFront distribution count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:cloud-outline"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, account_name: str, region: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._attr_unique_id = f"aws_{account_name}_global_cloudfront_count"
        self._attr_name = "CloudFront Distributions"
        self._attr_device_info = _make_global_device_info(account_name)

    @property
    def native_value(self) -> int:
        """Return the count of distributions."""
        if self.coordinator.data:
            return len(self.coordinator.data.get("distributions", []))
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {"last_updated": dt_util.now()}


class AwsCloudFrontDistributionSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual CloudFront distribution."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:cloud-outline"

    def __init__(self, coordinator, account_name: str, region: str, dist_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._dist_id = dist_id
        id_normalized = dist_id.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_global_cloudfront_{id_normalized}"
        self._attr_name = f"CloudFront {dist_id}"
        self._attr_device_info = _make_global_device_info(account_name)

    @property
    def native_value(self) -> str:
        """Return the distribution status."""
        if self.coordinator.data and "distributions" in self.coordinator.data:
            for dist in self.coordinator.data["distributions"]:
                if dist.get("id") == self._dist_id:
                    return dist.get("status", "unknown")
        return "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if self.coordinator.data and "distributions" in self.coordinator.data:
            for dist in self.coordinator.data["distributions"]:
                if dist.get("id") == self._dist_id:
                    return {
                        "distribution_id": dist.get("id"),
                        "domain_name": dist.get("domain_name"),
                        "status": dist.get("status"),
                        "enabled": dist.get("enabled"),
                        "http_version": dist.get("http_version"),
                        "price_class": dist.get("price_class"),
                        "origins": dist.get("origins"),
                        "aliases": dist.get("aliases"),
                        "comment": dist.get("comment"),
                        "last_modified": dist.get("last_modified"),
                        "last_updated": dt_util.now(),
                    }
        return {"last_updated": dt_util.now()}


# ============================================================================
# SENSORS - EFS
# ============================================================================


class AwsEFSCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for EFS file system count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:folder-network"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, account_name: str, region: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_efs_count"
        self._attr_name = "EFS File Systems"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> int:
        """Return the count of EFS file systems."""
        if self.coordinator.data:
            return len(self.coordinator.data.get("file_systems", []))
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {"last_updated": dt_util.now()}


class AwsEFSSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual EFS file system."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:folder-network"

    def __init__(self, coordinator, account_name: str, region: str, fs_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._fs_id = fs_id
        region_normalized = region.replace("-", "_")
        id_normalized = fs_id.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_efs_{id_normalized}"
        self._attr_name = f"EFS {fs_id}"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> str:
        """Return the file system state."""
        if self.coordinator.data and "file_systems" in self.coordinator.data:
            for fs in self.coordinator.data["file_systems"]:
                if fs.get("id") == self._fs_id:
                    return fs.get("state", "unknown")
        return "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if self.coordinator.data and "file_systems" in self.coordinator.data:
            for fs in self.coordinator.data["file_systems"]:
                if fs.get("id") == self._fs_id:
                    return {
                        "filesystem_id": fs.get("id"),
                        "name": fs.get("name"),
                        "state": fs.get("state"),
                        "size_bytes": fs.get("size_bytes"),
                        "size_gb": round(fs.get("size_bytes", 0) / 1024 / 1024 / 1024, 2),
                        "number_of_mount_targets": fs.get("number_of_mount_targets"),
                        "performance_mode": fs.get("performance_mode"),
                        "throughput_mode": fs.get("throughput_mode"),
                        "encrypted": fs.get("encrypted"),
                        "availability_zone": fs.get("availability_zone"),
                        "created_time": fs.get("created_time"),
                        "tags": fs.get("tags"),
                        "last_updated": dt_util.now(),
                    }
        return {"last_updated": dt_util.now()}


# ============================================================================
# SENSORS - Route 53
# ============================================================================


class AwsRoute53CountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Route 53 hosted zone count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:dns"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, account_name: str, region: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._attr_unique_id = f"aws_{account_name}_global_route53_count"
        self._attr_name = "Route 53 Hosted Zones"
        self._attr_device_info = _make_global_device_info(account_name)

    @property
    def native_value(self) -> int:
        """Return the count of hosted zones."""
        if self.coordinator.data:
            return len(self.coordinator.data.get("zones", []))
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {"last_updated": dt_util.now()}


class AwsRoute53ZoneSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual Route 53 hosted zone."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:dns"

    def __init__(self, coordinator, account_name: str, region: str, zone_id: str, zone_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._zone_id = zone_id
        self._zone_name = zone_name
        id_normalized = zone_id.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_global_route53_{id_normalized}"
        self._attr_name = f"Route 53 {zone_name}"
        self._attr_device_info = _make_global_device_info(account_name)

    @property
    def native_value(self) -> int:
        """Return the record count."""
        if self.coordinator.data and "zones" in self.coordinator.data:
            for zone in self.coordinator.data["zones"]:
                if zone.get("id") == self._zone_id:
                    return zone.get("record_count", 0)
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if self.coordinator.data and "zones" in self.coordinator.data:
            for zone in self.coordinator.data["zones"]:
                if zone.get("id") == self._zone_id:
                    return {
                        "zone_id": zone.get("id"),
                        "name": zone.get("name"),
                        "private": zone.get("private"),
                        "record_count": zone.get("record_count"),
                        "comment": zone.get("comment"),
                        "last_updated": dt_util.now(),
                    }
        return {"last_updated": dt_util.now()}


# ============================================================================
# SENSORS - Kinesis
# ============================================================================


class AwsKinesisCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Kinesis stream count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:chart-timeline-variant"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, account_name: str, region: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_kinesis_count"
        self._attr_name = "Kinesis Streams"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> int:
        """Return the count of Kinesis streams."""
        if self.coordinator.data:
            return len(self.coordinator.data.get("streams", []))
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {"last_updated": dt_util.now()}


class AwsKinesisStreamSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual Kinesis stream."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:chart-timeline-variant"

    def __init__(self, coordinator, account_name: str, region: str, stream_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._stream_name = stream_name
        region_normalized = region.replace("-", "_")
        name_normalized = stream_name.replace("-", "_").replace(".", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_kinesis_{name_normalized}"
        self._attr_name = f"Kinesis {stream_name}"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> str:
        """Return the stream status."""
        if self.coordinator.data and "streams" in self.coordinator.data:
            for stream in self.coordinator.data["streams"]:
                if stream.get("name") == self._stream_name:
                    return stream.get("status", "unknown")
        return "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if self.coordinator.data and "streams" in self.coordinator.data:
            for stream in self.coordinator.data["streams"]:
                if stream.get("name") == self._stream_name:
                    return {
                        "stream_name": stream.get("name"),
                        "status": stream.get("status"),
                        "stream_mode": stream.get("stream_mode"),
                        "shard_count": stream.get("shard_count"),
                        "retention_hours": stream.get("retention_hours"),
                        "consumer_count": stream.get("consumer_count"),
                        "last_updated": dt_util.now(),
                    }
        return {"last_updated": dt_util.now()}


# ============================================================================
# SENSORS - Elastic Beanstalk
# ============================================================================


class AwsBeanstalkCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Elastic Beanstalk environment count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:sprout"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, account_name: str, region: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_beanstalk_count"
        self._attr_name = "Beanstalk Environments"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> int:
        """Return the count of Beanstalk environments."""
        if self.coordinator.data:
            return len(self.coordinator.data.get("environments", []))
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {"last_updated": dt_util.now()}


class AwsBeanstalkEnvironmentSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual Elastic Beanstalk environment."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:sprout"

    def __init__(self, coordinator, account_name: str, region: str, env_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._env_name = env_name
        region_normalized = region.replace("-", "_")
        name_normalized = env_name.replace("-", "_").replace(".", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_beanstalk_{name_normalized}"
        self._attr_name = f"Beanstalk {env_name}"
        self._attr_device_info = _make_device_info(account_name, region)

    @property
    def native_value(self) -> str:
        """Return the environment health."""
        if self.coordinator.data and "environments" in self.coordinator.data:
            for env in self.coordinator.data["environments"]:
                if env.get("name") == self._env_name:
                    return env.get("health", "unknown")
        return "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if self.coordinator.data and "environments" in self.coordinator.data:
            for env in self.coordinator.data["environments"]:
                if env.get("name") == self._env_name:
                    return {
                        "environment_name": env.get("name"),
                        "environment_id": env.get("id"),
                        "application_name": env.get("application_name"),
                        "status": env.get("status"),
                        "health": env.get("health"),
                        "health_status": env.get("health_status"),
                        "tier_name": env.get("tier_name"),
                        "tier_type": env.get("tier_type"),
                        "solution_stack": env.get("solution_stack"),
                        "cname": env.get("cname"),
                        "endpoint_url": env.get("endpoint_url"),
                        "date_created": env.get("date_created"),
                        "date_updated": env.get("date_updated"),
                        "last_updated": dt_util.now(),
                    }
        return {"last_updated": dt_util.now()}
