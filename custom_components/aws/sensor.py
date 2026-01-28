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
    COORDINATOR_AUTO_SCALING,
    COORDINATOR_COST,
    COORDINATOR_EC2,
    COORDINATOR_LAMBDA,
    COORDINATOR_LOAD_BALANCER,
    COORDINATOR_RDS,
    DEFAULT_CREATE_INDIVIDUAL_COUNT_SENSORS,
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
    
    # Get configuration option for individual count sensors
    create_count_sensors = entry.data.get(
        CONF_CREATE_INDIVIDUAL_COUNT_SENSORS,
        DEFAULT_CREATE_INDIVIDUAL_COUNT_SENSORS
    )

    sensors: list[SensorEntity] = []

    # 1. ALWAYS: Create region summary sensors
    for region, coordinators in all_coordinators.items():
        sensors.append(AwsRegionSummarySensor(coordinators, account_name, region))
    
    # 2. ALWAYS: Create global summary sensor
    sensors.append(AwsGlobalSummarySensor(hass, account_name, entry.entry_id))
    
    # 3. ALWAYS: Create new graphable cost sensors
    cost_created = False
    for region, coordinators in all_coordinators.items():
        if COORDINATOR_COST in coordinators and not cost_created:
            coordinator = coordinators[COORDINATOR_COST]
            
            # Main graphable cost sensors (NEW)
            sensors.extend([
                AwsCostYesterdaySensor(coordinator, account_name),
                AwsCostMonthToDateSensor(coordinator, account_name),
            ])
            
            # Per-service cost sensors (NEW)
            if coordinator.data and "service_costs" in coordinator.data:
                for service_slug, cost_data in coordinator.data["service_costs"].items():
                    sensors.append(
                        AwsServiceCostSensor(coordinator, account_name, service_slug, cost_data)
                    )
            
            # Legacy cost sensors (backward compatibility)
            sensors.extend([
                AwsCostTodaySensor(coordinator, account_name, region),
                AwsCostMtdSensor(coordinator, account_name, region),
            ])
            
            cost_created = True  # Only create cost sensors once (us-east-1)

    # 4. CONDITIONAL: Create individual count sensors (only if enabled)
    if create_count_sensors:
        for region, coordinators in all_coordinators.items():
            if COORDINATOR_EC2 in coordinators:
                coordinator = coordinators[COORDINATOR_EC2]
                sensors.extend([
                    AwsEc2CountSensor(coordinator, account_name, region, "running"),
                    AwsEc2CountSensor(coordinator, account_name, region, "stopped"),
                ])

            if COORDINATOR_RDS in coordinators:
                coordinator = coordinators[COORDINATOR_RDS]
                sensors.append(AwsRdsCountSensor(coordinator, account_name, region))

            if COORDINATOR_LAMBDA in coordinators:
                coordinator = coordinators[COORDINATOR_LAMBDA]
                sensors.append(AwsLambdaCountSensor(coordinator, account_name, region))

    # 5. ALWAYS: Create individual resource sensors
    for region, coordinators in all_coordinators.items():
        if COORDINATOR_EC2 in coordinators:
            coordinator = coordinators[COORDINATOR_EC2]
            if coordinator.data and "instances" in coordinator.data:
                for instance_id in coordinator.data["instances"].keys():
                    sensors.append(
                        AwsEc2InstanceSensor(coordinator, account_name, region, instance_id)
                    )

        if COORDINATOR_RDS in coordinators:
            coordinator = coordinators[COORDINATOR_RDS]
            if coordinator.data and "instances" in coordinator.data:
                for db_id in coordinator.data["instances"].keys():
                    sensors.append(
                        AwsRdsInstanceSensor(coordinator, account_name, region, db_id)
                    )

        if COORDINATOR_LAMBDA in coordinators:
            coordinator = coordinators[COORDINATOR_LAMBDA]
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


