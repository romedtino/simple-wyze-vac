import logging

from homeassistant import core
from homeassistant.helpers import discovery
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from const import DOMAIN, WYZE_VAC_CLIENT, WYZE_VACUUMS

from wyze_sdk import Client

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: core.HomeAssistant, config: dict) -> bool:
    """Set up the Simple Wyze Vacuum component."""

    hass.data[WYZE_VACUUMS] = []

    username = config[DOMAIN].get[CONF_USERNAME]
    password = config[DOMAIN].get[CONF_PASSWORD]
    client = Client(email=username, password=password)

    hass.data[WYZE_VAC_CLIENT] = client

    for device in client.vacuums.list():
        _LOGGER.info(
            "Discovered Wyze device on account: %s with ID %s",
            username,
            device.mac,
        )

        hass.data[WYZE_VACUUMS].append(device.mac)


    discovery.load_platform(hass, "vacuum", DOMAIN, {}, config)

    return True
