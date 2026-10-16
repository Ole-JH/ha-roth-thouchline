"""The Roth Touchline SL integration."""

from __future__ import annotations

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import RothTouchlineApi
from .const import DOMAIN, MANUFACTURER
from .coordinator import RothTouchlineConfigEntry, RothTouchlineCoordinator

PLATFORMS: list[Platform] = [Platform.CLIMATE, Platform.SENSOR]


async def async_setup_entry(
    hass: HomeAssistant, entry: RothTouchlineConfigEntry
) -> bool:
    """Set up Roth Touchline SL from a config entry."""
    api = RothTouchlineApi(
        async_get_clientsession(hass),
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )
    coordinator = RothTouchlineCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    device_registry = dr.async_get(hass)
    for module in coordinator.data.values():
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, module.udid)},
            name=module.name,
            manufacturer=MANUFACTURER,
            model="Touchline SL controller",
            sw_version=module.version,
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: RothTouchlineConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
