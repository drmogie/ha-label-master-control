"""'Members' diagnostic sensor - one per device, regardless of domain.

Shows the current member count as its state and the full list of
matched entity_ids as an attribute, so the list is visible right on the
device's own page (Settings -> Devices & services -> that device) -
not just tucked inside a member entity's Related tab.
"""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .aggregator import LabelAggregator
from .const import DOMAIN
from .entity import MasterEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    aggregator = hass.data[DOMAIN][entry.entry_id]["aggregator"]
    async_add_entities([MembersSensor(entry, aggregator)])


class MembersSensor(MasterEntity, SensorEntity):
    """Diagnostic: how many entities currently match this device's labels."""

    _attr_name = "Members"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:tag-multiple"

    def __init__(self, entry: ConfigEntry, aggregator: LabelAggregator) -> None:
        super().__init__(entry, aggregator)
        self._attr_unique_id = f"{entry.entry_id}_members"

    @property
    def native_value(self) -> int:
        return len(self._aggregator.members())

    # extra_state_attributes (the {"entity_id": [...]} list) is inherited
    # from MasterEntity as-is - same list this sensor's count summarizes.
