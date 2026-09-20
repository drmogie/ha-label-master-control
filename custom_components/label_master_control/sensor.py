"""Diagnostic count sensors - one device gets three, regardless of domain:
Members (total), Members On, Members Off.

Each shows a live count as its state, with the matching subset of
entity_ids as its `entity_id` attribute, so both the total and the
on/off split are visible right on the device's own page (Settings ->
Devices & services -> that device) - not just tucked inside a member
entity's Related tab.
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
    async_add_entities(
        [
            MembersSensor(entry, aggregator),
            MembersOnSensor(entry, aggregator),
            MembersOffSensor(entry, aggregator),
        ]
    )


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


class MembersOnSensor(MasterEntity, SensorEntity):
    """Diagnostic: how many current members are on."""

    _attr_name = "Members On"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:toggle-switch"

    def __init__(self, entry: ConfigEntry, aggregator: LabelAggregator) -> None:
        super().__init__(entry, aggregator)
        self._attr_unique_id = f"{entry.entry_id}_members_on"

    @property
    def native_value(self) -> int:
        return len(self._aggregator.on_members())

    @property
    def extra_state_attributes(self) -> dict[str, list[str]]:
        return {"entity_id": self._aggregator.on_members()}


class MembersOffSensor(MasterEntity, SensorEntity):
    """Diagnostic: how many current members are off (or unavailable/unknown -
    anything not 'on' counts as off here, so On + Off always equals Members)."""

    _attr_name = "Members Off"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:toggle-switch-off"

    def __init__(self, entry: ConfigEntry, aggregator: LabelAggregator) -> None:
        super().__init__(entry, aggregator)
        self._attr_unique_id = f"{entry.entry_id}_members_off"

    @property
    def native_value(self) -> int:
        return len(self._aggregator.off_members())

    @property
    def extra_state_attributes(self) -> dict[str, list[str]]:
        return {"entity_id": self._aggregator.off_members()}
