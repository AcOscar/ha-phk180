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

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import Phk180Coordinator


@dataclass(frozen=True, kw_only=True)
class Phk180ButtonEntityDescription(ButtonEntityDescription):
    """Describe a PHK 180 button."""

    endpoint_htm: str
    param: str
    val: str


BUTTON_DESCRIPTIONS: tuple[Phk180ButtonEntityDescription, ...] = (
    Phk180ButtonEntityDescription(
        key="storung_reset",
        name="Störung Reset",
        icon="mdi:restart-alert",
        endpoint_htm="index.htm",
        param="S[313][0]",
        val="-",
    ),
    Phk180ButtonEntityDescription(
        key="filterwechsel_geratefilter_quittieren",
        name="Filterwechsel Gerätefilter Quittieren",
        icon="mdi:air-filter",
        endpoint_htm="index.htm",
        param="S[241][0]",
        val="-",
    ),
    Phk180ButtonEntityDescription(
        key="filterwechsel_aussenfilter_quittieren",
        name="Filterwechsel Außenfilter Quittieren",
        icon="mdi:air-filter",
        endpoint_htm="index.htm",
        param="S[241][1]",
        val="-",
    ),
    Phk180ButtonEntityDescription(
        key="wp_vorrangschaltung_umschalten",
        name="WP Vorrangschaltung Umschalten",
        icon="mdi:swap-horizontal",
        endpoint_htm="settings.htm",
        param="S[272][0]",
        val="0",
    ),
    Phk180ButtonEntityDescription(
        key="ferienbetrieb_beenden",
        name="Ferienbetrieb Beenden",
        icon="mdi:home-import-outline",
        endpoint_htm="index.htm",
        param="P[522][0]",
        val="3",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PHK 180 buttons."""
    coordinator: Phk180Coordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[ButtonEntity] = [
        Phk180Button(coordinator, desc) for desc in BUTTON_DESCRIPTIONS
    ]
    entities.append(Phk180SyncDateTimeButton(coordinator))
    async_add_entities(entities)


class Phk180Button(CoordinatorEntity[Phk180Coordinator], ButtonEntity):
    """Representation of a PHK 180 Button."""

    entity_description: Phk180ButtonEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: Phk180Coordinator,
        description: Phk180ButtonEntityDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"phk180_btn_{description.key}"
        self._attr_device_info = coordinator.device_info

    async def async_press(self) -> None:
        """Press the button."""
        await self.coordinator.api.async_send_cmd(
            self.entity_description.endpoint_htm,
            self.entity_description.param,
            self.entity_description.val,
        )
        await self.coordinator.async_request_refresh()


class Phk180SyncDateTimeButton(CoordinatorEntity[Phk180Coordinator], ButtonEntity):
    """Button to synchronize PHK 180 date and time with Home Assistant."""

    _attr_has_entity_name = True
    _attr_name = "Systemzeit Synchronisieren"
    _attr_icon = "mdi:clock-sync"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: Phk180Coordinator) -> None:
        """Initialize the sync date/time button."""
        super().__init__(coordinator)
        self._attr_unique_id = "phk180_btn_systemzeit_synchronisieren"
        self._attr_device_info = coordinator.device_info

    async def async_press(self) -> None:
        """Synchronize system time (T[1]/T[0]) and date (D[0]) with Home Assistant."""
        now = dt_util.now()
        await self.coordinator.api.async_sync_datetime(
            now.strftime("%d-%m-%Y"), now.hour, now.minute
        )
        await self.coordinator.async_request_refresh()
