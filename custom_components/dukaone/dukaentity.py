""" """

import asyncio
import logging
import time
from xmlrpc.client import boolean

from dukaonesdk.device import Device
from dukaonesdk.dukaclient import DukaClient

from homeassistant.core import HomeAssistant

from . import DukaEntityComponent
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class DukaEntity:
    """Implement the base of a duka entity with a reference to a device"""

    def __init__(self, hass: HomeAssistant, device_id):
        self._device_id = device_id
        self.device: Device = None
        component: DukaEntityComponent = hass.data[DOMAIN]
        self.the_client: DukaClient = component.the_client

    def initialize_device(self, password: str, ip_address: str) -> None:
        """Initialize the duka one device"""
        self.device = self.the_client.add_device(
            self._device_id,
            password,
            ip_address,
            self.on_change,
        )

    async def wait_for_device_to_be_ready(self) -> boolean:
        """Wait for the device to reponse to the initial get firmware version command."""
        timeout = time.time() + 10
        while self.device is None or self.device.firmware_version is None:
            if time.time() > timeout:
                _LOGGER.warning("Timeout getting dukaone firmware version")
                return False
            await asyncio.sleep(0.1)
        return True

    def on_change(self, device: Device):
        """Callback whe dukaone has changes - must be implemented in derived class"""
        raise NotImplementedError()

    def dukaone_device_info(self):
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
