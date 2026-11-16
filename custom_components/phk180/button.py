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
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import Phk180Coordinator


@dataclass(frozen=True, kw_only=True)
class Phk180ButtonEntityDescription(ButtonEntityDescription):
    """Describe an PHK 180 button."""

    endpoint_htm: str
    param: str
    val: str


BUTTON_DESCRIPTIONS: tuple[Phk180ButtonEntityDescription, ...] = (
    Phk180ButtonEntityDescription(
        key="storung_reset",
        name="PHK180 Störung Reset",
        icon="mdi:restart-alert",
        endpoint_htm="index.htm",
        param="S[313][0]",
        val="-",
    ),
    Phk180ButtonEntityDescription(
        key="filterwechsel_geratefilter_quittieren",
        name="PHK180 Filterwechsel Gerätefilter Quittieren",
        icon="mdi:air-filter",
        endpoint_htm="index.htm",
        param="S[241][0]",
        val="-",
    ),
    Phk180ButtonEntityDescription(
        key="filterwechsel_aussenfilter_quittieren",
        name="PHK180 Filterwechsel Außenfilter Quittieren",
        icon="mdi:air-filter",
        endpoint_htm="index.htm",
        param="S[241][1]",
        val="-",
    ),
    Phk180ButtonEntityDescription(
        key="wp_vorrangschaltung_umschalten",
        name="PHK180 WP Vorrangschaltung Umschalten",
        icon="mdi:swap-horizontal",
        endpoint_htm="settings.htm",
        param="S[272][0]",
        val="0",
    ),
    Phk180ButtonEntityDescription(
        key="ferienbetrieb_beenden_auf_auto_zeit",
        name="PHK180 Ferienbetrieb Beenden (Auf Auto Zeit)",
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
    entities.append(Phk180VacationDateSubmitButton(coordinator))
    async_add_entities(entities)


class Phk180Button(CoordinatorEntity[Phk180Coordinator], ButtonEntity):
    """Representation of an PHK 180 Button."""

    entity_description: Phk180ButtonEntityDescription

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


class Phk180VacationDateSubmitButton(
    CoordinatorEntity[Phk180Coordinator], ButtonEntity
):
    """Button that reads input_datetime.phk180_ferien_rueckkehrdatum and submits D[1]."""

    _attr_name = "PHK180 Ferien Rückkehrdatum Übertragen"
    _attr_icon = "mdi:calendar-check"

    def __init__(self, coordinator: Phk180Coordinator) -> None:
        """Initialize the vacation submit button."""
        super().__init__(coordinator)
        self._attr_unique_id = "phk180_btn_ferien_datum_senden"
        self._attr_device_info = coordinator.device_info

    async def async_press(self) -> None:
        """Read date helper if available and send D[1]=DD-MM-YYYY."""
        state = self.hass.states.get("input_datetime.phk180_ferien_rueckkehrdatum")
        if state and state.state not in ("unknown", "unavailable", ""):
            await self.hass.services.async_call(
                DOMAIN,
                "set_vacation_return_date",
                {"return_date": state.state},
                blocking=True,
            )
