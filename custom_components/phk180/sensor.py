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
from typing import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import extract_float, extract_int
from .const import DOMAIN
from .coordinator import Phk180Coordinator


@dataclass(frozen=True, kw_only=True)
class Phk180SensorEntityDescription(SensorEntityDescription):
    """Describe an PHK 180 sensor entity."""

    section: str
    xml_key: str
    value_fn: Callable[[Phk180Coordinator], str | int | float | None] | None = None
    parse_mode: str = "str"  # "str", "float", "int"


def _compute_error_text(coord: Phk180Coordinator) -> str:
    err_id = extract_int(coord.get_val("index", "Error_Id1", "0"), 0)
    sub_id = extract_int(coord.get_val("index", "Error_SubId1", "0"), 0)
    if err_id == 0:
        return "Kein Fehler"
    if err_id == 1:
        if sub_id in (1, 3, 5):
            return "Ventilator Außenluft"
        if sub_id in (2, 4, 6):
            return "Ventilator Fortluft"
        return f"Lüfterfehler ({sub_id})"
    if err_id == 2:
        if sub_id == 1:
            return "Kommunikation Haupt-Bedienteil"
        if sub_id == 2:
            return "Kommunikation GSM-Modul"
        return "Kommunikationsfehler"
    if err_id == 3:
        return f"Sensorfehler (Sub-ID {sub_id})"
    if err_id == 4:
        return "Systemspeicher" if sub_id == 1 else "System-Bus"
    if err_id == 5:
        if sub_id == 1:
            return "Wärmepumpe Niederdruck"
        if sub_id == 2:
            return "Wärmepumpe Hochdruck"
        if sub_id == 3:
            return "Wärmepumpe Abtauzeit"
        return "WP Fehler"
    if err_id == 6:
        return "Sicherheitstemperaturbegrenzer Speicher"
    if err_id == 7:
        if sub_id == 1:
            return "T-Lufteintritt zu kalt"
        if sub_id == 2:
            return "T-Zuluft zu kalt"
        return "Temperaturfehler"
    return f"Unbekannter Fehler ({err_id}/{sub_id})"


