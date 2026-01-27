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
    COORDINATOR_AUTO_SCALING,
    COORDINATOR_COST,
    COORDINATOR_EC2,
    COORDINATOR_LAMBDA,
    COORDINATOR_LOAD_BALANCER,
    COORDINATOR_RDS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AWS Infrastructure sensors."""
    data = hass.data[DOMAIN][entry.entry_id]
    account_name = data[CONF_ACCOUNT_NAME]
    all_coordinators = data["coordinators"]

    sensors: list[SensorEntity] = []

    for region, coordinators in all_coordinators.items():
        if COORDINATOR_COST in coordinators:
            coordinator = coordinators[COORDINATOR_COST]
            sensors.extend(
                [
                    AwsCostTodaySensor(coordinator, account_name, region),
                    AwsCostMtdSensor(coordinator, account_name, region),
                ]
            )

        if COORDINATOR_EC2 in coordinators:
            coordinator = coordinators[COORDINATOR_EC2]
            sensors.extend(
                [
                    AwsEc2CountSensor(coordinator, account_name, region, "running"),
                    AwsEc2CountSensor(coordinator, account_name, region, "stopped"),
                ]
            )

            if coordinator.data and "instances" in coordinator.data:
                for instance_id in coordinator.data["instances"].keys():
                    sensors.append(
                        AwsEc2InstanceSensor(coordinator, account_name, region, instance_id)
                    )

        if COORDINATOR_RDS in coordinators:
            coordinator = coordinators[COORDINATOR_RDS]
            sensors.append(AwsRdsCountSensor(coordinator, account_name, region))

            if coordinator.data and "instances" in coordinator.data:
                for db_id in coordinator.data["instances"].keys():
                    sensors.append(
                        AwsRdsInstanceSensor(coordinator, account_name, region, db_id)
                    )

        if COORDINATOR_LAMBDA in coordinators:
            coordinator = coordinators[COORDINATOR_LAMBDA]
            sensors.append(AwsLambdaCountSensor(coordinator, account_name, region))

            if coordinator.data and "functions" in coordinator.data:
                for function_name in coordinator.data["functions"].keys():
                    sensors.append(
                        AwsLambdaFunctionSensor(
                            coordinator, account_name, region, function_name
                        )
                    )

        if COORDINATOR_LOAD_BALANCER in coordinators:
            coordinator = coordinators[COORDINATOR_LOAD_BALANCER]

            if coordinator.data and "load_balancers" in coordinator.data:
                for lb_name in coordinator.data["load_balancers"].keys():
                    sensors.append(
                        AwsLoadBalancerSensor(
                            coordinator, account_name, region, lb_name
                        )
                    )

        if COORDINATOR_AUTO_SCALING in coordinators:
            coordinator = coordinators[COORDINATOR_AUTO_SCALING]

            if coordinator.data and "auto_scaling_groups" in coordinator.data:
                for asg_name in coordinator.data["auto_scaling_groups"].keys():
                    sensors.append(
                        AwsAsgSensor(coordinator, account_name, region, asg_name)
                    )

    async_add_entities(sensors)


class AwsBaseSensor(CoordinatorEntity, SensorEntity):
    """Base AWS sensor."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        account_name: str,
        region: str,
        resource_name: str,
        sensor_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._resource_name = resource_name
        self._sensor_type = sensor_type

        region_normalized = region.replace("-", "_")

        # SHORTENED entity_id format: aws_{account}_{region}_{resource}_{type}
        self._attr_unique_id = (
            f"aws_{account_name}_{region_normalized}_{resource_name}_{sensor_type}"
        )
        self._attr_name = f"{resource_name} {sensor_type}"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {
            "region": self._region,
            "account_name": self._account_name,
        }


class AwsCostTodaySensor(AwsBaseSensor):
    """Sensor for today's AWS cost."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = "USD"

    def __init__(self, coordinator, account_name: str, region: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, account_name, region, "cost", "today")

    @property
    def native_value(self) -> float | None:
        """Return the state."""
        if not self.coordinator.data or "cost_yesterday" not in self.coordinator.data:
            return None

        try:
            results = self.coordinator.data["cost_yesterday"].get("ResultsByTime", [])
            if results:
                amount = results[0].get("Total", {}).get("UnblendedCost", {}).get("Amount", "0")
                return round(float(amount), 2)
        except (KeyError, ValueError, IndexError):
            pass

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        attrs = super().extra_state_attributes

        if self.coordinator.data and "cost_yesterday" in self.coordinator.data:
            try:
                results = self.coordinator.data["cost_yesterday"].get("ResultsByTime", [])
                if results and "Groups" in results[0]:
                    services = {}
                    for group in results[0]["Groups"]:
                        service = group["Keys"][0]
                        amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
                        if amount > 0:
                            services[service] = round(amount, 2)

                    sorted_services = dict(
                        sorted(services.items(), key=lambda x: x[1], reverse=True)[:10]
                    )
                    attrs["service_breakdown"] = sorted_services
            except (KeyError, ValueError):
                pass

        return attrs


class AwsCostMtdSensor(AwsBaseSensor):
    """Sensor for month-to-date AWS cost."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = "USD"

    def __init__(self, coordinator, account_name: str, region: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, account_name, region, "cost", "mtd")

    @property
    def native_value(self) -> float | None:
        """Return the state."""
        if not self.coordinator.data or "cost_mtd" not in self.coordinator.data:
            return None

        try:
            results = self.coordinator.data["cost_mtd"].get("ResultsByTime", [])
            if results:
                amount = results[0].get("Total", {}).get("UnblendedCost", {}).get("Amount", "0")
                return round(float(amount), 2)
        except (KeyError, ValueError, IndexError):
            pass

        return None


