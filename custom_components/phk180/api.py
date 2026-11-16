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

import asyncio
import base64
import logging
import re
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any

from .const import PARAMETER_LIMITS

_LOGGER = logging.getLogger(__name__)


def extract_float(val_str: Any, default: float = 0.0) -> float:
    """Extract float from strings like '22.1 °C' or '-0.7 K'."""
    if val_str is None or val_str == "":
        return default
    match = re.search(r"[-+]?\d+(?:[\.,]\d+)?", str(val_str))
    if match:
        return float(match.group(0).replace(",", "."))
    return default


def extract_int(val_str: Any, default: int = 0) -> int:
    """Extract integer from strings like '2462 rpm' or '3173 h'."""
    if val_str is None or val_str == "":
        return default
    match = re.search(r"[-+]?\d+", str(val_str))
    if match:
        return int(match.group(0))
    return default


def clamp_and_align(target_val: float, min_val: float, max_val: float, step: float) -> float:
    """Clamp target value to [min_val, max_val] and align to step grid."""
    clamped = max(min_val, min(max_val, float(target_val)))
    steps_from_min = round((clamped - min_val) / step)
    aligned = round(min_val + steps_from_min * step, 2)
    return max(min_val, min(max_val, aligned))


class Phk180Api:
    """Thread-safe HTTP/XML client for the PHK 180 embedded web interface."""

    def __init__(self, host: str, username: str, password: str) -> None:
        """Initialize the API client."""
        self.host = host.strip().replace("http://", "").replace("https://", "").rstrip("/")
        self.username = username.strip()
        self.password = password or ""
        self._lock = asyncio.Lock()

    def _get_auth_header(self) -> dict[str, str]:
        token = base64.b64encode(f"{self.username}:{self.password}".encode("utf-8")).decode("utf-8")
        return {"Authorization": f"Basic {token}"}

    def _sync_fetch_cgx(self, page: str) -> dict[str, str]:
        """Synchronously fetch and parse a .cgx XML endpoint (ISO-8859-1)."""
        url = f"http://{self.host}/{page}"
        req = urllib.request.Request(url, headers=self._get_auth_header())
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw_bytes = resp.read()
        xml_str = raw_bytes.decode("iso-8859-1", errors="replace")
        root = ET.fromstring(xml_str)
        data: dict[str, str] = {}
        for el in root.findall("text"):
            id_el = el.find("id")
            val_el = el.find("value")
            if id_el is not None and id_el.text:
                key = id_el.text.strip()
                val = val_el.text.strip() if (val_el is not None and val_el.text) else ""
                data[key] = val
        return data

    def _sync_send_cmd(self, endpoint_htm: str, param_query: str) -> None:
        """Send unencoded bracket parameter query (e.g. P[522][0]=3) to .htm endpoint."""
        url = f"http://{self.host}/{endpoint_htm}?{param_query}"
        req = urllib.request.Request(url, headers=self._get_auth_header())
        with urllib.request.urlopen(req, timeout=8) as resp:
            resp.read()

    def _sync_set_step_closed_loop(
        self,
        endpoint_htm: str,
        cgx_page: str,
        xml_id: str,
        param_id: int,
        param_idx: int,
        step_size: float,
        target_val: float,
    ) -> None:
        """Verify technical limits, clamp target, and send exact jump difference."""
        p_key = (int(param_id), int(param_idx))
        step = float(step_size)

        if p_key in PARAMETER_LIMITS:
            min_limit, max_limit, official_step = PARAMETER_LIMITS[p_key]
            step = official_step
        else:
            min_limit, max_limit = -9999.0, 9999.0

        for _ in range(3):
            data = self._sync_fetch_cgx(cgx_page)
            if xml_id not in data:
                break

            dyn_min, dyn_max = min_limit, max_limit
            if p_key == (561, 0):
                # Coupled system limit: Raumsolltemperatur + Differenz <= 30 °C
                t_raum_soll = extract_float(data.get("Raumsolltemperatur"), 20.0)
                dyn_max = min(max_limit, max(min_limit, 30.0 - t_raum_soll))
            elif p_key == (964, 0):
                # Coupled system limit: WWS_T_Soll + Hysterese WP <= 55 °C
                t_ww_soll = extract_float(data.get("WWS_T_Soll"), 45.0)
                dyn_max = min(max_limit, max(min_limit, 55.0 - t_ww_soll))
            elif p_key == (965, 0):
                # Coupled system limit: WWS_T_Soll + Hysterese EHZ <= 60 °C
                t_ww_soll = extract_float(data.get("WWS_T_Soll"), 45.0)
                dyn_max = min(max_limit, max(min_limit, 60.0 - t_ww_soll))

            safe_target = clamp_and_align(target_val, dyn_min, dyn_max, step)
            current = extract_float(data[xml_id], safe_target)
            diff = round(safe_target - current, 2)

            if abs(diff) < (step / 2.0):
                break

            direction = 0 if diff > 0 else 1
            jump_val = abs(diff)
            jump_str = str(int(jump_val)) if jump_val.is_integer() else f"{jump_val:.1f}"
            query = f"C[{param_id}][{param_idx}][{direction}]={jump_str}"
            self._sync_send_cmd(endpoint_htm, query)

    async def async_fetch_all(self) -> dict[str, dict[str, str]]:
        """Fetch index.cgx, details.cgx, and settings.cgx sequentially."""
        async with self._lock:
            loop = asyncio.get_running_loop()
            index_data = await loop.run_in_executor(None, self._sync_fetch_cgx, "index.cgx")
            details_data = await loop.run_in_executor(None, self._sync_fetch_cgx, "details.cgx")
            settings_data = await loop.run_in_executor(None, self._sync_fetch_cgx, "settings.cgx")
            return {
                "index": index_data,
                "details": details_data,
                "settings": settings_data,
            }

    async def async_send_cmd(self, endpoint_htm: str, param: str, val: str | int | float) -> None:
        """Send a direct parameter or toggle command."""
        async with self._lock:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None, self._sync_send_cmd, endpoint_htm, f"{param}={val}"
            )

    async def async_set_step_value(
        self,
        endpoint_htm: str,
        cgx_page: str,
        xml_id: str,
        param_id: int,
        param_idx: int,
        step_size: float,
        target_val: float,
    ) -> None:
        """Set a C[...] step value with limit clamping and closed-loop check."""
        async with self._lock:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                self._sync_set_step_closed_loop,
                endpoint_htm,
                cgx_page,
                xml_id,
                param_id,
                param_idx,
                step_size,
                target_val,
            )
