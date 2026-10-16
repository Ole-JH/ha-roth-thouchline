<img src="custom_components/roth_touchline/brand/icon.png" alt="" width="96" align="right">

# Roth Touchline SL for Home Assistant

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Ole-JH&repository=ha-roth-thouchline&category=integration)
[![Open your Home Assistant instance and start setting up Roth Touchline SL.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=roth_touchline)

A custom integration for Roth Touchline SL floor heating, built as a more
dependable replacement for the official Touchline SL integration. It talks to
the same Roth cloud the Touchline SL app uses.

## What you get

- One device per room with a thermostat you can set the target temperature on.
- Sensors for room temperature, humidity, thermostat battery and signal
  strength (only the ones your thermostats actually report).
- Set up from the UI with your Roth app login. If the password stops working,
  Home Assistant asks you to log in again instead of going unavailable.

Setting a temperature puts that room on a constant setpoint, the same as doing
it in the app. Schedules and operating modes come in a later version.

## Compared with the official integration

Checked against the official Touchline SL integration in Home Assistant 2026.2
and the `pytouchlinesl` 0.6.0 library it uses.

| | This integration | Official Touchline SL |
|---|:---:|:---:|
| Set up from the UI | ✅ | ✅ |
| Install with HACS | ✅ | Built in |
| Thermostat per room | ✅ | ✅ |
| Heating / cooling / idle shown | ✅ | ✅ |
| Humidity on the thermostat | ✅ | ✅ |
| Separate temperature and humidity sensors | ✅ | ❌ |
| Battery sensor per thermostat | ✅ | ❌ |
| Signal strength sensor | ✅ (off by default) | ❌ |
| Window open shown on the thermostat | ✅ | ❌ |
| New setpoint stays put while the cloud catches up | ✅ | ❌ refreshes right away and can show the old value |
| Rooms switched off stay visible as off | ✅ | ❌ they disappear and go unavailable |
| Logs in again when the session expires | ✅ | ❌ |
| Asks for a new password when it changes | ✅ | ❌ no reauth step |
| Copes with unexpected values from the Roth cloud | ✅ | ❌ strict parsing fails the whole update |
| Reuses Home Assistant's HTTP connection | ✅ | ❌ new connection per request |
| Several controllers on one account | ✅ | ✅ (room devices can clash) |
| Pick a schedule (preset) | Planned | ✅ |
| Week programs and holiday mode | Planned | ❌ |
| Switch heat / cool / off from Home Assistant | ❌ | ❌ |
| Custom icon and logo | ✅ (HA 2026.3+) | ✅ |

## Installation

### HACS

Click the **Open in HACS** button above, or:

1. In HACS, open the menu and choose **Custom repositories**.
2. Add `https://github.com/Ole-JH/ha-roth-thouchline` with type **Integration**.
3. Install **Roth Touchline SL** and restart Home Assistant.

### Manual

Copy `custom_components/roth_touchline` into your Home Assistant
`config/custom_components` folder and restart.

## Setup

Click the **Add integration** button above, or go to **Settings → Devices &
services → Add integration** and search for **Roth Touchline SL**. Then log in with the email and password from the app.

You can keep the official integration installed while you try this one; they
don't share anything. Remove it once you're happy.

## Development

```bash
pip install -r requirements_test.txt
pytest
```
