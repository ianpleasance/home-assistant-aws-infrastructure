"""Config flow for AWS Infrastructure integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import (
    AWS_REGIONS,
    CONF_ACCOUNT_NAME,
    CONF_AWS_ACCESS_KEY_ID,
    CONF_AWS_SECRET_ACCESS_KEY,
    CONF_CREATE_INDIVIDUAL_COUNT_SENSORS,
    CONF_REFRESH_INTERVAL,
    CONF_REGION_MODE,
    CONF_REGIONS,
    DEFAULT_CREATE_INDIVIDUAL_COUNT_SENSORS,
    DEFAULT_REFRESH_INTERVAL,
    DOMAIN,
    MAX_REFRESH_INTERVAL,
    MIN_REFRESH_INTERVAL,
    REGION_MODE_ALL,
    REGION_MODE_SELECT,
)

_LOGGER = logging.getLogger(__name__)


class AwsInfrastructureConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AWS Infrastructure."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.data = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate credentials
            try:
                await self._test_credentials(user_input)
            except Exception as err:
                _LOGGER.error("Error validating credentials: %s", err)
                errors["base"] = "invalid_auth"
            else:
                self.data = user_input

                # If region mode is "select", go to region selection
                if user_input[CONF_REGION_MODE] == REGION_MODE_SELECT:
                    return await self.async_step_regions()

                # Otherwise, create entry
                return self.async_create_entry(
                    title=f"{user_input[CONF_ACCOUNT_NAME]} (All Regions)",
                    data=self.data,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ACCOUNT_NAME): str,
                    vol.Required(CONF_AWS_ACCESS_KEY_ID): str,
                    vol.Required(CONF_AWS_SECRET_ACCESS_KEY): str,
                    vol.Required(
                        CONF_REGION_MODE, default=REGION_MODE_ALL
                    ): vol.In(
                        {
                            REGION_MODE_ALL: "Monitor all AWS regions",
                            REGION_MODE_SELECT: "Select specific regions",
                        }
                    ),
                    vol.Required(
                        CONF_REFRESH_INTERVAL, default=DEFAULT_REFRESH_INTERVAL
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_REFRESH_INTERVAL, max=MAX_REFRESH_INTERVAL),
                    ),
                    vol.Required(
                        CONF_CREATE_INDIVIDUAL_COUNT_SENSORS,
                        default=DEFAULT_CREATE_INDIVIDUAL_COUNT_SENSORS,
                    ): bool,
                }
            ),
            errors=errors,
        )

    async def async_step_regions(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle region selection."""
        if user_input is not None:
            self.data[CONF_REGIONS] = user_input[CONF_REGIONS]
            return self.async_create_entry(
                title=f"{self.data[CONF_ACCOUNT_NAME]} (Selected Regions)",
                data=self.data,
            )

        return self.async_show_form(
            step_id="regions",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_REGIONS): cv.multi_select(AWS_REGIONS),
                }
            ),
        )

    async def _test_credentials(self, user_input: dict[str, Any]) -> None:
        """Test if the credentials are valid."""
        import boto3

        session = boto3.Session(
            aws_access_key_id=user_input[CONF_AWS_ACCESS_KEY_ID],
            aws_secret_access_key=user_input[CONF_AWS_SECRET_ACCESS_KEY],
        )
        sts = session.client("sts")
        # This will raise an exception if credentials are invalid
        sts.get_caller_identity()

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> AwsInfrastructureOptionsFlow:
        """Get the options flow for this handler."""
        return AwsInfrastructureOptionsFlow(config_entry)


class AwsInfrastructureOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_REFRESH_INTERVAL,
                        default=self.config_entry.data.get(
                            CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_REFRESH_INTERVAL, max=MAX_REFRESH_INTERVAL),
                    ),
                    vol.Required(
                        CONF_CREATE_INDIVIDUAL_COUNT_SENSORS,
                        default=self.config_entry.data.get(
                            CONF_CREATE_INDIVIDUAL_COUNT_SENSORS,
                            DEFAULT_CREATE_INDIVIDUAL_COUNT_SENSORS,
                        ),
                    ): bool,
                }
            ),
        )
