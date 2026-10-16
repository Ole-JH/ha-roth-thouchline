"""Constants for the Roth Touchline SL integration."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "roth_touchline"
MANUFACTURER: Final = "Roth"

API_URL: Final = "https://roth-touchlinesl.com/api/v1"
REQUEST_TIMEOUT: Final = 30

SCAN_INTERVAL: Final = timedelta(seconds=30)

# How long a newly set target temperature is shown while waiting for the
# cloud to confirm it. The Roth cloud relays changes to the controller with
# a delay, so polls right after a change still return the old setpoint.
PENDING_SETPOINT_TIMEOUT: Final = 120

MIN_TEMP: Final = 5.0
MAX_TEMP: Final = 35.0
TEMP_STEP: Final = 0.5
