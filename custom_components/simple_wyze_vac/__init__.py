import logging
import voluptuous as vol
import asyncio

import ssl
import tempfile
import urllib.request

from datetime import timedelta
from functools import lru_cache


import homeassistant.helpers.config_validation as cv

from homeassistant.config_entries import ConfigEntry
from homeassistant import core
from homeassistant.helpers import discovery

from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_API_KEY,
    CONF_SCAN_INTERVAL
)

from .const import (
    CONF_TOTP,
    CONF_KEY_ID,
    DOMAIN, 
    WYZE_VAC_CLIENT, 
    WYZE_VACUUMS, 
    WYZE_USERNAME, 
    WYZE_PASSWORD, 
    CONF_POLLING, 
    WYZE_SCAN_INTERVAL
)


from wyze_sdk import Client

_LOGGER = logging.getLogger(__name__)

# List of platforms to support. There should be a matching .py file for each,
# eg <cover.py> and <sensor.py>
PLATFORMS: list[str] = ["vacuum", "switch", "camera", "sensor"]


@lru_cache(maxsize=1)
def _patch_wyze_sdk_ssl() -> str | None:
    """Point wyze_sdk's requests sessions at the system CA bundle.

    Background: api.wyzecam.com's chain is rooted at DigiCert Global Root CA
    (the original 2006 root). Mozilla scheduled that root for distrust, and
    certifi 2026.04.22 — which ships in HA Core 2026.4's Python 3.14 image —
    no longer contains it. The HAOS system CA bundle still does, so we route
    wyze_sdk's verification through that instead of certifi.

    Patches BaseServiceClient._do_request to set session.verify before send().
    Returns the bundle path used (for logging) or None if no usable bundle was
    found, in which case the SDK falls back to certifi and will fail.
    """
    import os
    import ssl
    from wyze_sdk.service import base as wyze_base

    candidates = [
        ssl.get_default_verify_paths().cafile,
        "/etc/ssl/cert.pem",
        "/etc/ssl/certs/ca-certificates.crt",
        "/etc/pki/tls/certs/ca-bundle.crt",
    ]
    bundle = next((p for p in candidates if p and os.path.exists(p)), None)
    if bundle is None:
        _LOGGER.warning(
            "No system CA bundle found; wyze_sdk will use certifi, which on "
            "HA 2026.4+ no longer trusts api.wyzecam.com's root."
        )
        return None

    context = ssl._create_unverified_context()
    with urllib.request.urlopen("https://cacerts.digicert.com/DigiCertGlobalRootCA.crt.pem", context=context) as response:
        cert_data = response.read().decode('utf-8')

    with open(bundle, 'r') as f:
        base_bundle = f.read()

    with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.pem') as temp_bundle:
        temp_bundle.write(base_bundle + '\n' + cert_data)
        temp_bundle_path = temp_bundle.name


    original_do_request = wyze_base.BaseServiceClient._do_request

    def _do_request_with_system_ca(self, session, request):
        session.verify = temp_bundle_path
        return original_do_request(self, session, request)

    wyze_base.BaseServiceClient._do_request = _do_request_with_system_ca
    _LOGGER.info("Routed wyze_sdk SSL verification through system CA bundle: %s", temp_bundle_path)
    return temp_bundle_path


async def async_setup_entry(hass: core.HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Hello World from a config entry."""
    await hass.async_add_executor_job(_patch_wyze_sdk_ssl)

    # Store an instance of the "connecting" class that does the work of speaking
    # with your actual devices.
    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)
    key_id = entry.data.get(CONF_KEY_ID)
    api_key = entry.data.get(CONF_API_KEY)
    totp = entry.data.get(CONF_TOTP) if entry.data.get(CONF_TOTP) else None

    client = await hass.async_add_executor_job(Client, None, None, username, password, key_id, api_key, totp)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = client

    hass.data[WYZE_VACUUMS] = []

    hass.data[WYZE_USERNAME] = username
    hass.data[WYZE_PASSWORD] = password
    hass.data[CONF_KEY_ID] = key_id
    hass.data[CONF_API_KEY] = api_key
    hass.data[CONF_TOTP] = totp
    hass.data[CONF_POLLING] = entry.options.get(CONF_POLLING)
    hass.data[WYZE_SCAN_INTERVAL] = entry.options.get(CONF_SCAN_INTERVAL)

    device_list = await hass.async_add_executor_job(client.vacuums.list)
    for device in device_list:
        _LOGGER.info(
            "Discovered Wyze device on account: %s with ID %s",
            username,
            device.mac,
        )

        vac_info = await hass.async_add_executor_job(lambda: client.vacuums.info(device_mac=device.mac))

        try:
            rooms = []
            maps = await hass.async_add_executor_job(lambda: client.vacuums.get_maps(device_mac=device.mac))
            room_manager = SWVRoomManager({})
            for map in maps:
                if map.rooms:
                    rooms = rooms + map.rooms
            room_manager = SWVRoomManager(rooms)
                    
        except Exception as err:
            _LOGGER.warn("Failed to query vacuum rooms. If your firmware is higher than 1.6.113, rooms is currently not supported. Exception: " +  str(err))
            room_manager = SWVRoomManager({})

        payload = {
            "mac": device.mac,
            "model": device.product.model,
            "name": device.nickname,
            "suction": vac_info.clean_level.describe(),
            "filter": vac_info.supplies.filter.remaining,
            "main_brush": vac_info.supplies.main_brush.remaining,
            "side_brush": vac_info.supplies.side_brush.remaining,
            "room_manager": room_manager,
            "battery": WyzeBattery(vac_info.voltage)
        }

        hass.data[WYZE_VACUUMS].append(payload)

    # This creates each HA object for each platform your device requires.
    # It's done by calling the `async_setup_entry` function in each platform module.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(update_listener))
    return True

async def async_unload_entry(hass: core.HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # This is called when an entry/configured device is to be removed. The class
    # needs to unload itself, and remove callbacks. See the classes for further
    # details
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

async def update_listener(hass, entry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)

class SWVRoomManager:
    def __init__(self, rooms):
        self._rooms = {}
        for room in rooms:
            self._rooms[room.name] = True
    
    @property
    def rooms(self):
        return self._rooms

    def set(self, room_name):
        self._rooms[room_name] = True

    def clear(self, room_name):
        self._rooms[room_name] = False

class WyzeBattery:

    def __init__(self, value=0):
        self.value = value
    