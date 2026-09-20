"""Constants for the Label Master Control integration."""
from __future__ import annotations

DOMAIN = "label_master_control"
MANUFACTURER = "Label Master Control"

# Set once in the wizard (config_flow.py) and fixed for the device's
# lifetime - a different domain means building a different device.
CONF_TARGET_DOMAIN = "target_domain"

# The label set a device's members must all carry. Can be changed later
# via the options flow without rebuilding the device.
CONF_LABEL_IDS = "label_ids"

# Pinned choice from the light domain's "Representative light" select
# entity (select.py). Not currently written by the config/options flow
# directly - RestoreEntity persists it - but reserved here so any future
# flow step that needs to read/write it uses the same key.
CONF_REPRESENTATIVE_LIGHT = "representative_light"

# Domains the wizard lets you build a device for. "select" and "sensor"
# are also forwarded as platforms: "select" only to host the light
# domain's "Representative light" picker, "sensor" to host the
# "Members" diagnostic sensor every device gets regardless of domain -
# neither is ever itself a source of membership.
SUPPORTED_DOMAINS = ("light", "switch", "fan")
PLATFORMS = ["switch", "fan", "light", "select", "sensor"]

FIRST_FOUND = "__first_found__"

# Companion Lovelace card (Matrix Card, added 2026.09.20) - served the
# same way ha-piper-browser-speaker serves its own card: the whole www/
# folder registered as one static directory, plus an extra_js_url so it
# auto-loads on every dashboard with no manual Lovelace resource. See
# __init__.py's frontend-registration block.
CARD_FILENAME = "ha-label-master-control-card.js"
STATIC_URL_ROOT = f"/{DOMAIN}"
CARD_URL = f"{STATIC_URL_ROOT}/{CARD_FILENAME}"
CARD_VERSION = "2026.09.20.07"
