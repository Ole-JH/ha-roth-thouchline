"""Tests for the config flow."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.roth_touchline.const import API_URL, DOMAIN

from .conftest import USER_ID

LOGIN = {"username": "a@b.c", "password": "secret"}


async def test_user_flow(hass: HomeAssistant, mock_api) -> None:
    """A correct login creates an entry keyed on the Roth user id."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(result["flow_id"], LOGIN)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "a@b.c"
    assert result["data"] == LOGIN
    assert result["result"].unique_id == str(USER_ID)


async def test_user_flow_invalid_auth(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A rejected login shows an error and lets the user retry."""
    aioclient_mock.post(f"{API_URL}/authentication", status=401, json={})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], LOGIN)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_cannot_connect(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A network error shows cannot_connect."""
    aioclient_mock.post(f"{API_URL}/authentication", exc=TimeoutError)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], LOGIN)
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_already_configured(
    hass: HomeAssistant, mock_api, config_entry
) -> None:
    """The same account cannot be added twice."""
    config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], LOGIN)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth(hass: HomeAssistant, mock_api, config_entry) -> None:
    """Reauth stores the new password."""
    config_entry.add_to_hass(hass)
    result = await config_entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"password": "new"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert config_entry.data["password"] == "new"
