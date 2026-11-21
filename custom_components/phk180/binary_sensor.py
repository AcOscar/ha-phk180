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

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import Phk180Coordinator


@dataclass(frozen=True, kw_only=True)
class Phk180BinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describe a PHK 180 binary sensor (Schaltzustand)."""

    section: str
    xml_key: str
    off_value: str = "0"
    entity_category: EntityCategory = EntityCategory.DIAGNOSTIC


BINARY_SENSOR_DESCRIPTIONS: tuple[Phk180BinarySensorEntityDescription, ...] = (
    Phk180BinarySensorEntityDescription(
        key="ventilator_aussenluft",
        name="Ventilator Außenluft",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:fan",
        section="details",
        xml_key="Fan_State1",
    ),
    Phk180BinarySensorEntityDescription(
        key="ventilator_fortluft",
        name="Ventilator Fortluft",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:fan",
        section="details",
        xml_key="Fan_State2",
    ),
    Phk180BinarySensorEntityDescription(
        key="sommer_bypass_offen",
        name="Sommer-Bypass Offen",
        device_class=BinarySensorDeviceClass.OPENING,
        icon="mdi:valve-open",
        section="details",
        xml_key="BypassZustand",
        off_value="zu",
    ),
    Phk180BinarySensorEntityDescription(
        key="kompressor_warmepumpe",
        name="Kompressor (Wärmepumpe)",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:heat-pump",
        section="details",
        xml_key="HeatPump",
    ),
    Phk180BinarySensorEntityDescription(
        key="mv_anlaufentlastung",
        name="MV Anlaufentlastung",
        device_class=BinarySensorDeviceClass.OPENING,
        icon="mdi:valve",
        section="details",
        xml_key="MVAnlauf",
    ),
    Phk180BinarySensorEntityDescription(
        key="mv_flussigleitung",
        name="MV Flüssigleitung",
        device_class=BinarySensorDeviceClass.OPENING,
        icon="mdi:valve",
        section="details",
        xml_key="MV_Fluessig",
    ),
    Phk180BinarySensorEntityDescription(
        key="umschaltventil_trinkwasser_luft",
        name="Umschaltventil Trinkwasser/Luft",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:call-split",
        section="details",
        xml_key="MV_4_2_Wege",
    ),
    Phk180BinarySensorEntityDescription(
        key="speicherladepumpe",
        name="Speicherladepumpe",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:pump",
        section="details",
        xml_key="WpBrauchwasserpumpe",
    ),
    Phk180BinarySensorEntityDescription(
        key="sole_umwalzpumpe",
        name="Sole-Umwälzpumpe",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:pump",
        section="details",
        xml_key="SoleUwp",
    ),
    Phk180BinarySensorEntityDescription(
        key="e_heizstab_speicher",
        name="E-Heizstab Speicher",
        device_class=BinarySensorDeviceClass.HEAT,
        icon="mdi:heating-coil",
        section="details",
        xml_key="EHZ",
    ),
    Phk180BinarySensorEntityDescription(
        key="zusatzheizung_zuluft",
        name="Zusatzheizung Zuluft",
        device_class=BinarySensorDeviceClass.HEAT,
        icon="mdi:radiator",
        section="details",
        xml_key="ZHzuluft",
    ),
    Phk180BinarySensorEntityDescription(
        key="zusatzheizung_raum",
        name="Zusatzheizung Raum",
        device_class=BinarySensorDeviceClass.HEAT,
        icon="mdi:radiator",
        section="details",
        xml_key="ZHraum",
    ),
    Phk180BinarySensorEntityDescription(
        key="turkontakt_offen",
        name="Türkontakt Offen",
        device_class=BinarySensorDeviceClass.DOOR,
        section="details",
        xml_key="TuerKontakt",
    ),
    Phk180BinarySensorEntityDescription(
        key="evu_sperre_aktiv",
        name="EVU-Sperre Aktiv",
        device_class=BinarySensorDeviceClass.LOCK,
        section="details",
        xml_key="EVUSperre",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PHK 180 binary sensors."""
    coordinator: Phk180Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        Phk180BinarySensor(coordinator, desc)
        for desc in BINARY_SENSOR_DESCRIPTIONS
    )


class Phk180BinarySensor(
    CoordinatorEntity[Phk180Coordinator], BinarySensorEntity
):
    """Representation of a PHK 180 Binary Sensor."""

    entity_description: Phk180BinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: Phk180Coordinator,
        description: Phk180BinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"phk180_bin_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        val = str(
            self.coordinator.get_val(
                self.entity_description.section,
                self.entity_description.xml_key,
                self.entity_description.off_value,
            )
        ).strip()
        if self.entity_description.off_value != "0":
            return val != self.entity_description.off_value
        return val == "1"
