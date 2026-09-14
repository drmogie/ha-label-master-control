"""Config flow for Label Master Control.

A wizard, same shape as Device Emulator's own "pick a type, then name
it" flow:
  1. async_step_user - pick which domain this device controls (light,
     switch, or fan). Fixed for the device's lifetime - a different
     domain is a different device, not something you migrate one into.
  2. async_step_labels - pick one or more labels. Membership is every
     entity of the chosen domain that carries ALL of these labels.
  3. async_step_name - name the device. Defaults to something built from
     the domain and label names, but you can type your own instead.

Its "Configure" option lets you change the label set (not the domain)
after creation - handy if you relabel things and want an existing
device to follow, without rebuilding it.
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

from .const import CONF_LABEL_IDS, CONF_TARGET_DOMAIN, DOMAIN, SUPPORTED_DOMAINS


def _label_names(hass, label_ids: list[str]) -> list[str]:
    registry = lr.async_get(hass)
    names = []
    for label_id in label_ids:
        label = registry.async_get_label(label_id)
        names.append(label.name if label else label_id)
    return names


def _suggested_name(hass, domain: str, label_ids: list[str]) -> str:
    names = sorted(_label_names(hass, label_ids))
    return f"{domain.title()} — {', '.join(names)}" if names else domain.title()


class LabelMasterControlConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Build one master device: domain, then labels, then a name."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Pick which domain this device controls."""
        if user_input is not None:
            self._data[CONF_TARGET_DOMAIN] = user_input[CONF_TARGET_DOMAIN]
            return await self.async_step_labels()

        schema = vol.Schema(
            {
                vol.Required(CONF_TARGET_DOMAIN): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            {"value": domain, "label": domain.title()}
                            for domain in SUPPORTED_DOMAINS
                        ],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_labels(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Pick one or more labels this device will require on every member."""
        if user_input is not None:
            self._data[CONF_LABEL_IDS] = user_input[CONF_LABEL_IDS]
            return await self.async_step_name()

        schema = vol.Schema(
            {
                vol.Required(CONF_LABEL_IDS): LabelSelector(
                    LabelSelectorConfig(multiple=True)
                )
            }
        )
        return self.async_show_form(step_id="labels", data_schema=schema)

    async def async_step_name(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Name the device, defaulting to domain + label names."""
        if user_input is not None:
            domain = self._data[CONF_TARGET_DOMAIN]
            label_ids = self._data[CONF_LABEL_IDS]
            await self.async_set_unique_id(f"{domain}:{'|'.join(sorted(label_ids))}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input["name"], data=self._data)

        default = _suggested_name(
            self.hass, self._data[CONF_TARGET_DOMAIN], self._data[CONF_LABEL_IDS]
        )
        schema = vol.Schema({vol.Required("name", default=default): str})
        return self.async_show_form(step_id="name", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return LabelMasterControlOptionsFlow()


class LabelMasterControlOptionsFlow(config_entries.OptionsFlow):
    """Change the label set (not the domain) after creation."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        entry = self.config_entry

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = entry.options.get(CONF_LABEL_IDS, entry.data.get(CONF_LABEL_IDS, []))
        schema = vol.Schema(
            {
                vol.Required(CONF_LABEL_IDS, default=current): LabelSelector(
                    LabelSelectorConfig(multiple=True)
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
