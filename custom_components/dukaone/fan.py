"""
Platform for Duka One fan .

see http://www.dingus.dk for more information
"""
import asyncio
import homeassistant.core as ha
import logging
import voluptuous as vol

from homeassistant.components import fan
from homeassistant.components.fan import (
    PLATFORM_SCHEMA,
    SPEED_HIGH,
    SPEED_LOW,
    SPEED_MEDIUM,
    SPEED_OFF,
    SUPPORT_SET_SPEED,
    SUPPORT_OSCILLATE,
    SUPPORT_DIRECTION,
    FanEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType, HomeAssistantType
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_PASSWORD,
    CONF_IP_ADDRESS,
)
import homeassistant.helpers.config_validation as cv

from dukaonesdk.device import Device, Mode, Speed
from dukaonesdk.dukaclient import DukaClient

from .const import ATTR_MODE, DOMAIN, MODE_IN, MODE_INOUT, MODE_OUT

_LOGGER = logging.getLogger(__name__)


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Optional(CONF_PASSWORD, default="1111"): cv.string,
        vol.Optional(CONF_IP_ADDRESS, default="<broadcast>"): cv.string,
    }
)

_DUKACLIENT = None

def the_client() -> DukaClient:
    global _DUKACLIENT
    if _DUKACLIENT is None:
        _DUKACLIENT = DukaClient()
    return _DUKACLIENT

async def async_setup_platform(
    hass: HomeAssistantType, config: ConfigType, async_add_entities, discovery_info=None
):
    """Set up thet dukaone platform."""

    device_id = config[CONF_DEVICE_ID]
    password = config[CONF_PASSWORD]
    ip_address = config[CONF_IP_ADDRESS]
    dukaonefan = DukaOneFan(device_id, password, ip_address)
    await async_add_entities([dukaonefan])

async def async_setup_entry(
    hass: HomeAssistantType, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up Duka One based on a config entry."""

    device_id = entry.data[CONF_DEVICE_ID]
    password = entry.data[CONF_PASSWORD]
    ip_address = entry.data[CONF_IP_ADDRESS]
    if ip_address is  None or len(ip_address) == 0:
        ip_address = "<broadcast>"
    dukaonefan = DukaOneFan(device_id, password, ip_address)
    async_add_entities([dukaonefan], True)


class DukaOneFan(FanEntity):
    """A Duka One  fan component."""

    def __init__(self, device_id, password, ip_address):
        """Initialize the Duka One fan."""
        self._state = False
        self._speed = None
        self._mode: Mode = None
        self._device_id = device_id
        self._password = password
        self._ip_address = ip_address
        self._device : Device = None
        self._supported_features = SUPPORT_SET_SPEED
        if self._ip_address is not None and  len(self._ip_address) == 0:
            self._ip_address = None

    async def async_added_to_hass(self):
        """Make the duka one device."""
        if the_client().get_device( self._device_id) is None:
            self._device = the_client().add_device(
                self._device_id, self._password, self._ip_address, self.OnChange
            )
        return

    def OnChange(self, device: Device):
        """Callback when the duka one change state"""
        if device.speed == Speed.LOW:
            self._speed = SPEED_LOW
        elif device.speed == Speed.MEDIUM:
            self._speed = SPEED_MEDIUM
        elif device.speed == Speed.HIGH:
            self._speed = SPEED_HIGH
        else:
            self._speed = SPEED_OFF
        self._state = ((int)(device.speed)) != 0
        modeswitch = {
            Mode.ONEWAY: MODE_OUT,
            Mode.TWOWAY : MODE_INOUT,
            Mode.IN: MODE_IN
        }
        self._mode = modeswitch.get(device.mode, MODE_INOUT)
        self.schedule_update_ha_state()
        return

    async def async_will_remove_from_hass(self):
        """Unsubscribe when removed."""
        self._device = the_client().remove_device(self._device)
        return

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._device_id

    @property
    def should_poll(self):
        """No polling needed for a Duka One fan."""
        return False

    @property
    def assumed_state(self):
        """Return false  if we do optimistic updates."""
        return False

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

    @property
    def speed_list(self) -> list:
        """Get the list of available speeds."""
        return [SPEED_OFF, SPEED_LOW, SPEED_MEDIUM, SPEED_HIGH]

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return self._supported_features

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {"mode": self.mode}

    @property
    def speed(self):
        """Return the current speed."""
        return self._speed

    def set_speed(self, speed: str) -> None:
        """Set the speed of the fan.

        This method is a coroutine.
        """
        if speed == SPEED_HIGH:
            the_client().set_speed(self._device, Speed.HIGH)
        elif speed == SPEED_MEDIUM:
            the_client().set_speed(self._device, Speed.MEDIUM)
        elif speed == SPEED_LOW:
            the_client().set_speed(self._device, Speed.LOW)
        elif speed == SPEED_OFF:
            the_client().set_speed(self._device, Speed.OFF)

    @property
    def mode(self):
        """Return the current mode"""
        return self._mode

    def set_mode(self, mode):
        if mode == MODE_OUT:
            mode = 0
        elif mode == MODE_INOUT:
            mode = 1
        elif mode == MODE_IN:
            mode = 2
        the_client().set_mode(self._device, mode)

    def turn_on(self, speed: str = None, **kwargs) -> None:
        """Turn on the entity.

        This method is a coroutine.
        """
        if speed is not None:
            self.set_speed(speed)
        else:
            the_client().turn_on(self._device)

    def turn_off(self, **kwargs) -> None:
        """Turn off the entity.

        This method is a coroutine.
        """
        the_client().turn_off(self._device)
        return
