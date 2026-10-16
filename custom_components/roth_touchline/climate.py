"""Thermostats for Roth Touchline SL zones."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ATTR_TEMPERATURE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import RothApiError
from .const import DOMAIN, MAX_TEMP, MIN_TEMP, TEMP_STEP
from .coordinator import RothTouchlineConfigEntry, RothTouchlineCoordinator
from .entity import RothZoneEntity

PARALLEL_UPDATES = 1

ZONE_MODES = {
    "constantTemp": "constant",
    "globalSchedule": "global_schedule",
    "localSchedule": "local_schedule",
    "timeLimit": "time_limit",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RothTouchlineConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one thermostat per registered zone."""
    coordinator = entry.runtime_data
    async_add_entities(
        RothZoneClimate(coordinator, udid, zone.id)
        for udid, module in coordinator.data.items()
        for zone in module.zones.values()
        if zone.registered
    )


class RothZoneClimate(RothZoneEntity, ClimateEntity):
    """Thermostat for a single zone."""

    _attr_name = None
    _attr_translation_key = "zone"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_min_temp = MIN_TEMP
    _attr_max_temp = MAX_TEMP
    _attr_target_temperature_step = TEMP_STEP

    def __init__(
        self, coordinator: RothTouchlineCoordinator, udid: str, zone_id: int
    ) -> None:
        """Initialize the thermostat."""
        super().__init__(coordinator, udid, zone_id, "climate")

    @property
    def _base_mode(self) -> HVACMode:
        zone = self.zone
        return HVACMode.COOL if zone and zone.algorithm == "cooling" else HVACMode.HEAT

    @property
    def hvac_mode(self) -> HVACMode:
        """Return heat or cool, or off when the zone is switched off."""
        zone = self.zone
        if zone is None or not zone.enabled:
            return HVACMode.OFF
        return self._base_mode

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return the zone's current mode; switching modes is done on the controller."""
        return [self.hvac_mode]

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return whether the zone is calling for heat or cooling right now."""
        zone = self.zone
        if zone is None:
            return None
        if not zone.enabled:
            return HVACAction.OFF
        if not zone.relay_on:
            return HVACAction.IDLE
        return HVACAction.COOLING if zone.algorithm == "cooling" else HVACAction.HEATING

    @property
    def current_temperature(self) -> float | None:
        """Return the room temperature."""
        zone = self.zone
        return zone.current_temperature if zone else None

    @property
    def current_humidity(self) -> float | None:
        """Return the room humidity."""
        zone = self.zone
        return zone.humidity if zone else None

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        zone = self.zone
        return zone.target_temperature if zone else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return how the zone's target is being decided."""
        zone = self.zone
        if zone is None:
            return None
        return {
            "zone_mode": ZONE_MODES.get(zone.mode, zone.mode),
            "window_open": zone.window_open,
        }

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set a constant target temperature."""
        zone = self.zone
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if zone is None or temperature is None:
            return
        try:
            await self.coordinator.async_set_temperature(
                self._udid, zone, float(temperature)
            )
        except RothApiError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="set_temperature_failed",
                translation_placeholders={"error": str(err)},
            ) from err

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Changing heat/cool/off is not available through the Roth cloud API."""
        if hvac_mode != self.hvac_mode:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="hvac_mode_not_supported",
            )
