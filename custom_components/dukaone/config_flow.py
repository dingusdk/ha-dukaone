"""Config flow for Duka One integration."""
from dukaonesdk.dukaclient import DukaClient
import logging
import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_PASSWORD,
    CONF_IP_ADDRESS,
)

from .const import DOMAIN, CONF_STATICIP  # pylint:disable=unused-import
from .fan import the_client

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_DEVICE_ID) : str,
    vol.Optional(CONF_PASSWORD, default='1111'): str,
    vol.Optional(CONF_IP_ADDRESS, default=''): str,
    vol.Optional(CONF_STATICIP, default = True): bool,
    }
)

def dovalidate(user_input):

    if user_input[CONF_IP_ADDRESS] is None or len(user_input[CONF_IP_ADDRESS]) == 0:
        user_input[CONF_IP_ADDRESS] = "<broadcast>"
    device_id = user_input[CONF_DEVICE_ID]
    password = user_input[CONF_PASSWORD]
    ip_address = user_input[CONF_IP_ADDRESS]
    device = the_client().validate_device(device_id, password, ip_address)
    if device is None:
        raise CannotConnect()
    if user_input[CONF_STATICIP]:
        user_input[CONF_IP_ADDRESS] = device.ip_address
    return


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Duka One."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                await self.hass.async_add_executor_job( dovalidate, user_input)
                return self.async_create_entry(title=user_input[CONF_DEVICE_ID], data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""

