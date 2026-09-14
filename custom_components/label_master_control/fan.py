"""Master fan entity: on/off + percentage/preset_mode fan-out."""
from __future__ import annotations

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .aggregator import LabelAggregator
from .const import CONF_TARGET_DOMAIN, DOMAIN
from .entity import MasterEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    if entry.data[CONF_TARGET_DOMAIN] != "fan":
        return
    aggregator = hass.data[DOMAIN][entry.entry_id]["aggregator"]
    async_add_entities([MasterFan(entry, aggregator)])


class MasterFan(MasterEntity, FanEntity):
    # TURN_ON / TURN_OFF must be declared explicitly - modern Home
    # Assistant no longer calls async_turn_on/async_turn_off for a
    # FanEntity that doesn't advertise them, even though the methods
    # are implemented below. Without this, on/off silently does nothing.
    _attr_supported_features = (
        FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
        | FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
    )

    def __init__(self, entry: ConfigEntry, aggregator: LabelAggregator) -> None:
        super().__init__(entry, aggregator)
        self._attr_unique_id = f"{entry.entry_id}_fan"

    def _representative_state(self):
        rep = self._aggregator.representative()
        return self.hass.states.get(rep) if rep else None

    @property
    def is_on(self) -> bool:
        return self._aggregator.is_any_on()

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
        members = self._aggregator.members()
        if not members:
            return
        data = {"entity_id": members}
        if percentage is not None:
            data["percentage"] = percentage
        if preset_mode is not None:
            data["preset_mode"] = preset_mode
        await self.hass.services.async_call("fan", "turn_on", data, blocking=True)

    async def async_turn_off(self, **kwargs) -> None:
        members = self._aggregator.members()
        if members:
            await self.hass.services.async_call(
                "fan", "turn_off", {"entity_id": members}, blocking=True
            )

    async def async_set_percentage(self, percentage: int) -> None:
        members = self._aggregator.members()
        if members:
            await self.hass.services.async_call(
                "fan",
                "set_percentage",
                {"entity_id": members, "percentage": percentage},
                blocking=True,
            )

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        members = self._aggregator.members()
        if members:
            await self.hass.services.async_call(
                "fan",
                "set_preset_mode",
                {"entity_id": members, "preset_mode": preset_mode},
                blocking=True,
            )
