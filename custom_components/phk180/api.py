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
import ipaddress
import logging
import re
import socket
import struct
import time as time_mod
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any

from .const import PARAMETER_LIMITS

_LOGGER = logging.getLogger(__name__)


def parse_time_hm(val_str: Any) -> tuple[int, int] | None:
    """Extract (hour, minute) from strings like '18:27' or '13.11.2026 18:27'."""
    if val_str is None or val_str == "":
        return None
    match = re.search(r"(\d{1,2}):(\d{2})", str(val_str))
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2))
    if 0 <= hour <= 23 and 0 <= minute <= 59:
        return hour, minute
    return None


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


def _nbns_encode_name(name: str) -> bytes:
    """Encode a NetBIOS name (16 bytes padded with spaces -> 32 half-ASCII bytes)."""
    padded = name.upper().ljust(15)[:15] + "\x00"
    encoded = bytearray()
    for ch in padded.encode("ascii", errors="ignore"):
        encoded.append(((ch >> 4) & 0x0F) + 0x41)
        encoded.append((ch & 0x0F) + 0x41)
    return b"\x20" + bytes(encoded) + b"\x00"


def _resolve_netbios_broadcast(hostname: str, timeout: float = 1.2) -> str | None:
    """Resolve Windows/Keil NetBIOS name (like 'aerexphk180') via UDP port 137 broadcast.
    Home Assistant OS containers often lack nmbd/winbind, so DNS lookup for bare NetBIOS
    hostnames fails unless queried via NBNS or .local/.fritz.box suffix.
    """
    short_name = hostname.split(".")[0]
    if len(short_name) > 15:
        return None
    try:
        tx_id = b"\x13\x37"
        header = tx_id + b"\x01\x10\x00\x01\x00\x00\x00\x00\x00\x00"
        question = _nbns_encode_name(short_name) + b"\x00\x20\x00\x01"
        packet = header + question

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)
        sock.sendto(packet, ("255.255.255.255", 137))
        data, _ = sock.recvfrom(512)
        sock.close()

        # NBNS positive response has IPv4 address in the last 4 bytes
        if len(data) >= 62 and data[:2] == tx_id:
            ip_bytes = data[-4:]
            ip_str = socket.inet_ntoa(ip_bytes)
            if ip_str != "0.0.0.0":
                return ip_str
    except Exception:
        pass
    return None


def resolve_host_to_ip(host_input: str) -> str:
    """Resolve IPv4 address, standard DNS hostname, .fritz.box/.local, or NetBIOS name."""
    clean = host_input.strip().replace("http://", "").replace("https://", "").rstrip("/")
    # Extract optional port if provided
    host_only = clean.split(":")[0]
    port_part = f":{clean.split(':')[1]}" if ":" in clean else ""

    # 1. Direct IPv4 address?
    try:
        ipaddress.ip_address(host_only)
        return clean
    except ValueError:
        pass

    # 2. Try standard DNS resolution (as-is, .fritz.box, .local)
    candidates = [host_only]
    if "." not in host_only:
        candidates.extend([f"{host_only}.fritz.box", f"{host_only}.local"])

    for cand in candidates:
        try:
            resolved_ip = socket.gethostbyname(cand)
            if resolved_ip:
                return f"{resolved_ip}{port_part}"
        except socket.gaierror:
            continue

    # 3. Try NetBIOS Name Service (UDP 137) broadcast (used by Keil RL-TCPnet stack)
    nbns_ip = _resolve_netbios_broadcast(host_only)
    if nbns_ip:
        return f"{nbns_ip}{port_part}"

    # Fallback to original string
    return clean


