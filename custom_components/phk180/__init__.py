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

import logging
from pathlib import Path
from typing import Any
import voluptuous as vol

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace import dashboard as lovelace_dashboard
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv

from .api import Phk180Api
from .const import (
    CONF_INSTALL_DASHBOARD,
    DASHBOARD_ICON,
    DASHBOARD_TITLE,
    DASHBOARD_URL_PATH,
    DEFAULT_HOST,
    DEFAULT_INSTALL_DASHBOARD,
    DEFAULT_PASSWORD,
    DEFAULT_USERNAME,
    DOMAIN,
    PLATFORMS,
    STATIC_URL_PATH,
)
from .coordinator import Phk180Coordinator

_LOGGER = logging.getLogger(__name__)
_STATIC_PATH_REGISTERED = "_static_path_registered"
_DASHBOARD_REGISTERED = "_dashboard_registered"


def _get_lovelace_dashboards(hass: HomeAssistant) -> dict[str, Any] | None:
    """Return Home Assistant's Lovelace dashboards mapping across HA versions."""
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA
    except ImportError:
        LOVELACE_DATA = "lovelace"

    lovelace_data = hass.data.get(LOVELACE_DATA) or hass.data.get("lovelace")
    if lovelace_data is None:
        return None
    if hasattr(lovelace_data, "dashboards"):
        return lovelace_data.dashboards
    if isinstance(lovelace_data, dict):
        return lovelace_data.get("dashboards")
    return None


async def _async_register_static_assets(hass: HomeAssistant) -> None:
    """Register bundled graphics under /phk180 once per Home Assistant instance."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(_STATIC_PATH_REGISTERED) or hass.http is None:
        return

    static_dir = Path(__file__).parent / "www"
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                url_path=STATIC_URL_PATH,
                path=str(static_dir),
                cache_headers=True,
            )
        ]
    )
    domain_data[_STATIC_PATH_REGISTERED] = True


def _register_dashboard(hass: HomeAssistant) -> None:
    """Register the bundled PHK 180 YAML dashboard in the Home Assistant sidebar."""
    dashboards = _get_lovelace_dashboards(hass)
    if dashboards is None:
        _LOGGER.warning(
            "Lovelace ist nicht geladen – PHK 180 Dashboard konnte nicht registriert werden."
        )
        return

    dashboard_file = Path(__file__).parent / "dashboards" / "phk180_dashboard.yaml"
    dashboard_config = {
        "mode": "yaml",
        "filename": str(dashboard_file),
        "title": DASHBOARD_TITLE,
        "icon": DASHBOARD_ICON,
        "show_in_sidebar": True,
        "require_admin": False,
    }
    dashboards[DASHBOARD_URL_PATH] = lovelace_dashboard.LovelaceYAML(
        hass, DASHBOARD_URL_PATH, dashboard_config
    )
    frontend.async_register_built_in_panel(
        hass,
        "lovelace",
        frontend_url_path=DASHBOARD_URL_PATH,
        sidebar_title=DASHBOARD_TITLE,
        sidebar_icon=DASHBOARD_ICON,
        require_admin=False,
        show_in_sidebar=True,
        config={"mode": "yaml"},
        update=True,
    )
    hass.data.setdefault(DOMAIN, {})[_DASHBOARD_REGISTERED] = True


def _unregister_dashboard(hass: HomeAssistant) -> None:
    """Remove the bundled PHK 180 dashboard from the sidebar if registered."""
    domain_data = hass.data.get(DOMAIN, {})
    if not domain_data.get(_DASHBOARD_REGISTERED):
        return

    dashboards = _get_lovelace_dashboards(hass)
    if isinstance(dashboards, dict):
        dashboards.pop(DASHBOARD_URL_PATH, None)
    frontend.async_remove_panel(hass, DASHBOARD_URL_PATH)
    domain_data[_DASHBOARD_REGISTERED] = False


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up PHK 180 Local Web Control from a config entry."""
    await _async_register_static_assets(hass)

    install_dashboard = entry.options.get(
        CONF_INSTALL_DASHBOARD,
        entry.data.get(CONF_INSTALL_DASHBOARD, DEFAULT_INSTALL_DASHBOARD),
    )
    if install_dashboard:
        _register_dashboard(hass)
    else:
        _unregister_dashboard(hass)

    host = entry.data.get(CONF_HOST, DEFAULT_HOST)
    username = entry.data.get(CONF_USERNAME, DEFAULT_USERNAME)
    password = entry.data.get(CONF_PASSWORD, DEFAULT_PASSWORD)

    api = Phk180Api(host=host, username=username, password=password)
    coordinator = Phk180Coordinator(hass, entry, api)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_set_vacation_return_date(call: ServiceCall) -> None:
        return_date = call.data["return_date"]
        date_obj = cv.date(return_date)
        formatted = date_obj.strftime("%d-%m-%Y")
        await api.async_send_cmd("index.htm", "D[1]", formatted)
        await coordinator.async_request_refresh()

    async def handle_sync_system_date(call: ServiceCall) -> None:
        from homeassistant.util import dt as dt_util
        now_str = dt_util.now().strftime("%d-%m-%Y")
        await api.async_set_date(now_str)
        await coordinator.async_request_refresh()

    async def handle_sync_system_datetime(call: ServiceCall) -> None:
        from homeassistant.util import dt as dt_util
        now = dt_util.now()
        await api.async_sync_datetime(now.strftime("%d-%m-%Y"), now.hour, now.minute)
        await coordinator.async_request_refresh()

    if not hass.services.has_service(DOMAIN, "set_vacation_return_date"):
        hass.services.async_register(
            DOMAIN,
            "set_vacation_return_date",
            handle_set_vacation_return_date,
            schema=vol.Schema({vol.Required("return_date"): cv.string}),
        )

    if not hass.services.has_service(DOMAIN, "sync_system_date"):
        hass.services.async_register(
            DOMAIN,
            "sync_system_date",
            handle_sync_system_date,
        )

    if not hass.services.has_service(DOMAIN, "sync_system_datetime"):
        hass.services.async_register(
            DOMAIN,
            "sync_system_datetime",
            handle_sync_system_datetime,
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        domain_data = hass.data[DOMAIN]
        domain_data.pop(entry.entry_id, None)
        remaining_entries = [
            k for k in domain_data if not k.startswith("_")
        ]
        if not remaining_entries:
            _unregister_dashboard(hass)
    return unload_ok
