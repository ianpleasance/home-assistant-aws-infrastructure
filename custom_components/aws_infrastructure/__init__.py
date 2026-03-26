"""The AWS Infrastructure integration."""
from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .aws_client import AwsClient
from .const import (
    AWS_REGIONS,
    CONF_ACCOUNT_NAME,
    CONF_AWS_ACCESS_KEY_ID,
    CONF_AWS_SECRET_ACCESS_KEY,
    CONF_REFRESH_INTERVAL,
    CONF_COST_REFRESH_INTERVAL,
    CONF_REGION_MODE,
    CONF_REGIONS,
    COORDINATOR_ASG,
    COORDINATOR_COST,
    COORDINATOR_EC2,
    COORDINATOR_LAMBDA,
    COORDINATOR_LOADBALANCER,
    COORDINATOR_RDS,
    COORDINATOR_CLOUDWATCH_ALARMS,
    COORDINATOR_DYNAMODB,
    COORDINATOR_EBS,
    COORDINATOR_ECS,
    COORDINATOR_EKS,
    COORDINATOR_ELASTICACHE,
    COORDINATOR_ELASTIC_IPS,
    COORDINATOR_S3,
    COORDINATOR_SNS,
    COORDINATOR_SQS,
    COORDINATOR_CLASSIC_LB,
    COORDINATOR_EFS,
    COORDINATOR_KINESIS,
    COORDINATOR_BEANSTALK,
    COORDINATOR_ROUTE53,
    COORDINATOR_API_GATEWAY,
    COORDINATOR_CLOUDFRONT,
    COORDINATOR_VPC,
    COORDINATOR_ACM,
    COORDINATOR_ECR,
    COORDINATOR_CLOUDTRAIL,
    COORDINATOR_IAM,
    COORDINATOR_REDSHIFT,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_SERVICES,
    DEFAULT_COST_REFRESH_INTERVAL,
    CONF_SERVICES,
    DOMAIN,
    REGION_MODE_ALL,
    SERVICE_REFRESH_ACCOUNT,
    SERVICE_REFRESH_ALL,
)
from .coordinator import (
    AwsAutoScalingCoordinator,
    AwsCloudWatchAlarmsCoordinator,
    AwsCostCoordinator,
    AwsDynamoDBCoordinator,
    AwsEBSCoordinator,
    AwsECSCoordinator,
    AwsEc2Coordinator,
    AwsEKSCoordinator,
    AwsElastiCacheCoordinator,
    AwsElasticIPsCoordinator,
    AwsLambdaCoordinator,
    AwsLoadBalancerCoordinator,
    AwsRdsCoordinator,
    AwsS3Coordinator,
    AwsSNSCoordinator,
    AwsSQSCoordinator,
    AwsClassicLBCoordinator,
    AwsEFSCoordinator,
    AwsKinesisCoordinator,
    AwsBeanstalkCoordinator,
    AwsRoute53Coordinator,
    AwsApiGatewayCoordinator,
    AwsCloudFrontCoordinator,
    AwsVPCCoordinator,
    AwsACMCoordinator,
    AwsECRCoordinator,
    AwsCloudTrailCoordinator,
    AwsIAMCoordinator,
    AwsRedshiftCoordinator,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AWS Infrastructure from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    account_name = entry.data[CONF_ACCOUNT_NAME]
    aws_access_key_id = entry.data[CONF_AWS_ACCESS_KEY_ID]
    aws_secret_access_key = entry.data[CONF_AWS_SECRET_ACCESS_KEY]

    refresh_interval = entry.options.get(
        CONF_REFRESH_INTERVAL,
        entry.data.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL),
    )

    region_mode = entry.data.get(CONF_REGION_MODE, REGION_MODE_ALL)
    if region_mode == REGION_MODE_ALL:
        regions = await _get_all_aws_regions(hass, aws_access_key_id, aws_secret_access_key)
    else:
        regions = entry.data.get(CONF_REGIONS, ["us-east-1"])

    _LOGGER.info(
        "Setting up AWS account '%s' monitoring %d regions: %s",
        account_name,
        len(regions),
        regions,
    )

    all_coordinators = {}

    for region in regions:
        aws_client = AwsClient(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region=region,
        )

        coordinators = {}

        # Only create coordinators for selected services
        selected_services = set(
            entry.data.get(CONF_SERVICES, list(DEFAULT_SERVICES))
        )

        def add(key, coordinator_instance):
            """Only add coordinator if service is selected."""
            if key in selected_services:
                coordinators[key] = coordinator_instance

        if region == "us-east-1":
            cost_refresh_interval = entry.options.get(
                CONF_COST_REFRESH_INTERVAL,
                entry.data.get(CONF_COST_REFRESH_INTERVAL, DEFAULT_COST_REFRESH_INTERVAL),
            )
            # Global services — only fetched from us-east-1
            add(COORDINATOR_COST, AwsCostCoordinator(hass, aws_client, account_name, cost_refresh_interval))
            add(COORDINATOR_ROUTE53, AwsRoute53Coordinator(hass, aws_client, account_name, refresh_interval))
            add(COORDINATOR_CLOUDFRONT, AwsCloudFrontCoordinator(hass, aws_client, account_name, refresh_interval))
            add(COORDINATOR_IAM, AwsIAMCoordinator(hass, aws_client, account_name, refresh_interval))

        # Regional services
        add(COORDINATOR_EC2, AwsEc2Coordinator(hass, aws_client, account_name, refresh_interval))
        add(COORDINATOR_RDS, AwsRdsCoordinator(hass, aws_client, account_name, refresh_interval))
        add(COORDINATOR_LAMBDA, AwsLambdaCoordinator(hass, aws_client, account_name, refresh_interval))
        add(COORDINATOR_LOADBALANCER, AwsLoadBalancerCoordinator(hass, aws_client, account_name, refresh_interval))
        add(COORDINATOR_ASG, AwsAutoScalingCoordinator(hass, aws_client, account_name, refresh_interval))
        add(COORDINATOR_DYNAMODB, AwsDynamoDBCoordinator(hass, aws_client, account_name, refresh_interval))
        add(COORDINATOR_ELASTICACHE, AwsElastiCacheCoordinator(hass, aws_client, account_name, refresh_interval))
        add(COORDINATOR_ECS, AwsECSCoordinator(hass, aws_client, account_name, refresh_interval))
        add(COORDINATOR_EKS, AwsEKSCoordinator(hass, aws_client, account_name, refresh_interval))
        add(COORDINATOR_EBS, AwsEBSCoordinator(hass, aws_client, account_name, refresh_interval))
        add(COORDINATOR_SNS, AwsSNSCoordinator(hass, aws_client, account_name, refresh_interval))
        add(COORDINATOR_SQS, AwsSQSCoordinator(hass, aws_client, account_name, refresh_interval))
        add(COORDINATOR_S3, AwsS3Coordinator(hass, aws_client, account_name, refresh_interval))
        add(COORDINATOR_CLOUDWATCH_ALARMS, AwsCloudWatchAlarmsCoordinator(hass, aws_client, account_name, refresh_interval))
        add(COORDINATOR_ELASTIC_IPS, AwsElasticIPsCoordinator(hass, aws_client, account_name, refresh_interval))
        add(COORDINATOR_CLASSIC_LB, AwsClassicLBCoordinator(hass, aws_client, account_name, refresh_interval))
        add(COORDINATOR_EFS, AwsEFSCoordinator(hass, aws_client, account_name, refresh_interval))
        add(COORDINATOR_KINESIS, AwsKinesisCoordinator(hass, aws_client, account_name, refresh_interval))
        add(COORDINATOR_BEANSTALK, AwsBeanstalkCoordinator(hass, aws_client, account_name, refresh_interval))
        add(COORDINATOR_API_GATEWAY, AwsApiGatewayCoordinator(hass, aws_client, account_name, refresh_interval))
        add(COORDINATOR_VPC, AwsVPCCoordinator(hass, aws_client, account_name, refresh_interval))
        add(COORDINATOR_ACM, AwsACMCoordinator(hass, aws_client, account_name, refresh_interval))
        add(COORDINATOR_ECR, AwsECRCoordinator(hass, aws_client, account_name, refresh_interval))
        add(COORDINATOR_CLOUDTRAIL, AwsCloudTrailCoordinator(hass, aws_client, account_name, refresh_interval))
        add(COORDINATOR_REDSHIFT, AwsRedshiftCoordinator(hass, aws_client, account_name, refresh_interval))

        # skip_initial_refresh only applies when HA is restarting with an existing
        # entry — on a fresh setup or reconfigure we always do a full blocking refresh
        # so the user sees real data immediately after adding the integration.
        is_new_entry = entry.state == ConfigEntryState.SETUP_IN_PROGRESS and not entry.unique_id
        skip_initial_refresh = (
            entry.options.get("skip_initial_refresh", False)
            and entry.state != ConfigEntryState.SETUP_IN_PROGRESS
        )

        if not skip_initial_refresh:
            # Refresh all coordinators for this region concurrently.
            # Use async_refresh() instead of async_config_entry_first_refresh()
            # so a single failing coordinator (e.g. Redshift not enabled in a region,
            # or missing IAM permission) never cancels the entire entry setup.
            async def _refresh_one(key, coord):
                _LOGGER.debug(
                    "Starting first refresh for %s [account=%s region=%s]",
                    key, account_name, region,
                )
                try:
                    await coord.async_refresh()
                    _LOGGER.debug(
                        "Completed first refresh for %s [account=%s region=%s]",
                        key, account_name, region,
                    )
                except Exception as err:
                    _LOGGER.error(
                        "First refresh failed for %s [account=%s region=%s]: %s",
                        key, account_name, region, err,
                    )

            await asyncio.gather(
                *[_refresh_one(k, c) for k, c in coordinators.items()],
                return_exceptions=True,
            )

        all_coordinators[region] = coordinators

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinators": all_coordinators,
        "account_name": account_name,
        "regions": regions,
        "global": {
          "coordinators": all_coordinators,
        },
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    if "_services_registered" not in hass.data[DOMAIN]:
        await async_setup_services(hass)
        hass.data[DOMAIN]["_services_registered"] = True

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update — clean up deselected service/region entities then reload."""
    from homeassistant.helpers import entity_registry as er
    entity_reg = er.async_get(hass)

    # ----------------------------------------------------------------
    # Clean up entities for deselected services
    # ----------------------------------------------------------------
    old_services = set(entry.options.get("_old_services", list(DEFAULT_SERVICES)))
    new_services = set(entry.data.get(CONF_SERVICES, list(DEFAULT_SERVICES)))
    removed_services = old_services - new_services

    if removed_services:
        _LOGGER.info("Removing entities for deselected services: %s", removed_services)
        _SERVICE_ENTITY_PATTERNS = {
            COORDINATOR_EC2: "_ec2_i_",
            COORDINATOR_RDS: "_rds_",
            COORDINATOR_LAMBDA: "_lambda_",
            COORDINATOR_LOADBALANCER: "_load_balancer_",
            COORDINATOR_ASG: "_auto_scaling_group_",
            COORDINATOR_DYNAMODB: "_dynamodb_",
            COORDINATOR_ELASTICACHE: "_elasticache_",
            COORDINATOR_ECS: "_ecs_",
            COORDINATOR_EKS: "_eks_",
            COORDINATOR_EBS: "_ebs_",
            COORDINATOR_SNS: "_sns_",
            COORDINATOR_SQS: "_sqs_",
            COORDINATOR_S3: "_s3_bucket_",
            COORDINATOR_CLOUDWATCH_ALARMS: "_alarm_",
            COORDINATOR_ELASTIC_IPS: "_eip_",
            COORDINATOR_CLASSIC_LB: "_classic_lb_",
            COORDINATOR_EFS: "_efs_fs_",
            COORDINATOR_KINESIS: "_kinesis_",
            COORDINATOR_BEANSTALK: "_beanstalk_",
            COORDINATOR_API_GATEWAY: "_apigw_",
            COORDINATOR_VPC: "_vpc_vpc_",
            COORDINATOR_ACM: "_acm_",
            COORDINATOR_ECR: "_ecr_",
            COORDINATOR_CLOUDTRAIL: "_cloudtrail_",
            COORDINATOR_CLOUDFRONT: "_cloudfront_",
            COORDINATOR_ROUTE53: "_route_53_",
            COORDINATOR_IAM: "_iam_",
            COORDINATOR_COST: "_cost_",
            COORDINATOR_REDSHIFT: "_redshift_",
        }
        to_remove = []
        for svc in removed_services:
            pattern = _SERVICE_ENTITY_PATTERNS.get(svc)
            if not pattern:
                continue
            for entity_entry in list(entity_reg.entities.values()):
                if (entity_entry.config_entry_id == entry.entry_id
                        and pattern in entity_entry.unique_id):
                    to_remove.append(entity_entry.entity_id)
        for entity_id in to_remove:
            entity_reg.async_remove(entity_id)
        _LOGGER.info("Removed %d entities for deselected services", len(to_remove))

    # ----------------------------------------------------------------
    # Clean up entities for deselected regions
    # ----------------------------------------------------------------
    old_region_mode = entry.options.get("_old_region_mode", REGION_MODE_ALL)
    old_regions = entry.options.get("_old_regions", [])
    new_region_mode = entry.data.get(CONF_REGION_MODE, REGION_MODE_ALL)
    new_regions = entry.data.get(CONF_REGIONS, [])

    old_active_regions = set(AWS_REGIONS) if old_region_mode == REGION_MODE_ALL else set(old_regions)
    new_active_regions = set(AWS_REGIONS) if new_region_mode == REGION_MODE_ALL else set(new_regions)
    removed_regions = old_active_regions - new_active_regions

    if removed_regions:
        _LOGGER.info("Removing entities for deselected regions: %s", removed_regions)
        to_remove = []
        for entity_entry in list(entity_reg.entities.values()):
            if entity_entry.config_entry_id == entry.entry_id:
                for region in removed_regions:
                    region_normalized = region.replace("-", "_")
                    if f"_{region_normalized}_" in entity_entry.unique_id:
                        to_remove.append(entity_entry.entity_id)
                        break
        for entity_id in to_remove:
            entity_reg.async_remove(entity_id)
        _LOGGER.info("Removed %d entities for deselected regions", len(to_remove))

    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

        if len([k for k in hass.data[DOMAIN].keys() if k != "_services_registered"]) == 0:
            hass.services.async_remove(DOMAIN, SERVICE_REFRESH_ACCOUNT)
            hass.services.async_remove(DOMAIN, SERVICE_REFRESH_ALL)
            hass.data[DOMAIN].pop("_services_registered", None)

    return unload_ok


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for the integration."""

    async def handle_refresh_account(call: ServiceCall) -> None:
        """Handle refresh account service call."""
        account_name = call.data[CONF_ACCOUNT_NAME]
        region_filter = call.data.get("region")

        for entry_id, data in hass.data[DOMAIN].items():
            if (
                isinstance(data, dict)
                and data.get(CONF_ACCOUNT_NAME) == account_name
            ):
                all_coordinators = data["coordinators"]

                for region, coordinators in all_coordinators.items():
                    if region_filter and region != region_filter:
                        continue

                    for service_name, coordinator in coordinators.items():
                        _LOGGER.info(
                            "Refreshing %s for %s in %s",
                            service_name,
                            account_name,
                            region,
                        )
                        await coordinator.async_request_refresh()

    async def handle_refresh_all(call: ServiceCall) -> None:
        """Handle refresh all accounts service call."""
        _LOGGER.info("Manually refreshing all AWS accounts")

        for entry_id, data in hass.data[DOMAIN].items():
            if not isinstance(data, dict) or CONF_ACCOUNT_NAME not in data:
                continue

            account_name = data[CONF_ACCOUNT_NAME]
            all_coordinators = data.get("coordinators", {})

            for region, coordinators in all_coordinators.items():
                for service_name, coordinator in coordinators.items():
                    _LOGGER.info(
                        "Refreshing %s for account %s in %s",
                        service_name,
                        account_name,
                        region,
                    )
                    await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_ACCOUNT,
        handle_refresh_account,
        schema=vol.Schema(
            {
                vol.Required(CONF_ACCOUNT_NAME): cv.string,
                vol.Optional("region"): cv.string,
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_ALL,
        handle_refresh_all,
    )


async def _get_all_aws_regions(
    hass: HomeAssistant, access_key: str, secret_key: str
) -> list[str]:
    """Get all enabled AWS regions for the account."""
    import boto3

    def _get_regions():
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="us-east-1",
        )
        ec2 = session.client("ec2")

        response = ec2.describe_regions(AllRegions=False)
        return [region["RegionName"] for region in response["Regions"]]

    try:
        regions = await hass.async_add_executor_job(_get_regions)
        _LOGGER.info("Discovered %d enabled AWS regions", len(regions))
        return regions
    except Exception as err:
        _LOGGER.error("Failed to discover regions: %s", err)
        return [
            "us-east-1",
            "us-east-2",
            "us-west-1",
            "us-west-2",
            "eu-west-1",
            "eu-central-1",
            "ap-southeast-1",
            "ap-northeast-1",
        ]
