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

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import extract_float
from .const import DOMAIN
from .coordinator import Phk180Coordinator


@dataclass(frozen=True, kw_only=True)
class Phk180NumberEntityDescription(NumberEntityDescription):
    """Describe a PHK 180 number entity."""

    endpoint_htm: str
    cgx_page: str
    section: str
    xml_key: str
    param_id: int
    param_idx: int = 0
    default_val: float = 0.0


NUMBER_DESCRIPTIONS: tuple[Phk180NumberEntityDescription, ...] = (
    Phk180NumberEntityDescription(
        key="raumsolltemperatur",
        name="Raumsolltemperatur",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=18.0,
        native_max_value=25.0,
        native_step=0.5,
        endpoint_htm="index.htm",
        cgx_page="index.cgx",
        section="index",
        xml_key="SollTempRaum",
        param_id=550,
        default_val=20.0,
    ),
    Phk180NumberEntityDescription(
        key="absenktemperatur_ferien",
        name="Absenktemperatur Ferien",
        icon="mdi:home-thermometer-outline",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=18.0,
        native_max_value=20.0,
        native_step=1.0,
        endpoint_htm="index.htm",
        cgx_page="index.cgx",
        section="index",
        xml_key="AbsenkTemperatur",
        param_id=547,
        default_val=18.0,
    ),
    Phk180NumberEntityDescription(
        key="warmwassersolltemperatur",
        name="Warmwassersolltemperatur",
        icon="mdi:water-thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=30.0,
        native_max_value=50.0,
        native_step=1.0,
        endpoint_htm="settings.htm",
        cgx_page="settings.cgx",
        section="settings",
        xml_key="WWS_T_Soll",
        param_id=951,
        default_val=45.0,
    ),
    Phk180NumberEntityDescription(
        key="ww_hysterese_warmepumpe",
        name="WW-Hysterese Wärmepumpe",
        icon="mdi:thermometer-chevron-up",
        native_unit_of_measurement="K",
        native_min_value=5.0,
        native_max_value=10.0,
        native_step=1.0,
        endpoint_htm="settings.htm",
        cgx_page="settings.cgx",
        section="settings",
        xml_key="Wp_WW_AusschaltHyst",
        param_id=964,
        default_val=5.0,
    ),
    Phk180NumberEntityDescription(
        key="ww_hysterese_e_heizstab",
        name="WW-Hysterese E-Heizstab",
        icon="mdi:heating-coil",
        native_unit_of_measurement="K",
        native_min_value=5.0,
        native_max_value=15.0,
        native_step=1.0,
        endpoint_htm="settings.htm",
        cgx_page="settings.cgx",
        section="settings",
        xml_key="EHZ_WW_AusschaltHyst",
        param_id=965,
        default_val=5.0,
    ),
    Phk180NumberEntityDescription(
        key="abgleich_raumtemperatur",
        name="Abgleich Raumtemperatur",
        icon="mdi:thermometer-plus",
        native_unit_of_measurement="K",
        native_min_value=-3.0,
        native_max_value=3.0,
        native_step=0.1,
        endpoint_htm="settings.htm",
        cgx_page="settings.cgx",
        section="settings",
        xml_key="Raumtempabgleich",
        param_id=551,
        default_val=0.0,
    ),
    Phk180NumberEntityDescription(
        key="einschaltpunkt_zh_zuluft",
        name="Einschaltpunkt ZH Zuluft",
        icon="mdi:radiator",
        native_unit_of_measurement="K",
        native_min_value=-2.0,
        native_max_value=-0.4,
        native_step=0.1,
        endpoint_htm="settings.htm",
        cgx_page="settings.cgx",
        section="settings",
        xml_key="ZhEinschaltpunkt",
        param_id=553,
        default_val=-0.7,
    ),
    Phk180NumberEntityDescription(
        key="dauer_stossluftung",
        name="Dauer Stoßlüftung",
        icon="mdi:timer-cog-outline",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        native_min_value=5.0,
        native_max_value=90.0,
        native_step=5.0,
        endpoint_htm="settings.htm",
        cgx_page="settings.cgx",
        section="settings",
        xml_key="IL_Dauer",
        param_id=230,
        default_val=30.0,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PHK 180 number entities."""
    coordinator: Phk180Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        Phk180Number(coordinator, desc) for desc in NUMBER_DESCRIPTIONS
    )


class Phk180Number(CoordinatorEntity[Phk180Coordinator], NumberEntity):
    """Representation of a PHK 180 Number with closed-loop limit enforcement."""

    entity_description: Phk180NumberEntityDescription
    _attr_has_entity_name = True
    _attr_mode = NumberMode.SLIDER

    def __init__(
        self,
        coordinator: Phk180Coordinator,
        description: Phk180NumberEntityDescription,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"phk180_num_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def native_max_value(self) -> float:
        """Dynamically enforce coupled system sum limits for WW hysteresis (55 °C / 60 °C)."""
        base_max = float(self.entity_description.native_max_value)
        if self.entity_description.param_id == 964:
            ww_soll = extract_float(
                self.coordinator.get_val("settings", "WWS_T_Soll"), 45.0
            )
            return min(base_max, max(5.0, 55.0 - ww_soll))
        if self.entity_description.param_id == 965:
            ww_soll = extract_float(
                self.coordinator.get_val("settings", "WWS_T_Soll"), 45.0
            )
            return min(base_max, max(5.0, 60.0 - ww_soll))
        return base_max

    @property
    def native_value(self) -> float:
        """Return the current value."""
        raw = self.coordinator.get_val(
            self.entity_description.section, self.entity_description.xml_key
        )
        return extract_float(raw, self.entity_description.default_val)

    async def async_set_native_value(self, value: float) -> None:
        """Set new value using closed-loop step verification."""
        await self.coordinator.api.async_set_step_value(
            endpoint_htm=self.entity_description.endpoint_htm,
            cgx_page=self.entity_description.cgx_page,
            xml_id=self.entity_description.xml_key,
            param_id=self.entity_description.param_id,
            param_idx=self.entity_description.param_idx,
            step_size=float(self.entity_description.native_step),
            target_val=value,
        )
        await self.coordinator.async_request_refresh()
