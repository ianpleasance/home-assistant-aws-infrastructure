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
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

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
    DOMAIN,
)


_LOGGER = logging.getLogger(__name__)

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
            
            # New cost sensors (no region parameter - they get it from coordinator)
            entities.extend([
                AwsCostYesterdaySensor(cost_coordinator, account_name),
                AwsCostMonthToDateSensor(cost_coordinator, account_name),
            ])
            
            # Legacy cost sensors (for backward compatibility)
            entities.extend([
                AwsCostTodaySensor(cost_coordinator, account_name, region),
                AwsCostMtdSensor(cost_coordinator, account_name, region),
            ])

            # Add service cost sensors (top 10 services by cost)
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
            
            # Individual EC2 instance sensors
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
            
            # Individual RDS instance sensors
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
            
            # Individual Lambda function sensors
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
            
            # Individual load balancer sensors
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
            
            # Individual ASG sensors
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
            
            # Individual DynamoDB table sensors
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
            
            # Individual ElastiCache cluster sensors
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
            
            # Individual ECS cluster sensors
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
            
            # Individual EKS cluster sensors
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
            
            # Individual EBS volume sensors
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
            
            # Individual SNS topic sensors
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
            
            # Individual SQS queue sensors
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
            
            # Individual S3 bucket sensors
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
            
            # Individual CloudWatch alarm sensors
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
            
            # Individual Elastic IP sensors
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

    async_add_entities(entities)

# ============================================================================
# SENSORS - Region & Global Summaries
# ============================================================================


