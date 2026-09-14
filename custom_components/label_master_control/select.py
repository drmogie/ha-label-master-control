"""Hidden 'representative light' picker - one per light-domain group,
created/removed alongside its master light in light.py. Lets you pin
which member's brightness/color the master light reports, instead of
the default (first member currently on)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, FIRST_FOUND
from .entity import device_info_for
from .group_tracker import GroupKey, GroupTracker
from .light import representative_select_unique_id

_DOMAIN_KEY = "light"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    tracker: GroupTracker = hass.data[DOMAIN][entry.entry_id]["tracker"]
    live: dict[GroupKey, RepresentativeSelect] = {}

    def _add(key: GroupKey) -> None:
        if key[0] != _DOMAIN_KEY or key in live:
            return
        entity = RepresentativeSelect(tracker, key)
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


class RepresentativeSelect(SelectEntity, RestoreEntity):
    """Hidden config control: which member light represents the group."""

    _attr_has_entity_name = True
    _attr_name = "Representative light"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_should_poll = False

    def __init__(self, tracker: GroupTracker, key: GroupKey) -> None:
        self._tracker = tracker
        self._key = key
        label_names = tracker.label_names(key[1])
        self._attr_device_info = device_info_for(key, label_names)
        self._attr_unique_id = representative_select_unique_id(key)
        self._attr_current_option = FIRST_FOUND

    @property
    def options(self) -> list[str]:
        return [FIRST_FOUND, *self._tracker.members(self._key)]

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            if last_state.state in self.options:
                self._attr_current_option = last_state.state

    async def async_select_option(self, option: str) -> None:
        self._attr_current_option = option
        self.async_write_ha_state()

    def refresh_membership(self) -> None:
        if self._attr_current_option not in self.options:
            self._attr_current_option = FIRST_FOUND
        self.async_write_ha_state()
