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

# Domains the wizard lets you build a device for. "select" is also
# forwarded as a platform, but only to host the light domain's
# "Representative light" picker - it's never itself a source of
# membership.
SUPPORTED_DOMAINS = ("light", "switch", "fan")
PLATFORMS = ["switch", "fan", "light", "select"]

FIRST_FOUND = "__first_found__"
