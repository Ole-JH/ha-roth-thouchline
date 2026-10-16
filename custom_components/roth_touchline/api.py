"""Client for the Roth Touchline SL cloud API.

Endpoints follow https://api-documentation.roth-touchlinesl.com/. Temperatures
are sent and received as integers in tenths of a degree.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

import aiohttp

from .const import API_URL, REQUEST_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class RothApiError(Exception):
    """Raised when the Roth API returns an unexpected response."""


class RothAuthError(RothApiError):
    """Raised when the Roth API rejects the credentials."""


class RothConnectionError(RothApiError):
    """Raised when the Roth API cannot be reached."""


def _tenths(value: Any) -> float | None:
    """Convert an API temperature in tenths of a degree to degrees."""
    if value is None:
        return None
    try:
        return int(value) / 10
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> int | None:
    try:
        return None if value is None else int(value)
    except (TypeError, ValueError):
        return None


@dataclass(slots=True)
class Zone:
    """A single heating zone (usually a room)."""

    id: int
    name: str
    state: str
    mode: str
    mode_id: int
    schedule_index: int
    current_temperature: float | None
    target_temperature: float | None
    humidity: int | None
    battery_level: int | None
    signal_strength: int | None
    relay_on: bool
    algorithm: str
    window_open: bool
    during_change: bool

    @property
    def registered(self) -> bool:
        """Return whether a thermostat is paired to this zone slot."""
        return self.state != "zoneUnregistered"

    @property
    def enabled(self) -> bool:
        """Return whether the zone is switched on."""
        return self.state not in ("zoneOff", "zoneUnregistered")

    @property
    def available(self) -> bool:
        """Return whether the zone's thermostat is reporting."""
        return self.state not in (
            "noCommunication",
            "sensorDamaged",
            "zoneUnregistered",
        )

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Zone:
        """Build a zone from one element of the module's zone list."""
        zone = data.get("zone") or {}
        description = data.get("description") or {}
        mode = data.get("mode") or {}
        flags = zone.get("flags") or {}

        current = _tenths(zone.get("currentTemperature"))
        # The API reports 0 for zones without a working sensor.
        if current == 0:
            current = None

        humidity = _optional_int(zone.get("humidity"))
        if humidity == 0:
            humidity = None

        return cls(
            id=int(zone["id"]),
            name=str(
                description.get("name") or f"Zone {zone.get('index', zone['id'])}"
            ),
            state=str(zone.get("zoneState", "noAlarm")),
            mode=str(mode.get("mode", "constantTemp")),
            mode_id=int(mode.get("id", 0)),
            schedule_index=int(mode.get("scheduleIndex", 0)),
            current_temperature=current,
            target_temperature=_tenths(zone.get("setTemperature")),
            humidity=humidity,
            battery_level=_optional_int(zone.get("batteryLevel")),
            signal_strength=_optional_int(zone.get("signalStrength")),
            relay_on=flags.get("relayState") == "on",
            algorithm=str(flags.get("algorithm", "heating")),
            window_open=bool(flags.get("minOneWindowOpen", False)),
            during_change=bool(zone.get("duringChange", False)),
        )


@dataclass(slots=True)
class Module:
    """A Touchline SL controller and its zones."""

    udid: str
    name: str
    version: str | None
    zones: dict[int, Zone] = field(default_factory=dict)


class RothTouchlineApi:
    """Async client for a single Roth Touchline SL account."""

    def __init__(
        self, session: aiohttp.ClientSession, username: str, password: str
    ) -> None:
        """Initialize the client."""
        self._session = session
        self._username = username
        self._password = password
        self._token: str | None = None
        self._user_id: int | None = None
        self._login_lock = asyncio.Lock()

    @property
    def user_id(self) -> int | None:
        """Return the account's user id, known after the first login."""
        return self._user_id

    async def login(self) -> int:
        """Log in and return the account's user id."""
        async with self._login_lock:
            data = await self._request(
                "POST",
                "/authentication",
                json={"username": self._username, "password": self._password},
                authenticated=False,
            )
            token = data.get("token") if isinstance(data, dict) else None
            user_id = data.get("user_id") if isinstance(data, dict) else None
            if not token or user_id is None:
                raise RothAuthError("Login response did not contain a token")
            self._token = token
            self._user_id = int(user_id)
            return self._user_id

    async def async_get_modules(self) -> list[dict[str, Any]]:
        """Return the controllers linked to the account."""
        data = await self._authed("GET", "/users/{user_id}/modules")
        if not isinstance(data, list):
            raise RothApiError(f"Unexpected modules response: {data!r}")
        return data

    async def async_get_module(
        self, udid: str, name: str, version: str | None
    ) -> Module:
        """Fetch a controller and all its zones."""
        data = await self._authed("GET", f"/users/{{user_id}}/modules/{udid}")
        if not isinstance(data, dict):
            raise RothApiError(f"Unexpected module response: {data!r}")

        module = Module(udid=udid, name=name, version=version)
        for element in (data.get("zones") or {}).get("elements") or []:
            try:
                zone = Zone.from_api(element)
            except (KeyError, TypeError, ValueError):
                _LOGGER.debug("Skipping malformed zone: %s", element)
                continue
            module.zones[zone.id] = zone
        return module

    async def async_set_zone_temperature(
        self, udid: str, zone: Zone, temperature: float
    ) -> None:
        """Set a constant target temperature on a zone."""
        await self._authed(
            "POST",
            f"/users/{{user_id}}/modules/{udid}/zones",
            json={
                "mode": {
                    "id": zone.mode_id,
                    "parentId": zone.id,
                    "mode": "constantTemp",
                    "constTempTime": 0,
                    "setTemperature": round(temperature * 10),
                    "scheduleIndex": 0,
                }
            },
        )

    async def _authed(self, method: str, path: str, json: Any = None) -> Any:
        """Make an authenticated request, logging in again once if the token expired."""
        if self._token is None:
            await self.login()
        try:
            return await self._request(
                method, path.format(user_id=self._user_id), json=json
            )
        except RothAuthError:
            _LOGGER.debug("Token rejected, logging in again")
            await self.login()
            return await self._request(
                method, path.format(user_id=self._user_id), json=json
            )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        authenticated: bool = True,
    ) -> Any:
        headers = {"Accept": "application/json"}
        if authenticated:
            headers["Authorization"] = f"Bearer {self._token}"

        _LOGGER.debug("%s %s", method, path)
        try:
            async with self._session.request(
                method,
                f"{API_URL}{path}",
                json=json,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as resp:
                try:
                    data = await resp.json(content_type=None)
                except ValueError:
                    data = None

                if resp.status in (401, 403) or (
                    not authenticated and resp.status == 400
                ):
                    raise RothAuthError(f"Authentication failed ({resp.status})")
                if resp.status >= 400:
                    raise RothApiError(f"Roth API returned {resp.status}: {data!r}")
                return data
        except (aiohttp.ClientError, TimeoutError) as err:
            raise RothConnectionError(f"Cannot reach Roth API: {err}") from err
