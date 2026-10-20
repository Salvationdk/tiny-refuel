"""Fuel, charging, source-health and optional vehicle sensors."""
from datetime import datetime
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers import entity_registry as er
from homeassistant.core import callback
from .const import DOMAIN, VERSION
from .entity_data import (BRANDS, FUELS, FUEL_FIELDS, positive,
                          station_attributes, vehicle_origin, error_count)

BASE = {
    "locations": ("Ladesteder", "mdi:ev-station", None),
    "prices": ("Steder med lokal elpris", "mdi:ev-station", None),
    "updated": ("Seneste hentning", "mdi:update", None),
    "fuel_stations": ("Brændstofstationer", "mdi:gas-station", None),
    "errors": ("Fejl i seneste hentning", "mdi:alert-circle-outline", None),
    "coordinates_pending": ("Adresser uden koordinater", "mdi:map-marker-question", None),
}
for field, label in FUELS.items():
    BASE["lowest_" + field] = ("Billigste lokale " + label.lower(), "mdi:cash", "DKK/kWh" if field == "kwh" else "DKK/L")
    BASE["average_" + field] = ("Gennemsnitlig lokal " + label.lower(), "mdi:chart-line", "DKK/kWh" if field == "kwh" else "DKK/L")


def device_info():
    return DeviceInfo(identifiers={(DOMAIN, DOMAIN)}, name="Tiny Refuel", manufacturer="Tiny Refuel",
                      model="Benzin, diesel og opladning", sw_version=VERSION)


async def async_setup_entry(hass, entry, async_add_entities):
    manager = entry.runtime_data
    entities = [RefuelSensor(manager, key) for key in BASE]
    catalog_store=hass.data.get(DOMAIN,{}).get("catalogs") if hasattr(hass,"data") else None
    if catalog_store is not None:entities.append(RefuelCatalogStatusSensor(catalog_store))
    # Optional provider sensors remain available without cluttering a default install.
    for brand in BRANDS:
        fields = ("kwh",) if brand in ("Clever", "E.ON", "IONITY") else tuple(FUELS)
        for field in fields:
            entities.append(RefuelPriceSensor(manager, field, brand))
    entities.extend(RefuelTariffSensor(manager, brand) for brand in ("OK", "Q8", "Circle K", "E.ON", "IONITY"))
    for kind, sources in SOURCE_NAMES.items():
        entities.extend(RefuelSourceSensor(manager, kind, source, label) for source, label in sources.items())
    from .station_entities import RefuelStationPriceSensor
    selected_stations = set(getattr(entry, "options", {}).get("station_sensor_ids", []))
    for station_id in sorted(selected_stations):
        entities.extend(RefuelStationPriceSensor(manager, station_id, field) for field in FUELS)
    for vehicle in manager.vehicles:
        entities.extend(RefuelVehicleInfoSensor(manager, vehicle, metric) for metric in ("info", "tank_liters", "batteri_kwh"))
        for field in FUEL_FIELDS.get(vehicle.get("brændstof"), ()):
            for metric in ("station", "distance", "price", "full_cost"):
                entities.append(RefuelVehicleSensor(manager, vehicle, field, metric))
    if getattr(entry, "entry_id", None):
        valid = {entity.unique_id for entity in entities if isinstance(entity, (RefuelVehicleSensor, RefuelVehicleInfoSensor, RefuelStationPriceSensor))}
        registry = er.async_get(hass)
        for registered in er.async_entries_for_config_entry(registry, entry.entry_id):
            if registered.unique_id.startswith((DOMAIN + "_vehicle_", DOMAIN + "_station_")) and registered.unique_id not in valid:
                registry.async_remove(registered.entity_id)
    async_add_entities(entities)