class AwsRegionSummarySensor(CoordinatorEntity, SensorEntity):
    """Sensor that summarizes all resources in a region."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinators: dict,
        account_name: str,
        region: str,
    ) -> None:
        """Initialize the sensor."""
        # Use EC2 coordinator as primary (most likely to exist)
        super().__init__(coordinators.get(COORDINATOR_EC2) or list(coordinators.values())[0])
        self._coordinators = coordinators
        self._account_name = account_name
        self._region = region

        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_summary"
        self._attr_name = f"{region} summary"
        self._attr_icon = "mdi:aws"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

    @property
    def native_value(self) -> int:
        """Return total resource count for this region."""
        total = 0
        
        # EC2
        if COORDINATOR_EC2 in self._coordinators and self._coordinators[COORDINATOR_EC2].data:
            total += len(self._coordinators[COORDINATOR_EC2].data.get("instances", []))
        
        # RDS
        if COORDINATOR_RDS in self._coordinators and self._coordinators[COORDINATOR_RDS].data:
            total += len(self._coordinators[COORDINATOR_RDS].data.get("instances", []))
        
        # Lambda
        if COORDINATOR_LAMBDA in self._coordinators and self._coordinators[COORDINATOR_LAMBDA].data:
            total += len(self._coordinators[COORDINATOR_LAMBDA].data.get("functions", []))
        
        # Load Balancers
        if COORDINATOR_LOADBALANCER in self._coordinators and self._coordinators[COORDINATOR_LOADBALANCER].data:
            total += len(self._coordinators[COORDINATOR_LOADBALANCER].data.get("load_balancers", []))
        
        # Auto Scaling Groups
        if COORDINATOR_ASG in self._coordinators and self._coordinators[COORDINATOR_ASG].data:
            total += len(self._coordinators[COORDINATOR_ASG].data.get("auto_scaling_groups", []))
        
        # DynamoDB
        if COORDINATOR_DYNAMODB in self._coordinators and self._coordinators[COORDINATOR_DYNAMODB].data:
            total += len(self._coordinators[COORDINATOR_DYNAMODB].data.get("tables", []))
        
        # ElastiCache
        if COORDINATOR_ELASTICACHE in self._coordinators and self._coordinators[COORDINATOR_ELASTICACHE].data:
            total += len(self._coordinators[COORDINATOR_ELASTICACHE].data.get("clusters", []))
        
        # ECS
        if COORDINATOR_ECS in self._coordinators and self._coordinators[COORDINATOR_ECS].data:
            total += len(self._coordinators[COORDINATOR_ECS].data.get("clusters", []))
        
        # EKS
        if COORDINATOR_EKS in self._coordinators and self._coordinators[COORDINATOR_EKS].data:
            total += len(self._coordinators[COORDINATOR_EKS].data.get("clusters", []))
        
        # EBS
        if COORDINATOR_EBS in self._coordinators and self._coordinators[COORDINATOR_EBS].data:
            total += len(self._coordinators[COORDINATOR_EBS].data.get("volumes", []))
        
        # SNS
        if COORDINATOR_SNS in self._coordinators and self._coordinators[COORDINATOR_SNS].data:
            total += len(self._coordinators[COORDINATOR_SNS].data.get("topics", []))
        
        # SQS
        if COORDINATOR_SQS in self._coordinators and self._coordinators[COORDINATOR_SQS].data:
            total += len(self._coordinators[COORDINATOR_SQS].data.get("queues", []))
        
        # S3
        if COORDINATOR_S3 in self._coordinators and self._coordinators[COORDINATOR_S3].data:
            total += len(self._coordinators[COORDINATOR_S3].data.get("buckets", []))
        
        # CloudWatch Alarms
        if COORDINATOR_CLOUDWATCH_ALARMS in self._coordinators and self._coordinators[COORDINATOR_CLOUDWATCH_ALARMS].data:
            total += len(self._coordinators[COORDINATOR_CLOUDWATCH_ALARMS].data.get("alarms", []))
        
        # Elastic IPs
        if COORDINATOR_ELASTIC_IPS in self._coordinators and self._coordinators[COORDINATOR_ELASTIC_IPS].data:
            total += len(self._coordinators[COORDINATOR_ELASTIC_IPS].data.get("addresses", []))
        
        return total

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return resource breakdown."""
        attrs = {
            "region": self._region, 
        }
        
        # EC2
        if COORDINATOR_EC2 in self._coordinators and self._coordinators[COORDINATOR_EC2].data:
            instances = self._coordinators[COORDINATOR_EC2].data.get("instances", [])
            running = sum(1 for i in instances if i.get("state") == "running")
            stopped = sum(1 for i in instances if i.get("state") == "stopped")
            attrs["ec2_total"] = len(instances)
            attrs["ec2_running"] = running
            attrs["ec2_stopped"] = stopped
        
        # RDS
        if COORDINATOR_RDS in self._coordinators and self._coordinators[COORDINATOR_RDS].data:
            attrs["rds_instances"] = len(self._coordinators[COORDINATOR_RDS].data.get("instances", []))
        
        # Lambda
        if COORDINATOR_LAMBDA in self._coordinators and self._coordinators[COORDINATOR_LAMBDA].data:
            attrs["lambda_functions"] = len(self._coordinators[COORDINATOR_LAMBDA].data.get("functions", []))
        
        # Load Balancers
        if COORDINATOR_LOADBALANCER in self._coordinators and self._coordinators[COORDINATOR_LOADBALANCER].data:
            attrs["load_balancers"] = len(self._coordinators[COORDINATOR_LOADBALANCER].data.get("load_balancers", []))
        
        # Auto Scaling Groups
        if COORDINATOR_ASG in self._coordinators and self._coordinators[COORDINATOR_ASG].data:
            attrs["auto_scaling_groups"] = len(self._coordinators[COORDINATOR_ASG].data.get("auto_scaling_groups", []))
        
        # DynamoDB
        if COORDINATOR_DYNAMODB in self._coordinators and self._coordinators[COORDINATOR_DYNAMODB].data:
            attrs["dynamodb_tables"] = len(self._coordinators[COORDINATOR_DYNAMODB].data.get("tables", []))
        
        # ElastiCache
        if COORDINATOR_ELASTICACHE in self._coordinators and self._coordinators[COORDINATOR_ELASTICACHE].data:
            attrs["elasticache_clusters"] = len(self._coordinators[COORDINATOR_ELASTICACHE].data.get("clusters", []))
        
        # ECS
        if COORDINATOR_ECS in self._coordinators and self._coordinators[COORDINATOR_ECS].data:
            attrs["ecs_clusters"] = len(self._coordinators[COORDINATOR_ECS].data.get("clusters", []))
        
        # EKS
        if COORDINATOR_EKS in self._coordinators and self._coordinators[COORDINATOR_EKS].data:
            attrs["eks_clusters"] = len(self._coordinators[COORDINATOR_EKS].data.get("clusters", []))
        
        # EBS
        if COORDINATOR_EBS in self._coordinators and self._coordinators[COORDINATOR_EBS].data:
            volumes = self._coordinators[COORDINATOR_EBS].data.get("volumes", [])
            attached = sum(1 for v in volumes if v.get("attached_to"))
            attrs["ebs_volumes"] = len(volumes)
            attrs["ebs_attached"] = attached
            attrs["ebs_unattached"] = len(volumes) - attached
        
        # SNS
        if COORDINATOR_SNS in self._coordinators and self._coordinators[COORDINATOR_SNS].data:
            attrs["sns_topics"] = len(self._coordinators[COORDINATOR_SNS].data.get("topics", []))
        
        # SQS
        if COORDINATOR_SQS in self._coordinators and self._coordinators[COORDINATOR_SQS].data:
            attrs["sqs_queues"] = len(self._coordinators[COORDINATOR_SQS].data.get("queues", []))
        
        # S3
        if COORDINATOR_S3 in self._coordinators and self._coordinators[COORDINATOR_S3].data:
            attrs["s3_buckets"] = len(self._coordinators[COORDINATOR_S3].data.get("buckets", []))
        
        # CloudWatch Alarms
        if COORDINATOR_CLOUDWATCH_ALARMS in self._coordinators and self._coordinators[COORDINATOR_CLOUDWATCH_ALARMS].data:
            alarms = self._coordinators[COORDINATOR_CLOUDWATCH_ALARMS].data.get("alarms", [])
            alarm_state = sum(1 for a in alarms if a.get("state") == "ALARM")
            attrs["cloudwatch_alarms"] = len(alarms)
            attrs["cloudwatch_alarms_alarm"] = alarm_state
        
        # Elastic IPs
        if COORDINATOR_ELASTIC_IPS in self._coordinators and self._coordinators[COORDINATOR_ELASTIC_IPS].data:
            addresses = self._coordinators[COORDINATOR_ELASTIC_IPS].data.get("addresses", [])
            unattached = sum(1 for a in addresses if not a.get("attached"))
            attrs["elastic_ips"] = len(addresses)
            attrs["elastic_ips_unattached"] = unattached
        
        return attrs


