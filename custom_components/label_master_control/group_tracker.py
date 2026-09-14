"""Live label-combination discovery and grouping engine.

There is no "pick a label, get a device" config flow. Instead this
watches every entity in the registry, and for each domain it cares about
(light/switch/fan) works out which entities should be grouped together
based purely on which labels they carry. A group appearing or
disappearing is a normal side effect of you labeling/unlabeling entities
through Home Assistant's own entity settings - nothing integration-
specific about that step.

Two grouping modes (chosen once, in the integration's own options):
  - "exact": a group's key is an entity's FULL label set. Two entities
    only share a device if they carry EXACTLY the same labels - simplest
    to predict, but adding any unrelated label to an entity splits it
    into a new group.
  - "pairs": a group's key is every unordered PAIR of labels an entity
    carries (an entity with 3 labels participates in 3 pair-groups at
    once, one per pair). This tolerates extra, unrelated labels riding
    along on the same entity - closer to how the original template's
    two-label intersection behaved - at the cost of an entity
    potentially belonging to more than one group.

GroupTracker recomputes every group on every entity_registry_updated
event (a full rescan is cheap - just an in-memory registry walk, no I/O)
and diffs the result against what it had, calling on_added / on_removed /
on_changed callbacks so the platform modules can create, remove, or
refresh master entities to match - see light.py / switch.py / fan.py.
"""
from __future__ import annotations

from collections.abc import Callable
from itertools import combinations
import logging

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er, label_registry as lr

from .const import GROUPING_PAIRS, SUPPORTED_DOMAINS

_LOGGER = logging.getLogger(__name__)

GroupKey = tuple[str, frozenset[str]]  # (domain, label_ids)


class GroupTracker:
    """Derives (domain, label-combination) groups from the registries, live."""

    def __init__(self, hass: HomeAssistant, grouping_mode: str) -> None:
        self.hass = hass
        self.grouping_mode = grouping_mode
        self._groups: dict[GroupKey, list[str]] = {}
        self._on_added: list[Callable[[GroupKey], None]] = []
        self._on_removed: list[Callable[[GroupKey], None]] = []
        self._on_changed: list[Callable[[GroupKey], None]] = []
        self._unsub_registry: Callable[[], None] | None = None

    def label_names(self, label_ids: frozenset[str]) -> list[str]:
        registry = lr.async_get(self.hass)
        names = []
        for label_id in label_ids:
            label = registry.async_get_label(label_id)
            names.append(label.name if label else label_id)
        return names

    def members(self, key: GroupKey) -> list[str]:
        return list(self._groups.get(key, []))

    def groups_for_domain(self, domain: str) -> list[GroupKey]:
        return [key for key in self._groups if key[0] == domain]

    def on_added(self, cb: Callable[[GroupKey], None]) -> None:
        self._on_added.append(cb)

    def on_removed(self, cb: Callable[[GroupKey], None]) -> None:
        self._on_removed.append(cb)

    def on_changed(self, cb: Callable[[GroupKey], None]) -> None:
        self._on_changed.append(cb)

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

    @callback
    def _handle_registry_updated(self, event: Event) -> None:
        # An entity's labels (among other things) may have changed - the
        # cheapest correct response is a full rescan rather than working
        # out whether this particular change affects any group.
        self._rescan()

    def _keys_for_labels(self, labels: frozenset[str]) -> list[frozenset[str]]:
        if not labels:
            return []
        if self.grouping_mode == GROUPING_PAIRS:
            if len(labels) < 2:
                return []
            return [frozenset(pair) for pair in combinations(sorted(labels), 2)]
        return [labels]  # exact mode: the whole label set is the one key

    def _rescan(self) -> None:
        registry = er.async_get(self.hass)
        new_groups: dict[GroupKey, list[str]] = {}

        for entity_entry in registry.entities.values():
            domain = entity_entry.entity_id.split(".", 1)[0]
            if domain not in SUPPORTED_DOMAINS:
                continue
            labels = frozenset(entity_entry.labels)
            for label_key in self._keys_for_labels(labels):
                group_key: GroupKey = (domain, label_key)
                new_groups.setdefault(group_key, []).append(entity_entry.entity_id)

        old_keys = set(self._groups)
        new_keys = set(new_groups)

        for key in new_keys - old_keys:
            self._groups[key] = new_groups[key]
            self._fire(self._on_added, key)
        for key in old_keys - new_keys:
            del self._groups[key]
            self._fire(self._on_removed, key)
        for key in new_keys & old_keys:
            if new_groups[key] != self._groups[key]:
                self._groups[key] = new_groups[key]
                self._fire(self._on_changed, key)

    def _fire(self, callbacks: list[Callable[[GroupKey], None]], key: GroupKey) -> None:
        for cb in list(callbacks):
            cb(key)
