import logging
import voluptuous as vol

from homeassistant import core
from homeassistant.helpers import discovery
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from .const import DOMAIN, WYZE_VAC_CLIENT, WYZE_VACUUMS, WYZE_USERNAME, WYZE_PASSWORD

from wyze_sdk import Client

_LOGGER = logging.getLogger(__name__)

from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD
)

import homeassistant.helpers.config_validation as cv

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string, 
                vol.Required(CONF_PASSWORD): cv.string,
            }
        )
        
    },
    extra=vol.ALLOW_EXTRA,
)

# async def async_setup(hass: core.HomeAssistant, config: dict) -> bool:
def setup(hass: core.HomeAssistant, config: dict) -> bool:
    """Set up the Simple Wyze Vacuum component."""

    hass.data[WYZE_VACUUMS] = []

    username = config[DOMAIN].get(CONF_USERNAME)
    password = config[DOMAIN].get(CONF_PASSWORD)
    # client = await hass.async_add_executor_job(Client(email=username, password=password))
    client = Client(email=username, password=password)
    hass.data[WYZE_VAC_CLIENT] = client
    hass.data[WYZE_USERNAME] = username
    hass.data[WYZE_PASSWORD] = password

    for device in client.vacuums.list():
        _LOGGER.info(
            "Discovered Wyze device on account: %s with ID %s",
            username,
            device.mac,
        )

        vac_info = client.vacuums.info(device_mac=device.mac)

        payload = {
            "mac": device.mac,
            "model": device.product.model,
            "name": device.nickname,
            "suction": vac_info.clean_level.describe(),
            "battery": vac_info.voltage,
            "filter": vac_info.filter,
            "main_brush": vac_info.main_brush,
            "side_brush": vac_info.side_brush
        }

        hass.data[WYZE_VACUUMS].append(payload)


    discovery.load_platform(hass, "vacuum", DOMAIN, {}, config)

    return True
