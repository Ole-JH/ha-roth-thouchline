"""Base entity for the Roth Touchline SL integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import Module, Zone
from .const import DOMAIN, MANUFACTURER
from .coordinator import RothTouchlineCoordinator


class RothZoneEntity(CoordinatorEntity[RothTouchlineCoordinator]):
    """An entity belonging to one zone. Each zone is its own device."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: RothTouchlineCoordinator, udid: str, zone_id: int, key: str
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._udid = udid
        self._zone_id = zone_id
        self._attr_unique_id = f"{udid}_{zone_id}_{key}"
        zone = self.zone
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{udid}_{zone_id}")},
            name=zone.name if zone else f"Zone {zone_id}",
            manufacturer=MANUFACTURER,
            model="Touchline SL zone",
            suggested_area=zone.name if zone else None,
            via_device=(DOMAIN, udid),
        )

    @property
    def module(self) -> Module | None:
        """Return the controller this zone belongs to."""
        return (self.coordinator.data or {}).get(self._udid)

    @property
    def zone(self) -> Zone | None:
        """Return the latest data for this zone."""
        module = self.module
        return module.zones.get(self._zone_id) if module else None

    @property
    def available(self) -> bool:
        """Return whether the zone is reporting."""
        zone = self.zone
        return super().available and zone is not None and zone.available
