"""Config flow for AWS Infrastructure integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_ACCOUNT_NAME,
    CONF_AWS_ACCESS_KEY_ID,
    CONF_AWS_SECRET_ACCESS_KEY,
    CONF_REFRESH_INTERVAL,
    CONF_REGION_MODE,
    CONF_REGIONS,
    DEFAULT_REFRESH_INTERVAL,
    DOMAIN,
    MAX_REFRESH_INTERVAL,
    MIN_REFRESH_INTERVAL,
    REGION_MODE_ALL,
    REGION_MODE_SELECT,
    AWS_REGIONS,
)

_LOGGER = logging.getLogger(__name__)


class AwsInfrastructureConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AWS Infrastructure."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._data.update(user_input)

            try:
                await self._test_credentials(user_input)
            except Exception as err:
                _LOGGER.error("Authentication failed: %s", err)
                errors["base"] = "invalid_auth"
            else:
                if user_input[CONF_REGION_MODE] == REGION_MODE_ALL:
                    await self.async_set_unique_id(user_input[CONF_ACCOUNT_NAME])
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=f"{user_input[CONF_ACCOUNT_NAME]} (All Regions)",
                        data=self._data,
                    )

                return await self.async_step_select_regions()

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
                    vol.Optional(
                        CONF_REFRESH_INTERVAL, default=DEFAULT_REFRESH_INTERVAL
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_REFRESH_INTERVAL, max=MAX_REFRESH_INTERVAL),
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_select_regions(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle region selection step."""
        if user_input is not None:
            self._data[CONF_REGIONS] = user_input[CONF_REGIONS]

            await self.async_set_unique_id(self._data[CONF_ACCOUNT_NAME])
            self._abort_if_unique_id_configured()

            region_count = len(user_input[CONF_REGIONS])
            return self.async_create_entry(
                title=f"{self._data[CONF_ACCOUNT_NAME]} ({region_count} regions)",
                data=self._data,
            )

        return self.async_show_form(
            step_id="select_regions",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_REGIONS): cv.multi_select(AWS_REGIONS),
                }
            ),
        )

    async def _test_credentials(self, data: dict[str, Any]) -> None:
        """Test AWS credentials."""
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError

        try:
            session = boto3.Session(
                aws_access_key_id=data[CONF_AWS_ACCESS_KEY_ID],
                aws_secret_access_key=data[CONF_AWS_SECRET_ACCESS_KEY],
                region_name="us-east-1",
            )
            sts = session.client("sts")
            await self.hass.async_add_executor_job(sts.get_caller_identity)
        except (ClientError, NoCredentialsError) as err:
            raise Exception(f"Invalid credentials: {err}") from err

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> AwsInfrastructureOptionsFlow:
        """Get the options flow for this handler."""
        return AwsInfrastructureOptionsFlow(config_entry)


class AwsInfrastructureOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for AWS Infrastructure."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_refresh = self.config_entry.options.get(
            CONF_REFRESH_INTERVAL,
            self.config_entry.data.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL),
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_REFRESH_INTERVAL, default=current_refresh
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_REFRESH_INTERVAL, max=MAX_REFRESH_INTERVAL),
                    ),
                }
            ),
        )