class AwsGlobalSummarySensor(SensorEntity):
    """Sensor for global AWS summary across all regions."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:earth"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        hass: HomeAssistant,
        account_name: str,
        all_coordinators: dict,
    ) -> None:
        """Initialize the sensor."""
        self._hass = hass
        self._account_name = account_name
        self._all_coordinators = all_coordinators  # ✅ CRITICAL: Store this!

        self._attr_unique_id = f"aws_{account_name}_global_summary"
        self._attr_name = "summary"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_global")},
            "name": f"AWS {account_name} (Global)",
            "manufacturer": "Amazon Web Services",
            "model": "Global",
            "entry_type": "service",
        }

    @property
    def native_value(self) -> int:
        """Return total resource count across all regions."""
        total = 0
        for region_coordinators in self._all_coordinators.values():
            # EC2
            if COORDINATOR_EC2 in region_coordinators and region_coordinators[COORDINATOR_EC2].data:
                total += len(region_coordinators[COORDINATOR_EC2].data.get("instances", []))
            
            # RDS
            if COORDINATOR_RDS in region_coordinators and region_coordinators[COORDINATOR_RDS].data:
                total += len(region_coordinators[COORDINATOR_RDS].data.get("instances", []))
            
            # Lambda
            if COORDINATOR_LAMBDA in region_coordinators and region_coordinators[COORDINATOR_LAMBDA].data:
                total += len(region_coordinators[COORDINATOR_LAMBDA].data.get("functions", []))
            
            # Load Balancers
            if COORDINATOR_LOADBALANCER in region_coordinators and region_coordinators[COORDINATOR_LOADBALANCER].data:
                total += len(region_coordinators[COORDINATOR_LOADBALANCER].data.get("load_balancers", []))
            
            # Auto Scaling Groups
            if COORDINATOR_ASG in region_coordinators and region_coordinators[COORDINATOR_ASG].data:
                total += len(region_coordinators[COORDINATOR_ASG].data.get("auto_scaling_groups", []))
            
            # DynamoDB
            if COORDINATOR_DYNAMODB in region_coordinators and region_coordinators[COORDINATOR_DYNAMODB].data:
                total += len(region_coordinators[COORDINATOR_DYNAMODB].data.get("tables", []))
            
            # ElastiCache
            if COORDINATOR_ELASTICACHE in region_coordinators and region_coordinators[COORDINATOR_ELASTICACHE].data:
                total += len(region_coordinators[COORDINATOR_ELASTICACHE].data.get("clusters", []))
            
            # ECS
            if COORDINATOR_ECS in region_coordinators and region_coordinators[COORDINATOR_ECS].data:
                total += len(region_coordinators[COORDINATOR_ECS].data.get("clusters", []))
            
            # EKS
            if COORDINATOR_EKS in region_coordinators and region_coordinators[COORDINATOR_EKS].data:
                total += len(region_coordinators[COORDINATOR_EKS].data.get("clusters", []))
            
            # EBS
            if COORDINATOR_EBS in region_coordinators and region_coordinators[COORDINATOR_EBS].data:
                total += len(region_coordinators[COORDINATOR_EBS].data.get("volumes", []))
            
            # SNS
            if COORDINATOR_SNS in region_coordinators and region_coordinators[COORDINATOR_SNS].data:
                total += len(region_coordinators[COORDINATOR_SNS].data.get("topics", []))
            
            # SQS
            if COORDINATOR_SQS in region_coordinators and region_coordinators[COORDINATOR_SQS].data:
                total += len(region_coordinators[COORDINATOR_SQS].data.get("queues", []))
            
            # S3
            if COORDINATOR_S3 in region_coordinators and region_coordinators[COORDINATOR_S3].data:
                total += len(region_coordinators[COORDINATOR_S3].data.get("buckets", []))
            
            # CloudWatch Alarms
            if COORDINATOR_CLOUDWATCH_ALARMS in region_coordinators and region_coordinators[COORDINATOR_CLOUDWATCH_ALARMS].data:
                total += len(region_coordinators[COORDINATOR_CLOUDWATCH_ALARMS].data.get("alarms", []))
            
            # Elastic IPs
            if COORDINATOR_ELASTIC_IPS in region_coordinators and region_coordinators[COORDINATOR_ELASTIC_IPS].data:
                total += len(region_coordinators[COORDINATOR_ELASTIC_IPS].data.get("addresses", []))
        
        return total

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return aggregated attributes."""
        total_ec2_running = 0
        total_ec2_stopped = 0
        total_lambda = 0
        total_rds = 0
        total_lb = 0
        total_asg = 0
        total_dynamodb = 0
        total_elasticache = 0
        total_ecs = 0
        total_eks = 0
        total_ebs = 0
        total_ebs_attached = 0
        total_ebs_unattached = 0
        total_sns = 0
        total_sqs = 0
        total_s3 = 0
        total_cloudwatch_alarms = 0
        total_cloudwatch_alarms_alarm = 0
        total_eips = 0
        total_eips_unattached = 0
        active_regions = 0

        for region_coordinators in self._all_coordinators.values():
            region_has_resources = False
            
            # EC2
            if COORDINATOR_EC2 in region_coordinators and region_coordinators[COORDINATOR_EC2].data:
                instances = region_coordinators[COORDINATOR_EC2].data.get("instances", [])
                if instances:
                    region_has_resources = True
                for instance in instances:
                    if instance.get("state") == "running":
                        total_ec2_running += 1
                    elif instance.get("state") == "stopped":
                        total_ec2_stopped += 1
            
            # RDS
            if COORDINATOR_RDS in region_coordinators and region_coordinators[COORDINATOR_RDS].data:
                instances = region_coordinators[COORDINATOR_RDS].data.get("instances", [])
                if instances:
                    region_has_resources = True
                total_rds += len(instances)
            
            # Lambda
            if COORDINATOR_LAMBDA in region_coordinators and region_coordinators[COORDINATOR_LAMBDA].data:
                functions = region_coordinators[COORDINATOR_LAMBDA].data.get("functions", [])
                if functions:
                    region_has_resources = True
                total_lambda += len(functions)
            
            # Load Balancers
            if COORDINATOR_LOADBALANCER in region_coordinators and region_coordinators[COORDINATOR_LOADBALANCER].data:
                lbs = region_coordinators[COORDINATOR_LOADBALANCER].data.get("load_balancers", [])
                if lbs:
                    region_has_resources = True
                total_lb += len(lbs)
            
            # Auto Scaling Groups
            if COORDINATOR_ASG in region_coordinators and region_coordinators[COORDINATOR_ASG].data:
                asgs = region_coordinators[COORDINATOR_ASG].data.get("auto_scaling_groups", [])
                if asgs:
                    region_has_resources = True
                total_asg += len(asgs)
            
            # DynamoDB
            if COORDINATOR_DYNAMODB in region_coordinators and region_coordinators[COORDINATOR_DYNAMODB].data:
                tables = region_coordinators[COORDINATOR_DYNAMODB].data.get("tables", [])
                if tables:
                    region_has_resources = True
                total_dynamodb += len(tables)
            
            # ElastiCache
            if COORDINATOR_ELASTICACHE in region_coordinators and region_coordinators[COORDINATOR_ELASTICACHE].data:
                clusters = region_coordinators[COORDINATOR_ELASTICACHE].data.get("clusters", [])
                if clusters:
                    region_has_resources = True
                total_elasticache += len(clusters)
            
            # ECS
            if COORDINATOR_ECS in region_coordinators and region_coordinators[COORDINATOR_ECS].data:
                clusters = region_coordinators[COORDINATOR_ECS].data.get("clusters", [])
                if clusters:
                    region_has_resources = True
                total_ecs += len(clusters)
            
            # EKS
            if COORDINATOR_EKS in region_coordinators and region_coordinators[COORDINATOR_EKS].data:
                clusters = region_coordinators[COORDINATOR_EKS].data.get("clusters", [])
                if clusters:
                    region_has_resources = True
                total_eks += len(clusters)
            
            # EBS
            if COORDINATOR_EBS in region_coordinators and region_coordinators[COORDINATOR_EBS].data:
                volumes = region_coordinators[COORDINATOR_EBS].data.get("volumes", [])
                if volumes:
                    region_has_resources = True
                total_ebs += len(volumes)
                for volume in volumes:
                    if volume.get("attached_to"):
                        total_ebs_attached += 1
                    else:
                        total_ebs_unattached += 1
            
            # SNS
            if COORDINATOR_SNS in region_coordinators and region_coordinators[COORDINATOR_SNS].data:
                topics = region_coordinators[COORDINATOR_SNS].data.get("topics", [])
                if topics:
                    region_has_resources = True
                total_sns += len(topics)
            
            # SQS
            if COORDINATOR_SQS in region_coordinators and region_coordinators[COORDINATOR_SQS].data:
                queues = region_coordinators[COORDINATOR_SQS].data.get("queues", [])
                if queues:
                    region_has_resources = True
                total_sqs += len(queues)
            
            # S3
            if COORDINATOR_S3 in region_coordinators and region_coordinators[COORDINATOR_S3].data:
                buckets = region_coordinators[COORDINATOR_S3].data.get("buckets", [])
                if buckets:
                    region_has_resources = True
                total_s3 += len(buckets)
            
            # CloudWatch Alarms
            if COORDINATOR_CLOUDWATCH_ALARMS in region_coordinators and region_coordinators[COORDINATOR_CLOUDWATCH_ALARMS].data:
                alarms = region_coordinators[COORDINATOR_CLOUDWATCH_ALARMS].data.get("alarms", [])
                if alarms:
                    region_has_resources = True
                total_cloudwatch_alarms += len(alarms)
                for alarm in alarms:
                    if alarm.get("state") == "ALARM":
                        total_cloudwatch_alarms_alarm += 1
            
            # Elastic IPs
            if COORDINATOR_ELASTIC_IPS in region_coordinators and region_coordinators[COORDINATOR_ELASTIC_IPS].data:
                addresses = region_coordinators[COORDINATOR_ELASTIC_IPS].data.get("addresses", [])
                if addresses:
                    region_has_resources = True
                total_eips += len(addresses)
                for address in addresses:
                    if not address.get("attached"):
                        total_eips_unattached += 1
            
            if region_has_resources:
                active_regions += 1

        return {
            "active_regions": active_regions,
            "ec2_running": total_ec2_running,
            "ec2_stopped": total_ec2_stopped,
            "lambda_functions": total_lambda,
            "rds_instances": total_rds,
            "load_balancers": total_lb,
            "auto_scaling_groups": total_asg,
            "dynamodb_tables": total_dynamodb,
            "elasticache_clusters": total_elasticache,
            "ecs_clusters": total_ecs,
            "eks_clusters": total_eks,
            "ebs_volumes": total_ebs,
            "ebs_attached": total_ebs_attached,
            "ebs_unattached": total_ebs_unattached,
            "sns_topics": total_sns,
            "sqs_queues": total_sqs,
            "s3_buckets": total_s3,
            "cloudwatch_alarms": total_cloudwatch_alarms,
            "cloudwatch_alarms_alarm": total_cloudwatch_alarms_alarm,
            "elastic_ips": total_eips,
            "elastic_ips_unattached": total_eips_unattached,
        }

