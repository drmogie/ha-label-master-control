"""Master fan entity: on/off + percentage/preset_mode fan-out."""
from __future__ import annotations

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .aggregator import LabelAggregator
from .const import DOMAIN
from .entity import MasterEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Always create the master fan, even with zero current members."""
    aggregator = hass.data[DOMAIN][entry.entry_id]["aggregator"]
    async_add_entities([MasterFan(entry, aggregator)])


class MasterFan(MasterEntity, FanEntity):
    _attr_name = "Fan"
    _attr_supported_features = FanEntityFeature.SET_SPEED | FanEntityFeature.PRESET_MODE

    def __init__(self, entry: ConfigEntry, aggregator: LabelAggregator) -> None:
        super().__init__(entry, aggregator, "fan")
        self._attr_unique_id = f"{entry.entry_id}_fan"

    def _representative_state(self):
        rep = self._aggregator.representative("fan")
        return self.hass.states.get(rep) if rep else None

    @property
    def is_on(self) -> bool:
        return self._aggregator.is_any_on("fan")

    @property
    def percentage(self) -> int | None:
        state = self._representative_state()
        return state.attributes.get("percentage") if state else None

    @property
    def preset_mode(self) -> str | None:
        state = self._representative_state()
        return state.attributes.get("preset_mode") if state else None

    @property
    def preset_modes(self) -> list[str] | None:
        state = self._representative_state()
        return state.attributes.get("preset_modes") if state else None

    async def async_turn_on(self, percentage=None, preset_mode=None, **kwargs) -> None:
        members = self._aggregator.members("fan")
        if not members:
            return
        data = {"entity_id": members}
        if percentage is not None:
            data["percentage"] = percentage
        if preset_mode is not None:
            data["preset_mode"] = preset_mode
        await self.hass.services.async_call("fan", "turn_on", data, blocking=True)

    async def async_turn_off(self, **kwargs) -> None:
        members = self._aggregator.members("fan")
        if members:
            await self.hass.services.async_call(
                "fan", "turn_off", {"entity_id": members}, blocking=True
            )

    async def async_set_percentage(self, percentage: int) -> None:
        members = self._aggregator.members("fan")
        if members:
            await self.hass.services.async_call(
                "fan",
                "set_percentage",
                {"entity_id": members, "percentage": percentage},
                blocking=True,
            )

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        members = self._aggregator.members("fan")
        if members:
            await self.hass.services.async_call(
                "fan",
                "set_preset_mode",
                {"entity_id": members, "preset_mode": preset_mode},
                blocking=True,
            )