class AwsEc2CountSensor(AwsBaseSensor):
    """Sensor for EC2 instance count by state."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, coordinator, account_name: str, region: str, state: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator, account_name, region, f"ec2_instances", state
        )
        self._state_filter = state
        self._attr_icon = "mdi:server"

    @property
    def native_value(self) -> int:
        """Return the state."""
        if not self.coordinator.data or "instances" not in self.coordinator.data:
            return 0

        count = sum(
            1
            for instance in self.coordinator.data["instances"].values()
            if instance.get("state") == self._state_filter
        )
        return count


class AwsEc2InstanceSensor(AwsBaseSensor):
    """Sensor for individual EC2 instance."""

    def __init__(
        self, coordinator, account_name: str, region: str, instance_id: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator, account_name, region, f"ec2_{instance_id}", "state"
        )
        self._instance_id = instance_id
        self._attr_icon = "mdi:server"

    @property
    def native_value(self) -> str:
        """Return the state."""
        if not self.coordinator.data or "instances" not in self.coordinator.data:
            return "unknown"

        instance = self.coordinator.data["instances"].get(self._instance_id, {})
        return instance.get("state", "unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        attrs = super().extra_state_attributes

        if self.coordinator.data and "instances" in self.coordinator.data:
            instance = self.coordinator.data["instances"].get(self._instance_id, {})
            attrs.update(
                {
                    "instance_type": instance.get("instance_type"),
                    "launch_time": instance.get("launch_time"),
                    "private_ip": instance.get("private_ip"),
                    "public_ip": instance.get("public_ip"),
                    "tags": instance.get("tags", {}),
                    "volumes": instance.get("volumes", []),
                }
            )

        return attrs


class AwsRdsCountSensor(AwsBaseSensor):
    """Sensor for RDS instance count."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, account_name: str, region: str) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator, account_name, region, "rds", "total_instances"
        )
        self._attr_icon = "mdi:database"

    @property
    def native_value(self) -> int:
        """Return the state."""
        if not self.coordinator.data or "instances" not in self.coordinator.data:
            return 0

        return len(self.coordinator.data["instances"])


class AwsRdsInstanceSensor(AwsBaseSensor):
    """Sensor for individual RDS instance."""

    def __init__(
        self, coordinator, account_name: str, region: str, db_id: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, account_name, region, f"rds_{db_id}", "status")
        self._db_id = db_id
        self._attr_icon = "mdi:database"

    @property
    def native_value(self) -> str:
        """Return the state."""
        if not self.coordinator.data or "instances" not in self.coordinator.data:
            return "unknown"

        instance = self.coordinator.data["instances"].get(self._db_id, {})
        return instance.get("status", "unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        attrs = super().extra_state_attributes

        if self.coordinator.data and "instances" in self.coordinator.data:
            instance = self.coordinator.data["instances"].get(self._db_id, {})
            attrs.update(instance)

        return attrs


class AwsLambdaCountSensor(AwsBaseSensor):
    """Sensor for Lambda function count."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, account_name: str, region: str) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator, account_name, region, "lambda", "total_functions"
        )
        self._attr_icon = "mdi:lambda"

    @property
    def native_value(self) -> int:
        """Return the state."""
        if not self.coordinator.data or "functions" not in self.coordinator.data:
            return 0

        return len(self.coordinator.data["functions"])


class AwsLambdaFunctionSensor(AwsBaseSensor):
    """Sensor for individual Lambda function."""

    def __init__(
        self, coordinator, account_name: str, region: str, function_name: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator, account_name, region, f"lambda_{function_name}", "state"
        )
        self._function_name = function_name
        self._attr_icon = "mdi:lambda"

    @property
    def native_value(self) -> str:
        """Return the state."""
        if not self.coordinator.data or "functions" not in self.coordinator.data:
            return "unknown"

        function = self.coordinator.data["functions"].get(self._function_name, {})
        return function.get("state", "Active")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        attrs = super().extra_state_attributes

        if self.coordinator.data and "functions" in self.coordinator.data:
            function = self.coordinator.data["functions"].get(self._function_name, {})
            attrs.update(function)

        return attrs


class AwsLoadBalancerSensor(AwsBaseSensor):
    """Sensor for Load Balancer."""

    def __init__(
        self, coordinator, account_name: str, region: str, lb_name: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator, account_name, region, f"lb_{lb_name}", "state"
        )
        self._lb_name = lb_name
        self._attr_icon = "mdi:scale-balance"

    @property
    def native_value(self) -> str:
        """Return the state."""
        if not self.coordinator.data or "load_balancers" not in self.coordinator.data:
            return "unknown"

        lb = self.coordinator.data["load_balancers"].get(self._lb_name, {})
        return lb.get("state", "unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        attrs = super().extra_state_attributes

        if self.coordinator.data and "load_balancers" in self.coordinator.data:
            lb = self.coordinator.data["load_balancers"].get(self._lb_name, {})
            attrs.update(lb)

        return attrs


class AwsAsgSensor(AwsBaseSensor):
    """Sensor for Auto Scaling Group."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, coordinator, account_name: str, region: str, asg_name: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator, account_name, region, f"asg_{asg_name}", "instances"
        )
        self._asg_name = asg_name
        self._attr_icon = "mdi:server-network"

    @property
    def native_value(self) -> int:
        """Return the state."""
        if (
            not self.coordinator.data
            or "auto_scaling_groups" not in self.coordinator.data
        ):
            return 0

        asg = self.coordinator.data["auto_scaling_groups"].get(self._asg_name, {})
        return asg.get("instances", 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        attrs = super().extra_state_attributes

        if self.coordinator.data and "auto_scaling_groups" in self.coordinator.data:
            asg = self.coordinator.data["auto_scaling_groups"].get(self._asg_name, {})
            attrs.update(asg)

        return attrs
