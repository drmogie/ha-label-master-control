"""'Representative light' picker - one per light-domain device, created
alongside its master light in light.py. Lets you pin which member's
brightness/color the master light reports, instead of the default
(first member currently on)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .aggregator import LabelAggregator
from .const import CONF_TARGET_DOMAIN, DOMAIN, FIRST_FOUND
from .entity import device_info_for
from .light import representative_select_unique_id


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    if entry.data[CONF_TARGET_DOMAIN] != "light":
        return
    aggregator = hass.data[DOMAIN][entry.entry_id]["aggregator"]
    async_add_entities([RepresentativeSelect(entry, aggregator)])


class RepresentativeSelect(SelectEntity, RestoreEntity):
    """Config control: which member light represents the device."""

    _attr_has_entity_name = True
    _attr_name = "Representative light"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, aggregator: LabelAggregator) -> None:
        self._entry = entry
        self._aggregator = aggregator
        self._attr_device_info = device_info_for(entry)
        self._attr_unique_id = representative_select_unique_id(entry)
        self._attr_current_option = FIRST_FOUND
        self._unsub_listener = None

    @property
    def options(self) -> list[str]:
        return [FIRST_FOUND, *self._aggregator.members()]

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            if last_state.state in self.options:
                self._attr_current_option = last_state.state
        self._unsub_listener = self._aggregator.add_listener(self._handle_aggregator_update)

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub_listener:
            self._unsub_listener()
            self._unsub_listener = None
        await super().async_will_remove_from_hass()

    def _handle_aggregator_update(self) -> None:
        if self._attr_current_option not in self.options:
            self._attr_current_option = FIRST_FOUND
        self.async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        self._attr_current_option = option
        self.async_write_ha_state()
