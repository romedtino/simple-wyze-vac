import logging

from datetime import timedelta
from datetime import datetime
from pathlib import Path

import time
import urllib.request
import voluptuous as vol

from .const import CONF_TOTP, WYZE_VACUUMS, WYZE_USERNAME, WYZE_PASSWORD, \
                   DOMAIN, \
                   CONF_POLLING, WYZE_SCAN_INTERVAL, CONF_KEY_ID, CONF_API_KEY

from wyze_sdk.models.devices import VacuumMode, VacuumSuctionLevel
from wyze_sdk.errors import WyzeApiError, WyzeClientNotConnectedError
from wyze_sdk import Client

from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.components.vacuum import (
    STATE_CLEANING,
    STATE_DOCKED,
    STATE_RETURNING,
    STATE_ERROR,
    STATE_PAUSED,
    StateVacuumEntity,
    VacuumEntityFeature,
)

SUPPORT_WYZE = (
    VacuumEntityFeature.BATTERY |
    VacuumEntityFeature.CLEAN_SPOT |
    VacuumEntityFeature.FAN_SPEED |
    VacuumEntityFeature.LOCATE |
    VacuumEntityFeature.MAP |
    VacuumEntityFeature.PAUSE |
    VacuumEntityFeature.RETURN_HOME |
    VacuumEntityFeature.SEND_COMMAND |
    VacuumEntityFeature.START |
    VacuumEntityFeature.STOP |
    VacuumEntityFeature.STATE 
)

_LOGGER = logging.getLogger(__name__)

FAN_SPEEDS = [VacuumSuctionLevel.QUIET.describe(),
            VacuumSuctionLevel.STANDARD.describe(),
            VacuumSuctionLevel.STRONG.describe()]

async def async_setup_entry(hass, config_entry, async_add_entities):

    username = hass.data[WYZE_USERNAME]
    password = hass.data[WYZE_PASSWORD]
    key_id = hass.data[CONF_KEY_ID]
    api_key = hass.data[CONF_API_KEY]
    polling = hass.data[CONF_POLLING]
    totp = hass.data[CONF_TOTP]

    client = hass.data[DOMAIN][config_entry.entry_id]
    
    if isinstance(hass.data[WYZE_SCAN_INTERVAL], timedelta):
        scan_interval = hass.data[WYZE_SCAN_INTERVAL]
    elif isinstance(hass.data[WYZE_SCAN_INTERVAL], str):
        t = datetime.strptime(hass.data[WYZE_SCAN_INTERVAL],"%H:%M:%S")
        scan_interval = timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
    else:
        scan_interval = timedelta(hours=4)

    vacs = []
    for pl in hass.data[WYZE_VACUUMS]:
        vacs.append(WyzeVac(client, pl, username, password, key_id, api_key, totp, polling, scan_interval))

    def refresh(event_time):
        """Refresh"""
        for vac in vacs:
            vac.async_schedule_update_ha_state(force_refresh=True)

    if polling:
        config_entry.async_on_unload(async_track_time_interval(hass ,refresh, scan_interval))

    async_add_entities(vacs, True)

    platform = entity_platform.current_platform.get()

    platform.async_register_entity_service(
        "sweep_rooms",
        vol.Schema(cv.make_entity_service_schema({"entry_id": cv.entity_ids, "rooms": cv.entity_ids})),
        "sweep_rooms_wrapper"
    )



