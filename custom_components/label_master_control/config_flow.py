"""Config flow for Label Master Control.

  - The main "Add integration" flow (LabelMasterControlConfigFlow) asks
    for one label and creates a device for it, titled after the label's
    own name.
  - Each device's "Configure" option (LabelMasterControlOptionsFlow)
    lets you reassign the label, or pin the light domain's representative
    entity (the one whose brightness/color the master light reports) to
    a specific currently-labeled light instead of the default
    first-found.
"""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import label_registry as lr
from homeassistant.helpers.selector import (
    LabelSelector,
    LabelSelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import CONF_LABEL_ID, CONF_REPRESENTATIVE_LIGHT, DOMAIN

FIRST_FOUND = "__first_found__"


def _label_name(hass, label_id: str) -> str:
    registry = lr.async_get(hass)
    label = registry.async_get_label(label_id)
    return label.name if label else label_id


class LabelMasterControlConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Pick a label; creates one device tracking it."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask which label this device should track."""
        if user_input is not None:
            label_id = user_input[CONF_LABEL_ID]
            await self.async_set_unique_id(label_id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=_label_name(self.hass, label_id),
                data={CONF_LABEL_ID: label_id},
            )

        schema = vol.Schema({vol.Required(CONF_LABEL_ID): LabelSelector(LabelSelectorConfig())})
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return LabelMasterControlOptionsFlow()


class LabelMasterControlOptionsFlow(config_entries.OptionsFlow):
    """Reassign the label, or pick the light domain's representative."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        entry = self.config_entry
        aggregator = self.hass.data.get(DOMAIN, {}).get(entry.entry_id, {}).get("aggregator")
        current_lights = aggregator.members("light") if aggregator else []

        if user_input is not None:
            new_label = user_input[CONF_LABEL_ID]
            representative = user_input.get(CONF_REPRESENTATIVE_LIGHT)
            if representative == FIRST_FOUND:
                representative = None

            if new_label != entry.data.get(CONF_LABEL_ID):
                self.hass.config_entries.async_update_entry(
                    entry, data={**entry.data, CONF_LABEL_ID: new_label}
                )
            return self.async_create_entry(
                title="", data={CONF_REPRESENTATIVE_LIGHT: representative}
            )

        light_options = [{"value": FIRST_FOUND, "label": "Use first found"}] + [
            {"value": entity_id, "label": entity_id} for entity_id in current_lights
        ]
        current_representative = entry.options.get(CONF_REPRESENTATIVE_LIGHT) or FIRST_FOUND

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_LABEL_ID, default=entry.data.get(CONF_LABEL_ID)
                ): LabelSelector(LabelSelectorConfig()),
                vol.Required(
                    CONF_REPRESENTATIVE_LIGHT, default=current_representative
                ): SelectSelector(
                    SelectSelectorConfig(options=light_options, mode=SelectSelectorMode.DROPDOWN)
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
