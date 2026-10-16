"""Tests for setup, entities and setting temperatures."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.components.climate import HVACAction, HVACMode
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
    AiohttpClientMockResponse,
)

from custom_components.roth_touchline.const import API_URL

from .conftest import UDID, USER_ID


async def _setup(hass: HomeAssistant, config_entry) -> None:
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


async def test_entities(hass: HomeAssistant, mock_api, config_entry) -> None:
    """Each registered zone gets a thermostat and sensors."""
    await _setup(hass, config_entry)
    assert config_entry.state is ConfigEntryState.LOADED

    living = hass.states.get("climate.living_room")
    assert living.state == HVACMode.HEAT
    assert living.attributes["current_temperature"] == 21.5
    assert living.attributes["temperature"] == 22.0
    assert living.attributes["current_humidity"] == 45
    assert living.attributes["hvac_action"] == HVACAction.HEATING
    assert living.attributes["zone_mode"] == "constant"

    bedroom = hass.states.get("climate.bedroom")
    assert bedroom.attributes["hvac_action"] == HVACAction.IDLE
    assert bedroom.attributes["zone_mode"] == "global_schedule"

    assert hass.states.get("sensor.living_room_temperature").state == "21.5"
    assert hass.states.get("sensor.living_room_humidity").state == "45"
    assert hass.states.get("sensor.living_room_battery").state == "90"

    # The empty zone slot is skipped.
    assert len(hass.states.async_entity_ids("climate")) == 2


async def test_set_temperature_holds_until_confirmed(
    hass: HomeAssistant, mock_api: AiohttpClientMocker, config_entry, module_data
) -> None:
    """A new setpoint doesn't jump back while the cloud still reports the old one."""
    await _setup(hass, config_entry)

    await hass.services.async_call(
        "climate",
        "set_temperature",
        {"entity_id": "climate.living_room", "temperature": 23.5},
        blocking=True,
    )
    post = [
        c
        for c in mock_api.mock_calls
        if c[0] == "POST" and str(c[1]).endswith("/zones")
    ]
    assert post[-1][2]["mode"]["setTemperature"] == 235
    assert post[-1][2]["mode"]["mode"] == "constantTemp"
    assert hass.states.get("climate.living_room").attributes["temperature"] == 23.5

    # The next poll still returns 22.0; the card must keep showing 23.5.
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))
    await hass.async_block_till_done()
    assert hass.states.get("climate.living_room").attributes["temperature"] == 23.5

    # Once the cloud catches up the real value is used again.
    module_data["zones"]["elements"][0]["zone"]["setTemperature"] = 235
    mock_api.clear_requests()
    mock_api.get(f"{API_URL}/users/{USER_ID}/modules/{UDID}", json=module_data)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=62))
    await hass.async_block_till_done()
    assert hass.states.get("climate.living_room").attributes["temperature"] == 23.5
    coordinator = config_entry.runtime_data
    assert not coordinator._pending


async def test_expired_token_relogs(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_entry, module_data
) -> None:
    """A 401 on a poll logs in again instead of making everything unavailable."""
    calls = {"n": 0}

    async def module_response(method, url, data):
        calls["n"] += 1
        if calls["n"] == 2:
            return AiohttpClientMockResponse(method, url, status=401, json={})
        return AiohttpClientMockResponse(method, url, json=module_data)

    aioclient_mock.post(
        f"{API_URL}/authentication", json={"user_id": USER_ID, "token": "tok"}
    )
    aioclient_mock.get(
        f"{API_URL}/users/{USER_ID}/modules", json=[{"udid": UDID, "name": "Home"}]
    )
    aioclient_mock.get(
        f"{API_URL}/users/{USER_ID}/modules/{UDID}", side_effect=module_response
    )

    await _setup(hass, config_entry)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))
    await hass.async_block_till_done()

    assert calls["n"] == 3
    assert hass.states.get("climate.living_room").state == HVACMode.HEAT
    logins = [
        c for c in aioclient_mock.mock_calls if str(c[1]).endswith("/authentication")
    ]
    assert len(logins) == 2


async def test_bad_login_starts_reauth(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_entry
) -> None:
    """A rejected password on startup asks the user to log in again."""
    aioclient_mock.post(f"{API_URL}/authentication", status=401, json={})
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert flows and flows[0]["context"]["source"] == "reauth"


async def test_cloud_down_retries(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_entry
) -> None:
    """If the Roth cloud is unreachable on startup, setup is retried later."""
    aioclient_mock.post(f"{API_URL}/authentication", exc=TimeoutError)
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload(hass: HomeAssistant, mock_api, config_entry) -> None:
    """The entry unloads cleanly."""
    await _setup(hass, config_entry)
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.NOT_LOADED