class WyzeVac(StateVacuumEntity):

    def __init__(self, client, pl, username, password, key_id, api_key, totp, polling, scan_interval):
        self._client = client
        self._vac_mac = pl["mac"]
        self._model = pl["model"]
        self._last_mode = STATE_DOCKED
        self._name = pl["name"]
        self._fan_speed = pl["suction"]
        self._battery_level = pl["battery"]

        self._filter = pl["filter"]
        self._main_brush = pl["main_brush"]
        self._side_brush = pl["side_brush"]

        self._username = username
        self._password = password
        self._key_id = key_id
        self._api_key = api_key
        self._totp = totp

        self._polling = polling

        self._room_manager = pl["room_manager"]
        self._rooms = []
        for name, stat in self._room_manager.rooms.items():
            self._rooms.append(name)

        self._force_update = False
        self._last_update = datetime(1970,1,1)

        self._scan_interval = scan_interval
        global SCAN_INTERVAL
        SCAN_INTERVAL = self._scan_interval
        if self._polling:
            _LOGGER.warn(f"Simple Wyze Vac Polling every {scan_interval} ({SCAN_INTERVAL}). Careful of hitting Wyze servers rate limits.")

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

    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state."""
        return self._polling
    
    @property
    def battery_level(self):
        """Return the battery level of the vacuum cleaner."""
        return self._battery_level

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the vacuum cleaner."""
        data = {}

        if self._filter is not None:
            data["filter"] = int(self._filter)
        if self._main_brush is not None:
            data["main_brush"] = int(self._main_brush)
        if self._side_brush is not None:
            data["side_brush"] = int(self._side_brush)
        if self._rooms is not None:
            data["rooms"] = self._rooms

        return data

    async def get_new_client(self):
        _LOGGER.warn("Refreshing Wyze Client. Do this sparingly to be prevent lockout.")
        self._client = await self.hass.async_add_executor_job(lambda: Client(email=self._username, password=self._password, key_id=self._key_id, api_key=self._api_key, totp_key=self._totp))

    async def async_start(self, **kwargs):
        try:
            vacuum = await self.hass.async_add_executor_job(lambda: self._client.vacuums.info(device_mac=self._vac_mac))
        except (WyzeApiError, WyzeClientNotConnectedError) as e:
            _LOGGER.warn("Received WyzeApiError")
            await self.get_new_client()
        finally:
            await self.hass.async_add_executor_job(lambda: self._client.vacuums.clean(device_mac=self._vac_mac, device_model=self._model))
        
        self.async_schedule_update_ha_state(force_refresh=True)

    async def async_pause(self, **kwargs):
        """Stop the vacuum cleaner."""
        try:
            vacuum = await self.hass.async_add_executor_job(lambda: self._client.vacuums.info(device_mac=self._vac_mac))
        except (WyzeApiError, WyzeClientNotConnectedError) as e:
            _LOGGER.warn("Received WyzeApiError")
            await self.get_new_client()
        finally:
            await self.hass.async_add_executor_job(lambda: self._client.vacuums.pause(device_mac=self._vac_mac, device_model=self._model))
        self._last_mode = STATE_PAUSED

        self.async_schedule_update_ha_state(force_refresh=True)

    async def async_stop(self, **kwargs):
        """Stop the vacuum cleaner."""
        try:
            vacuum = await self.hass.async_add_executor_job(lambda: self._client.vacuums.info(device_mac=self._vac_mac))
        except (WyzeApiError, WyzeClientNotConnectedError) as e:
            _LOGGER.warn("Received WyzeApiError")
            await self.get_new_client()
        finally:
            await self.hass.async_add_executor_job(lambda: self._client.vacuums.pause(device_mac=self._vac_mac, device_model=self._model))
        self._last_mode = STATE_PAUSED

        self.async_schedule_update_ha_state(force_refresh=True)

    async def async_return_to_base(self, **kwargs):
        """Set the vacuum cleaner to return to the dock."""
        try:
           vacuum = await self.hass.async_add_executor_job(lambda: self._client.vacuums.info(device_mac=self._vac_mac))
        except (WyzeApiError, WyzeClientNotConnectedError) as e:
            _LOGGER.warn("Received WyzeApiError")
            await self.get_new_client()
        finally:
            await self.hass.async_add_executor_job(lambda: self._client.vacuums.dock(device_mac=self._vac_mac, device_model=self._model))
        self._last_mode = STATE_RETURNING

        self.async_schedule_update_ha_state(force_refresh=True)

    async def async_locate(self, **kwargs):
        """Locate the vacuum cleaner."""
        _LOGGER.warn("Locate called. Not Implemented.")
        pass

    async def async_start_pause(self, **kwargs):
        """Start, pause or resume the cleaning task."""
        if self._last_mode in [ STATE_CLEANING, STATE_RETURNING]:
            await self.async_pause()
        else:
            await self.async_start()
        
        self.async_schedule_update_ha_state(force_refresh=True)

    async def async_send_command(self, command, params=None, **kwargs):
        try:
            vacuum = await self.hass.async_add_executor_job(lambda: self._client.vacuums.info(device_mac=self._vac_mac))
        except (WyzeApiError, WyzeClientNotConnectedError) as e:
            _LOGGER.warn("Received WyzeApiError")
            await self.get_new_client()
            vacuum = await self.hass.async_add_executor_job(lambda: self._client.vacuums.info(device_mac=self._vac_mac))
            
        _LOGGER.info("Command: %s, params: %s", command, params)
        if command in "sweep_rooms":
            """Perform a spot clean-up."""
            if "rooms" in params:
                await self.sweep_rooms(params["rooms"])
            else:
                _LOGGER.warn("No rooms specified for vacuum. Cannot do spot clean")
        
        elif command in "sweep_auto":
            filtered_rooms = [name for name, val in self._room_manager.rooms.items() if val]
            await self.sweep_rooms(filtered_rooms)

        elif command in "update":
            self._force_update = True
            self.async_schedule_update_ha_state(force_refresh=True)
            
        elif command in ["refresh_token", "get_new_client"]:
            await self.get_new_client()
        
        elif command in ["get_map", "get_last_map"]:
            await self.get_last_map()

        elif command in ["set_map", "set_current_map"]:
            if params and "map" in params:
                await self.set_current_map(params["map"])
            else:
                _LOGGER.warn("No map specified for vacuum.")
        
        else:
            _LOGGER.warn(f"Unknown wyze vac command: {command}")

    async def async_update(self):
        cur_time = datetime.now()
        if not self._force_update and self._polling and self._last_update.timestamp() + self._scan_interval.total_seconds() > cur_time.timestamp():
            _LOGGER.warn(f"self._scan_interval is bugged? The last update was {self._last_update} which {self._scan_interval} hasn't passed. Not updating.")
            _LOGGER.warn(f"Please reload this component.")
            return

        # Get vacuum states
        try:
            vacuum = await self.hass.async_add_executor_job(lambda: self._client.vacuums.info(device_mac=self._vac_mac))
        except (WyzeApiError, WyzeClientNotConnectedError) as e:
            _LOGGER.warn("Received WyzeApiError")
            await self.get_new_client()
            vacuum = await self.hass.async_add_executor_job(lambda: self._client.vacuums.info(device_mac=self._vac_mac))            

        # Get vacuum mode
        if vacuum.mode in [VacuumMode.SWEEPING, VacuumMode.CLEANING, VacuumMode.QUICK_MAPPING_MAPPING]:
            self._last_mode = STATE_CLEANING
        elif vacuum.mode in [VacuumMode.IDLE, VacuumMode.BREAK_POINT, VacuumMode.DOCKED_NOT_COMPLETE, VacuumMode.QUICK_MAPPING_DOCKED_NOT_COMPLETE]:
            self._last_mode = STATE_DOCKED
        elif vacuum.mode in [VacuumMode.ON_WAY_CHARGE, VacuumMode.FULL_FINISH_SWEEPING_ON_WAY_CHARGE, VacuumMode.FINISHED_RETURNING_TO_CHARGE, VacuumMode.RETURNING_TO_CHARGE, VacuumMode.QUICK_MAPPING_COMPLETED_RETURNING_TO_CHARGE]:
            self._last_mode = STATE_RETURNING
        elif vacuum.mode in [VacuumMode.PAUSED, VacuumMode.PAUSE, VacuumMode.QUICK_MAPPING_PAUSED]:
            self._last_mode = STATE_PAUSED
        else:
            self._last_mode = STATE_ERROR

        # Update battery
        self._battery_level = vacuum.voltage

        # Update suction level
        self._fan_speed = vacuum.clean_level.describe()

        # Update filter information
        self._filter = vacuum.supplies.filter.remaining
        self._main_brush = vacuum.supplies.main_brush.remaining
        self._side_brush = vacuum.supplies.side_brush.remaining

        self._last_update = cur_time

        self._force_update = False

        await self.get_last_map()

    async def async_set_fan_speed(self, fan_speed, **kwargs):
        """Set the vacuum's fan speed."""
        if self.supported_features & VacuumEntityFeature.FAN_SPEED == 0:
            return

        if fan_speed in self.fan_speed_list:
            self._fan_speed = fan_speed
            wyze_suction = VacuumSuctionLevel.QUIET
            if self._fan_speed == FAN_SPEEDS[1]:
                wyze_suction = VacuumSuctionLevel.STANDARD
            elif self._fan_speed == FAN_SPEEDS[2]:
                wyze_suction = VacuumSuctionLevel.STRONG
                
            try:
                vacuum = await self.hass.async_add_executor_job(lambda: self._client.vacuums.info(device_mac=self._vac_mac))
            except (WyzeApiError, WyzeClientNotConnectedError) as e:
                _LOGGER.warn("Received WyzeApiError")
                await self.get_new_client()
            finally:
                await self.hass.async_add_executor_job(lambda: self._client.vacuums.set_suction_level(device_mac=self._vac_mac, device_model=self._model, suction_level=wyze_suction))
            self.async_schedule_update_ha_state(force_refresh=True)
    
    async def get_last_map(self):
        try:
            vacuum = await self.hass.async_add_executor_job(lambda: self._client.vacuums.info(device_mac=self._vac_mac))
        except (WyzeApiError, WyzeClientNotConnectedError) as e:
            _LOGGER.warn("Received WyzeApiError")
            await self.get_new_client()
        finally:
            maps = await self.hass.async_add_executor_job(lambda: self._client.vacuums.get_maps(device_mac=self._vac_mac))
            
        latest = None
        try:
            latest = await self.hass.async_add_executor_job(lambda: self._client.vacuums.get_sweep_records(device_mac=self._vac_mac, since=datetime.now())[0])
        except:
            _LOGGER.warn("Could not grab latest map, will use maps from maps list")
        url = None
        if not latest:
            for map in maps:
            # Grab current map
                if map.is_current:
                    url = map.img_url
        else:
            url = latest.map_img_big_url

        try:
            Path(f"www/{DOMAIN}").mkdir(parents=True, exist_ok=True)
            await self.hass.async_add_executor_job(lambda: urllib.request.urlretrieve(url, f"www/{DOMAIN}/{self._name}_last_map.jpg"))
        except:
            _LOGGER.warn("Failed to grab latest map image. Try again later.")

    async def set_current_map(self, target_map):
        target_map_id = None
        try:
            map_info = await self.hass.async_add_executor_job(lambda: self._client.vacuums.get_maps(device_mac=self._vac_mac))
            for map_sum in map_info:
                if map_sum.name == target_map:
                    target_map_id = map_sum.id
                    break
        except (WyzeApiError, WyzeClientNotConnectedError) as e:
            _LOGGER.warn("Received WyzeApiError")
            await self.get_new_client()
            map_info = await self.hass.async_add_executor_job(lambda: self._client.vacuums.get_maps(device_mac=self._vac_mac))
            for map_sum in map_info:
                if map_sum.name == target_map:
                    target_map_id = map_sum.id
                    break

        if target_map_id:
            await self.hass.async_add_executor_job(lambda: self._client.vacuums.set_current_map(device_mac=self._vac_mac, map_id=target_map_id))
            self.async_schedule_update_ha_state(force_refresh=True)
        else:
            _LOGGER.warn(f"No matching map named {target_map}")

    async def sweep_rooms(self, target_rooms=None):
        rooms = []
        try:
            map_info = await self.hass.async_add_executor_job(lambda: self._client.vacuums.get_maps(device_mac=self._vac_mac))
            for map_sum in map_info:
                rooms = rooms + map_sum.rooms
        except (WyzeApiError, WyzeClientNotConnectedError) as e:
            _LOGGER.warn("Received WyzeApiError")
            await self.get_new_client()
            map_info = await self.hass.async_add_executor_job(lambda: self._client.vacuums.get_maps(device_mac=self._vac_mac))
            for map_sum in map_info:
                rooms = rooms + map_sum.rooms
            
        if not rooms:
            _LOGGER.warn("No rooms from Wyze servers. Failed to grab any rooms from any existing maps.")
            rooms = None

        if target_rooms:
            await self.hass.async_add_executor_job(lambda: self._client.vacuums.sweep_rooms(device_mac=self._vac_mac, room_ids=[room.id for room in rooms if room.name in target_rooms]))
            self.async_schedule_update_ha_state(force_refresh=True)
        else:
            await self.async_start()
        
    async def sweep_rooms_wrapper(self, rooms):
        for room in self._room_manager.rooms.keys():
            self._room_manager.rooms[room] = False

        target_rooms = []
        for entry in rooms:
            name = self.hass.states.get(entry).attributes['room_name']
            target_rooms.append(name)
            self._room_manager.rooms[name] = True

        await self.sweep_rooms(target_rooms)

        self.async_schedule_update_ha_state(force_refresh=True)