# ============================================================================
# SENSORS - Graphable Cost Sensors
# ============================================================================


class AwsCostYesterdaySensor(CoordinatorEntity, SensorEntity):
    """Sensor for yesterday's AWS cost - GRAPHABLE."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = "USD"

    def __init__(
        self,
        coordinator,
        account_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name

        self._attr_unique_id = f"aws_{account_name}_cost_yesterday"
        self._attr_name = "cost yesterday"
        self._attr_icon = "mdi:cash"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_global")},
            "name": f"AWS {account_name} (Global)",
            "manufacturer": "Amazon Web Services",
            "model": "Global",
            "entry_type": "service",
        }

    @property
    def native_value(self) -> float | None:
        """Return yesterday's cost."""
        if not self.coordinator.data or "cost_yesterday" not in self.coordinator.data:
            return None
    
        results = self.coordinator.data["cost_yesterday"].get("ResultsByTime", [])
        if results and len(results) > 0:
            try:
                # When using GroupBy, Total is empty - sum from Groups instead
                groups = results[0].get("Groups", [])
                if groups:
                    total = sum(
                        float(group["Metrics"]["UnblendedCost"]["Amount"])
                        for group in groups
                    )
                    return round(total, 2)
                # Fallback to Total if no groups
                amount = results[0]["Total"]["UnblendedCost"]["Amount"]
                return round(float(amount), 2)
            except (KeyError, ValueError, TypeError):
                return None
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        from datetime import date, timedelta
        yesterday = date.today() - timedelta(days=1)
        return {
            "date": yesterday.isoformat(),
            "account_name": self._account_name,
        }


