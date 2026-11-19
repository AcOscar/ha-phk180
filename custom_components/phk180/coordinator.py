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

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import Phk180Api
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class Phk180Coordinator(DataUpdateCoordinator[dict[str, dict[str, str]]]):
    """Coordinator to manage polling the 3 .cgx XML endpoints."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: Phk180Api) -> None:
        """Initialize the coordinator."""
        self.api = api
        self.entry = entry
        scan_interval = entry.options.get(
            "scan_interval", entry.data.get("scan_interval", DEFAULT_SCAN_INTERVAL)
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=int(scan_interval)),
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry info representing the physical PHK 180 hardware unit."""
        sw_lt = self.get_val("details", "SwVersionLT", "1.0.6")
        sw_bde = self.get_val("details", "SwVersionBDE", "1.0.4")
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name="PHK180",
            manufacturer="Community Integration (Kompatibel mit AEREX PHK 180)",
            model="PHK 180 / PHS 300",
            sw_version=f"LT {sw_lt} / BDE {sw_bde}",
            configuration_url=f"http://{self.api.host}/index.htm",
        )

    def get_val(self, section: str, key: str, default: Any = None) -> Any:
        """Safely retrieve a value from the cached XML dictionary."""
        if not self.data or section not in self.data:
            return default
        val = self.data[section].get(key)
        if val is None or val == "":
            return default
        return val

    async def _async_update_data(self) -> dict[str, dict[str, str]]:
        """Fetch latest data from the PHK 180."""
        try:
            return await self.api.async_fetch_all()
        except Exception as err:
            raise UpdateFailed(f"Fehler beim Abrufen der PHK 180 Daten: {err}") from err