class RefuelSensor(SensorEntity):
    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, manager, key):
        self.manager, self.key = manager, key
        self._attr_unique_id = DOMAIN + "_" + key
        self._attr_name, self._attr_icon, unit = BASE[key]
        self._attr_device_info = device_info()
        self._attr_native_unit_of_measurement = unit
        if key == "updated":
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
        elif unit:
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif key in ("errors", "coordinates_pending"):
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(self.manager.subscribe(self.async_write_ha_state))

    @property
    def native_value(self):
        data = self.manager.data
        if self.key == "updated":
            value = data.get("updated")
            try:
                stamp = datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None
                return stamp if stamp is None or stamp.tzinfo else None
            except (ValueError, TypeError, AttributeError):
                return None
        if self.key in ("locations", "prices"):
            return self.manager.counts()[0 if self.key == "locations" else 1]
        if self.key == "fuel_stations":
            return len({(r.get("brand"), r.get("location_id") or r.get("address") or r.get("name"))
                        for r in data.get("stations", []) if isinstance(r, dict) and not r.get("liste")})
        if self.key == "errors":
            return error_count(self.manager)
        if self.key == "coordinates_pending":
            geo = data.get("geocoding", {})
            return geo.get("queued", 0) + geo.get("not_found", 0) if geo else data.get("geocode_pending", 0)
        method, field = self.key.split("_", 1)
        rows = self.manager.current_price_rows(field)
        if not rows:
            return None
        values = [r[field] for r in rows]
        return round(min(values) if method == "lowest" else sum(values)/len(values), 3)

    @property
    def extra_state_attributes(self):
        data = self.manager.data
        if self.key.startswith(("lowest_", "average_")):
            field = self.key.split("_", 1)[1]
            rows = self.manager.current_price_rows(field)
            row = min(rows, key=lambda r: r[field]) if rows and self.key.startswith("lowest_") else None
            return {**station_attributes(row, data), "antal_priser": len(rows), "seneste_fejl": self.manager.last_error}
        return {"opdaterer": self.manager.refreshing, "fejl": error_count(self.manager),
                "seneste_fejl": self.manager.last_error, "version": VERSION,
                "brændstofkilder": data.get("fuel_sources", {}), "ladekilder": data.get("ev_sources", {}),
                "adresser_afventer_koordinater": data.get("geocode_pending", 0)}


class RefuelPriceSensor(RefuelSensor):
    """Optional cheapest local price by company and energy type."""
    _attr_entity_registry_enabled_default = False

    def __init__(self, manager, field, brand):
        super().__init__(manager, "lowest_" + field)
        self.brand = brand
        self._attr_unique_id = DOMAIN + "_provider_" + brand.casefold().replace(" ", "_") + "_" + field
        self._attr_name = brand + " " + FUELS[field] + " billigste lokale pris"

    @property
    def native_value(self):
        rows = self.manager.current_price_rows(self.key.split("_", 1)[1], self.brand)
        return min(r[self.key.split("_", 1)[1]] for r in rows) if rows else None

    @property
    def extra_state_attributes(self):
        field = self.key.split("_", 1)[1]
        rows = self.manager.current_price_rows(field, self.brand)
        row = min(rows, key=lambda r: r[field]) if rows else None
        return {**station_attributes(row, self.manager.data), "antal_priser": len(rows), "seneste_fejl": self.manager.last_error}


class RefuelVehicleSensor(RefuelSensor):
    def __init__(self, manager, vehicle, field, metric):
        super().__init__(manager, "lowest_" + field)
        self.vehicle, self.field, self.metric = vehicle, field, metric
        self._attr_unique_id = f"{DOMAIN}_vehicle_{vehicle['id']}_{field}_{metric}"
        title = {"station": "nærmeste station", "distance": "afstand", "price": "pris ved nærmeste station", "full_cost": "fuld opladning" if field == "kwh" else "fuld tank"}[metric]
        self._attr_name = f"{vehicle['navn']} {FUELS[field]} {title}"
        self._attr_native_unit_of_measurement = {"station": None, "distance": "km", "price": "DKK/kWh" if field == "kwh" else "DKK/L", "full_cost": "DKK"}[metric]
        self._attr_state_class = SensorStateClass.MEASUREMENT if metric != "station" else None
        self._attr_icon = "mdi:map-marker-distance" if metric == "distance" else "mdi:gas-station"

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        entity_id = self.vehicle.get("location_entity")
        if entity_id:
            self.async_on_remove(async_track_state_change_event(self.hass, [entity_id], self._position_changed))

    @callback
    def _position_changed(self, event):
        self.async_write_ha_state()

    def _nearest(self):
        return self.manager.nearest(self.field, vehicle_origin(self.manager.hass, self.vehicle))

    @property
    def native_value(self):
        row, distance = self._nearest()
        if row is None:
            return None
        if self.metric == "station":
            return str(row.get("name") or row.get("address") or row.get("brand"))[:255]
        if self.metric == "distance":
            return round(distance, 2)
        price = row.get(self.field)
        if not positive(price) or row.get("app_only"):
            return None
        if self.metric == "price":
            return price
        capacity = self.vehicle.get("batteri_kwh" if self.field == "kwh" else "tank_liters")
        return round(price * capacity, 2) if positive(capacity) else None

    @property
    def extra_state_attributes(self):
        row, distance = self._nearest()
        return {**station_attributes(row, self.manager.data), "koeretoej_id": self.vehicle["id"],
                "position_entity": self.vehicle.get("location_entity"), "seneste_fejl": self.manager.last_error, "afstand_km": round(distance, 2) if distance is not None else None,
                "beregning": "Luftlinje. Fuld kapacitet uden ladetab, rabatter eller ekstra gebyrer."}


