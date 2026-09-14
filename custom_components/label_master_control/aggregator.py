"""Live membership tracking for one manually-created master device.

Each config entry fixes a domain and a set of labels at creation time
(via the wizard in config_flow.py). This class is what stays live
afterward: on startup and on every entity_registry_updated event, it
rescans the entity registry for every entity of that domain carrying
ALL of the entry's chosen labels (a subset/AND check, the same
intersection the original template's `select('in', ...)` chain did -
just generalized from exactly two labels to however many the entry
was given), and notifies listeners when membership or a member's state
changes.

Domain matching is a plain entity_id.split(".")[0] check - no regex, so
the class of bug found in the original template (an unanchored search
happening to match unrelated entities) doesn't exist here.
"""
from __future__ import annotations

from collections.abc import Callable
import logging

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event

_LOGGER = logging.getLogger(__name__)


class LabelAggregator:
    """Tracks every entity of one domain carrying a fixed set of labels."""

    def __init__(self, hass: HomeAssistant, domain: str, label_ids: list[str]) -> None:
        self.hass = hass
        self.domain = domain
        self.label_ids = frozenset(label_ids)
        self._members: list[str] = []
        self._listeners: list[Callable[[], None]] = []
        self._unsub_registry: Callable[[], None] | None = None
        self._unsub_state: Callable[[], None] | None = None

    def members(self) -> list[str]:
        return list(self._members)

    def on_members(self) -> list[str]:
        result = []
        for entity_id in self._members:
            state = self.hass.states.get(entity_id)
            if state is not None and state.state == "on":
                result.append(entity_id)
        return result

    def is_any_on(self) -> bool:
        return len(self.on_members()) > 0

    def representative(self, preferred: str | None = None) -> str | None:
        """The entity whose attributes should represent the whole group.

        Prefers `preferred` (the user's pinned choice) while it's on;
        otherwise the first member that's on; otherwise just the first
        member at all, so an all-off group still reports *something*.
        """
        on_members = self.on_members()
        if preferred and preferred in on_members:
            return preferred
        if on_members:
            return on_members[0]
        return self._members[0] if self._members else None

    def add_listener(self, callback_fn: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(callback_fn)

        def _remove() -> None:
            if callback_fn in self._listeners:
                self._listeners.remove(callback_fn)

        return _remove

    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener()

    async def async_start(self) -> None:
        self._rescan()
        self._unsub_registry = self.hass.bus.async_listen(
            "entity_registry_updated", self._handle_registry_updated
        )

    async def async_stop(self) -> None:
        if self._unsub_registry:
            self._unsub_registry()
            self._unsub_registry = None
        if self._unsub_state:
            self._unsub_state()
            self._unsub_state = None
        self._listeners.clear()

    @callback
    def _handle_registry_updated(self, event: Event) -> None:
        self._rescan()

    def _rescan(self) -> None:
        registry = er.async_get(self.hass)
        new_members = []

        for entity_entry in registry.entities.values():
            if entity_entry.entity_id.split(".", 1)[0] != self.domain:
                continue
            if self.label_ids.issubset(entity_entry.labels):
                new_members.append(entity_entry.entity_id)

        changed = new_members != self._members
        self._members = new_members
        self._resubscribe_state_tracking()
        if changed:
            self._notify()

    def _resubscribe_state_tracking(self) -> None:
        if self._unsub_state:
            self._unsub_state()
            self._unsub_state = None
        if self._members:
            self._unsub_state = async_track_state_change_event(
                self.hass, self._members, self._handle_state_changed
            )

    @callback
    def _handle_state_changed(self, event: Event) -> None:
        self._notify()
