"""Polling coordinator for the Roth Touchline SL integration."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import Module, RothApiError, RothAuthError, RothTouchlineApi, Zone
from .const import DOMAIN, PENDING_SETPOINT_TIMEOUT, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

type RothTouchlineConfigEntry = ConfigEntry[RothTouchlineCoordinator]


@dataclass(slots=True)
class _PendingSetpoint:
    temperature: float
    expires: float


class RothTouchlineCoordinator(DataUpdateCoordinator[dict[str, Module]]):
    """Fetches every controller on the account on a fixed interval."""

    config_entry: RothTouchlineConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: RothTouchlineConfigEntry,
        api: RothTouchlineApi,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.api = api
        self._modules: list[dict[str, Any]] | None = None
        self._pending: dict[tuple[str, int], _PendingSetpoint] = {}

    async def _async_update_data(self) -> dict[str, Module]:
        try:
            if self._modules is None:
                self._modules = await self.api.async_get_modules()
            modules: dict[str, Module] = {}
            for info in self._modules:
                udid = str(info["udid"])
                modules[udid] = await self.api.async_get_module(
                    udid, str(info.get("name") or udid), info.get("version")
                )
        except RothAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except RothApiError as err:
            raise UpdateFailed(str(err)) from err

        self._apply_pending(modules)
        return modules

    def _apply_pending(self, modules: dict[str, Module]) -> None:
        """Keep showing a just-set target until the cloud reports it or it times out.

        Without this the thermostat card jumps back to the old setpoint for a
        poll or two after every change.
        """
        now = time.monotonic()
        for key, pending in list(self._pending.items()):
            udid, zone_id = key
            module = modules.get(udid)
            zone = module.zones.get(zone_id) if module else None
            if (
                zone is None
                or now > pending.expires
                or (
                    zone.target_temperature is not None
                    and abs(zone.target_temperature - pending.temperature) < 0.05
                    and not zone.during_change
                )
            ):
                del self._pending[key]
                continue
            zone.target_temperature = pending.temperature
            zone.mode = "constantTemp"

    async def async_set_temperature(
        self, udid: str, zone: Zone, temperature: float
    ) -> None:
        """Set a zone's target temperature and update entities right away."""
        try:
            await self.api.async_set_zone_temperature(udid, zone, temperature)
        except RothAuthError as err:
            self.config_entry.async_start_reauth(self.hass)
            raise RothApiError(str(err)) from err

        self._pending[(udid, zone.id)] = _PendingSetpoint(
            temperature, time.monotonic() + PENDING_SETPOINT_TIMEOUT
        )
        if self.data:
            self._apply_pending(self.data)
            self.async_set_updated_data(self.data)
