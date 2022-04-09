"""
Duka One Integration.

see http://www.dingus.dk for more information
"""
import asyncio
import logging
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_component import EntityComponent

from dukaonesdk.dukaclient import DukaClient, Device

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)


def setup(hass: HomeAssistant, config: dict):
    """Set up the Duka One component."""

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = DukaEntityComponent(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Duka One from a config entry."""

    hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, "fan"))
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, "fan"),
                hass.config_entries.async_forward_entry_unload(entry, "sensor"),
            ]
        )
    )
    # if unload_ok:
    #     hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class DukaEntityComponent(EntityComponent):
    """We only want to have one instance of the dukaclient."""

    def __init__(self, hass):
        super(DukaEntityComponent, self).__init__(_LOGGER, DOMAIN, hass)
        self._the_client = None

    @property
    def the_client(self) -> DukaClient:
        """Get the duka one client."""
        if self._the_client is None:
            self._the_client = DukaClient()
        return self._the_client
