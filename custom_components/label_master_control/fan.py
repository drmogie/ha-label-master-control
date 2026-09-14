"""Master fan platform: one entity per (fan, label-combo) group."""
from __future__ import annotations

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import GroupEntity
from .group_tracker import GroupKey, GroupTracker

_DOMAIN_KEY = "fan"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    tracker: GroupTracker = hass.data[DOMAIN][entry.entry_id]["tracker"]
    live: dict[GroupKey, MasterFan] = {}

    def _add(key: GroupKey) -> None:
        if key[0] != _DOMAIN_KEY or key in live:
            return
        entity = MasterFan(tracker, key)
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


class MasterFan(GroupEntity, FanEntity):
    _attr_name = None
    _attr_supported_features = FanEntityFeature.SET_SPEED | FanEntityFeature.PRESET_MODE

    def __init__(self, tracker: GroupTracker, key: GroupKey) -> None:
        super().__init__(tracker, key)
        domain, label_ids = key
        self._attr_unique_id = f"{domain}_{'_'.join(sorted(label_ids))}_fan"

    def _representative_state(self):
        members = self.members
        for entity_id in members:
            state = self.hass.states.get(entity_id)
            if state is not None and state.state == "on":
                return state
        return self.hass.states.get(members[0]) if members else None

    @property
    def is_on(self) -> bool:
        return self.is_any_on()

    @property
    def percentage(self):
        state = self._representative_state()
        return state.attributes.get("percentage") if state else None

    @property
    def preset_mode(self):
        state = self._representative_state()
        return state.attributes.get("preset_mode") if state else None

    @property
    def preset_modes(self):
        state = self._representative_state()
        return state.attributes.get("preset_modes") if state else None

    async def async_turn_on(self, percentage=None, preset_mode=None, **kwargs) -> None:
        if not self.members:
            return
        data = {"entity_id": self.members}
        if percentage is not None:
            data["percentage"] = percentage
        if preset_mode is not None:
            data["preset_mode"] = preset_mode
        await self.hass.services.async_call("fan", "turn_on", data, blocking=True)

    async def async_turn_off(self, **kwargs) -> None:
        if self.members:
            await self.hass.services.async_call(
                "fan", "turn_off", {"entity_id": self.members}, blocking=True
            )

    async def async_set_percentage(self, percentage: int) -> None:
        if self.members:
            await self.hass.services.async_call(
                "fan",
                "set_percentage",
                {"entity_id": self.members, "percentage": percentage},
                blocking=True,
            )

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if self.members:
            await self.hass.services.async_call(
                "fan",
                "set_preset_mode",
                {"entity_id": self.members, "preset_mode": preset_mode},
                blocking=True,
            )
