"""Master switch entity: on/off fan-out for a manually-built device."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .aggregator import LabelAggregator
from .const import CONF_TARGET_DOMAIN, DOMAIN
from .entity import MasterEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    if entry.data[CONF_TARGET_DOMAIN] != "switch":
        return
    aggregator = hass.data[DOMAIN][entry.entry_id]["aggregator"]
    async_add_entities([MasterSwitch(entry, aggregator)])


class MasterSwitch(MasterEntity, SwitchEntity):
    def __init__(self, entry: ConfigEntry, aggregator: LabelAggregator) -> None:
        super().__init__(entry, aggregator)
        self._attr_unique_id = f"{entry.entry_id}_switch"

    @property
    def is_on(self) -> bool:
        return self._aggregator.is_any_on()

    async def async_turn_on(self, **kwargs) -> None:
        members = self._aggregator.members()
        if members:
            await self.hass.services.async_call(
                "switch", "turn_on", {"entity_id": members}, blocking=True
            )

    async def async_turn_off(self, **kwargs) -> None:
        members = self._aggregator.members()
        if members:
            await self.hass.services.async_call(
                "switch", "turn_off", {"entity_id": members}, blocking=True
            )
