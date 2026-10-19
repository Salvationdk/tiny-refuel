"""Refresh and source-health binary sensors."""
from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.helpers.entity import EntityCategory
from .sensor import device_info
from .const import DOMAIN
from .entity_data import error_count


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([RefuelBinarySensor(entry.runtime_data, key) for key in ("refreshing", "problem")])


class RefuelBinarySensor(BinarySensorEntity):
    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, manager, key):
        self.manager, self.key = manager, key
        self._attr_unique_id = DOMAIN + "_" + key
        self._attr_name = "Hentning i gang" if key == "refreshing" else "Datakildefejl"
        self._attr_device_class = BinarySensorDeviceClass.RUNNING if key == "refreshing" else BinarySensorDeviceClass.PROBLEM
        self._attr_device_info = device_info()

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(self.manager.subscribe(self.async_write_ha_state))

    @property
    def is_on(self):
        return self.manager.refreshing if self.key == "refreshing" else bool(error_count(self.manager))
