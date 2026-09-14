"""Constants for the Label Master Control integration."""
from __future__ import annotations

DOMAIN = "label_master_control"
MANUFACTURER = "Label Master Control"

CONF_LABEL_ID = "label_id"
CONF_REPRESENTATIVE_LIGHT = "representative_light"

# Domains this integration builds a master entity for. Every entry
# forwards all three platforms unconditionally (see __init__.py) - each
# platform's master entity just reports "off / no members" when nothing
# of that domain currently carries the label, which is simpler and more
# robust under live relabeling than trying to add/remove platforms on
# the fly as membership changes.
PLATFORMS = ["switch", "fan", "light"]
SUPPORTED_DOMAINS = ("light", "switch", "fan")
