"""Master light platform: one entity per (light, label-combo) group.

Brightness/color come from a "representative" member - by default the
first member found on, but pinnable via the paired hidden select entity
this platform's sibling (select.py) creates alongside it on the same
device. A real LightEntity's async_turn_on receives brightness/hs_color/
color_temp_kelvin directly in kwargs, so unlike the template-light
version this replaces, there's no need for separate set_level/set_hs/
set_temperature steps.
"""
from __future__ import annotations

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, FIRST_FOUND
from .entity import GroupEntity
from .group_tracker import GroupKey, GroupTracker

_DOMAIN_KEY = "light"
_SUPPORTED_MODES = {ColorMode.COLOR_TEMP, ColorMode.HS}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    tracker: GroupTracker = hass.data[DOMAIN][entry.entry_id]["tracker"]
    live: dict[GroupKey, MasterLight] = {}

    def _add(key: GroupKey) -> None:
        if key[0] != _DOMAIN_KEY or key in live:
            return
        entity = MasterLight(tracker, key)
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


def representative_select_unique_id(key: GroupKey) -> str:
    """Deterministic unique_id of the select entity paired with a light group."""
    domain, label_ids = key
    return f"{domain}_{'_'.join(sorted(label_ids))}_representative"


class MasterLight(GroupEntity, LightEntity):
    _attr_name = None
    _attr_supported_color_modes = _SUPPORTED_MODES
    _attr_min_color_temp_kelvin = 2000
    _attr_max_color_temp_kelvin = 6500

    def __init__(self, tracker: GroupTracker, key: GroupKey) -> None:
        super().__init__(tracker, key)
        domain, label_ids = key
        self._attr_unique_id = f"{domain}_{'_'.join(sorted(label_ids))}_light"

    def _preferred_entity_id(self) -> str | None:
        registry = er.async_get(self.hass)
        select_entity_id = registry.async_get_entity_id(
            "select", DOMAIN, representative_select_unique_id(self._key)
        )
        if not select_entity_id:
            return None
        state = self.hass.states.get(select_entity_id)
        if state is None or state.state in (None, FIRST_FOUND, "unknown", "unavailable"):
            return None
        return state.state

    def _representative_state(self):
        members = self.members
        if not members:
            return None
        preferred = self._preferred_entity_id()
        if preferred and preferred in members:
            preferred_state = self.hass.states.get(preferred)
            if preferred_state is not None and preferred_state.state == "on":
                return preferred_state
        for entity_id in members:
            state = self.hass.states.get(entity_id)
            if state is not None and state.state == "on":
                return state
        return self.hass.states.get(members[0])

    @property
    def is_on(self) -> bool:
        return self.is_any_on()

    @property
    def color_mode(self):
        state = self._representative_state()
        mode = state.attributes.get("color_mode") if state else None
        return mode if mode in _SUPPORTED_MODES else ColorMode.COLOR_TEMP

    @property
    def brightness(self):
        state = self._representative_state()
        return state.attributes.get(ATTR_BRIGHTNESS) if state else None

    @property
    def hs_color(self):
        state = self._representative_state()
        return state.attributes.get(ATTR_HS_COLOR) if state else None

    @property
    def color_temp_kelvin(self):
        state = self._representative_state()
        return state.attributes.get(ATTR_COLOR_TEMP_KELVIN) if state else None

    async def async_turn_on(self, **kwargs) -> None:
        if not self.members:
            return
        data = {"entity_id": self.members}
        if ATTR_BRIGHTNESS in kwargs:
            data[ATTR_BRIGHTNESS] = kwargs[ATTR_BRIGHTNESS]
        if ATTR_HS_COLOR in kwargs:
            data[ATTR_HS_COLOR] = kwargs[ATTR_HS_COLOR]
        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            data[ATTR_COLOR_TEMP_KELVIN] = kwargs[ATTR_COLOR_TEMP_KELVIN]
        await self.hass.services.async_call("light", "turn_on", data, blocking=True)

    async def async_turn_off(self, **kwargs) -> None:
        if self.members:
            await self.hass.services.async_call(
                "light", "turn_off", {"entity_id": self.members}, blocking=True
            )
