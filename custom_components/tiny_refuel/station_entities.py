"""Explicitly selected station prices, using the same cache as Tiny Refuel cards."""
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from .const import DOMAIN
from .entity_data import FUELS
from .sensor import device_info


def station_lookup(manager, station_id):
    marker = (id(manager.data), bool(manager.last_error))
    if getattr(manager, "_entity_station_marker", None) != marker:
        manager._entity_station_rows = {row["id"]: row for row in manager.station_snapshot()["stations"]}
        manager._entity_station_marker = marker
    return manager._entity_station_rows.get(station_id)


class RefuelStationPriceSensor(SensorEntity):
    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:cash"
    _unrecorded_attributes = frozenset({"station", "last_error"})
    _attr_device_info = device_info()

    def __init__(self, manager, station_id, fuel):
        self.manager, self.station_id, self.fuel = manager, station_id, fuel
        self._attr_unique_id = f"{DOMAIN}_station_{station_id}_{fuel}"
        self._attr_native_unit_of_measurement = "DKK/kWh" if fuel == "kwh" else "DKK/L"

    @property
    def name(self):
        row = station_lookup(self.manager, self.station_id)
        title = (row["brand"] + " " + row["name"]) if row else self.station_id
        return title + " " + FUELS[self.fuel]

    @property
    def native_value(self):
        row = station_lookup(self.manager, self.station_id)
        return row["prices"].get(self.fuel) if row and row["current"] else None

    @property
    def extra_state_attributes(self):
        row = station_lookup(self.manager, self.station_id)
        return {"station_id": self.station_id, "fuel": self.fuel, "current": bool(row and row["current"]),
                "station": row, "last_error": self.manager.last_error}

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(self.manager.subscribe(self.async_write_ha_state))
