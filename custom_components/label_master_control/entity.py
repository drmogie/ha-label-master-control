"""Shared plumbing for every Label Master Control entity."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo, Entity

from .aggregator import LabelAggregator
from .const import DOMAIN, MANUFACTURER


def device_info_for(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer=MANUFACTURER,
        model="Label Master Control",
    )


class MasterEntity(Entity):
    """Base for every master entity: hooks itself to the aggregator."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, aggregator: LabelAggregator, domain: str) -> None:
        self._entry = entry
        self._aggregator = aggregator
        self._domain = domain
        self._attr_device_info = device_info_for(entry)
        self._unsub_listener = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._unsub_listener = self._aggregator.add_listener(self._handle_aggregator_update)

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub_listener:
            self._unsub_listener()
            self._unsub_listener = None
        await super().async_will_remove_from_hass()

    def _handle_aggregator_update(self) -> None:
        self.async_write_ha_state()
