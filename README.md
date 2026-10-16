# Roth Touchline SL for Home Assistant

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

## Installation

### HACS

1. In HACS, open the menu and choose **Custom repositories**.
2. Add `https://github.com/Ole-JH/ha-roth-thouchline` with type **Integration**.
3. Install **Roth Touchline SL** and restart Home Assistant.

### Manual

Copy `custom_components/roth_touchline` into your Home Assistant
`config/custom_components` folder and restart.

## Setup

Go to **Settings → Devices & services → Add integration**, search for
**Roth Touchline SL** and log in with the email and password from the app.

You can keep the official integration installed while you try this one; they
don't share anything. Remove it once you're happy.

## Development

```bash
pip install -r requirements_test.txt
pytest
```
