"""Shared plumbing for every dynamically-discovered master entity."""
from __future__ import annotations

from collections.abc import Callable

from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN, MANUFACTURER
from .group_tracker import GroupKey, GroupTracker


def device_info_for(key: GroupKey, label_names: list[str]) -> DeviceInfo:
    domain, label_ids = key
    device_key = f"{domain}:{'|'.join(sorted(label_ids))}"
    title = f"{domain.title()} — {', '.join(sorted(label_names))}"
    return DeviceInfo(
        identifiers={(DOMAIN, device_key)},
        name=title,
        manufacturer=MANUFACTURER,
        model="Label group",
    )


class GroupEntity(Entity):
    """Base for a master entity backing one (domain, label-combo) group."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, tracker: GroupTracker, key: GroupKey) -> None:
        self._tracker = tracker
        self._key = key
        label_names = tracker.label_names(key[1])
        self._attr_device_info = device_info_for(key, label_names)
        self._unsub_state: Callable[[], None] | None = None

    @property
    def members(self) -> list[str]:
        return self._tracker.members(self._key)

    def is_any_on(self) -> bool:
        for entity_id in self.members:
            state = self.hass.states.get(entity_id)
            if state is not None and state.state == "on":
                return True
        return False

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._resubscribe_state_tracking()

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub_state:
            self._unsub_state()
            self._unsub_state = None
        await super().async_will_remove_from_hass()

    def refresh_membership(self) -> None:
        """Call when the tracker reports this group's membership changed."""
        self._resubscribe_state_tracking()
        self.async_write_ha_state()

    def _resubscribe_state_tracking(self) -> None:
        if self._unsub_state:
            self._unsub_state()
            self._unsub_state = None
        members = self.members
        if members:
            self._unsub_state = async_track_state_change_event(
                self.hass, members, self._handle_state_changed
            )

    def _handle_state_changed(self, event) -> None:
        self.async_write_ha_state()
