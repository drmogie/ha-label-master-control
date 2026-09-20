"""Shared plumbing for every master entity."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo, Entity

from .aggregator import LabelAggregator
from .const import CONF_TARGET_DOMAIN, DOMAIN, MANUFACTURER


def device_info_for(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer=MANUFACTURER,
        model=f"{entry.data[CONF_TARGET_DOMAIN].title()} label group",
    )


class MasterEntity(Entity):
    """Base for every master entity: hooks itself to its aggregator."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_name = None  # the device's own name already describes this entity

    def __init__(self, entry: ConfigEntry, aggregator: LabelAggregator) -> None:
        self._entry = entry
        self._aggregator = aggregator
        self._attr_device_info = device_info_for(entry)
        self._unsub_listener = None

    @property
    def extra_state_attributes(self) -> dict[str, list[str]]:
        """Expose current members the same way HA's own group entities do.

        `entity_id` is the attribute HA's frontend already looks for to
        populate an entity's "Related" tab in the more-info dialog (it's
        how a native Light/Switch/Cover Group shows what it's made of) -
        reusing it here means Settings -> Devices & services -> Entities
        -> this entity -> Related shows exactly what's currently being
        controlled, live, with no extra UI to build.
        """
        return {"entity_id": self._aggregator.members()}

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
