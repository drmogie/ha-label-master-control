"""Master light entity: one per light-domain device you built in the wizard.

Brightness/color come from a "representative" member - by default the
first member found on, but pinnable via the paired "Representative
light" select entity this platform's sibling (select.py) creates
alongside it on the same device. A real LightEntity's async_turn_on
receives brightness/hs_color/color_temp_kelvin directly in kwargs, so
unlike the template-light version this replaces, there's no need for
separate set_level/set_hs/set_temperature steps.
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

from .aggregator import LabelAggregator
from .const import CONF_TARGET_DOMAIN, DOMAIN, FIRST_FOUND
from .entity import MasterEntity

_SUPPORTED_MODES = {ColorMode.COLOR_TEMP, ColorMode.HS}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    if entry.data[CONF_TARGET_DOMAIN] != "light":
        return
    aggregator = hass.data[DOMAIN][entry.entry_id]["aggregator"]
    async_add_entities([MasterLight(entry, aggregator)])


def representative_select_unique_id(entry: ConfigEntry) -> str:
    """Deterministic unique_id of the select entity paired with this light."""
    return f"{entry.entry_id}_representative"


class MasterLight(MasterEntity, LightEntity):
    _attr_supported_color_modes = _SUPPORTED_MODES
    _attr_min_color_temp_kelvin = 2000
    _attr_max_color_temp_kelvin = 6500

    def __init__(self, entry: ConfigEntry, aggregator: LabelAggregator) -> None:
        super().__init__(entry, aggregator)
        self._attr_unique_id = f"{entry.entry_id}_light"

    def _preferred_entity_id(self) -> str | None:
        registry = er.async_get(self.hass)
        select_entity_id = registry.async_get_entity_id(
            "select", DOMAIN, representative_select_unique_id(self._entry)
        )
        if not select_entity_id:
            return None
        state = self.hass.states.get(select_entity_id)
        if state is None or state.state in (None, FIRST_FOUND, "unknown", "unavailable"):
            return None
        return state.state

    def _representative_state(self):
        members = self._aggregator.members()
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
        return self._aggregator.is_any_on()

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
        members = self._aggregator.members()
        if not members:
            return
        data = {"entity_id": members}
        if ATTR_BRIGHTNESS in kwargs:
            data[ATTR_BRIGHTNESS] = kwargs[ATTR_BRIGHTNESS]
        if ATTR_HS_COLOR in kwargs:
            data[ATTR_HS_COLOR] = kwargs[ATTR_HS_COLOR]
        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            data[ATTR_COLOR_TEMP_KELVIN] = kwargs[ATTR_COLOR_TEMP_KELVIN]
        await self.hass.services.async_call("light", "turn_on", data, blocking=True)

    async def async_turn_off(self, **kwargs) -> None:
        members = self._aggregator.members()
        if members:
            await self.hass.services.async_call(
                "light", "turn_off", {"entity_id": members}, blocking=True
            )