SOURCE_NAMES = {
    "fuel_sources": {"api.circlek.com": "Circle K og Ingo brændstof", "f24.dk": "Q8 og F24 brændstof",
                     "goon.nu": "Go'on brændstof", "unoxmobility.dk": "Uno-X brændstof",
                     "shellservice.dk": "Shell brændstof", "mobility-prices.ok.dk": "OK brændstof",
                     "oil-fuel-api": "OIL brændstof"},
    "ev_sources": {"clever": "Clever ladesteder", "eon": "E.ON ladesteder", "ionity": "IONITY ladesteder",
                   "ok": "OK ladesteder", "oil": "OIL ladesteder", "shell": "Shell ladesteder", "circle_k": "Circle K ladesteder"},
}


class RefuelSourceSensor(RefuelSensor):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, manager, kind, source, label):
        super().__init__(manager, "errors")
        self.kind, self.source = kind, source
        self._attr_name = label + " kildestatus"
        self._attr_unique_id = f"{DOMAIN}_{kind}_{source}"

    @property
    def native_value(self):
        return self.manager.data.get(self.kind, {}).get(self.source, {}).get("status")

    @property
    def extra_state_attributes(self):
        return dict(self.manager.data.get(self.kind, {}).get(self.source, {}))


class RefuelTariffSensor(RefuelSensor):
    """Standard public tariff, explicitly separate from verified local prices."""
    _attr_entity_registry_enabled_default = False

    def __init__(self, manager, brand):
        super().__init__(manager, "lowest_kwh")
        self.brand = brand
        self._attr_name = brand + " generel standardladetakst"
        self._attr_unique_id = DOMAIN + "_tariff_" + brand.casefold().replace(" ", "_")

    def _tariffs(self):
        from .entity_data import has_location
        return [r for r in self.manager.data.get("ev", []) if isinstance(r, dict)
                and str(r.get("brand", "")).casefold() == self.brand.casefold()
                and not has_location(r) and positive(r.get("kwh"))]

    def _standard(self):
        match = {"OK": "normal", "Q8": "normal", "E.ON": "ac", "Circle K": "lyn", "IONITY": "direkte betaling"}[self.brand]
        return next((r for r in self._tariffs() if match in str(r.get("name", "")).casefold()), None)

    @property
    def native_value(self):
        row = self._standard()
        return row["kwh"] if row and not row.get("stale") and not self.manager.last_error else None

    @property
    def extra_state_attributes(self):
        row = self._standard()
        return {**station_attributes(row, self.manager.data),
                "datagrundlag": "Generel selskabstakst eller fra-pris; ikke en lokal stationspris. Abonnement og ekstra gebyrer er ikke medregnet.",
                "takster": [{"navn": r.get("name"), "kr_kwh": r["kwh"], "gemte_data": bool(r.get("stale")),
                             "hentet": r.get("source_updated")} for r in self._tariffs()]}



class RefuelCatalogStatusSensor(SensorEntity):
    """One diagnostic entity; catalogs themselves are not sensor states."""
    _attr_should_poll=False
    _attr_has_entity_name=True
    _attr_name="Katalogstatus"
    _attr_icon="mdi:book-search-outline"
    _attr_entity_category=EntityCategory.DIAGNOSTIC
    _attr_unique_id=DOMAIN+"_catalog_status"
    _attr_device_info=device_info()

    def __init__(self,store):self.store=store

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(self.store.subscribe(self.async_write_ha_state))

    @property
    def native_value(self):
        data=self.store.snapshot()
        if not data['loaded_types']:return 'not_loaded'
        return 'cached' if data['stale_types'] else 'ready'

    @property
    def extra_state_attributes(self):return self.store.snapshot()


class RefuelVehicleInfoSensor(RefuelSensor):
    """Stable shared vehicle metadata and capacities for standard HA cards."""

    def __init__(self, manager, vehicle, metric="info"):
        super().__init__(manager, "errors")
        self.vehicle, self.metric = vehicle, metric
        self._attr_unique_id = f"{DOMAIN}_vehicle_{vehicle['id']}_{metric}"
        label = {"info": "oplysninger", "tank_liters": "tankkapacitet", "batteri_kwh": "batterikapacitet"}[metric]
        self._attr_name = vehicle["navn"] + " " + label
        self._attr_icon = "mdi:car-info" if metric == "info" else "mdi:gas-station" if metric == "tank_liters" else "mdi:battery"
        self._attr_entity_category = None
        self._attr_native_unit_of_measurement = {"info": None, "tank_liters": "L", "batteri_kwh": "kWh"}[metric]
        self._attr_state_class = None if metric == "info" else SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        if self.metric == "info":
            return str(self.vehicle.get("navn") or "Køretøj")[:255]
        value = self.vehicle.get(self.metric)
        return value if positive(value) else None

    @property
    def extra_state_attributes(self):
        return dict(self.vehicle)
