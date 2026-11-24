"""
PHK 180 Local Web Control - Unofficial Community Integration for Home Assistant.

LEGAL DISCLAIMER / HAFTUNGSAUSSCHLUSS:
Dieses Softwareprojekt ist eine unabhängige, private und inoffizielle
Open-Source-Community-Entwicklung unter der MIT-Lizenz.
Es besteht keinerlei wirtschaftliche, organisatorische oder rechtliche
Verbindung zur AEREX HaustechnikSysteme GmbH oder der MAICO-Gruppe.
Marken- und Modellbezeichnungen (wie PHK 180 / PHS 300) werden ausschließlich
als technischer Kompatibilitätshinweis (§ 23 MarkenG) genannt.
Die Nutzung erfolgt vollständig auf eigene Gefahr.
"""
from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .api import Phk180Api
from .const import (
    CONF_INSTALL_DASHBOARD,
    DEFAULT_HOST,
    DEFAULT_INSTALL_DASHBOARD,
    DEFAULT_PASSWORD,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USERNAME,
    DOMAIN,
)


class Phk180ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PHK 180 Local Web Control (Unofficial)."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> Phk180OptionsFlow:
        """Return the options flow handler."""
        return Phk180OptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip().replace("http://", "").replace("https://", "").rstrip("/")
            username = user_input[CONF_USERNAME].strip()
            password = user_input.get(CONF_PASSWORD, "")

            await self.async_set_unique_id(host.lower())
            self._abort_if_unique_id_configured()

            api = Phk180Api(host=host, username=username, password=password)
            try:
                data = await api.async_fetch_all()
                if not data.get("details"):
                    errors["base"] = "cannot_connect"
                else:
                    clean_data = {**user_input, CONF_HOST: host}
                    return self.async_create_entry(
                        title=f"PHK180 ({host})",
                        data=clean_data,
                    )
            except Exception:
                errors["base"] = "cannot_connect"

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
                vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
                vol.Optional(CONF_PASSWORD, default=DEFAULT_PASSWORD): str,
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
                    vol.Coerce(int), vol.Range(min=5, max=300)
                ),
                vol.Optional(
                    CONF_INSTALL_DASHBOARD, default=DEFAULT_INSTALL_DASHBOARD
                ): bool,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )


class Phk180OptionsFlow(config_entries.OptionsFlow):
    """Handle PHK 180 options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        current_dashboard = self.config_entry.options.get(
            CONF_INSTALL_DASHBOARD,
            self.config_entry.data.get(
                CONF_INSTALL_DASHBOARD, DEFAULT_INSTALL_DASHBOARD
            ),
        )

        schema = vol.Schema(
            {
                vol.Optional(CONF_SCAN_INTERVAL, default=int(current_interval)): vol.All(
                    vol.Coerce(int), vol.Range(min=5, max=300)
                ),
                vol.Optional(
                    CONF_INSTALL_DASHBOARD, default=bool(current_dashboard)
                ): bool,
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
