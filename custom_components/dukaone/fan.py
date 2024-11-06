"""
Platform for Duka One fan.

see http://www.dingus.dk for more information
"""

import asyncio
import logging
import time
import voluptuous as vol

from homeassistant.components.fan import (
    PLATFORM_SCHEMA,
    FanEntityFeature,
    FanEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_platform
from homeassistant.core import HomeAssistant
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_DEVICE_ID,
    CONF_IP_ADDRESS,
    CONF_NAME,
    CONF_PASSWORD,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.config_validation import make_entity_service_schema

from dukaonesdk.device import Device, Mode, Speed

from .const import (
    ATTR_MANUAL_SPEED,
    ATTR_MODE,
    MODE_IN,
    MODE_INOUT,
    MODE_OUT,
    SPEED_HIGH,
    SPEED_MANUAL,
    SPEED_MEDIUM,
    SPEED_LOW,
    SPEED_OFF,
)
from .dukaentity import DukaEntity

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Optional(CONF_PASSWORD, default="1111"): cv.string,
        vol.Optional(CONF_IP_ADDRESS, default="<broadcast>"): cv.string,
    }
)

VALID_MODE = vol.Any(vol.All(vol.Coerce(int), vol.Clamp(min=0, max=2)), cv.string)
SET_MODE_SCHEMA = make_entity_service_schema(
    {vol.Required(ATTR_ENTITY_ID): cv.entity_ids, vol.Required(ATTR_MODE): VALID_MODE}
)
RESET_FILTER_TIMER_SCHEMA = make_entity_service_schema(
    {vol.Required(ATTR_ENTITY_ID): cv.entity_ids}
)
SET_MANUAL_SPEED_SCHEMA = make_entity_service_schema(
    {vol.Required(ATTR_ENTITY_ID): cv.entity_ids, vol.Required(ATTR_MANUAL_SPEED): int}
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up Duka One based on a config entry."""

    name = entry.data[CONF_NAME]
    device_id = entry.data[CONF_DEVICE_ID]
    password = entry.data[CONF_PASSWORD]
    ip_address = entry.data[CONF_IP_ADDRESS]
    if ip_address is None or len(ip_address) == 0:
        ip_address = "<broadcast>"

    platform = entity_platform.current_platform.get()
    platform.async_register_entity_service("set_mode", SET_MODE_SCHEMA, "set_mode")
    platform.async_register_entity_service(
        "reset_filter_timer", RESET_FILTER_TIMER_SCHEMA, "reset_filter_timer"
    )
    platform.async_register_entity_service(
        "set_manual_speed", SET_MANUAL_SPEED_SCHEMA, "set_manual_speed"
    )
    dukaonefan = DukaOneFan(hass, name, device_id, password, ip_address)
    await dukaonefan.wait_for_device_to_be_ready()
    async_add_entities([dukaonefan], True)


class DukaOneFan(FanEntity, DukaEntity):
    """A Duka One  fan component."""

    def __init__(self, hass: HomeAssistant, name, device_id, password, ip_address):
        """Initialize the Duka One fan."""
        super(DukaOneFan, self).__init__(hass, device_id)
        self._mode: Mode = None
        self._name = name
        self._attr_percentage = None
        self._supported_features = (
            FanEntityFeature.SET_SPEED
            | FanEntityFeature.PRESET_MODE
            | FanEntityFeature.TURN_ON
            | FanEntityFeature.TURN_OFF
        )
        self._attr_preset_mode = None
        self._attr_preset_modes = [
            SPEED_OFF,
            SPEED_LOW,
            SPEED_MEDIUM,
            SPEED_HIGH,
            SPEED_MANUAL,
        ]
        hass.async_add_executor_job(self.initialize_device, password, ip_address)

    async def async_will_remove_from_hass(self):
        """Unsubscribe when removed."""
        self.device = self.the_client.remove_device(self.device)
        return

    def on_change(self, device: Device):
        """Callback when the duka one change state"""
        newspeed = SPEED_OFF
        newpercentage = 0
        if device.speed == Speed.LOW:
            newspeed = SPEED_LOW
            newpercentage = 10
        elif device.speed == Speed.MEDIUM:
            newspeed = SPEED_MEDIUM
            newpercentage = 35
        elif device.speed == Speed.HIGH:
            newspeed = SPEED_HIGH
            newpercentage = 70
        elif device.speed == Speed.MANUAL:
            newspeed = SPEED_MANUAL
            if device.manualspeed is not None:
                newpercentage = int(round(device.manualspeed * 100 / 255))
        modeswitch = {Mode.ONEWAY: MODE_OUT, Mode.TWOWAY: MODE_INOUT, Mode.IN: MODE_IN}
        newmode = modeswitch.get(device.mode, MODE_INOUT)
        # Are there any changes?
        if (
            newspeed == self._attr_preset_mode
            and newmode == self._mode
            and newpercentage == self._attr_percentage
        ):
            return
        self._mode = newmode
        self._attr_percentage = newpercentage
        self._attr_preset_mode = newspeed
        if self.hass is not None:
            self.schedule_update_ha_state()
        _LOGGER.debug(
            "Duka change, mode(%s), speed(%s), percentage(%s)",
            self._mode,
            self._attr_preset_mode,
            self._attr_percentage,
        )
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
        return self._attr_preset_mode != SPEED_OFF

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return self._supported_features

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if self.device is None or not self.device.is_initialized():
            return {}
        nicetime: str = ""
        if self.device.filter_timer is not None:
            timeinmin: int = self.device.filter_timer
            days: int = int(timeinmin / 60 / 24)
            timeinmin -= days * 60 * 24
            hours: int = int(timeinmin / 60)
            timeinmin -= hours * 60
            nicetime = f"{days}d {str(hours).zfill(2)}:{str(timeinmin).zfill(2)}"
        return {
            "mode": self.mode,
            "filter_alarm": self.device.filter_alarm,
            "filter_timer": self.device.filter_timer,
            "filter_timer_nice": nicetime,
            "humidity": self.device.humidity,
        }

    def set_percentage(self, percentage: int) -> None:
        """Set the speed of the fan, as a percentage."""
        manual_speed: int = int(percentage * 255 / 100)
        self.the_client.set_manual_speed(self.device, manual_speed)

    @property
    def percentage_step(self):
        """Return the step size for percentage."""
        return 1

    def set_preset_mode(self, preset_mode: str):
        """Set new preset mode."""
        if preset_mode == SPEED_HIGH:
            self.the_client.set_speed(self.device, Speed.HIGH)
        elif preset_mode == SPEED_MEDIUM:
            self.the_client.set_speed(self.device, Speed.MEDIUM)
        elif preset_mode == SPEED_LOW:
            self.the_client.set_speed(self.device, Speed.LOW)
        elif preset_mode == SPEED_OFF:
            self.the_client.set_speed(self.device, Speed.OFF)
        elif preset_mode == SPEED_MANUAL:
            self.the_client.set_speed(self.device, Speed.MANUAL)
        self._attr_preset_mode = preset_mode

    @property
    def mode(self):
        """Return the current mode"""
        return self._mode

    def set_mode(self, mode):
        """Set the fan mode."""
        if mode == MODE_OUT:
            mode = 0
        elif mode == MODE_INOUT:
            mode = 1
        elif mode == MODE_IN:
            mode = 2
        self.the_client.set_mode(self.device, mode)

    # pylint: disable=arguments-differ
    def turn_on(
        self,
        speed: str = None,
        **kwargs,
    ) -> None:
        """Turn on the entity."""
        if speed is not None:
            self.set_preset_mode(speed)
        else:
            self.the_client.turn_on(self.device)

    def turn_off(self, **kwargs) -> None:
        """Turn off the entity."""
        self.the_client.turn_off(self.device)
        return

    def reset_filter_timer(self):
        """Reset the filter timer to 90 days"""
        self.the_client.reset_filter_alarm(self.device)
        return

    def set_manual_speed(self, manual_speed: int):
        """Set the manual fan speed"""
        self.the_client.set_manual_speed(self.device, manual_speed)
        return

    @property
    def device_info(self):
        return self.dukaone_device_info()
