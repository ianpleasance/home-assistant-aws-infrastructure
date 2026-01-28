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
    CONF_SKIP_INITIAL_REFRESH,
    DEFAULT_CREATE_INDIVIDUAL_COUNT_SENSORS,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_SKIP_INITIAL_REFRESH,
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
                    vol.Optional(
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
        
        def _verify():
            session = boto3.Session(
                aws_access_key_id=user_input[CONF_AWS_ACCESS_KEY_ID],
                aws_secret_access_key=user_input[CONF_AWS_SECRET_ACCESS_KEY],
                region_name="us-east-1",
            )
            sts = session.client("sts")
            return sts.get_caller_identity()
        
        await self.hass.async_add_executor_job(_verify)

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
        self._config_entry = config_entry
        self._user_input = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Manage the options - first step."""
        if user_input is not None:
            self._user_input = user_input
            
            # If user selected specific regions, go to region selection
            if user_input.get(CONF_REGION_MODE) == REGION_MODE_SELECT:
                return await self.async_step_select_regions()
            
            # Otherwise, save and finish
            return await self._update_options(user_input)

        # Get current settings
        current_region_mode = self._config_entry.data.get(CONF_REGION_MODE, REGION_MODE_ALL)
        
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_REFRESH_INTERVAL,
                        default=self._config_entry.data.get(
                            CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_REFRESH_INTERVAL, max=MAX_REFRESH_INTERVAL),
                    ),
                    vol.Required(
                        CONF_REGION_MODE,
                        default=current_region_mode,
                    ): vol.In({
                        REGION_MODE_ALL: "Monitor all AWS regions",
                        REGION_MODE_SELECT: "Select specific regions"
                    }),
                    vol.Optional(
                        CONF_CREATE_INDIVIDUAL_COUNT_SENSORS,
                        default=self._config_entry.data.get(
                            CONF_CREATE_INDIVIDUAL_COUNT_SENSORS,
                            DEFAULT_CREATE_INDIVIDUAL_COUNT_SENSORS,
                        ),
                    ): bool,
                    vol.Optional(
                        CONF_SKIP_INITIAL_REFRESH,
                        default=self._config_entry.options.get(
                            CONF_SKIP_INITIAL_REFRESH, DEFAULT_SKIP_INITIAL_REFRESH
                        ),
                    ): bool,
                }
            ),
        )
    
    async def async_step_select_regions(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Select specific regions to monitor."""
        if user_input is not None:
            # Merge with previous input
            self._user_input[CONF_REGIONS] = user_input[CONF_REGIONS]
            return await self._update_options(self._user_input)
        
        # Get current regions
        current_regions = self._config_entry.data.get(CONF_REGIONS, [])
        
        return self.async_show_form(
            step_id="select_regions",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_REGIONS,
                    default=current_regions,
                ): cv.multi_select(AWS_REGIONS),
            }),
        )
    
    async def _update_options(self, user_input: dict[str, Any]) -> config_entries.FlowResult:
        """Update the config entry with new options."""
        # Store old regions BEFORE updating (for cleanup)
        old_region_mode = self._config_entry.data.get(CONF_REGION_MODE, REGION_MODE_ALL)
        old_regions = self._config_entry.data.get(CONF_REGIONS, [])
        
        # Update the config entry data with new values
        new_data = {**self._config_entry.data}
        new_data[CONF_REFRESH_INTERVAL] = user_input.get(CONF_REFRESH_INTERVAL)
        new_data[CONF_REGION_MODE] = user_input.get(CONF_REGION_MODE)
        new_data[CONF_CREATE_INDIVIDUAL_COUNT_SENSORS] = user_input.get(
            CONF_CREATE_INDIVIDUAL_COUNT_SENSORS,
            DEFAULT_CREATE_INDIVIDUAL_COUNT_SENSORS
        )
        
        # Only update regions if in select mode
        if user_input.get(CONF_REGION_MODE) == REGION_MODE_SELECT:
            new_data[CONF_REGIONS] = user_input.get(CONF_REGIONS, [])
        
        # Update entry data
        self.hass.config_entries.async_update_entry(
            self._config_entry,
            data=new_data,
        )
        
        # Save options with old region info for cleanup
        return self.async_create_entry(
            title="",
            data={
                CONF_SKIP_INITIAL_REFRESH: user_input.get(
                    CONF_SKIP_INITIAL_REFRESH, DEFAULT_SKIP_INITIAL_REFRESH
                ),
                "_old_region_mode": old_region_mode,
                "_old_regions": old_regions,
            }
        )
