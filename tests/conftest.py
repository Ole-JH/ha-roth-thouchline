"""Fixtures for Roth Touchline SL tests."""

from __future__ import annotations

import copy
from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.roth_touchline.const import API_URL, DOMAIN

USER_ID = 1234
UDID = "abc123"


def zone(
    zone_id: int,
    name: str,
    *,
    state: str = "noAlarm",
    current: int | None = 215,
    target: int = 220,
    humidity: int = 45,
    relay: str = "on",
    mode: str = "constantTemp",
) -> dict[str, Any]:
    """Return one zone element as the Roth API sends it."""
    return {
        "zone": {
            "id": zone_id,
            "parentId": 1,
            "time": "0",
            "duringChange": False,
            "index": zone_id,
            "currentTemperature": current,
            "setTemperature": target,
            "flags": {
                "relayState": relay,
                "minOneWindowOpen": False,
                "algorithm": "heating",
                "floorSensor": 0,
                "humidityAlgorytm": 0,
                "zoneExcluded": 0,
            },
            "zoneState": state,
            "signalStrength": 80,
            "batteryLevel": 90,
            "actuatorsOpen": 1,
            "humidity": humidity,
            "visibility": True,
        },
        "description": {
            "id": zone_id,
            "parentId": zone_id,
            "name": name,
            "styleId": 0,
            "styleIcon": "",
            "duringChange": False,
        },
        "mode": {
            "id": 100 + zone_id,
            "parentId": zone_id,
            "mode": mode,
            "constTempTime": 0,
            "setTemperature": target,
            "scheduleIndex": 0,
        },
        "schedule": {},
        "actuators": [],
        "underfloor": {},
        "windowsSensors": [],
        "additionalContacts": [],
    }


MODULE = {
    "zones": {
        "transaction_time": "0",
        "elements": [
            zone(1, "Living room"),
            zone(2, "Bedroom", relay="off", mode="globalSchedule"),
            zone(3, "", state="zoneUnregistered", current=None, humidity=0),
        ],
        "globalSchedules": {"time": "0", "duringChange": False, "elements": []},
        "controllerParameters": {},
    },
    "tiles": [],
}

MODULES = [
    {
        "id": 1,
        "default": True,
        "name": "Home",
        "email": "a@b.c",
        "type": "sl",
        "udid": UDID,
        "version": "1.2",
    }
]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading the custom integration."""
    yield


@pytest.fixture
def module_data() -> dict[str, Any]:
    """Return a mutable copy of the module response."""
    return copy.deepcopy(MODULE)


@pytest.fixture
def mock_api(aioclient_mock: AiohttpClientMocker, module_data) -> AiohttpClientMocker:
    """Mock a working Roth cloud."""
    aioclient_mock.post(
        f"{API_URL}/authentication", json={"user_id": USER_ID, "token": "tok"}
    )
    aioclient_mock.get(f"{API_URL}/users/{USER_ID}/modules", json=MODULES)
    aioclient_mock.get(f"{API_URL}/users/{USER_ID}/modules/{UDID}", json=module_data)
    aioclient_mock.post(f"{API_URL}/users/{USER_ID}/modules/{UDID}/zones", json={})
    return aioclient_mock


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Return a config entry for the test account."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="a@b.c",
        unique_id=str(USER_ID),
        data={"username": "a@b.c", "password": "secret"},
    )
