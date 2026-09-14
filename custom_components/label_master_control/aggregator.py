"""Live label -> member-entity aggregation engine.

One LabelAggregator per config entry. It:
  - discovers every entity carrying the entry's chosen label, split by
    domain (light / switch / fan)
  - stays live: an entity_registry_updated event (an entity's labels
    changed, among other things) triggers a full re-scan, no reload
    needed - this is the piece a template light can't do, since its
    entity list is fixed at template-render time
  - tracks the current state of every member so master entities can read
    "is any member on" / "what should the representative report" without
    each entity re-querying the registry itself
  - notifies registered listener callbacks whenever membership or a
    member's state changes, so entities know to refresh themselves

Domain matching is done by splitting entity_id on "." rather than any
kind of string search - the class of bug found in the original template
(an unanchored regex search happening to match unrelated entities) simply
doesn't exist here.
"""
from __future__ import annotations

from collections.abc import Callable
import logging

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er, label_registry as lr
from homeassistant.helpers.event import async_track_state_change_event

from .const import SUPPORTED_DOMAINS

_LOGGER = logging.getLogger(__name__)


class LabelAggregator:
    """Tracks every entity under one label, grouped by domain, live."""

    def __init__(self, hass: HomeAssistant, label_id: str) -> None:
        self.hass = hass
        self.label_id = label_id
        self._members: dict[str, list[str]] = {domain: [] for domain in SUPPORTED_DOMAINS}
        self._listeners: list[Callable[[], None]] = []
        self._unsub_registry: Callable[[], None] | None = None
        self._unsub_state: Callable[[], None] | None = None

    @property
    def label_name(self) -> str | None:
        registry = lr.async_get(self.hass)
        label = registry.async_get_label(self.label_id)
        return label.name if label else None

    def members(self, domain: str) -> list[str]:
        """Entity ids under this label for one domain, in registry order."""
        return list(self._members.get(domain, []))

    def on_members(self, domain: str) -> list[str]:
        """Members of one domain that are currently on."""
        result = []
        for entity_id in self.members(domain):
            state = self.hass.states.get(entity_id)
            if state is not None and state.state == "on":
                result.append(entity_id)
        return result

    def is_any_on(self, domain: str) -> bool:
        return len(self.on_members(domain)) > 0

    def representative(self, domain: str, preferred: str | None = None) -> str | None:
        """The entity whose attributes should represent the whole group.

        Prefers `preferred` (the user's chosen representative, from the
        options flow) if it's currently on; otherwise the first member
        that's on; otherwise just the first member at all, so an
        all-off group still reports *something* instead of nothing.
        """
        on_members = self.on_members(domain)
        if preferred and preferred in on_members:
            return preferred
        if on_members:
            return on_members[0]
        members = self.members(domain)
        return members[0] if members else None

    def add_listener(self, callback_fn: Callable[[], None]) -> Callable[[], None]:
        """Register a callback fired whenever membership or state changes."""
        self._listeners.append(callback_fn)

        def _remove() -> None:
            if callback_fn in self._listeners:
                self._listeners.remove(callback_fn)

        return _remove

    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener()

    async def async_start(self) -> None:
        """Do the initial scan and start listening for live changes."""
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
        # An entity's labels (among other things) may have changed - the
        # cheapest correct response is a full rescan rather than working
        # out whether this particular change affects our label.
        self._rescan()

    def _rescan(self) -> None:
        registry = er.async_get(self.hass)
        new_members: dict[str, list[str]] = {domain: [] for domain in SUPPORTED_DOMAINS}

        for entity_entry in registry.entities.values():
            if self.label_id not in entity_entry.labels:
                continue
            domain = entity_entry.entity_id.split(".", 1)[0]
            if domain in new_members:
                new_members[domain].append(entity_entry.entity_id)

        changed = new_members != self._members
        self._members = new_members
        self._resubscribe_state_tracking()
        if changed:
            self._notify()

    def _resubscribe_state_tracking(self) -> None:
        if self._unsub_state:
            self._unsub_state()
            self._unsub_state = None

        all_members = [
            entity_id
            for domain_members in self._members.values()
            for entity_id in domain_members
        ]
        if not all_members:
            return

        self._unsub_state = async_track_state_change_event(
            self.hass, all_members, self._handle_state_changed
        )

    @callback
    def _handle_state_changed(self, event: Event) -> None:
        self._notify()
