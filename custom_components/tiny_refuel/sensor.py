"""Small status sensors; full station data is served by the authenticated API."""
from datetime import datetime
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN, VERSION


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([RefuelSensor(entry.runtime_data, key) for key in ("locations", "prices", "updated")])


class RefuelSensor(SensorEntity):
    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, manager, key):
        self.manager, self.key = manager, key
        self._attr_unique_id = DOMAIN + "_" + key
        self._attr_name = {"locations": "Ladesteder", "prices": "Steder med lokal elpris", "updated": "Seneste hentning"}[key]
        self._attr_icon = "mdi:ev-station"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, DOMAIN)}, name="Tiny Refuel", manufacturer="Tiny Refuel", model="Benzin, diesel og opladning", sw_version=VERSION)
        if key == "updated":
            self._attr_device_class = SensorDeviceClass.TIMESTAMP

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(self.manager.subscribe(self.async_write_ha_state))

    @property
    def native_value(self):
        if self.key == "updated":
            value = self.manager.data.get("updated")
            return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None
        return self.manager.counts()[0 if self.key == "locations" else 1]

    @property
    def extra_state_attributes(self):
        data = self.manager.data
        return {"opdaterer": self.manager.refreshing, "fejl": len(self.manager.data.get("errors", [])),
                "seneste_fejl": self.manager.last_error, "version": VERSION,
                "brændstofkilder": data.get("fuel_sources", {}),
                "ladekilder": data.get("ev_sources", {}),
                "adresser_afventer_koordinater": data.get("geocode_pending", 0)}
