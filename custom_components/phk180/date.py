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

from datetime import date, datetime

from homeassistant.components.date import DateEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import Phk180Coordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PHK 180 date entities."""
    coordinator: Phk180Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([Phk180FerienRueckreisedatum(coordinator)])


class Phk180FerienRueckreisedatum(
    CoordinatorEntity[Phk180Coordinator], DateEntity
):
    """Native Date picker entity for PHK 180 vacation return date (D[1])."""

    _attr_has_entity_name = True
    _attr_name = "Ferien Rückreisedatum"
    _attr_icon = "mdi:calendar-export"

    def __init__(self, coordinator: Phk180Coordinator) -> None:
        """Initialize the vacation return date entity."""
        super().__init__(coordinator)
        self._attr_unique_id = "phk180_date_ferien_rueckreisedatum"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> date | None:
        """Return the currently configured vacation return date from index.cgx (FerienEnde)."""
        raw = str(self.coordinator.get_val("index", "FerienEnde", "00.00.2000")).strip()
        if not raw or raw == "00.00.2000":
            return None
        for fmt in ("%d.%m.%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
        return None

    async def async_set_value(self, value: date) -> None:
        """Send new vacation return date in format DD-MM-YYYY to index.htm?D[1]=..."""
        formatted = value.strftime("%d-%m-%Y")
        await self.coordinator.api.async_send_cmd("index.htm", "D[1]", formatted)
        await self.coordinator.async_request_refresh()
