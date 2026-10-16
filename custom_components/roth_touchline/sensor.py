"""Sensors for Roth Touchline SL zones."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import Zone
from .coordinator import RothTouchlineConfigEntry, RothTouchlineCoordinator
from .entity import RothZoneEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class RothSensorDescription(SensorEntityDescription):
    """Describes a zone sensor."""

    value_fn: Callable[[Zone], float | int | None]


SENSORS: tuple[RothSensorDescription, ...] = (
    RothSensorDescription(
        key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        value_fn=lambda zone: zone.current_temperature,
    ),
    RothSensorDescription(
        key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda zone: zone.humidity,
    ),
    RothSensorDescription(
        key="battery",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda zone: zone.battery_level,
    ),
    RothSensorDescription(
        key="signal_strength",
        translation_key="signal_strength",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda zone: zone.signal_strength,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RothTouchlineConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors each zone actually reports."""
    coordinator = entry.runtime_data
    async_add_entities(
        RothZoneSensor(coordinator, udid, zone.id, description)
        for udid, module in coordinator.data.items()
        for zone in module.zones.values()
        if zone.registered
        for description in SENSORS
        if description.value_fn(zone) is not None
    )


class RothZoneSensor(RothZoneEntity, SensorEntity):
    """A single measurement from a zone."""

    entity_description: RothSensorDescription

    def __init__(
        self,
        coordinator: RothTouchlineCoordinator,
        udid: str,
        zone_id: int,
        description: RothSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, udid, zone_id, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | int | None:
        """Return the sensor value."""
        zone = self.zone
        return self.entity_description.value_fn(zone) if zone else None
