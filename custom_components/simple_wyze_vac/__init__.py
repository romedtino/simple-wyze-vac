import logging
import voluptuous as vol

from datetime import timedelta

from homeassistant import core
from homeassistant.helpers import discovery
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from .const import DOMAIN, WYZE_VAC_CLIENT, WYZE_VACUUMS

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

SCAN_INTERVAL = timedelta(minutes=2)

# async def async_setup(hass: core.HomeAssistant, config: dict) -> bool:
def setup(hass: core.HomeAssistant, config: dict) -> bool:
    """Set up the Simple Wyze Vacuum component."""

    hass.data[WYZE_VACUUMS] = []

    username = config[DOMAIN].get(CONF_USERNAME)
    password = config[DOMAIN].get(CONF_PASSWORD)
    # client = await hass.async_add_executor_job(Client(email=username, password=password))
    client = Client(email=username, password=password)
    hass.data[WYZE_VAC_CLIENT] = client

    for device in client.vacuums.list():
        _LOGGER.info(
            "Discovered Wyze device on account: %s with ID %s",
            username,
            device.mac,
        )

        payload = {
            "mac": device.mac,
            "model": device.product.model,
            "name": device.nickname,
            # "suction": device.clean_level #TODO - wyze_sdk currently broken self._clean_level != self.clean_level. Needs to be fixed first. 
        }

        hass.data[WYZE_VACUUMS].append(payload)


    discovery.load_platform(hass, "vacuum", DOMAIN, {}, config)

    return True
