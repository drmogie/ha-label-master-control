"""Master switch platform: one entity per (switch, label-combo) group,
created and removed live as groups appear/disappear."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import GroupEntity
from .group_tracker import GroupKey, GroupTracker

_DOMAIN_KEY = "switch"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    tracker: GroupTracker = hass.data[DOMAIN][entry.entry_id]["tracker"]
    live: dict[GroupKey, MasterSwitch] = {}

    def _add(key: GroupKey) -> None:
        if key[0] != _DOMAIN_KEY or key in live:
            return
        entity = MasterSwitch(tracker, key)
        live[key] = entity
        async_add_entities([entity])

    def _remove(key: GroupKey) -> None:
        entity = live.pop(key, None)
        if entity:
            hass.async_create_task(entity.async_remove(force_remove=True))

    def _changed(key: GroupKey) -> None:
        entity = live.get(key)
        if entity:
            entity.refresh_membership()

    for key in tracker.groups_for_domain(_DOMAIN_KEY):
        _add(key)

    tracker.on_added(_add)
    tracker.on_removed(_remove)
    tracker.on_changed(_changed)


class MasterSwitch(GroupEntity, SwitchEntity):
    _attr_name = None  # the device's own name already describes this entity

    def __init__(self, tracker: GroupTracker, key: GroupKey) -> None:
        super().__init__(tracker, key)
        domain, label_ids = key
        self._attr_unique_id = f"{domain}_{'_'.join(sorted(label_ids))}_switch"

    @property
    def is_on(self) -> bool:
        return self.is_any_on()

    async def async_turn_on(self, **kwargs) -> None:
        if self.members:
            await self.hass.services.async_call(
                "switch", "turn_on", {"entity_id": self.members}, blocking=True
            )

    async def async_turn_off(self, **kwargs) -> None:
        if self.members:
            await self.hass.services.async_call(
                "switch", "turn_off", {"entity_id": self.members}, blocking=True
            )
