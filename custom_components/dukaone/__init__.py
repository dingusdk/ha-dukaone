"""
Duka One Integration.

see http://www.dingus.dk for more information
"""
import asyncio
import logging
import voluptuous as vol
from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_IP_ADDRESS,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_component import EntityComponent

from dukaonesdk.dukaclient import DukaClient

from .const import ATTR_MODE, DOMAIN
from .fan import DukaOneFan

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

SCAN_INTERVAL = timedelta(seconds=30)

VALID_MODE = vol.Any(
    vol.All(vol.Coerce(int), vol.Clamp(min=0, max=2)),
    cv.string
)
SET_MODE_SCHEMA = {ATTR_MODE: VALID_MODE}



async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Duka One component."""

    component = hass.data[DOMAIN] = EntityComponent(
        _LOGGER, DOMAIN, hass, SCAN_INTERVAL
    )
    component.async_register_entity_service(
        "set_mode", SET_MODE_SCHEMA, async_service_set_mode
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Duka One from a config entry."""
    # TODO Store an API object for your platforms to access

    # hass.data[DOMAIN][entry.entry_id] = MyApi(...)

    device_id = entry.data[CONF_DEVICE_ID]
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, 'fan')
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[hass.config_entries.async_forward_entry_unload(entry, 'fan')]
        )
    )
    # if unload_ok:
    #     hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_service_set_mode(device, call):
    """Handle the set_mode service call."""
    mode = call.data.get(ATTR_MODE, 1)
    device.set_mode(mode)
    return True
