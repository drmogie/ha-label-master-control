"""Config flow for Label Master Control.

One entry for the whole integration - installing it just turns the
feature on and asks for a grouping mode; it never asks you to pick a
label. Every actual device is discovered afterward from your entities'
own labels (see group_tracker.py).
"""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_GROUPING_MODE,
    DEFAULT_GROUPING_MODE,
    DOMAIN,
    GROUPING_EXACT,
    GROUPING_PAIRS,
    SINGLETON_UNIQUE_ID,
)

_MODE_OPTIONS = [
    {"value": GROUPING_EXACT, "label": "Exact label match"},
    {"value": GROUPING_PAIRS, "label": "Shared label pairs"},
]


def _mode_schema(default: str) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_GROUPING_MODE, default=default): SelectSelector(
                SelectSelectorConfig(options=_MODE_OPTIONS, mode=SelectSelectorMode.DROPDOWN)
            )
        }
    )


class LabelMasterControlConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """One-time setup: turn the feature on and pick a grouping mode."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        await self.async_set_unique_id(SINGLETON_UNIQUE_ID)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(title="Label Master Control", data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=_mode_schema(DEFAULT_GROUPING_MODE)
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return LabelMasterControlOptionsFlow()


class LabelMasterControlOptionsFlow(config_entries.OptionsFlow):
    """Change the grouping mode later."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get(
            CONF_GROUPING_MODE,
            self.config_entry.data.get(CONF_GROUPING_MODE, DEFAULT_GROUPING_MODE),
        )
        return self.async_show_form(step_id="init", data_schema=_mode_schema(current))
