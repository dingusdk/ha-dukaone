"""
Duka One Integration.

see http://www.dingus.dk for more information
"""
import asyncio
import logging
import voluptuous as vol
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

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)


def setup(hass: HomeAssistant, config: dict):
    """Set up the Duka One component."""

    if not DOMAIN in hass.data:
        hass.data[DOMAIN] = DukaEntityComponent(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Duka One from a config entry."""
    # TODO Store an API object for your platforms to access

    # hass.data[DOMAIN][entry.entry_id] = MyApi(...)

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


class DukaEntityComponent(EntityComponent):

    def __init__(self, hass):
        super(DukaEntityComponent, self).__init__(_LOGGER, DOMAIN, hass)
        self._the_client = None

    @property
    def the_client(self) -> DukaClient:
        if self._the_client is None:
            self._the_client = DukaClient()
        return self._the_client
