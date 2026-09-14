"""The Label Master Control integration.

One config entry = one label = one HA device with three master entities
(switch, fan, light for v1), each fanning commands out to every current
member of that label in its own domain. Unlike a hand-written template,
membership is tracked live via the entity registry (see aggregator.py) -
relabeling something takes effect immediately, no reload required.
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .aggregator import LabelAggregator
from .const import CONF_LABEL_ID, DOMAIN, MANUFACTURER, PLATFORMS


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a Label Master Control config entry (one label -> one device)."""
    aggregator = LabelAggregator(hass, entry.data[CONF_LABEL_ID])
    await aggregator.async_start()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"aggregator": aggregator}

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer=MANUFACTURER,
        model="Label Master Control",
    )

    entry.async_on_unload(entry.add_update_listener(_async_entry_updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Label Master Control config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        if data:
            await data["aggregator"].async_stop()
    return unload_ok


async def _async_entry_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload so a changed label (or representative light) takes effect.

    The aggregator is constructed once, at setup, with the label id it
    was given then - reloading is the simplest correct way to pick up a
    newly reassigned label rather than trying to mutate a live
    aggregator's identity in place.
    """
    await hass.config_entries.async_reload(entry.entry_id)
