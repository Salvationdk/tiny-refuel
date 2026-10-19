"""One refresh button for all sources."""
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN, VERSION


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([RefuelRefreshButton(entry.runtime_data, fuel) for fuel in (None, "benzin", "diesel", "el")])


class RefuelRefreshButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Hent alle data"
    _attr_icon = "mdi:refresh"
    _attr_unique_id = DOMAIN + "_refresh"
    _attr_device_info = DeviceInfo(identifiers={(DOMAIN, DOMAIN)}, name="Tiny Refuel", manufacturer="Tiny Refuel", model="Benzin, diesel og opladning", sw_version=VERSION)

    def __init__(self, manager, fuel=None):
        self.manager = manager
        self.fuel = fuel
        if fuel:
            self._attr_name = "Hent " + {"benzin": "benzinpriser", "diesel": "dieselpriser", "el": "ladedata"}[fuel]
            self._attr_unique_id = DOMAIN + "_refresh_" + fuel

    async def async_press(self):
        self.manager.start_refresh([self.fuel] if self.fuel else None)
