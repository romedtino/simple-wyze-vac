import logging
import voluptuous as vol
from datetime import timedelta

import homeassistant.helpers.config_validation as cv
from homeassistant.core import callback
from homeassistant import config_entries
from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
)

from .const import (
    DOMAIN,
    CONF_POLLING,
    WYZE_SCAN_INTERVAL,
)

from wyze_sdk import Client

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=60)


DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_USERNAME): str, 
    vol.Required(CONF_PASSWORD): str
})

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            if self._async_current_entries():
                return self.async_abort(reason="already_configured")

            try:
                client = await self.hass.async_add_executor_job(Client, user_input[CONF_USERNAME], user_input[CONF_PASSWORD])
                return self.async_create_entry(title="Simple Wyze Vac", data=user_input)
            except Exception:
                _LOGGER.error("Failed to login Wyze servers.")
                errors["password"] = "auth_error"

        # If there is no user input or there were errors, show the form again, including any errors that were found with the input.
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)

class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="Simple Wyze Vac", data=user_input)

        if self._config_entry.options.get(CONF_POLLING):
            poll_default = self._config_entry.options.get(CONF_POLLING)
        else:
            poll_default = False
            
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(CONF_POLLING, default=poll_default): bool,
                vol.Optional(CONF_SCAN_INTERVAL, default=self._config_entry.options.get(CONF_SCAN_INTERVAL)): str
            }),
        )