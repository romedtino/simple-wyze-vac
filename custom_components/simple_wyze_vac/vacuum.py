import logging
from datetime import timedelta

import wyze_sdk

from .const import WYZE_VAC_CLIENT, WYZE_VACUUMS

from wyze_sdk.models.devices import VacuumMode, VacuumSuctionLevel

from homeassistant.components.vacuum import (
    PLATFORM_SCHEMA,
    # SUPPORT_BATTERY,
    # SUPPORT_CLEAN_SPOT,
    SUPPORT_FAN_SPEED,
    SUPPORT_LOCATE,
    SUPPORT_RETURN_HOME,
    SUPPORT_SEND_COMMAND,
    SUPPORT_STATUS,
    SUPPORT_STOP,
    SUPPORT_START,
    # SUPPORT_TURN_OFF,
    # SUPPORT_TURN_ON,
    STATES,
    STATE_CLEANING,
    STATE_DOCKED,
    STATE_RETURNING,
    STATE_ERROR,
    STATE_PAUSED,
    StateVacuumEntity
)

SUPPORT_WYZE = (
    # SUPPORT_BATTERY
    # SUPPORT_CLEAN_SPOT
    SUPPORT_FAN_SPEED
    | SUPPORT_LOCATE
    | SUPPORT_RETURN_HOME
    | SUPPORT_SEND_COMMAND
    | SUPPORT_STATUS
    | SUPPORT_STOP
    | SUPPORT_START
    # | SUPPORT_TURN_OFF
    # | SUPPORT_TURN_ON
)

from homeassistant.helpers.icon import icon_for_battery_level

_LOGGER = logging.getLogger(__name__)

FAN_SPEEDS = ["quiet", "standard", "strong"]

def setup_platform(hass, config, add_entities, discovery_info=None):
    
    vacs = []
    for pl in hass.data[WYZE_VACUUMS]:
        vacs.append(WyzeVac(hass.data[WYZE_VAC_CLIENT], pl["mac"], pl["model"], pl["name"]))

    add_entities(vacs)
        