class AwsCostMonthToDateSensor(CoordinatorEntity, SensorEntity):
    """Sensor for month-to-date AWS cost - GRAPHABLE."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = "USD"
    _attr_icon = "mdi:cash-multiple"

    def __init__(
        self,
        coordinator,
        account_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name

        self._attr_unique_id = f"aws_{account_name}_cost_month_to_date"
        self._attr_name = "cost month to date"
        self._attr_icon = "mdi:calendar-cash"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_global")},
            "name": f"AWS {account_name} (Global)",
            "manufacturer": "Amazon Web Services",
            "model": "Global",
            "entry_type": "service",
        }

    @property
    def native_value(self) -> float | None:
        """Return month-to-date cost."""
        if not self.coordinator.data or "cost_mtd" not in self.coordinator.data:
            return None
    
        results = self.coordinator.data["cost_mtd"].get("ResultsByTime", [])
        if results and len(results) > 0:
            try:
                # When using GroupBy, Total is empty - sum from Groups instead
                groups = results[0].get("Groups", [])
                if groups:
                    total = sum(
                        float(group["Metrics"]["UnblendedCost"]["Amount"])
                        for group in groups
                    )
                    return round(total, 2)
                # Fallback to Total if no groups
                amount = results[0]["Total"]["UnblendedCost"]["Amount"]
                return round(float(amount), 2)
            except (KeyError, ValueError, TypeError):
                return None
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        from datetime import date
        today = date.today()
        return {
            "month": today.strftime("%Y-%m"),
            "account_name": self._account_name,
        }


class AwsServiceCostSensor(CoordinatorEntity, SensorEntity):
    """Sensor for per-service AWS cost - GRAPHABLE."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = "USD"

    def __init__(
        self,
        coordinator,
        account_name: str,
        service_slug: str,
        cost_data: dict,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._service_slug = service_slug
        self._service_name = cost_data.get("name", service_slug)

        self._attr_unique_id = f"aws_{account_name}_cost_service_{service_slug}"
        self._attr_name = f"cost service {service_slug}"
        self._attr_icon = "mdi:cash-multiple"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_global")},
            "name": f"AWS {account_name} (Global)",
            "manufacturer": "Amazon Web Services",
            "model": "Global",
            "entry_type": "service",
        }

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
        attrs = {
            "service_name": self._service_name,
            "account_name": self._account_name,
        }
        
        if self.coordinator.data and "service_costs" in self.coordinator.data:
            service_costs = self.coordinator.data["service_costs"]
            if self._service_slug in service_costs:
                cost_data = service_costs[self._service_slug]
                attrs["rank"] = cost_data.get("rank", 0)
                attrs["percentage"] = cost_data.get("percentage", 0)
        
        return attrs


# ============================================================================
# EXISTING SENSORS - Legacy Cost (Backward Compatibility)
# ============================================================================


