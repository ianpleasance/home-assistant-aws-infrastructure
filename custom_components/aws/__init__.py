"""The AWS Infrastructure integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .aws_client import AwsClient
from .const import (
    CONF_ACCOUNT_NAME,
    CONF_AWS_ACCESS_KEY_ID,
    CONF_AWS_SECRET_ACCESS_KEY,
    CONF_REFRESH_INTERVAL,
    CONF_REGION_MODE,
    CONF_REGIONS,
    COORDINATOR_AUTO_SCALING,
    COORDINATOR_COST,
    COORDINATOR_EC2,
    COORDINATOR_LAMBDA,
    COORDINATOR_LOAD_BALANCER,
    COORDINATOR_RDS,
    DEFAULT_REFRESH_INTERVAL,
    DOMAIN,
    REGION_MODE_ALL,
    SERVICE_REFRESH_ACCOUNT,
    SERVICE_REFRESH_ALL,
)
from .coordinator import (
    AwsAutoScalingCoordinator,
    AwsCostCoordinator,
    AwsEc2Coordinator,
    AwsLambdaCoordinator,
    AwsLoadBalancerCoordinator,
    AwsRdsCoordinator,
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

        if region == "us-east-1":
            coordinators[COORDINATOR_COST] = AwsCostCoordinator(
                hass, aws_client, account_name, refresh_interval
            )

        coordinators[COORDINATOR_EC2] = AwsEc2Coordinator(
            hass, aws_client, account_name, refresh_interval
        )
        coordinators[COORDINATOR_RDS] = AwsRdsCoordinator(
            hass, aws_client, account_name, refresh_interval
        )
        coordinators[COORDINATOR_LAMBDA] = AwsLambdaCoordinator(
            hass, aws_client, account_name, refresh_interval
        )
        coordinators[COORDINATOR_LOAD_BALANCER] = AwsLoadBalancerCoordinator(
            hass, aws_client, account_name, refresh_interval
        )
        coordinators[COORDINATOR_AUTO_SCALING] = AwsAutoScalingCoordinator(
            hass, aws_client, account_name, refresh_interval
        )

        for coordinator in coordinators.values():
            await coordinator.async_config_entry_first_refresh()

        all_coordinators[region] = coordinators

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinators": all_coordinators,
        "account_name": account_name,
        "regions": regions,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    if not hasattr(hass.data[DOMAIN], "_services_registered"):
        await async_setup_services(hass)
        hass.data[DOMAIN]["_services_registered"] = True

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
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
