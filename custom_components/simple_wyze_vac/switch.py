import logging

from .const import WYZE_VACUUMS, WYZE_USERNAME, WYZE_PASSWORD, \
                   DOMAIN

from homeassistant.components.switch import SwitchEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):

    username = hass.data[WYZE_USERNAME]
    password = hass.data[WYZE_PASSWORD]

    client = hass.data[DOMAIN][config_entry.entry_id]

    room_list = []
    for pl in hass.data[WYZE_VACUUMS]:
        room_manager = pl["room_manager"]
        
        for room_name, stat in room_manager.rooms.items():
            room_list.append(SWVRoomSwitch(client, username, password, pl, room_name))

    if room_list:
        async_add_entities(room_list)

class SWVRoomSwitch(SwitchEntity):
    def __init__(self, client, username, password, pl, room_name):
        self._client = client
        self._username = username
        self._password = password
        self._room_name = room_name
        self._room_manager =  pl["room_manager"]
        self._name = pl["name"]
        self._model = pl["model"]

    @property
    def device_info(self):
        """Return device registry information for this entity."""
        return {
            "identifiers": {(DOMAIN, self._name)},
            "name": self._name,
            "manufacturer": "Wyze Inc.",
            "model": self._model,
        }

    @property
    def name(self):
        return "SWV - " + str(self._room_name)
    
    @property
    def unique_id(self) -> str:
        """Return an unique ID."""
        return "swv_" + str(self._room_name)

    @property
    def icon(self):
        return 'mdi:broom'

    @property
    def is_on(self):
        return self._room_manager.rooms[self._room_name]

    def turn_on(self, **kwargs) -> None:
        self._room_manager.set(self._room_name)

    def turn_off(self, **kwargs) -> None:
        self._room_manager.clear(self._room_name)