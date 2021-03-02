"""
Platform for Duka One fan.

see http://www.dingus.dk for more information
"""
import logging


from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_NAME,
)
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import HomeAssistantType

from dukaonesdk.device import Device

from . import DukaEntityComponent
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistantType, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up Duka One humidity sensor based on a config entry."""

    name = entry.data[CONF_NAME]
    device_id = entry.data[CONF_DEVICE_ID]
    dukaonesensor = DukaOneHumidity(hass, name, device_id)
    async_add_entities([dukaonesensor], True)


class DukaOneHumidity(Entity):
    """A Duka One humidity sensor entity."""

    def __init__(self, hass: HomeAssistantType, name, device_id):
        """Initialize the Duka One fan."""
        self._name = name
        self._device_id = device_id
        self._device: Device = None

    @property
    def name(self):
        """Return then name"""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._device_id

    @property
    def should_poll(self):
        """No polling needed for a Duka One fan."""
        return True

    @property
    def assumed_state(self):
        """Return false if we do optimistic updates."""
        return False

    @property
    def state(self):
        """Return the state of the sensor."""
        if self.device is None:
            return None
        return self.device.humidity

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity"""
        return "%"

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:water-percent"

    @property
    def device(self):
        if self._device is None:
            component: DukaEntityComponent = self.hass.data[DOMAIN]
            self._device = component.the_client.get_device(self._device_id)
        return self._device

    @property
    def device_info(self):
        """Return device information."""
        if self.device is None:
            return None
        info = {
            "name": "DukaOne",
            "identifiers": {(DOMAIN, self._device_id)},
            "manufacturer": "Duka Ventilation",
            "model": f"Type {self.device.unit_type}",
            "sw_version": f"{self.device.firmware_version} {self.device.firmware_date}",
        }
        return info
