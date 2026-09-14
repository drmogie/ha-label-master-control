"""Master light entity: brightness/color fan-out, representative-driven
attributes.

Unlike the template-light version this replaces, a real LightEntity's
async_turn_on receives brightness/hs_color/color_temp_kelvin directly in
kwargs - there's no need for separate set_level/set_hs/set_temperature
steps, which removes a whole layer of the repetition the template had.
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
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .aggregator import LabelAggregator
from .const import CONF_REPRESENTATIVE_LIGHT, DOMAIN
from .entity import MasterEntity

_SUPPORTED_MODES = {ColorMode.COLOR_TEMP, ColorMode.HS}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Always create the master light, even with zero current members."""
    aggregator = hass.data[DOMAIN][entry.entry_id]["aggregator"]
    async_add_entities([MasterLight(entry, aggregator)])


class MasterLight(MasterEntity, LightEntity):
    _attr_name = "Light"
    _attr_supported_color_modes = _SUPPORTED_MODES
    _attr_min_color_temp_kelvin = 2000
    _attr_max_color_temp_kelvin = 6500

    def __init__(self, entry: ConfigEntry, aggregator: LabelAggregator) -> None:
        super().__init__(entry, aggregator, "light")
        self._attr_unique_id = f"{entry.entry_id}_light"

    def _representative_state(self):
        preferred = self._entry.options.get(CONF_REPRESENTATIVE_LIGHT)
        rep = self._aggregator.representative("light", preferred)
        return self.hass.states.get(rep) if rep else None

    @property
    def is_on(self) -> bool:
        return self._aggregator.is_any_on("light")

    @property
    def color_mode(self) -> ColorMode | None:
        state = self._representative_state()
        mode = state.attributes.get("color_mode") if state else None
        return mode if mode in _SUPPORTED_MODES else ColorMode.COLOR_TEMP

    @property
    def brightness(self) -> int | None:
        state = self._representative_state()
        return state.attributes.get(ATTR_BRIGHTNESS) if state else None

    @property
    def hs_color(self):
        state = self._representative_state()
        return state.attributes.get(ATTR_HS_COLOR) if state else None

    @property
    def color_temp_kelvin(self) -> int | None:
        state = self._representative_state()
        return state.attributes.get(ATTR_COLOR_TEMP_KELVIN) if state else None

    async def async_turn_on(self, **kwargs) -> None:
        members = self._aggregator.members("light")
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
        members = self._aggregator.members("light")
        if members:
            await self.hass.services.async_call(
                "light", "turn_off", {"entity_id": members}, blocking=True
            )
