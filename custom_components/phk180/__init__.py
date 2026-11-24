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

from pathlib import Path
import voluptuous as vol

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv

from .api import Phk180Api
from .const import (
    DEFAULT_HOST,
    DEFAULT_PASSWORD,
    DEFAULT_USERNAME,
    DOMAIN,
    PLATFORMS,
    STATIC_URL_PATH,
)
from .coordinator import Phk180Coordinator

_STATIC_PATH_REGISTERED = "_static_path_registered"


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


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up PHK 180 Local Web Control from a config entry."""
    await _async_register_static_assets(hass)

    host = entry.data.get(CONF_HOST, DEFAULT_HOST)
    username = entry.data.get(CONF_USERNAME, DEFAULT_USERNAME)
    password = entry.data.get(CONF_PASSWORD, DEFAULT_PASSWORD)

    api = Phk180Api(host=host, username=username, password=password)
    coordinator = Phk180Coordinator(hass, entry, api)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

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
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
