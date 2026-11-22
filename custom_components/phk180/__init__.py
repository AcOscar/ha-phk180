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

import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import device_registry as dr, entity_registry as er
import homeassistant.helpers.config_validation as cv

from .api import Phk180Api
from .const import (
    DEFAULT_HOST,
    DEFAULT_PASSWORD,
    DEFAULT_USERNAME,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import Phk180Coordinator

_LOGGER = logging.getLogger(__name__)

_LEGACY_OBJECT_ID_PREFIXES = (
    "phk_180_kompaktgerat_phk180_",
    "phk_180_kompaktgeraet_phk180_",
    "phk_180_kompaktgerat_",
    "phk_180_kompaktgeraet_",
    "phk180_phk180_",
)


def _async_migrate_legacy_names(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Migrate legacy device name and entity IDs (e.g. phk_180_kompaktgerat_phk180_*)."""
    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    if device is not None:
        update_kwargs: dict[str, str | None] = {}
        if device.name == "PHK 180 Kompaktgerät":
            update_kwargs["name"] = "PHK180"
        if device.name_by_user == "PHK 180 Kompaktgerät":
            update_kwargs["name_by_user"] = None
        if update_kwargs:
            dev_reg.async_update_device(device.id, **update_kwargs)

    ent_reg = er.async_get(hass)
    for ent_entry in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
        if "." not in ent_entry.entity_id:
            continue
        domain, object_id = ent_entry.entity_id.split(".", 1)
        new_object_id = object_id
        for prefix in _LEGACY_OBJECT_ID_PREFIXES:
            if new_object_id.startswith(prefix):
                new_object_id = f"phk180_{new_object_id.removeprefix(prefix)}"
                break

        if new_object_id == object_id:
            continue

        new_entity_id = f"{domain}.{new_object_id}"
        if ent_reg.async_get(new_entity_id) is not None:
            _LOGGER.warning(
                "Kann Entity-ID %s nicht auf %s migrieren, da Ziel-ID bereits existiert.",
                ent_entry.entity_id,
                new_entity_id,
            )
            continue

        _LOGGER.info(
            "Migriere veraltete Entity-ID %s -> %s",
            ent_entry.entity_id,
            new_entity_id,
        )
        ent_reg.async_update_entity(ent_entry.entity_id, new_entity_id=new_entity_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up PHK 180 Local Web Control from a config entry."""
    host = entry.data.get(CONF_HOST, DEFAULT_HOST)
    username = entry.data.get(CONF_USERNAME, DEFAULT_USERNAME)
    password = entry.data.get(CONF_PASSWORD, DEFAULT_PASSWORD)

    api = Phk180Api(host=host, username=username, password=password)
    coordinator = Phk180Coordinator(hass, entry, api)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    _async_migrate_legacy_names(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_set_vacation_return_date(call: ServiceCall) -> None:
        return_date = call.data["return_date"]
        date_obj = cv.date(return_date)
        formatted = date_obj.strftime("%d-%m-%Y")
        await api.async_send_cmd("index.htm", "D[1]", formatted)
        await coordinator.async_request_refresh()

    async def handle_sync_system_date(call: ServiceCall) -> None:
        from homeassistant.util import dt as dt_util
        now_str = dt_util.now().strftime("%d-%m-%Y")
        await api.async_set_date(now_str)
        await coordinator.async_request_refresh()

    async def handle_sync_system_datetime(call: ServiceCall) -> None:
        from homeassistant.util import dt as dt_util
        now = dt_util.now()
        await api.async_sync_datetime(now.strftime("%d-%m-%Y"), now.hour, now.minute)
        await coordinator.async_request_refresh()

    if not hass.services.has_service(DOMAIN, "set_vacation_return_date"):
        hass.services.async_register(
            DOMAIN,
            "set_vacation_return_date",
            handle_set_vacation_return_date,
            schema=vol.Schema({vol.Required("return_date"): cv.string}),
        )

    if not hass.services.has_service(DOMAIN, "sync_system_date"):
        hass.services.async_register(
            DOMAIN,
            "sync_system_date",
            handle_sync_system_date,
        )

    if not hass.services.has_service(DOMAIN, "sync_system_datetime"):
        hass.services.async_register(
            DOMAIN,
            "sync_system_datetime",
            handle_sync_system_datetime,
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
