import logging
from functools import partial

import voluptuous as vol

from const import WYZE_VAC_CLIENT, WYZE_VACUUMS

from wyze_sdk.models.devices import VacuumMode

from homeassistant.components.vacuum import (
    PLATFORM_SCHEMA,
    SUPPORT_BATTERY,
    # SUPPORT_CLEAN_SPOT,
    # SUPPORT_FAN_SPEED,
    # SUPPORT_LOCATE,
    SUPPORT_RETURN_HOME,
    # SUPPORT_SEND_COMMAND,
    SUPPORT_STATUS,
    SUPPORT_STOP,
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON,
    STATES,
    VacuumEntity
)

SUPPORT_WYZE = (
    SUPPORT_BATTERY,
    # SUPPORT_CLEAN_SPOT,
    # SUPPORT_FAN_SPEED,
    # SUPPORT_LOCATE,
    SUPPORT_RETURN_HOME,
    # SUPPORT_SEND_COMMAND,
    SUPPORT_STATUS,
    SUPPORT_STOP,
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON,
)

from homeassistant.helpers.icon import icon_for_battery_level

from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD
)

import homeassistant.helpers.config_validation as cv

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_USERNAME): cv.string, 
        vol.Required(CONF_PASSWORD): cv.string,
    }
)

_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_entities, discovery_info=None):
    
    for dev_mac in hass.data[WYZE_VACUUMS]:
        add_entities(WyzeVac(hass.data[WYZE_VAC_CLIENT], dev_mac))
        


class WyzeVac(VacuumEntity):

    def __init__(self, client, vac_mac):
        self._client = client
        self._vac_mac = vac_mac

    @property
    def supported_features(self):
        """Flag vacuum cleaner features that are supported."""
        return SUPPORT_WYZE

    @property
    def unique_id(self) -> str:
        """Return an unique ID."""
        return self._vac_mac

    @property
    def is_on(self):
        """Return true if vacuum is currently cleaning."""
        vacuum = self._client.vacuums.info(device_mac=self._vac_mac)
        return vacuum.mode != VacuumMode.IDLE

    @property
    def status(self):
        """Return the status of the vacuum cleaner."""
        vacuum = self._client.vacuums.info(device_mac=self._vac_mac)
        if vacuum.mode in [VacuumMode.SWEEPING]:
            return STATES.STATE_CLEANING
        if vacuum.mode in [VacuumMode.IDLE]:
            return STATES.STATE_DOCKED
        if vacuum.mode in [VacuumMode.ON_WAY_CHARGE, VacuumMode.FULL_FINISH_SWEEPING_ON_WAY_CHARGE]:
            return STATES.RETURNING
        return STATES.STATE_ERROR

    @property
    def is_charging(self):
        """Return true if vacuum is currently charging."""
        vacuum = self._client.vacuums.info(device_mac=self._vac_mac)
        return vacuum.charge_state

    @property
    def battery_level(self):
        """Return the battery level of the vacuum cleaner."""
        vacuum = self._client.vacuums.info(device_mac=self._vac_mac)

        return vacuum.battery

    @property
    def battery_icon(self):
        """Return the battery icon for the vacuum cleaner."""
        return icon_for_battery_level(
            battery_level=self.battery_level, charging=self.is_charging
        )

    def turn_on(self, **kwargs):
        """Turn the vacuum on and start cleaning."""
        vacuum = self._client.vacuums.info(device_mac=self._vac_mac)
        self._client.vacuums.clean(device_mac=self._vac_mac, device_model=vacuum.product.model)

    def stop(self, **kwargs):
        """Stop the vacuum cleaner."""
        vacuum = self._client.vacuums.info(device_mac=self._vac_mac)
        self._client.vacuums.pause(device_mac=self._vac_mac, device_model=vacuum.product.model)

    async def async_stop(self, **kwargs):
        """Stop the vacuum cleaner.
        This method must be run in the event loop.
        """
        await self.hass.async_add_executor_job(partial(self.stop, **kwargs))

    def return_to_base(self, **kwargs):
        """Set the vacuum cleaner to return to the dock."""
        vacuum = self._client.vacuums.info(device_mac=self._vac_mac)
        self._client.vacuums.dock(device_mac=self._vac_mac, device_model=vacuum.product.model)

    async def async_return_to_base(self, **kwargs):
        """Set the vacuum cleaner to return to the dock.
        This method must be run in the event loop.
        """
        await self.hass.async_add_executor_job(partial(self.return_to_base, **kwargs))