class Phk180Api:
    """Thread-safe HTTP/XML client for the PHK 180 embedded web interface."""

    def __init__(self, host: str, username: str, password: str) -> None:
        """Initialize the API client."""
        self.raw_host = host.strip().replace("http://", "").replace("https://", "").rstrip("/")
        self.resolved_host: str | None = None
        self.username = username.strip()
        self.password = password or ""
        self._lock = asyncio.Lock()

    @property
    def host(self) -> str:
        """Return resolved IP/host if available, else raw_host."""
        return self.resolved_host or self.raw_host

    def _ensure_resolved(self) -> str:
        if not self.resolved_host:
            self.resolved_host = resolve_host_to_ip(self.raw_host)
        return self.resolved_host

    def _get_auth_header(self) -> dict[str, str]:
        token = base64.b64encode(f"{self.username}:{self.password}".encode("utf-8")).decode("utf-8")
        return {"Authorization": f"Basic {token}"}

    def _sync_fetch_cgx(self, page: str) -> dict[str, str]:
        """Synchronously fetch and parse a .cgx XML endpoint (ISO-8859-1)."""
        target = self._ensure_resolved()
        url = f"http://{target}/{page}"
        req = urllib.request.Request(url, headers=self._get_auth_header())
        try:
            resp_ctx = urllib.request.urlopen(req, timeout=8)
        except Exception:
            # Re-resolve in case DHCP lease changed IP
            self.resolved_host = resolve_host_to_ip(self.raw_host)
            url = f"http://{self.resolved_host}/{page}"
            req = urllib.request.Request(url, headers=self._get_auth_header())
            resp_ctx = urllib.request.urlopen(req, timeout=8)

        with resp_ctx as resp:
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
        target = self._ensure_resolved()
        url = f"http://{target}/{endpoint_htm}?{param_query}"
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
                t_raum_soll = extract_float(data.get("Raumsolltemperatur"), 20.0)
                dyn_max = min(max_limit, max(min_limit, 30.0 - t_raum_soll))
            elif p_key == (964, 0):
                t_ww_soll = extract_float(data.get("WWS_T_Soll"), 45.0)
                dyn_max = min(max_limit, max(min_limit, 55.0 - t_ww_soll))
            elif p_key == (965, 0):
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

    def _sync_read_device_time(self) -> tuple[int, int] | None:
        """Read current (hour, minute) from settings.cgx."""
        data = self._sync_fetch_cgx("settings.cgx")
        return parse_time_hm(
            data.get("aktuelleUhrzeit") or data.get("aktuellesDatum")
        )

    def _sync_advance_time_component(
        self,
        param_name: str,
        target_val: int,
        modulo: int,
        component_idx: int,
    ) -> None:
        """Advance hour (T[0]) or minute (T[1]) to target_val using adaptive closed-loop steps.

        Tries a single jump T[x]=diff first; if the firmware only supports +1 per request,
        falls back automatically to single T[x]=1 increments.
        """
        cur_hm = self._sync_read_device_time()
        if cur_hm is None:
            _LOGGER.warning("Konnte aktuelle Geräteuhrzeit nicht aus settings.cgx lesen.")
            return

        cur = cur_hm[component_idx]
        diff = (target_val - cur) % modulo
        if diff == 0:
            return

        if diff == 1:
            self._sync_send_cmd("settings.htm", f"{param_name}=1")
            return

        # Try multi-step jump first (diff is 2..59, fits maxlength=2)
        self._sync_send_cmd("settings.htm", f"{param_name}={diff}")
        new_hm = self._sync_read_device_time()
        if new_hm is None:
            return

        new_val = new_hm[component_idx]
        if new_val == target_val:
            return

        # If multi-step had no effect at all, verify that single-step (=1) advances the value
        if new_val == cur:
            self._sync_send_cmd("settings.htm", f"{param_name}=1")
            check_hm = self._sync_read_device_time()
            if check_hm is None or check_hm[component_idx] == cur:
                _LOGGER.warning(
                    "Parameter %s konnte nicht verändert werden (bleibt bei %s).",
                    param_name,
                    cur,
                )
                return
            new_val = check_hm[component_idx]

        remaining = (target_val - new_val) % modulo
        for _ in range(remaining):
            time_mod.sleep(0.05)
            self._sync_send_cmd("settings.htm", f"{param_name}=1")

    def _sync_set_time_closed_loop(self, target_hour: int, target_minute: int) -> None:
        """Set device time via settings.htm T[1] (minutes) and T[0] (hours)."""
        # Minutes first so any 59->00 hour rollover is corrected in the next step
        self._sync_advance_time_component("T[1]", target_minute, 60, 1)
        self._sync_advance_time_component("T[0]", target_hour, 24, 0)

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

    async def async_set_date(self, date_str: str) -> None:
        """Set system date (DD-MM-YYYY) via settings.htm?D[0]=..."""
        await self.async_send_cmd("settings.htm", "D[0]", date_str)

    async def async_set_time(self, target_hour: int, target_minute: int) -> None:
        """Set system time via settings.htm?T[1]=... and T[0]=..."""
        async with self._lock:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None, self._sync_set_time_closed_loop, int(target_hour), int(target_minute)
            )

    async def async_sync_datetime(
        self, date_str: str, target_hour: int, target_minute: int
    ) -> None:
        """Synchronize both system time and date (date last to guard against midnight wrap)."""
        async with self._lock:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None, self._sync_set_time_closed_loop, int(target_hour), int(target_minute)
            )
            await loop.run_in_executor(
                None, self._sync_send_cmd, "settings.htm", f"D[0]={date_str}"
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