class WyzeVac(StateVacuumEntity):

    def __init__(self, client, vac_mac, model, name):
        self._client = client
        self._vac_mac = vac_mac
        self._model = model
        self._last_mode = STATE_DOCKED
        self._name = name
        self._fan_speed = FAN_SPEEDS[0]

    @property
    def unique_id(self) -> str:
        """Return an unique ID."""
        return self._name

    @property
    def supported_features(self):
        """Flag vacuum cleaner features that are supported."""
        return SUPPORT_WYZE

    @property
    def is_on(self):
        """Return true if vacuum is currently cleaning."""
        return self._last_mode != STATE_DOCKED

    @property
    def status(self):
        """Return the status of the vacuum cleaner."""
        return self._last_mode

    @property
    def state(self):
        """Return the state of the vacuum cleaner."""
        return self._last_mode

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def fan_speed(self):
        """Return the status of the vacuum."""
        return self._fan_speed

    @property
    def fan_speed_list(self):
        """Return the status of the vacuum."""
        return FAN_SPEEDS

    # @property
    # async def is_charging(self):
    #     """Return true if vacuum is currently charging."""
    #     vacuum = await self.hass.async_add_executor_job(self._client.vacuums.info(device_mac=self._vac_mac))
    #     return vacuum.charge_state

    # @property
    # async def battery_level(self):
    #     """Return the battery level of the vacuum cleaner."""
    #     vacuum = await self.hass.async_add_executor_job(self._client.vacuums.info(device_mac=self._vac_mac))

    #     return vacuum.battery

    # @property
    # async def battery_icon(self):
    #     """Return the battery icon for the vacuum cleaner."""
    #     bat_level = await self.battery_level()
    #     is_charge = await self.is_charging()
    #     return icon_for_battery_level(
    #         battery_level=bat_level, charging=is_charge
        # )

    # def turn_on(self, **kwargs):
    #     """Turn the vacuum on and start cleaning."""
    #     self._client.vacuums.clean(device_mac=self._vac_mac, device_model=self._model)
    #     self._last_mode = STATE_CLEANING
    
    # def turn_off(self, **kwargs):
    #     """Turn the vacuum on and start cleaning."""
    #     self.return_to_base()

    def start(self, **kwargs):
        self._client.vacuums.clean(device_mac=self._vac_mac, device_model=self._model)
        self.schedule_update_ha_state()

    def pause(self, **kwargs):
        """Stop the vacuum cleaner."""
        self._client.vacuums.pause(device_mac=self._vac_mac, device_model=self._model)
        self._last_mode = STATE_PAUSED
        self.schedule_update_ha_state()

    def stop(self, **kwargs):
        """Stop the vacuum cleaner."""
        self._client.vacuums.pause(device_mac=self._vac_mac, device_model=self._model)
        self._last_mode = STATE_PAUSED
        self.schedule_update_ha_state()

    def return_to_base(self, **kwargs):
        """Set the vacuum cleaner to return to the dock."""
        self._client.vacuums.dock(device_mac=self._vac_mac, device_model=self._model)
        self._last_mode = STATE_RETURNING
        self.schedule_update_ha_state()

    def locate(self, **kwargs):
        """Locate the vacuum cleaner."""
        _LOGGER.warn("Locate called. Not Implemented.")
        pass

    def start_pause(self, **kwargs):
        """Start, pause or resume the cleaning task."""
        if self._last_mode in [ STATE_CLEANING, STATE_RETURNING]:
            self._client.vacuums.pause(device_mac=self._vac_mac, device_model=self._model)
        else:
            self._client.vacuums.clean(device_mac=self._vac_mac, device_model=self._model)
        
        self.schedule_update_ha_state()

    def send_command(self, command, params=None, **kwargs):
        """Perform a spot clean-up."""
        vacuum = self._client.vacuums.info(device_mac=self._vac_mac)
        _LOGGER.info("Command: %s, params: %s", command, params)
        if command in "sweep_rooms":
            if "rooms" in params:
                desired_rooms = params["rooms"]
                self._client.vacuums.sweep_rooms(device_mac=self._vac_mac, room_ids=[room.id for room in vacuum.current_map.rooms if room.name in desired_rooms])
                self.schedule_update_ha_state()
            else:
                _LOGGER.warn("No rooms specified for vacuum. Cannot do spot clean")
        else:
            _LOGGER.warn("Unknown wyze vac command")

    def update(self):
        vacuum = self._client.vacuums.info(device_mac=self._vac_mac)
        if vacuum.mode in [VacuumMode.SWEEPING]:
            self._last_mode = STATE_CLEANING
        elif vacuum.mode in [VacuumMode.IDLE, VacuumMode.BREAK_POINT]:
            self._last_mode = STATE_DOCKED
        elif vacuum.mode in [VacuumMode.ON_WAY_CHARGE, VacuumMode.FULL_FINISH_SWEEPING_ON_WAY_CHARGE]:
            self._last_mode = STATE_RETURNING
        elif vacuum.mode in [VacuumMode.PAUSE]:
            self._last_mode = STATE_PAUSED
        else:
            self._last_mode = STATE_ERROR

    def set_fan_speed(self, fan_speed, **kwargs):
        """Set the vacuum's fan speed."""
        if self.supported_features & SUPPORT_FAN_SPEED == 0:
            return

        if fan_speed in self.fan_speed_list:
            self._fan_speed = fan_speed
            wyze_suction = VacuumSuctionLevel.QUIET
            if self._fan_speed == FAN_SPEEDS[1]:
                wyze_suction = VacuumSuctionLevel.STANDARD
            elif self._fan_speed == FAN_SPEEDS[2]:
                wyze_suction = VacuumSuctionLevel.STRONG
            else:
                return
                
            self._client.vacuums.set_suction_level(device_mac=self._vac_mac, device_model=self._model, suction_level=wyze_suction)
            self.schedule_update_ha_state()
        
