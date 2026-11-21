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

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import extract_int
from .const import DOMAIN
from .coordinator import Phk180Coordinator

BETRIEBSART_MAP = {
    0: "Aus",
    1: "Warmwasser",
    2: "Manuell",
    3: "Auto Zeit",
    4: "Auto Sensor",
    5: "Ferien",
    6: "Ferien",
}

BETRIEBSART_REV_MAP = {
    "Auto Zeit": 3,
    "Auto Sensor": 4,
    "Manuell": 2,
    "Warmwasser": 1,
    "Ferien": 6,
    "Aus": 0,
}

FAN_LEVEL_REV_MAP = {
    "Aus": 0,
    "Feuchteschutz": 1,
    "Reduziert": 2,
    "Nenn": 3,
    "Intensiv": 4,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PHK 180 select entities."""
    coordinator: Phk180Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            Phk180BetriebsartSelect(coordinator),
            Phk180LueftungsstufeSelect(coordinator),
        ]
    )


class Phk180BetriebsartSelect(CoordinatorEntity[Phk180Coordinator], SelectEntity):
    """Select entity for PHK 180 operating mode (P[522][0])."""

    _attr_has_entity_name = True
    _attr_name = "Betriebsart Auswahl"
    _attr_icon = "mdi:thermostat-cog"
    _attr_options = list(BETRIEBSART_REV_MAP.keys())

    def __init__(self, coordinator: Phk180Coordinator) -> None:
        """Initialize the operating mode select."""
        super().__init__(coordinator)
        self._attr_unique_id = "phk180_select_betriebsart"
        self._attr_device_info = coordinator.device_info

    @property
    def current_option(self) -> str:
        """Return the current selected operating mode."""
        mode = extract_int(self.coordinator.get_val("index", "Betriebsmode", "3"), 3)
        return BETRIEBSART_MAP.get(mode, "Auto Zeit")

    async def async_select_option(self, option: str) -> None:
        """Change the selected operating mode."""
        val = BETRIEBSART_REV_MAP.get(option, 3)
        await self.coordinator.api.async_send_cmd("index.htm", "P[522][0]", val)
        await self.coordinator.async_request_refresh()


class Phk180LueftungsstufeSelect(CoordinatorEntity[Phk180Coordinator], SelectEntity):
    """Select entity for PHK 180 fan speed level (P[225][0])."""

    _attr_has_entity_name = True
    _attr_name = "Lüftungsstufe Auswahl"
    _attr_icon = "mdi:fan-speed-2"
    _attr_options = list(FAN_LEVEL_REV_MAP.keys())

    def __init__(self, coordinator: Phk180Coordinator) -> None:
        """Initialize the fan level select."""
        super().__init__(coordinator)
        self._attr_unique_id = "phk180_select_lueftungsstufe"
        self._attr_device_info = coordinator.device_info

    @property
    def current_option(self) -> str:
        """Return the current fan speed level."""
        raw = str(self.coordinator.get_val("index", "FanMode", "Nenn"))
        if "Intensiv" in raw:
            return "Intensiv"
        if "Nenn" in raw:
            return "Nenn"
        if "Reduziert" in raw:
            return "Reduziert"
        if "Feuchte" in raw:
            return "Feuchteschutz"
        if "Aus" in raw:
            return "Aus"
        return "Nenn"

    async def async_select_option(self, option: str) -> None:
        """Change the selected fan speed level."""
        val = FAN_LEVEL_REV_MAP.get(option, 3)
        await self.coordinator.api.async_send_cmd("index.htm", "P[225][0]", val)
        await self.coordinator.async_request_refresh()
