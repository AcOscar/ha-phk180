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
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import Phk180Coordinator


@dataclass(frozen=True, kw_only=True)
class Phk180SwitchEntityDescription(SwitchEntityDescription):
    """Describe a PHK 180 switch."""

    endpoint_htm: str
    param: str
    val: str
    section: str
    xml_key: str
    on_string: str


SWITCH_DESCRIPTIONS: tuple[Phk180SwitchEntityDescription, ...] = (
    Phk180SwitchEntityDescription(
        key="stossluftung",
        name="Stoßlüftung",
        icon="mdi:fan-plus",
        endpoint_htm="index.htm",
        param="S[229][0]",
        val="0",
        section="index",
        xml_key="IL_Aktiv_string",
        on_string="ja",
    ),
    Phk180SwitchEntityDescription(
        key="sommerbetrieb_jahreszeit",
        name="Sommerbetrieb (Jahreszeit)",
        icon="mdi:white-balance-sunny",
        endpoint_htm="index.htm",
        param="S[523][0]",
        val="0",
        section="index",
        xml_key="Jahreszeitstring",
        on_string="Sommer",
    ),
    Phk180SwitchEntityDescription(
        key="legionellenschutz",
        name="Legionellenschutz",
        icon="mdi:bacteria-outline",
        endpoint_htm="settings.htm",
        param="S[958][0]",
        val="0",
        section="settings",
        xml_key="LegionellenSchutzstring",
        on_string="ja",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PHK 180 switches."""
    coordinator: Phk180Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        Phk180Switch(coordinator, desc) for desc in SWITCH_DESCRIPTIONS
    )


class Phk180Switch(CoordinatorEntity[Phk180Coordinator], SwitchEntity):
    """Representation of a PHK 180 toggle switch."""

    entity_description: Phk180SwitchEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: Phk180Coordinator,
        description: Phk180SwitchEntityDescription,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"phk180_switch_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        cur = str(
            self.coordinator.get_val(
                self.entity_description.section, self.entity_description.xml_key, ""
            )
        ).strip()
        return cur == self.entity_description.on_string

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on (only send toggle if currently off)."""
        if not self.is_on:
            await self.coordinator.api.async_send_cmd(
                self.entity_description.endpoint_htm,
                self.entity_description.param,
                self.entity_description.val,
            )
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off (only send toggle if currently on)."""
        if self.is_on:
            await self.coordinator.api.async_send_cmd(
                self.entity_description.endpoint_htm,
                self.entity_description.param,
                self.entity_description.val,
            )
            await self.coordinator.async_request_refresh()
