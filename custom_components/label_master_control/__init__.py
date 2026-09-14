"""The Label Master Control integration.

There is exactly one config entry for the whole integration (see
config_flow.py) - it just holds the grouping-mode choice. Every actual
"device" you see (a light group, a switch group, a fan group) is
discovered live from your entities' labels, not configured by hand:
label a light with two labels and a matching light-domain device appears
on its own - see group_tracker.py for the mechanism.
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_GROUPING_MODE, DEFAULT_GROUPING_MODE, DOMAIN, PLATFORMS
from .group_tracker import GroupTracker


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the single Label Master Control config entry."""
    grouping_mode = entry.options.get(
        CONF_GROUPING_MODE, entry.data.get(CONF_GROUPING_MODE, DEFAULT_GROUPING_MODE)
    )
    tracker = GroupTracker(hass, grouping_mode)
    await tracker.async_start()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"tracker": tracker}

    entry.async_on_unload(entry.add_update_listener(_async_entry_updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the Label Master Control config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        if data:
            await data["tracker"].async_stop()
    return unload_ok


async def _async_entry_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload so a changed grouping mode re-derives every group under it."""
    await hass.config_entries.async_reload(entry.entry_id)
