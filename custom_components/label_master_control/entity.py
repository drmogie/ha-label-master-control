"""Shared plumbing for every master entity."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import label_registry as lr
from homeassistant.helpers.entity import DeviceInfo, Entity

from .aggregator import LabelAggregator
from .const import CONF_LABEL_IDS, CONF_TARGET_DOMAIN, DOMAIN, MANUFACTURER


def device_info_for(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer=MANUFACTURER,
        model=f"{entry.data[CONF_TARGET_DOMAIN].title()} label group",
    )


class MasterEntity(Entity):
    """Base for every master entity: hooks itself to its aggregator."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_name = None  # the device's own name already describes this entity

    def __init__(self, entry: ConfigEntry, aggregator: LabelAggregator) -> None:
        self._entry = entry
        self._aggregator = aggregator
        self._attr_device_info = device_info_for(entry)
        self._unsub_listener = None

    def _label_names(self) -> list[str]:
        """Resolve this device's configured label IDs to their display names.

        Added 2026.09.20 so an outside consumer (the companion Matrix Card,
        or anyone else's automation/template) can tell WHICH labels a given
        master device was built from without already knowing its entry_id
        or guessing from its display name - the device's domain + label
        names together are enough to place it on a grid keyed by category
        label and target domain.
        """
        registry = lr.async_get(self.hass)
        label_ids = self._entry.options.get(
            CONF_LABEL_IDS, self._entry.data.get(CONF_LABEL_IDS, [])
        )
        names = []
        for label_id in label_ids:
            label = registry.async_get_label(label_id)
            names.append(label.name if label else label_id)
        return names

    @property
    def extra_state_attributes(self) -> dict[str, list[str]]:
        """Expose current members the same way HA's own group entities do.

        `entity_id` is the attribute HA's frontend already looks for to
        populate an entity's More info -> Related tab (it's how a native
        Light/Switch/Cover Group shows what it's made of) - reusing it here
        means Settings -> Devices & services -> Entities -> this entity ->
        Related shows exactly what's currently being controlled, live, with
        no extra UI to build.

        `labels` (added 2026.09.20) is this device's own configured label
        set, by name - see `_label_names()` above.
        """
        return {"entity_id": self._aggregator.members(), "labels": self._label_names()}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._unsub_listener = self._aggregator.add_listener(self._handle_aggregator_update)

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub_listener:
            self._unsub_listener()
            self._unsub_listener = None
        await super().async_will_remove_from_hass()

    def _handle_aggregator_update(self) -> None:
        self.async_write_ha_state()