# ============================================================================
# NEW SENSORS - Region & Global Summaries
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
        """Return the total resource count."""
        total = 0
        
        # Count EC2 instances
        if COORDINATOR_EC2 in self._coordinators:
            ec2_data = self._coordinators[COORDINATOR_EC2].data
            if ec2_data and "instances" in ec2_data:
                total += len(ec2_data["instances"])
        
        # Count RDS instances
        if COORDINATOR_RDS in self._coordinators:
            rds_data = self._coordinators[COORDINATOR_RDS].data
            if rds_data and "instances" in rds_data:
                total += len(rds_data["instances"])
        
        # Count Lambda functions
        if COORDINATOR_LAMBDA in self._coordinators:
            lambda_data = self._coordinators[COORDINATOR_LAMBDA].data
            if lambda_data and "functions" in lambda_data:
                total += len(lambda_data["functions"])
        
        # Count Load Balancers
        if COORDINATOR_LOAD_BALANCER in self._coordinators:
            lb_data = self._coordinators[COORDINATOR_LOAD_BALANCER].data
            if lb_data and "load_balancers" in lb_data:
                total += len(lb_data["load_balancers"])
        
        # Count Auto Scaling Groups
        if COORDINATOR_AUTO_SCALING in self._coordinators:
            asg_data = self._coordinators[COORDINATOR_AUTO_SCALING].data
            if asg_data and "auto_scaling_groups" in asg_data:
                total += len(asg_data["auto_scaling_groups"])
        
        return total

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return detailed resource counts."""
        attrs = {
            "region": self._region,
            "account_name": self._account_name,
        }
        
        # EC2 counts
        if COORDINATOR_EC2 in self._coordinators:
            ec2_data = self._coordinators[COORDINATOR_EC2].data
            if ec2_data and "instances" in ec2_data:
                instances = ec2_data["instances"]
                attrs["ec2_total"] = len(instances)
                attrs["ec2_running"] = sum(
                    1 for i in instances.values() if i.get("state") == "running"
                )
                attrs["ec2_stopped"] = sum(
                    1 for i in instances.values() if i.get("state") == "stopped"
                )
        
        # RDS counts
        if COORDINATOR_RDS in self._coordinators:
            rds_data = self._coordinators[COORDINATOR_RDS].data
            if rds_data and "instances" in rds_data:
                attrs["rds_instances"] = len(rds_data["instances"])
        
        # Lambda counts
        if COORDINATOR_LAMBDA in self._coordinators:
            lambda_data = self._coordinators[COORDINATOR_LAMBDA].data
            if lambda_data and "functions" in lambda_data:
                attrs["lambda_functions"] = len(lambda_data["functions"])
        
        # Load Balancer counts
        if COORDINATOR_LOAD_BALANCER in self._coordinators:
            lb_data = self._coordinators[COORDINATOR_LOAD_BALANCER].data
            if lb_data and "load_balancers" in lb_data:
                attrs["load_balancers"] = len(lb_data["load_balancers"])
        
        # Auto Scaling Group counts
        if COORDINATOR_AUTO_SCALING in self._coordinators:
            asg_data = self._coordinators[COORDINATOR_AUTO_SCALING].data
            if asg_data and "auto_scaling_groups" in asg_data:
                attrs["auto_scaling_groups"] = len(asg_data["auto_scaling_groups"])
        
        return attrs


class AwsGlobalSummarySensor(SensorEntity):
    """Sensor that summarizes all resources across all regions."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_should_poll = True

    def __init__(
        self,
        hass: HomeAssistant,
        account_name: str,
        entry_id: str,
    ) -> None:
        """Initialize the sensor."""
        self._hass = hass
        self._account_name = account_name
        self._entry_id = entry_id
        self._cached_value = 0
        self._cached_attrs = {}
        
        self._attr_unique_id = f"aws_{account_name.lower()}_global_summary"
        self._attr_name = "global summary"
        self._attr_icon = "mdi:aws"
        
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_global")},
            "name": f"AWS {account_name} (Global)",
            "manufacturer": "Amazon Web Services",
            "model": "Global",
            "entry_type": "service",
        }

    async def async_update(self) -> None:
        """Update the sensor by aggregating region sensors."""
        total = 0
        attrs = {
            "account_name": self._account_name,
            "active_regions": 0,
            "ec2_total": 0,
            "ec2_running": 0,
            "ec2_stopped": 0,
            "rds_instances": 0,
            "lambda_functions": 0,
            "load_balancers": 0,
            "auto_scaling_groups": 0,
            "regions": {},
        }
        
        # Get all states asynchronously
        account_lower = self._account_name.lower()
        all_states = self._hass.states.async_all()
        
        for state in all_states:
            if (
                state.entity_id.startswith(f"sensor.aws_{account_lower}_")
                and state.entity_id.endswith("_summary")
                and "global" not in state.entity_id
            ):
                # Sum totals
                try:
                    if state.state not in ["unavailable", "unknown", "none"]:
                        total += int(state.state)
                except (ValueError, TypeError):
                    pass
                
                # Aggregate attributes
                region_attrs = state.attributes
                region_name = region_attrs.get("region", "unknown")
                
                # Count active regions
                try:
                    if state.state not in ["unavailable", "unknown", "none"] and int(state.state) > 0:
                        attrs["active_regions"] += 1
                except (ValueError, TypeError):
                    pass
                
                # Aggregate counts
                attrs["ec2_total"] += region_attrs.get("ec2_total", 0)
                attrs["ec2_running"] += region_attrs.get("ec2_running", 0)
                attrs["ec2_stopped"] += region_attrs.get("ec2_stopped", 0)
                attrs["rds_instances"] += region_attrs.get("rds_instances", 0)
                attrs["lambda_functions"] += region_attrs.get("lambda_functions", 0)
                attrs["load_balancers"] += region_attrs.get("load_balancers", 0)
                attrs["auto_scaling_groups"] += region_attrs.get("auto_scaling_groups", 0)
                
                # Store per-region breakdown
                try:
                    region_total = int(state.state) if state.state not in ["unavailable", "unknown", "none"] else 0
                except (ValueError, TypeError):
                    region_total = 0
                    
                attrs["regions"][region_name] = {
                    "total": region_total,
                    "ec2_running": region_attrs.get("ec2_running", 0),
                    "lambda_functions": region_attrs.get("lambda_functions", 0),
                    "rds_instances": region_attrs.get("rds_instances", 0),
                }
        
        self._cached_value = total
        self._cached_attrs = attrs

    @property
    def native_value(self) -> int:
        """Return total resources across all regions."""
        return self._cached_value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return aggregated counts."""
        return self._cached_attrs


# ============================================================================
# NEW SENSORS - Graphable Cost Sensors
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
        if results:
            amount = results[0]["Total"]["UnblendedCost"]["Amount"]
            return round(float(amount), 2)
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
        if results:
            amount = results[0]["Total"]["UnblendedCost"]["Amount"]
            return round(float(amount), 2)
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
        if results:
            amount = results[0]["Total"]["UnblendedCost"]["Amount"]
            return round(float(amount), 2)
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
        if results:
            amount = results[0]["Total"]["UnblendedCost"]["Amount"]
            return round(float(amount), 2)
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
        instance_id_normalized = instance_id.replace("-", "_")
        self._attr_unique_id = (
            f"aws_{account_name}_{region_normalized}_ec2_{instance_id_normalized}_state"
        )
        self._attr_name = f"ec2 {instance_id} state"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

    @property
    def native_value(self) -> str | None:
        """Return the instance state."""
        if not self.coordinator.data or "instances" not in self.coordinator.data:
            return None

        instance = self.coordinator.data["instances"].get(self._instance_id)
        if instance:
            return instance["state"]
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return instance details."""
        if not self.coordinator.data or "instances" not in self.coordinator.data:
            return {}

        instance = self.coordinator.data["instances"].get(self._instance_id)
        if not instance:
            return {}

        return {
            "instance_id": self._instance_id,
            "instance_type": instance.get("instance_type"),
            "private_ip": instance.get("private_ip"),
            "public_ip": instance.get("public_ip"),
            "launch_time": instance.get("launch_time"),
            "tags": instance.get("tags", {}),
            "volumes": instance.get("volumes", []),
        }


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
        db_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._account_name = account_name
        self._region = region
        self._db_id = db_id

        region_normalized = region.replace("-", "_")
        db_id_normalized = db_id.replace("-", "_")
        self._attr_unique_id = (
            f"aws_{account_name}_{region_normalized}_rds_{db_id_normalized}_status"
        )
        self._attr_name = f"rds {db_id} status"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

    @property
    def native_value(self) -> str | None:
        """Return the instance status."""
        if not self.coordinator.data or "instances" not in self.coordinator.data:
            return None

        instance = self.coordinator.data["instances"].get(self._db_id)
        if instance:
            return instance["status"]
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return instance details."""
        if not self.coordinator.data or "instances" not in self.coordinator.data:
            return {}

        instance = self.coordinator.data["instances"].get(self._db_id)
        if not instance:
            return {}

        return {
            "db_instance_identifier": self._db_id,
            "engine": instance.get("engine"),
            "engine_version": instance.get("engine_version"),
            "instance_class": instance.get("instance_class"),
            "allocated_storage": instance.get("allocated_storage"),
            "multi_az": instance.get("multi_az"),
            "endpoint": instance.get("endpoint"),
            "port": instance.get("port"),
        }


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
        function_name_normalized = function_name.replace("-", "_")
        self._attr_unique_id = (
            f"aws_{account_name}_{region_normalized}_lambda_{function_name_normalized}_state"
        )
        self._attr_name = f"lambda {function_name} state"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

    @property
    def native_value(self) -> str | None:
        """Return the function state."""
        if not self.coordinator.data or "functions" not in self.coordinator.data:
            return None

        function = self.coordinator.data["functions"].get(self._function_name)
        if function:
            return function["state"]
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return function details."""
        if not self.coordinator.data or "functions" not in self.coordinator.data:
            return {}

        function = self.coordinator.data["functions"].get(self._function_name)
        if not function:
            return {}

        return {
            "function_name": self._function_name,
            "runtime": function.get("runtime"),
            "handler": function.get("handler"),
            "memory_size": function.get("memory_size"),
            "timeout": function.get("timeout"),
            "code_size": function.get("code_size"),
            "last_modified": function.get("last_modified"),
        }