class AwsCostTodaySensor(CoordinatorEntity, SensorEntity):
    """Legacy sensor for yesterday's cost - BACKWARD COMPATIBILITY."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:cash"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = "USD"

    def __init__(
        self,
        coordinator,
        account_name: str,
        region: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region

        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_cost_today"
        self._attr_name = "cost today"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

    @property
    def native_value(self) -> float | None:
        """Return yesterday's cost."""
        if not self.coordinator.data or "cost_yesterday" not in self.coordinator.data:
            return None
    
        results = self.coordinator.data["cost_yesterday"].get("ResultsByTime", [])
        if results and len(results) > 0:
            try:
                # When using GroupBy, Total is empty - sum from Groups instead
                groups = results[0].get("Groups", [])
                if groups:
                    total = sum(
                        float(group["Metrics"]["UnblendedCost"]["Amount"])
                        for group in groups
                    )
                    return round(total, 2)
                # Fallback to Total if no groups
                amount = results[0]["Total"]["UnblendedCost"]["Amount"]
                return round(float(amount), 2)
            except (KeyError, ValueError, TypeError):
                return None
        return None

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return "USD"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return service breakdown."""
        if not self.coordinator.data or "cost_yesterday" not in self.coordinator.data:
            return {}

        results = self.coordinator.data["cost_yesterday"].get("ResultsByTime", [])
        if not results or "Groups" not in results[0]:
            return {}

        service_breakdown = {}
        for group in results[0]["Groups"]:
            service = group["Keys"][0]
            amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
            if amount > 0:
                service_breakdown[service] = round(amount, 2)

        return {"service_breakdown": service_breakdown}


class AwsCostMtdSensor(CoordinatorEntity, SensorEntity):
    """Legacy sensor for month-to-date cost - BACKWARD COMPATIBILITY."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-cash"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = "USD"
    _attr_icon = "mdi:cash-multiple"

    def __init__(
        self,
        coordinator,
        account_name: str,
        region: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region

        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_cost_mtd"
        self._attr_name = "cost mtd"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

    @property
    def native_value(self) -> float | None:
        """Return month-to-date cost."""
        if not self.coordinator.data or "cost_mtd" not in self.coordinator.data:
            return None
    
        results = self.coordinator.data["cost_mtd"].get("ResultsByTime", [])
        if results and len(results) > 0:
            try:
                # When using GroupBy, Total is empty - sum from Groups instead
                groups = results[0].get("Groups", [])
                if groups:
                    total = sum(
                        float(group["Metrics"]["UnblendedCost"]["Amount"])
                        for group in groups
                    )
                    return round(total, 2)
                # Fallback to Total if no groups
                amount = results[0]["Total"]["UnblendedCost"]["Amount"]
                return round(float(amount), 2)
            except (KeyError, ValueError, TypeError):
                return None
        return None

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return "USD"


# ============================================================================
# EXISTING SENSORS - EC2
# ============================================================================


class AwsEc2CountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for EC2 instance count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:server"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator,
        account_name: str,
        region: str,
        state_filter: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._state_filter = state_filter

        region_normalized = region.replace("-", "_")
        self._attr_unique_id = (
            f"aws_{account_name}_{region_normalized}_ec2_instances_{state_filter}"
        )
        self._attr_name = f"ec2 instances {state_filter}"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

    @property
    def native_value(self) -> int:
        """Return the count of instances."""
        if not self.coordinator.data or "instances" not in self.coordinator.data:
            return 0

        instances = self.coordinator.data["instances"]
        return sum(
            1 for instance in instances.values() if instance["state"] == self._state_filter
        )

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return "instances"


class AwsEc2InstanceSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual EC2 instance."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:server"

    def __init__(
        self,
        coordinator,
        account_name: str,
        region: str,
        instance_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._instance_id = instance_id

        region_normalized = region.replace("-", "_")
        instance_normalized = instance_id.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_ec2_{instance_normalized}"
        self._attr_name = f"ec2 {instance_id}"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

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
                    }
        return {}

# ============================================================================
# EXISTING SENSORS - RDS
# ============================================================================


class AwsRdsCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for RDS instance count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:database"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator,
        account_name: str,
        region: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region

        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_rds_total_instances"
        self._attr_name = "rds total instances"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

    @property
    def native_value(self) -> int:
        """Return the count of instances."""
        if not self.coordinator.data or "instances" not in self.coordinator.data:
            return 0
        return len(self.coordinator.data["instances"])

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return "instances"

class AwsRdsInstanceSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual RDS instance."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:database"

    def __init__(
        self,
        coordinator,
        account_name: str,
        region: str,
        db_identifier: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._db_identifier = db_identifier

        region_normalized = region.replace("-", "_")
        db_normalized = db_identifier.replace("-", "_").replace(".", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_rds_{db_normalized}"
        self._attr_name = f"rds {db_identifier}"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

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
                    }
        return {}

# ============================================================================
# EXISTING SENSORS - Lambda
# ============================================================================


class AwsLambdaCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Lambda function count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:lambda"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator,
        account_name: str,
        region: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region

        region_normalized = region.replace("-", "_")
        self._attr_unique_id = (
            f"aws_{account_name}_{region_normalized}_lambda_total_functions"
        )
        self._attr_name = "lambda total functions"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

    @property
    def native_value(self) -> int:
        """Return the count of functions."""
        if not self.coordinator.data or "functions" not in self.coordinator.data:
            return 0
        return len(self.coordinator.data["functions"])

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return "functions"

class AwsLambdaFunctionSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual Lambda function."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:lambda"

    def __init__(
        self,
        coordinator,
        account_name: str,
        region: str,
        function_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._function_name = function_name

        region_normalized = region.replace("-", "_")
        function_normalized = function_name.replace("-", "_").replace(".", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_lambda_{function_normalized}"
        self._attr_name = f"lambda {function_name}"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

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
                    }
        return {}

# ============================================================================
# EXISTING SENSORS - Load Balancer
# ============================================================================

class AwsLoadBalancerSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual load balancer."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:scale-balance"

    def __init__(
        self,
        coordinator,
        account_name: str,
        region: str,
        lb_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._lb_name = lb_name

        region_normalized = region.replace("-", "_")
        lb_normalized = lb_name.replace("-", "_").replace(".", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_lb_{lb_normalized}"
        self._attr_name = f"lb {lb_name}"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

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
                    }
        return {}

# ============================================================================
# EXISTING SENSORS - Auto Scaling Group
# ============================================================================


class AwsAsgSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual Auto Scaling Group."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:server-network"

    def __init__(
        self,
        coordinator,
        account_name: str,
        region: str,
        asg_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._asg_name = asg_name

        region_normalized = region.replace("-", "_")
        asg_normalized = asg_name.replace("-", "_").replace(".", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_asg_{asg_normalized}"
        self._attr_name = f"asg {asg_name}"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

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
                    }
        return {}

# ============================================================================
# DYNAMODB SENSORS
# ============================================================================

class AwsDynamoDBCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for DynamoDB table count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:database"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator,
        account_name: str,
        region: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region

        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_dynamodb_count"
        self._attr_name = "dynamodb count"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

    @property
    def native_value(self) -> int:
        """Return the number of DynamoDB tables."""
        if self.coordinator.data:
            return len(self.coordinator.data.get("tables", []))
        return 0


class AwsDynamoDBTableSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual DynamoDB table."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:database"

    def __init__(
        self,
        coordinator,
        account_name: str,
        region: str,
        table_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._table_name = table_name

        region_normalized = region.replace("-", "_")
        table_normalized = table_name.replace("-", "_").replace(".", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_dynamodb_{table_normalized}"
        self._attr_name = f"dynamodb {table_name}"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

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
                    }
        return {}


# ============================================================================
# ELASTICACHE SENSORS
# ============================================================================

class AwsElastiCacheCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for ElastiCache cluster count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:memory"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator,
        account_name: str,
        region: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region

        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_elasticache_count"
        self._attr_name = "elasticache count"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

    @property
    def native_value(self) -> int:
        """Return the number of ElastiCache clusters."""
        if self.coordinator.data:
            return len(self.coordinator.data.get("clusters", []))
        return 0


class AwsElastiCacheClusterSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual ElastiCache cluster."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:memory"

    def __init__(
        self,
        coordinator,
        account_name: str,
        region: str,
        cluster_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._cluster_id = cluster_id

        region_normalized = region.replace("-", "_")
        cluster_normalized = cluster_id.replace("-", "_").replace(".", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_elasticache_{cluster_normalized}"
        self._attr_name = f"elasticache {cluster_id}"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

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
                    }
        return {}


# ============================================================================
# ECS SENSORS
# ============================================================================

class AwsECSCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for ECS cluster count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:docker"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator,
        account_name: str,
        region: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region

        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_ecs_count"
        self._attr_name = "ecs count"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

    @property
    def native_value(self) -> int:
        """Return the number of ECS clusters."""
        if self.coordinator.data:
            return len(self.coordinator.data.get("clusters", []))
        return 0

class AwsECSClusterSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual ECS cluster."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:docker"

    def __init__(
        self,
        coordinator,
        account_name: str,
        region: str,
        cluster_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._cluster_name = cluster_name

        region_normalized = region.replace("-", "_")
        cluster_normalized = cluster_name.replace("-", "_").replace(".", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_ecs_{cluster_normalized}"
        self._attr_name = f"ecs {cluster_name}"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

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
                    }
        return {}

# ============================================================================
# EKS SENSORS
# ============================================================================

class AwsEKSCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for EKS cluster count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:kubernetes"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator,
        account_name: str,
        region: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region

        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_eks_count"
        self._attr_name = "eks count"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

    @property
    def native_value(self) -> int:
        """Return the number of EKS clusters."""
        if self.coordinator.data:
            return len(self.coordinator.data.get("clusters", []))
        return 0

class AwsEKSClusterSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual EKS cluster."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:kubernetes"

    def __init__(
        self,
        coordinator,
        account_name: str,
        region: str,
        cluster_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._cluster_name = cluster_name

        region_normalized = region.replace("-", "_")
        cluster_normalized = cluster_name.replace("-", "_").replace(".", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_eks_{cluster_normalized}"
        self._attr_name = f"eks {cluster_name}"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

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
                    }
        return {}

# ============================================================================
# EBS VOLUME SENSORS
# ============================================================================

class AwsEBSCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for EBS volume count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:harddisk"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator,
        account_name: str,
        region: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region

        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_ebs_count"
        self._attr_name = "ebs volume count"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

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
            unattached = sum(1 for v in volumes if not v.get("attached_to"))
            total_size = sum(v.get("size", 0) for v in volumes)
            
            return {
                "total_volumes": len(volumes),
                "attached": attached,
                "unattached": unattached,
                "total_size_gb": total_size,
            }
        return {}

class AwsEBSVolumeSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual EBS volume."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:harddisk"

    def __init__(
        self,
        coordinator,
        account_name: str,
        region: str,
        volume_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._volume_id = volume_id

        region_normalized = region.replace("-", "_")
        volume_normalized = volume_id.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_ebs_{volume_normalized}"
        self._attr_name = f"ebs {volume_id}"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

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
                    }
        return {}

# ============================================================================
# SNS SENSORS
# ============================================================================

class AwsSNSCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for SNS topic count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:bell"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator,
        account_name: str,
        region: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region

        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_sns_count"
        self._attr_name = "sns topic count"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

    @property
    def native_value(self) -> int:
        """Return the number of SNS topics."""
        if self.coordinator.data:
            return len(self.coordinator.data.get("topics", []))
        return 0

class AwsSNSTopicSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual SNS topic."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:bell"

    def __init__(
        self,
        coordinator,
        account_name: str,
        region: str,
        topic_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._topic_name = topic_name

        region_normalized = region.replace("-", "_")
        topic_normalized = topic_name.replace("-", "_").replace(".", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_sns_{topic_normalized}"
        self._attr_name = f"sns {topic_name}"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

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
                    }
        return {}

# ============================================================================
# SQS SENSORS
# ============================================================================

class AwsSQSCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for SQS queue count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:format-list-bulleted"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator,
        account_name: str,
        region: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region

        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_sqs_count"
        self._attr_name = "sqs queue count"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

    @property
    def native_value(self) -> int:
        """Return the number of SQS queues."""
        if self.coordinator.data:
            return len(self.coordinator.data.get("queues", []))
        return 0

class AwsSQSQueueSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual SQS queue."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:format-list-bulleted"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator,
        account_name: str,
        region: str,
        queue_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._queue_name = queue_name

        region_normalized = region.replace("-", "_")
        queue_normalized = queue_name.replace("-", "_").replace(".", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_sqs_{queue_normalized}"
        self._attr_name = f"sqs {queue_name}"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

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
                    }
        return {}


# ============================================================================
# S3 SENSORS
# ============================================================================

class AwsS3CountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for S3 bucket count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:bucket"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator,
        account_name: str,
        region: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region

        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_s3_count"
        self._attr_name = "s3 bucket count"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

    @property
    def native_value(self) -> int:
        """Return the number of S3 buckets in this region."""
        if self.coordinator.data:
            return len(self.coordinator.data.get("buckets", []))
        return 0

class AwsS3BucketSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual S3 bucket."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:bucket"

    def __init__(
        self,
        coordinator,
        account_name: str,
        region: str,
        bucket_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._bucket_name = bucket_name

        region_normalized = region.replace("-", "_")
        bucket_normalized = bucket_name.replace("-", "_").replace(".", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_s3_{bucket_normalized}"
        self._attr_name = f"s3 {bucket_name}"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

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
                    }
        return {}



# ============================================================================
# CLOUDWATCH ALARMS SENSORS
# ============================================================================

class AwsCloudWatchAlarmsCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for CloudWatch alarm count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:alarm-light"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator,
        account_name: str,
        region: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region

        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_cloudwatch_alarms_count"
        self._attr_name = "cloudwatch alarm count"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

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
            ok = sum(1 for a in alarms if a.get("state") == "OK")
            alarm = sum(1 for a in alarms if a.get("state") == "ALARM")
            insufficient = sum(1 for a in alarms if a.get("state") == "INSUFFICIENT_DATA")
            
            return {
                "total_alarms": len(alarms),
                "ok": ok,
                "alarm": alarm,
                "insufficient_data": insufficient,
            }
        return {}


class AwsCloudWatchAlarmSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual CloudWatch alarm."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:alarm-light"

    def __init__(
        self,
        coordinator,
        account_name: str,
        region: str,
        alarm_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._alarm_name = alarm_name

        region_normalized = region.replace("-", "_")
        alarm_normalized = alarm_name.replace("-", "_").replace(".", "_").replace(" ", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_alarm_{alarm_normalized}"
        self._attr_name = f"alarm {alarm_name}"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

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
                    }
        return {}


# ============================================================================
# ELASTIC IP SENSORS
# ============================================================================

class AwsElasticIPsCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Elastic IP count."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:ip-network"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator,
        account_name: str,
        region: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region

        region_normalized = region.replace("-", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_elastic_ips_count"
        self._attr_name = "elastic ip count"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

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
            unattached = sum(1 for a in addresses if not a.get("attached"))
            
            return {
                "total_ips": len(addresses),
                "attached": attached,
                "unattached": unattached,
            }
        return {}

class AwsElasticIPSensor(CoordinatorEntity, SensorEntity):
    """Sensor for individual Elastic IP."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:ip-network"

    def __init__(
        self,
        coordinator,
        account_name: str,
        region: str,
        ip_address: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._ip_address = ip_address

        region_normalized = region.replace("-", "_")
        ip_normalized = ip_address.replace(".", "_")
        self._attr_unique_id = f"aws_{account_name}_{region_normalized}_eip_{ip_normalized}"
        self._attr_name = f"eip {ip_address}"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

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
                    }
        return {}