SENSOR_DESCRIPTIONS: tuple[Phk180SensorEntityDescription, ...] = (
    # --- Betriebsart & Ferien ---
    Phk180SensorEntityDescription(
        key="betriebsart",
        name="PHK180 Betriebsart",
        icon="mdi:thermostat-cog",
        section="index",
        xml_key="Betriebsartstring",
    ),
    Phk180SensorEntityDescription(
        key="ferien_ruckkehrdatum_gerat",
        name="PHK180 Ferien Rückkehrdatum (Gerät)",
        icon="mdi:airplane-landing",
        section="index",
        xml_key="FerienEnde",
        value_fn=lambda c: (
            "Kein Ferienbetrieb (00.00.2000)"
            if c.get_val("index", "FerienEnde", "00.00.2000") == "00.00.2000"
            else c.get_val("index", "FerienEnde", "00.00.2000")
        ),
    ),
    Phk180SensorEntityDescription(
        key="absenktemperatur_ferien",
        name="PHK180 Absenktemperatur Ferien",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        section="index",
        xml_key="AbsenkTemperatur",
        parse_mode="float",
    ),
    # --- Lüftung & Sensoren ---
    Phk180SensorEntityDescription(
        key="luftungsstufe",
        name="PHK180 Lüftungsstufe",
        icon="mdi:fan",
        section="details",
        xml_key="FanLevel",
    ),
    Phk180SensorEntityDescription(
        key="volumenstrom",
        name="PHK180 Volumenstrom",
        native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        icon="mdi:weather-windy",
        state_class=SensorStateClass.MEASUREMENT,
        section="details",
        xml_key="Volumenstrom",
        parse_mode="float",
    ),
    Phk180SensorEntityDescription(
        key="drehzahl_aussenluft",
        name="PHK180 Drehzahl Außenluft",
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        icon="mdi:fan-chevron-up",
        state_class=SensorStateClass.MEASUREMENT,
        section="details",
        xml_key="DrehzahlZu",
        parse_mode="int",
    ),
    Phk180SensorEntityDescription(
        key="drehzahl_fortluft",
        name="PHK180 Drehzahl Fortluft",
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        icon="mdi:fan-chevron-down",
        state_class=SensorStateClass.MEASUREMENT,
        section="details",
        xml_key="DrehzahlAb",
        parse_mode="int",
    ),
    Phk180SensorEntityDescription(
        key="restlaufzeit_aussenfilter",
        name="PHK180 Restlaufzeit Außenfilter",
        native_unit_of_measurement=UnitOfTime.DAYS,
        icon="mdi:air-filter",
        section="details",
        xml_key="Fan_AussenFilterRestlaufzeit",
        parse_mode="int",
    ),
    Phk180SensorEntityDescription(
        key="restlaufzeit_geratefilter",
        name="PHK180 Restlaufzeit Gerätefilter",
        native_unit_of_measurement=UnitOfTime.DAYS,
        icon="mdi:air-filter",
        section="details",
        xml_key="Fan_GeraeteFilterRestlaufzeit",
        parse_mode="int",
    ),
    Phk180SensorEntityDescription(
        key="co2_sensor_1_wohnzimmer",
        name="PHK180 CO2 Sensor 1 (Wohnzimmer)",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        device_class=SensorDeviceClass.CO2,
        state_class=SensorStateClass.MEASUREMENT,
        section="details",
        xml_key="Co2_AktValue1",
        parse_mode="int",
    ),
    Phk180SensorEntityDescription(
        key="co2_sensor_2_wc",
        name="PHK180 CO2 Sensor 2 (WC)",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        device_class=SensorDeviceClass.CO2,
        state_class=SensorStateClass.MEASUREMENT,
        section="details",
        xml_key="Co2_AktValue2",
        parse_mode="int",
    ),
    Phk180SensorEntityDescription(
        key="co2_sensor_3_kuche",
        name="PHK180 CO2 Sensor 3 (Küche)",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        device_class=SensorDeviceClass.CO2,
        state_class=SensorStateClass.MEASUREMENT,
        section="details",
        xml_key="Co2_AktValue3",
        parse_mode="int",
    ),
    Phk180SensorEntityDescription(
        key="rel_luftfeuchte",
        name="PHK180 Rel. Luftfeuchte",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        section="details",
        xml_key="Rh_AktValue",
        parse_mode="int",
    ),
    # --- Temperaturen (Ist) ---
    Phk180SensorEntityDescription(
        key="t_raum",
        name="PHK180 T-Raum",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        section="details",
        xml_key="TempRaum",
        parse_mode="float",
    ),
    Phk180SensorEntityDescription(
        key="t_lufteintritt",
        name="PHK180 T-Lufteintritt",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        section="details",
        xml_key="T_Lufteintritt",
        parse_mode="float",
    ),
    Phk180SensorEntityDescription(
        key="t_zuluft",
        name="PHK180 T-Zuluft",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        section="details",
        xml_key="TempZuluft",
        parse_mode="float",
    ),
    Phk180SensorEntityDescription(
        key="t_abluft",
        name="PHK180 T-Abluft",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        section="details",
        xml_key="T_Abluft",
        parse_mode="float",
    ),
    Phk180SensorEntityDescription(
        key="t_verdampfer",
        name="PHK180 T-Verdampfer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        section="details",
        xml_key="tVerdampfer1",
        parse_mode="float",
    ),
    Phk180SensorEntityDescription(
        key="t_speicher_e_heizstab_oben",
        name="PHK180 T-Speicher E-Heizstab (Oben)",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        section="details",
        xml_key="HE_WWS_TE",
        parse_mode="float",
    ),
    Phk180SensorEntityDescription(
        key="t_speicher_warmepumpe_unten",
        name="PHK180 T-Speicher Wärmepumpe (Unten)",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        section="details",
        xml_key="HE_WWS_TW",
        parse_mode="float",
    ),
    # --- Sollwerte & Status ---
    Phk180SensorEntityDescription(
        key="raumsolltemperatur",
        name="PHK180 Raumsolltemperatur",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        section="settings",
        xml_key="Raumsolltemperatur",
        parse_mode="float",
    ),
    Phk180SensorEntityDescription(
        key="warmwassersolltemperatur",
        name="PHK180 Warmwassersolltemperatur",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        section="settings",
        xml_key="WWS_T_Soll",
        parse_mode="float",
    ),
    Phk180SensorEntityDescription(
        key="dauer_intensivluftung",
        name="PHK180 Dauer Intensivlüftung",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        icon="mdi:timer-outline",
        section="settings",
        xml_key="IL_Dauer",
        parse_mode="int",
    ),
    Phk180SensorEntityDescription(
        key="sommer_bypass",
        name="PHK180 Sommer-Bypass",
        icon="mdi:valve",
        section="details",
        xml_key="BypassZustand",
    ),
    Phk180SensorEntityDescription(
        key="umschaltventil_stellung",
        name="PHK180 Umschaltventil Stellung",
        icon="mdi:call-split",
        section="details",
        xml_key="MV_4_2_Wege",
        value_fn=lambda c: "Wasser" if c.get_val("details", "MV_4_2_Wege", "0") == "1" else "Luft",
    ),
    Phk180SensorEntityDescription(
        key="jahreszeit",
        name="PHK180 Jahreszeit",
        icon="mdi:weather-partly-snowy-rainy",
        section="index",
        xml_key="Jahreszeitstring",
    ),
    Phk180SensorEntityDescription(
        key="vorrangschaltung_wp",
        name="PHK180 Vorrangschaltung WP",
        icon="mdi:priority-high",
        section="settings",
        xml_key="WpVorrangschaltungstring",
    ),
    Phk180SensorEntityDescription(
        key="storungsmeldung",
        name="PHK180 Störungsmeldung",
        icon="mdi:alert-circle-outline",
        section="index",
        xml_key="Error_Id1",
        value_fn=_compute_error_text,
    ),
    # --- Alle 14 Betriebsstundenzähler ---
    Phk180SensorEntityDescription(
        key="betriebsstunden_feuchteschutzluftung",
        name="PHK180 Betriebsstunden Feuchteschutzlüftung",
        native_unit_of_measurement=UnitOfTime.HOURS,
        icon="mdi:clock-outline",
        state_class=SensorStateClass.TOTAL_INCREASING,
        section="details",
        xml_key="BSTD_FL",
        parse_mode="int",
    ),
    Phk180SensorEntityDescription(
        key="betriebsstunden_reduzierte_luftung",
        name="PHK180 Betriebsstunden Reduzierte Lüftung",
        native_unit_of_measurement=UnitOfTime.HOURS,
        icon="mdi:clock-outline",
        state_class=SensorStateClass.TOTAL_INCREASING,
        section="details",
        xml_key="BSTD_RL",
        parse_mode="int",
    ),
    Phk180SensorEntityDescription(
        key="betriebsstunden_nennluftung",
        name="PHK180 Betriebsstunden Nennlüftung",
        native_unit_of_measurement=UnitOfTime.HOURS,
        icon="mdi:clock-outline",
        state_class=SensorStateClass.TOTAL_INCREASING,
        section="details",
        xml_key="BSTD_NL",
        parse_mode="int",
    ),
    Phk180SensorEntityDescription(
        key="betriebsstunden_intensivluftung",
        name="PHK180 Betriebsstunden Intensivlüftung",
        native_unit_of_measurement=UnitOfTime.HOURS,
        icon="mdi:clock-outline",
        state_class=SensorStateClass.TOTAL_INCREASING,
        section="details",
        xml_key="BSTD_IL",
        parse_mode="int",
    ),
    Phk180SensorEntityDescription(
        key="betriebsstunden_luftung_gesamt",
        name="PHK180 Betriebsstunden Lüftung Gesamt",
        native_unit_of_measurement=UnitOfTime.HOURS,
        icon="mdi:clock-outline",
        state_class=SensorStateClass.TOTAL_INCREASING,
        section="details",
        xml_key="BSTD_Luftgesamt",
        parse_mode="int",
    ),
    Phk180SensorEntityDescription(
        key="betriebsstunden_warmepumpe",
        name="PHK180 Betriebsstunden Wärmepumpe",
        native_unit_of_measurement=UnitOfTime.HOURS,
        icon="mdi:clock-outline",
        state_class=SensorStateClass.TOTAL_INCREASING,
        section="details",
        xml_key="BSTD_WP",
        parse_mode="int",
    ),
    Phk180SensorEntityDescription(
        key="betriebsstunden_trinkwassererwarmung",
        name="PHK180 Betriebsstunden Trinkwassererwärmung",
        native_unit_of_measurement=UnitOfTime.HOURS,
        icon="mdi:clock-outline",
        state_class=SensorStateClass.TOTAL_INCREASING,
        section="details",
        xml_key="BSTD_BrauchUwp",
        parse_mode="int",
    ),
    Phk180SensorEntityDescription(
        key="betriebsstunden_zh_zuluft",
        name="PHK180 Betriebsstunden ZH Zuluft",
        native_unit_of_measurement=UnitOfTime.HOURS,
        icon="mdi:clock-outline",
        state_class=SensorStateClass.TOTAL_INCREASING,
        section="details",
        xml_key="BSTD_ZH_Zuluft",
        parse_mode="int",
    ),
    Phk180SensorEntityDescription(
        key="betriebsstunden_zh_raum",
        name="PHK180 Betriebsstunden ZH Raum",
        native_unit_of_measurement=UnitOfTime.HOURS,
        icon="mdi:clock-outline",
        state_class=SensorStateClass.TOTAL_INCREASING,
        section="details",
        xml_key="BSTD_ZH_Raum",
        parse_mode="int",
    ),
    Phk180SensorEntityDescription(
        key="betriebsstunden_e_heizstab",
        name="PHK180 Betriebsstunden E-Heizstab",
        native_unit_of_measurement=UnitOfTime.HOURS,
        icon="mdi:clock-outline",
        state_class=SensorStateClass.TOTAL_INCREASING,
        section="details",
        xml_key="BSTD_EHZ",
        parse_mode="int",
    ),
    Phk180SensorEntityDescription(
        key="betriebsstunden_sole_umwalzpumpe",
        name="PHK180 Betriebsstunden Sole-Umwälzpumpe",
        native_unit_of_measurement=UnitOfTime.HOURS,
        icon="mdi:clock-outline",
        state_class=SensorStateClass.TOTAL_INCREASING,
        section="details",
        xml_key="BSTD_SoleUwp",
        parse_mode="int",
    ),
    Phk180SensorEntityDescription(
        key="betriebsstunden_solar_umwalzpumpe",
        name="PHK180 Betriebsstunden Solar-Umwälzpumpe",
        native_unit_of_measurement=UnitOfTime.HOURS,
        icon="mdi:clock-outline",
        state_class=SensorStateClass.TOTAL_INCREASING,
        section="details",
        xml_key="BSTD_SolarUwp",
        parse_mode="int",
    ),
    Phk180SensorEntityDescription(
        key="betriebsstunden_ofen_umwalzpumpe",
        name="PHK180 Betriebsstunden Ofen-Umwälzpumpe",
        native_unit_of_measurement=UnitOfTime.HOURS,
        icon="mdi:clock-outline",
        state_class=SensorStateClass.TOTAL_INCREASING,
        section="details",
        xml_key="BSTD_OfenUwp",
        parse_mode="int",
    ),
    Phk180SensorEntityDescription(
        key="betriebsstunden_evu_sperre",
        name="PHK180 Betriebsstunden EVU-Sperre",
        native_unit_of_measurement=UnitOfTime.HOURS,
        icon="mdi:clock-outline",
        state_class=SensorStateClass.TOTAL_INCREASING,
        section="details",
        xml_key="BSTD_EVUsperre",
        parse_mode="int",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PHK 180 sensors."""
    coordinator: Phk180Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        Phk180Sensor(coordinator, desc) for desc in SENSOR_DESCRIPTIONS
    )


class Phk180Sensor(CoordinatorEntity[Phk180Coordinator], SensorEntity):
    """Representation of an PHK 180 Sensor."""

    entity_description: Phk180SensorEntityDescription

    def __init__(
        self,
        coordinator: Phk180Coordinator,
        description: Phk180SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"phk180_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> str | int | float | None:
        """Return the state of the sensor."""
        if self.entity_description.value_fn is not None:
            return self.entity_description.value_fn(self.coordinator)

        raw = self.coordinator.get_val(
            self.entity_description.section, self.entity_description.xml_key
        )
        if raw is None or (isinstance(raw, str) and raw.startswith("-")):
            if self.entity_description.parse_mode in ("float", "int") and "- °C" in str(raw):
                return None

        if self.entity_description.parse_mode == "float":
            return extract_float(raw, 0.0)
        if self.entity_description.parse_mode == "int":
            return extract_int(raw, 0)
        return str(raw) if raw is not None else None
