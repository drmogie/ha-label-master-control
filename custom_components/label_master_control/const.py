"""Constants for the Label Master Control integration."""
from __future__ import annotations

DOMAIN = "label_master_control"
MANUFACTURER = "Label Master Control"

CONF_GROUPING_MODE = "grouping_mode"
GROUPING_EXACT = "exact"
GROUPING_PAIRS = "pairs"
GROUPING_MODES = [GROUPING_EXACT, GROUPING_PAIRS]
DEFAULT_GROUPING_MODE = GROUPING_EXACT

# Domains this integration builds a master entity for. "select" is also
# forwarded as a platform, but only to host the light domain's hidden
# "representative" picker - it is never itself a source of group
# membership.
SUPPORTED_DOMAINS = ("light", "switch", "fan")
PLATFORMS = ["switch", "fan", "light", "select"]

SINGLETON_UNIQUE_ID = "global"

FIRST_FOUND = "__first_found__"
