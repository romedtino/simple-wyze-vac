import logging

from .const import WYZE_VACUUMS, \
                   DOMAIN

from homeassistant.components.local_file.camera import LocalFile

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):

    cameras = []
    for pl in hass.data[WYZE_VACUUMS]:
        cameras.append(SWVCamera(pl,f"www/{DOMAIN}/{pl['name']}_last_map.jpg"))

    async_add_entities(cameras)

class SWVCamera(LocalFile):
    def __init__(self, pl, file_path):
        super().__init__(pl["name"], file_path)
        self._model = pl["model"]

    @property
    def name(self):
        return self._name + " Camera"

    @property
    def unique_id(self):
        return "swv_" + self._name + "_camera"

    @property
    def device_info(self):
        """Return device registry information for this entity."""
        return {
            "identifiers": {(DOMAIN, self._name)},
            "name": self._name,
            "manufacturer": "Wyze Inc.",
            "model": self._model,
        }
