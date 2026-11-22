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

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import parse_time_hm
from .const import DOMAIN
from .coordinator import Phk180Coordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PHK 180 time entities."""
    coordinator: Phk180Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([Phk180Systemuhrzeit(coordinator)])


class Phk180Systemuhrzeit(CoordinatorEntity[Phk180Coordinator], TimeEntity):
    """Native Time picker entity for PHK 180 system time (settings.htm T[0]/T[1])."""

    _attr_has_entity_name = True
    _attr_name = "Systemuhrzeit"
    _attr_icon = "mdi:clock-edit-outline"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: Phk180Coordinator) -> None:
        """Initialize the system time entity."""
        super().__init__(coordinator)
        self._attr_unique_id = "phk180_time_systemuhrzeit"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> time | None:
        """Return the current system time from settings.cgx (aktuelleUhrzeit)."""
        raw = (
            self.coordinator.get_val("settings", "aktuelleUhrzeit")
            or self.coordinator.get_val("settings", "aktuellesDatum")
            or self.coordinator.get_val("index", "aktuellesDatum")
        )
        parsed = parse_time_hm(raw)
        if parsed is None:
            return None
        return time(parsed[0], parsed[1])

    async def async_set_value(self, value: time) -> None:
        """Set device system time via adaptive closed-loop T[1]/T[0] requests."""
        await self.coordinator.api.async_set_time(value.hour, value.minute)
        await self.coordinator.async_request_refresh()