# ============================================================================
# EXISTING SENSORS - Load Balancer
# ============================================================================


class AwsLoadBalancerSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Load Balancer."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:shuffle-variant"

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
        lb_name_normalized = lb_name.replace("-", "_")
        self._attr_unique_id = (
            f"aws_{account_name}_{region_normalized}_lb_{lb_name_normalized}_state"
        )
        self._attr_name = f"lb {lb_name} state"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

    @property
    def native_value(self) -> str | None:
        """Return the load balancer state."""
        if not self.coordinator.data or "load_balancers" not in self.coordinator.data:
            return None

        lb = self.coordinator.data["load_balancers"].get(self._lb_name)
        if lb:
            return lb["state"]
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return load balancer details."""
        if not self.coordinator.data or "load_balancers" not in self.coordinator.data:
            return {}

        lb = self.coordinator.data["load_balancers"].get(self._lb_name)
        if not lb:
            return {}

        return {
            "load_balancer_name": self._lb_name,
            "type": lb.get("type"),
            "scheme": lb.get("scheme"),
            "dns_name": lb.get("dns_name"),
            "vpc_id": lb.get("vpc_id"),
            "availability_zones": lb.get("availability_zones", []),
            "created_time": lb.get("created_time"),
        }


# ============================================================================
# EXISTING SENSORS - Auto Scaling Group
# ============================================================================


class AwsAsgSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Auto Scaling Group."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_icon = "mdi:chart-line"
    _attr_state_class = SensorStateClass.MEASUREMENT

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
        asg_name_normalized = asg_name.replace("-", "_")
        self._attr_unique_id = (
            f"aws_{account_name}_{region_normalized}_asg_{asg_name_normalized}_instances"
        )
        self._attr_name = f"asg {asg_name} instances"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{account_name}_{region}")},
            "name": f"AWS {account_name} ({region})",
            "manufacturer": "Amazon Web Services",
            "model": region,
            "entry_type": "service",
        }

    @property
    def native_value(self) -> int | None:
        """Return the instance count."""
        if not self.coordinator.data or "auto_scaling_groups" not in self.coordinator.data:
            return None

        asg = self.coordinator.data["auto_scaling_groups"].get(self._asg_name)
        if asg:
            return asg["instances"]
        return None

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return "instances"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return ASG details."""
        if not self.coordinator.data or "auto_scaling_groups" not in self.coordinator.data:
            return {}

        asg = self.coordinator.data["auto_scaling_groups"].get(self._asg_name)
        if not asg:
            return {}

        return {
            "asg_name": self._asg_name,
            "desired_capacity": asg.get("desired_capacity"),
            "min_size": asg.get("min_size"),
            "max_size": asg.get("max_size"),
            "healthy_instances": asg.get("healthy_instances"),
            "availability_zones": asg.get("availability_zones", []),
        }
