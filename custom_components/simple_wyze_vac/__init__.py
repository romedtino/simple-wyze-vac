import logging
import voluptuous as vol

from datetime import timedelta


import homeassistant.helpers.config_validation as cv

from homeassistant.config_entries import ConfigEntry
from homeassistant import core
from homeassistant.helpers import discovery

from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL
)

from .const import (
    CONF_TOTP,
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
PLATFORMS: list[str] = ["vacuum", "switch", "camera"]

async def async_setup_entry(hass: core.HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Hello World from a config entry."""
    # Store an instance of the "connecting" class that does the work of speaking
    # with your actual devices.
    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)
    totp = entry.data.get(CONF_TOTP) if entry.data.get(CONF_TOTP) else None

    client = await hass.async_add_executor_job(Client, username, password, totp)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = client

    hass.data[WYZE_VACUUMS] = []

    hass.data[WYZE_USERNAME] = username
    hass.data[WYZE_PASSWORD] = password
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

        if vac_info.current_map.rooms is not None:
            room_manager = SWVRoomManager(vac_info.current_map.rooms)

        payload = {
            "mac": device.mac,
            "model": device.product.model,
            "name": device.nickname,
            "suction": vac_info.clean_level.describe(),
            "battery": vac_info.voltage,
            "filter": vac_info.filter,
            "main_brush": vac_info.main_brush,
            "side_brush": vac_info.side_brush,
            "room_manager": room_manager
        }

        hass.data[WYZE_VACUUMS].append(payload)

    # This creates each HA object for each platform your device requires.
    # It's done by calling the `async_setup_entry` function in each platform module.
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(update_listener))
    return True

async def async_unload_entry(hass: core.HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # This is called when an entry/configured device is to be removed. The class
    # needs to unload itself, and remove callbacks. See the classes for further
    # details
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
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
