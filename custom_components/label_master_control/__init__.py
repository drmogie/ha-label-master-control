"""The Label Master Control integration.

Each config entry is one device you built yourself through the wizard in
config_flow.py (pick a domain, pick one or more labels, name it) - there
is no auto-discovery, and nothing is created without you explicitly
adding it. What DOES stay live is membership: label a new light with the
same labels a device was built from, and it joins that device's
aggregate automatically, no reload - see aggregator.py.
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .aggregator import LabelAggregator
from .const import CONF_LABEL_IDS, CONF_TARGET_DOMAIN, DOMAIN, MANUFACTURER, PLATFORMS


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one manually-built Label Master Control device."""
    label_ids = entry.options.get(CONF_LABEL_IDS, entry.data.get(CONF_LABEL_IDS, []))
    aggregator = LabelAggregator(hass, entry.data[CONF_TARGET_DOMAIN], label_ids)
    await aggregator.async_start()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"aggregator": aggregator}

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer=MANUFACTURER,
        model=f"{entry.data[CONF_TARGET_DOMAIN].title()} label group",
    )

    entry.async_on_unload(entry.add_update_listener(_async_entry_updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        if data:
            await data["aggregator"].async_stop()
    return unload_ok


async def _async_entry_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload so a changed label set (or representative light) takes effect."""
    await hass.config_entries.async_reload(entry.entry_id)
