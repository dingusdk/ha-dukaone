"""
Platform for Duka One fan.

see http://www.dingus.dk for more information
"""
import logging
import voluptuous as vol

from homeassistant.components.fan import (
    PLATFORM_SCHEMA,
    SPEED_HIGH,
    SPEED_LOW,
    SPEED_MEDIUM,
    SPEED_OFF,
    SUPPORT_SET_SPEED,
    FanEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_platform
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_DEVICE_ID,
    CONF_IP_ADDRESS,
    CONF_NAME,
    CONF_PASSWORD,
)
import homeassistant.helpers.config_validation as cv

from dukaonesdk.device import Device, Mode, Speed

from . import DukaEntityComponent
from .const import (
    ATTR_MANUAL_SPEED,
    ATTR_MODE,
    DOMAIN,
    MODE_IN,
    MODE_INOUT,
    MODE_OUT,
    SPEED_MANUAL,
)

_LOGGER = logging.getLogger(__name__)


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Optional(CONF_PASSWORD, default="1111"): cv.string,
        vol.Optional(CONF_IP_ADDRESS, default="<broadcast>"): cv.string,
    }
)

VALID_MODE = vol.Any(vol.All(vol.Coerce(int), vol.Clamp(min=0, max=2)), cv.string)
SET_MODE_SCHEMA = vol.Schema(
    {vol.Required(ATTR_ENTITY_ID): cv.entity_ids, vol.Required(ATTR_MODE): VALID_MODE}
)
RESET_FILTER_TIMER_SCHEMA = vol.Schema({vol.Required(ATTR_ENTITY_ID): cv.entity_ids})
SET_MANUAL_SPEED_SCHEMA = vol.Schema(
    {vol.Required(ATTR_ENTITY_ID): cv.entity_ids, vol.Required(ATTR_MANUAL_SPEED): int}
)


async def async_setup_entry(
    hass: HomeAssistantType, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up Duka One based on a config entry."""

    name = entry.data[CONF_NAME]
    device_id = entry.data[CONF_DEVICE_ID]
    password = entry.data[CONF_PASSWORD]
    ip_address = entry.data[CONF_IP_ADDRESS]
    if ip_address is None or len(ip_address) == 0:
        ip_address = "<broadcast>"
    dukaonefan = DukaOneFan(hass, name, device_id, password, ip_address)
    async_add_entities([dukaonefan], True)

    platform = entity_platform.current_platform.get()
    platform.async_register_entity_service("set_mode", SET_MODE_SCHEMA, "set_mode")
    platform.async_register_entity_service(
        "reset_filter_timer", RESET_FILTER_TIMER_SCHEMA, "reset_filter_timer"
    )
    platform.async_register_entity_service(
        "set_manual_speed", SET_MANUAL_SPEED_SCHEMA, "set_manual_speed"
    )


class DukaOneFan(FanEntity):
    """A Duka One  fan component."""

    def __init__(self, hass: HomeAssistantType, name, device_id, password, ip_address):
        """Initialize the Duka One fan."""
        self._state = False
        self._speed = None
        self._mode: Mode = None
        self._name = name
        self._device_id = device_id
        self._password = password
        self._ip_address = ip_address
        self._device: Device = None
        self._supported_features = SUPPORT_SET_SPEED
        if self._ip_address is not None and len(self._ip_address) == 0:
            self._ip_address = None
        component: DukaEntityComponent = hass.data[DOMAIN]
        self.the_client = component.the_client
        self._device = self.the_client.get_device(self._device_id)
        if self._device is None:
            self._device = self.the_client.add_device(
                self._device_id, self._password, self._ip_address, self.OnChange
            )

    def OnChange(self, device: Device):
        """Callback when the duka one change state"""
        if device.speed == Speed.LOW:
            self._speed = SPEED_LOW
        elif device.speed == Speed.MEDIUM:
            self._speed = SPEED_MEDIUM
        elif device.speed == Speed.HIGH:
            self._speed = SPEED_HIGH
        elif device.speed == Speed.MANUAL:
            self._speed = SPEED_MANUAL
        else:
            self._speed = SPEED_OFF
        self._state = device.speed != Speed.OFF
        modeswitch = {Mode.ONEWAY: MODE_OUT, Mode.TWOWAY: MODE_INOUT, Mode.IN: MODE_IN}
        self._mode = modeswitch.get(device.mode, MODE_INOUT)
        if self.hass is not None:
            self.schedule_update_ha_state()
        return

    async def async_will_remove_from_hass(self):
        """Unsubscribe when removed."""
        self._device = self.the_client.remove_device(self._device)
        return

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
        return [SPEED_OFF, SPEED_LOW, SPEED_MEDIUM, SPEED_HIGH, SPEED_MANUAL]

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return self._supported_features

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {
            "mode": self.mode,
            "filter_alarm": self._device.filter_alarm,
            "filter_timer": self._device.filter_timer,
            "humidity": self._device.humidity,
        }

    @property
    def speed(self):
        """Return the current speed."""
        return self._speed

    def set_speed(self, speed: str) -> None:
        """Set the speed of the fan.

        This method is a coroutine.
        """
        if speed == SPEED_HIGH:
            self.the_client.set_speed(self._device, Speed.HIGH)
        elif speed == SPEED_MEDIUM:
            self.the_client.set_speed(self._device, Speed.MEDIUM)
        elif speed == SPEED_LOW:
            self.the_client.set_speed(self._device, Speed.LOW)
        elif speed == SPEED_OFF:
            self.the_client.set_speed(self._device, Speed.OFF)
        elif speed == SPEED_MANUAL:
            self.the_client.set_speed(self._device, Speed.MANUAL)

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
        self.the_client.set_mode(self._device, mode)

    def turn_on(self, speed: str = None, **kwargs) -> None:
        """Turn on the entity.

        This method is a coroutine.
        """
        if speed is not None:
            self.set_speed(speed)
        else:
            self.the_client.turn_on(self._device)

    def turn_off(self, **kwargs) -> None:
        """Turn off the entity.

        This method is a coroutine.
        """
        self.the_client.turn_off(self._device)
        return

    def reset_filter_timer(self):
        """Reset the filter timer to 90 days"""
        self.the_client.reset_filter_alarm(self._device)
        return

    def set_manual_speed(self, manual_speed: int):
        """Set the manual fan speed"""
        self.the_client.set_manual_speed(self._device, manual_speed)
        return

    @property
    def device_info(self):
        """Return device information."""
        info = {
            "name": "DukaOne",
            "identifiers": {(DOMAIN, self._device_id)},
            "manufacturer": "Duka Ventilation",
            "model": f"Type {self._device.unit_type}",
            "sw_version": f"{self._device.firmware_version} {self._device.firmware_date}",
        }
        return info
