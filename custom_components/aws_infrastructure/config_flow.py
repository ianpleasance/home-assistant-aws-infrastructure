"""Config flow for AWS Infrastructure integration."""
from __future__ import annotations

import json
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import (
    ALL_SERVICE_KEYS,
    AWS_REGIONS,
    CONF_ACCOUNT_NAME,
    CONF_AWS_ACCESS_KEY_ID,
    CONF_AWS_SECRET_ACCESS_KEY,
    CONF_CREATE_INDIVIDUAL_COUNT_SENSORS,
    CONF_REFRESH_INTERVAL,
    CONF_COST_REFRESH_INTERVAL,
    CONF_REGION_MODE,
    CONF_REGIONS,
    CONF_SERVICES,
    CONF_SKIP_INITIAL_REFRESH,
    DEFAULT_CREATE_INDIVIDUAL_COUNT_SENSORS,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_COST_REFRESH_INTERVAL,
    DEFAULT_SERVICES,
    DEFAULT_SKIP_INITIAL_REFRESH,
    DOMAIN,
    MAX_REFRESH_INTERVAL,
    MIN_REFRESH_INTERVAL,
    REGION_MODE_ALL,
    REGION_MODE_SELECT,
    SELECT_ALL_SERVICES,
    SERVICE_UI_ORDER,
    get_iam_policy,
    get_new_iam_actions,
)

_LOGGER = logging.getLogger(__name__)

# Separator keys — not real services
SEPARATOR_KEYS = {key for key, _ in SERVICE_UI_ORDER if key.startswith("__sep_")}


def _build_service_options() -> dict[str, str]:
    """Build ordered dict of service options for the multi-select UI."""
    options = {SELECT_ALL_SERVICES: "★  Select All Services"}
    for key, label in SERVICE_UI_ORDER:
        if not key.startswith("__sep_"):
            options[key] = label
        else:
            options[key] = label
    return options


SERVICE_OPTIONS = _build_service_options()


def _resolve_services(raw_selection: list[str]) -> set[str]:
    """Resolve raw selection (possibly containing select-all) to actual service keys."""
    if SELECT_ALL_SERVICES in raw_selection:
        return set(ALL_SERVICE_KEYS)
    return {s for s in raw_selection if s not in SEPARATOR_KEYS and s != SELECT_ALL_SERVICES}


class AwsInfrastructureConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AWS Infrastructure."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.data: dict[str, Any] = {}
        self._selected_services: set[str] = set()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the initial step — credentials and basic config."""
        errors = {}

        if user_input is not None:
            try:
                await self._test_credentials(user_input)
            except Exception as err:
                _LOGGER.error("Error validating credentials: %s", err)
                errors["base"] = "invalid_auth"
            else:
                self.data = user_input
                if user_input[CONF_REGION_MODE] == REGION_MODE_SELECT:
                    return await self.async_step_regions()
                return await self.async_step_services()

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
            return await self.async_step_services()

        return self.async_show_form(
            step_id="regions",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_REGIONS): cv.multi_select(AWS_REGIONS),
                }
            ),
        )

    async def async_step_services(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle service selection."""
        if user_input is not None:
            raw = user_input.get(CONF_SERVICES, [])
            self._selected_services = _resolve_services(raw)
            self.data[CONF_SERVICES] = list(self._selected_services)
            return await self.async_step_iam_policy()

        return self.async_show_form(
            step_id="services",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SERVICES,
                        default=list(DEFAULT_SERVICES),
                    ): cv.multi_select(SERVICE_OPTIONS),
                }
            ),
            description_placeholders={
                "info": (
                    "Select the AWS services you want to monitor. "
                    "Only enable services you actually use. "
                    "The next step will show the minimum IAM policy needed."
                )
            },
        )

    async def async_step_iam_policy(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Display the minimum IAM policy for the selected services."""
        if user_input is not None:
            region_mode = self.data.get(CONF_REGION_MODE, REGION_MODE_ALL)
            title_suffix = "(All Regions)" if region_mode == REGION_MODE_ALL else "(Selected Regions)"
            return self.async_create_entry(
                title=f"{self.data[CONF_ACCOUNT_NAME]} {title_suffix}",
                data=self.data,
            )

        policy = get_iam_policy(self._selected_services)
        policy_json = json.dumps(policy, indent=2)

        return self.async_show_form(
            step_id="iam_policy",
            data_schema=vol.Schema({}),
            description_placeholders={
                "policy": policy_json,
                "service_count": str(len(self._selected_services)),
            },
        )

    async def _test_credentials(self, user_input: dict[str, Any]) -> None:
        """Test if the credentials are valid."""
        import boto3
        from botocore.config import Config
        from botocore.exceptions import ClientError, NoCredentialsError, ConnectTimeoutError

        def _verify():
            session = boto3.Session(
                aws_access_key_id=user_input[CONF_AWS_ACCESS_KEY_ID],
                aws_secret_access_key=user_input[CONF_AWS_SECRET_ACCESS_KEY],
                region_name="us-east-1",
            )
            sts = session.client(
                "sts",
                config=Config(connect_timeout=10, read_timeout=15, retries={"max_attempts": 1}),
            )
            try:
                return sts.get_caller_identity()
            except NoCredentialsError as err:
                raise ValueError("Invalid AWS credentials — check your Access Key ID and Secret Access Key") from err
            except ClientError as err:
                code = err.response.get("Error", {}).get("Code", "")
                if code in ("InvalidClientTokenId", "AuthFailure"):
                    raise ValueError("Invalid AWS credentials — check your Access Key ID and Secret Access Key") from err
                if code == "AccessDenied":
                    # Credentials are valid but lack sts:GetCallerIdentity — still usable
                    return {}
                raise ValueError(f"AWS error during credential check: {err}") from err
            except ConnectTimeoutError as err:
                raise ValueError("Timed out connecting to AWS — check your network connection") from err

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
        self._user_input: dict[str, Any] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Manage the options - first step."""
        if user_input is not None:
            self._user_input = user_input
            if user_input.get(CONF_REGION_MODE) == REGION_MODE_SELECT:
                return await self.async_step_select_regions()
            return await self.async_step_select_services()

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
                    vol.Optional(
                        CONF_COST_REFRESH_INTERVAL,
                        default=self._config_entry.options.get(
                            CONF_COST_REFRESH_INTERVAL,
                            DEFAULT_COST_REFRESH_INTERVAL,
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=60, max=1440)),
                    vol.Required(
                        CONF_REGION_MODE,
                        default=current_region_mode,
                    ): vol.In(
                        {
                            REGION_MODE_ALL: "Monitor all AWS regions",
                            REGION_MODE_SELECT: "Select specific regions",
                        }
                    ),
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
            self._user_input[CONF_REGIONS] = user_input[CONF_REGIONS]
            return await self.async_step_select_services()

        current_regions = self._config_entry.data.get(CONF_REGIONS, [])

        return self.async_show_form(
            step_id="select_regions",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_REGIONS,
                        default=current_regions,
                    ): cv.multi_select(AWS_REGIONS),
                }
            ),
        )

    async def async_step_select_services(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Select which services to monitor."""
        # Current services before any change
        old_services = set(
            self._config_entry.data.get(CONF_SERVICES, list(DEFAULT_SERVICES))
        )

        if user_input is not None:
            raw = user_input.get(CONF_SERVICES, [])
            selected = _resolve_services(raw)
            self._user_input[CONF_SERVICES] = list(selected)

            # Calculate any new IAM actions needed
            new_actions = get_new_iam_actions(old_services, selected)
            if new_actions:
                # Store for display in next step
                self._new_iam_actions = new_actions
                return await self.async_step_iam_additions()

            return await self._update_options(self._user_input)

        return self.async_show_form(
            step_id="select_services",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SERVICES,
                        default=list(old_services),
                    ): cv.multi_select(SERVICE_OPTIONS),
                }
            ),
            description_placeholders={
                "info": (
                    "Select the AWS services you want to monitor. "
                    "Removing a service will delete its sensors. "
                    "Adding a service may require updating your IAM policy."
                )
            },
        )

    async def async_step_iam_additions(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Show IAM actions needed for newly added services."""
        if user_input is not None:
            return await self._update_options(self._user_input)

        actions_list = "\n".join(f'  "{a}",' for a in self._new_iam_actions)

        return self.async_show_form(
            step_id="iam_additions",
            data_schema=vol.Schema({}),
            description_placeholders={
                "actions": actions_list,
            },
        )

    async def _update_options(
        self, user_input: dict[str, Any]
    ) -> config_entries.FlowResult:
        """Update the config entry with new options."""
        old_services = set(
            self._config_entry.data.get(CONF_SERVICES, list(DEFAULT_SERVICES))
        )
        old_region_mode = self._config_entry.data.get(CONF_REGION_MODE, REGION_MODE_ALL)
        old_regions = self._config_entry.data.get(CONF_REGIONS, [])

        new_data = {**self._config_entry.data}
        new_data[CONF_REFRESH_INTERVAL] = user_input.get(CONF_REFRESH_INTERVAL)
        new_data[CONF_REGION_MODE] = user_input.get(CONF_REGION_MODE)
        new_data[CONF_CREATE_INDIVIDUAL_COUNT_SENSORS] = user_input.get(
            CONF_CREATE_INDIVIDUAL_COUNT_SENSORS,
            DEFAULT_CREATE_INDIVIDUAL_COUNT_SENSORS,
        )
        new_data[CONF_SERVICES] = user_input.get(CONF_SERVICES, list(DEFAULT_SERVICES))

        if user_input.get(CONF_REGION_MODE) == REGION_MODE_SELECT:
            new_data[CONF_REGIONS] = user_input.get(CONF_REGIONS, [])

        self.hass.config_entries.async_update_entry(
            self._config_entry,
            data=new_data,
        )

        return self.async_create_entry(
            title="",
            data={
                CONF_SKIP_INITIAL_REFRESH: user_input.get(
                    CONF_SKIP_INITIAL_REFRESH, DEFAULT_SKIP_INITIAL_REFRESH
                ),
                "_old_services": list(old_services),
                "_old_region_mode": old_region_mode,
                "_old_regions": old_regions,
            },
        )
