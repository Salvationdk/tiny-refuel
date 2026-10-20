"""Read-only, response-capable actions for dashboards and automations."""
from copy import deepcopy
import sqlite3
import math
import voluptuous as vol
from homeassistant.auth.permissions.const import POLICY_READ
from homeassistant.core import SupportsResponse
from homeassistant.exceptions import HomeAssistantError, Unauthorized
from homeassistant.helpers import config_validation as cv
from .const import DOMAIN
from .catalog_store import CATALOG_FILES
from .dashboard_data import dashboard_snapshot
from .entity_data import coordinates, distance_km, positive, vehicle_origin, FUEL_FIELDS
from .price_history import FIELDS

PAGE = {vol.Optional("offset", default=0): vol.All(cv.positive_int),
        vol.Optional("limit", default=100): vol.All(cv.positive_int, vol.Range(min=1, max=500))}
def finite(value):
    if not math.isfinite(value):
        raise vol.Invalid("A finite number is required")
    return value


STATION_ID = vol.Match(r"^[0-9a-f]{24}$")
SCHEMAS = {
    "get_data": vol.Schema({vol.Optional("section", default="metadata"): str, **PAGE}),
    "get_status": vol.Schema({}),
    "get_stations": vol.Schema({
        vol.Optional("fuel"): vol.In(FIELDS),
        vol.Optional("brands", default=[]): [str],
        vol.Optional("station_ids", default=[]): [STATION_ID],
        vol.Optional("search", default=""): str,
        vol.Optional("current_only", default=True): cv.boolean,
        vol.Optional("location_entity"): cv.entity_id,
        vol.Optional("radius_km"): vol.All(vol.Coerce(float), finite, vol.Range(min=0, max=20000)),
        vol.Optional("sort", default="name"): vol.In(("name", "price", "distance")),
        **PAGE}),
    "get_vehicles": vol.Schema({
        vol.Optional("vehicle_id"): str,
        vol.Optional("vehicle"): vol.Schema({
            vol.Optional("id"): str, vol.Optional("navn"): str,
            vol.Optional("location_entity"): cv.entity_id,
            vol.Optional("brændstof"): vol.In(FUEL_FIELDS),
            vol.Optional("tank_liters"): vol.All(vol.Coerce(float), finite, vol.Range(min=0.01)),
            vol.Optional("batteri_kwh"): vol.All(vol.Coerce(float), finite, vol.Range(min=0.01)),
        }, extra=vol.ALLOW_EXTRA),
        **PAGE}),
    "get_history": vol.Schema({
        vol.Required("station_id"): STATION_ID,
        vol.Optional("fuel", default="p95"): vol.In(FIELDS),
        vol.Optional("days", default=7): vol.All(cv.positive_int, vol.Range(min=1, max=365))}),
    "get_catalog": vol.Schema({
        vol.Required("vehicle_type"): vol.In(tuple(CATALOG_FILES) + ("varevogn",)),
        vol.Optional("make", default=""): str,
        vol.Optional("search", default=""): str, **PAGE}),
}
SERVICE_NAMES = tuple(SCHEMAS)


def clean(value):
    """Detach responses from the live cache and keep every response valid JSON."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: clean(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(item) for item in value]
    return deepcopy(value)


def page(rows, options):
    offset, limit = options.get("offset", 0), options.get("limit", 100)
    end = min(len(rows), offset + limit)
    return {"items": rows[offset:end], "total": len(rows), "offset": offset,
            "limit": limit, "next_offset": end if end < len(rows) else None}


def select_stations(snapshot, options, origin=None):
    """Filter a shared station snapshot without changing it or collecting again."""
    fuel = options.get("fuel")
    sort = options.get("sort", "name")
    radius = options.get("radius_km")
    if sort == "price" and not fuel:
        raise HomeAssistantError("Vælg fuel ved sortering efter pris")
    if (sort == "distance" or radius) and origin is None:
        raise HomeAssistantError("En tilgængelig location_entity kræves til afstand og radius")
    brands = {brand.casefold() for brand in options.get("brands", [])}
    ids = set(options.get("station_ids", []))
    search = options.get("search", "").casefold()
    rows = []
    for station in snapshot["stations"]:
        if options.get("current_only", True) and not station["current"]:
            continue
        if brands and station["brand"].casefold() not in brands:
            continue
        if ids and station["id"] not in ids:
            continue
        if search and search not in " ".join(str(station.get(key) or "") for key in ("brand", "name", "address")).casefold():
            continue
        if fuel and not positive(station["prices"].get(fuel)):
            continue
        row = dict(station)
        position = coordinates(row)
        km = distance_km(origin, position) if origin and position else None
        row["distance_km"] = round(km, 3) if km is not None else None
        if radius and (km is None or km > radius):
            continue
        if sort == "distance" and km is None:
            continue
        if position:
            lat, lon = position
            row["navigation"] = {
                "google": f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}",
                "waze": f"https://waze.com/ul?ll={lat},{lon}&navigate=yes"}
        rows.append(row)
    if sort == "price":
        rows.sort(key=lambda r: (not r["current"], r["prices"][fuel], r["id"]))
    elif sort == "distance":
        rows.sort(key=lambda r: (not r["current"], r["distance_km"], r["id"]))
    else:
        rows.sort(key=lambda r: (r["brand"].casefold(), r["name"].casefold(), r["id"]))
    return page(rows, options)


def catalog_page(catalog, options):
    make, search = options.get("make", "").casefold(), options.get("search", "").casefold()
    rows = []
    for brand in catalog["brands"]:
        if make and brand["mærke"].casefold() != make:
            continue
        for model in brand["modeller"]:
            if search and search not in (brand["mærke"] + " " + model["model"]).casefold():
                continue
            rows.append({"make": {k: v for k, v in brand.items() if k != "modeller"}, "model": model})
    return {**page(rows, options), "metadata": {k: v for k, v in catalog.items() if k != "brands"}}


async def can_read_position(hass, call, entity_id):
    if not entity_id or not call.context.user_id:
        return True
    user = await hass.auth.async_get_user(call.context.user_id)
    if user is None or not user.is_active:
        return False
    return user.is_admin or user.permissions.check_entity(entity_id, POLICY_READ)


async def async_query(hass, manager, call):
    """Response actions reuse manager data. Only catalog requests can download catalogs."""
    options = dict(call.data)
    state = hass.data.get(DOMAIN, {})
    service = call.service
    if service == "get_history":
        try:
            return clean(await hass.async_add_executor_job(
                manager.history.query, options["station_id"], options.get("fuel", "p95"), options.get("days", 7)))
        except (OSError, ValueError, sqlite3.Error) as exc:
            raise HomeAssistantError("Historikken kunne ikke læses") from exc
    if service == "get_catalog":
        store = state.get("catalogs")
        if store is None:
            raise HomeAssistantError("Kataloget er ikke tilgængeligt")
        catalog = await store.get(options["vehicle_type"])
        return clean(await hass.async_add_executor_job(catalog_page, catalog, options))
    if service == "get_stations":
        entity_id = options.get("location_entity")
        if not await can_read_position(hass, call, entity_id):
            raise Unauthorized(entity_id=entity_id)
        origin = vehicle_origin(hass, {"location_entity": entity_id}) if entity_id else None
        def query():
            snapshot = manager.station_snapshot()
            return {**select_stations(snapshot, options, origin),
                    "updated": snapshot["updated"], "last_error": snapshot["last_error"],
                    "refreshing": snapshot["refreshing"]}
        return clean(await hass.async_add_executor_job(query))
    if service == "get_status":
        result = dashboard_snapshot(manager, state.get("catalogs"), state.get("map_status"))
        result.pop("vehicles", None)
        return clean({"schema_version": 1, **result})
    allowed = []
    configured = [options["vehicle"]] if "vehicle" in options else manager.vehicles
    for vehicle in configured:
        if await can_read_position(hass, call, vehicle.get("location_entity")):
            allowed.append(vehicle)
    if service == "get_vehicles":
        selected = options.get("vehicle_id")
        positioned = [(vehicle, vehicle_origin(hass, vehicle)) for vehicle in allowed
                      if not selected or vehicle.get("id") == selected]
        def calculate():
            rows = []
            for vehicle, origin in positioned:
                calculations = {}
                for fuel in FUEL_FIELDS.get(vehicle.get("brændstof"), ()):
                    station, km = manager.nearest(fuel, origin)
                    price = station.get(fuel) if station else None
                    if station and station.get("app_only"):
                        price = None
                    capacity = vehicle.get("batteri_kwh" if fuel == "kwh" else "tank_liters")
                    calculations[fuel] = {
                        "station": station, "distance_km": round(km, 3) if km is not None else None,
                        "price": price if positive(price) else None,
                        "full_cost": round(price * capacity, 2) if positive(price) and positive(capacity) else None}
                rows.append({**vehicle, "calculations": calculations})
            return {**page(rows, options), "updated": manager.data.get("updated"),
                    "basis": "Nærmeste aktuelle sted. Luftlinje; fuld kapacitet uden ladetab, rabatter og gebyrer."}
        return clean(await hass.async_add_executor_job(calculate))
    snapshot = manager.snapshot()
    snapshot["vehicles"] = allowed if "vehicle" not in options else []
    keys = sorted(snapshot)
    section = options.get("section", "metadata")
    if section == "metadata":
        return clean({"schema_version": 1, "sections": keys,
                      "data": {k: v for k, v in snapshot.items() if not isinstance(v, (dict, list))}})
    if section not in snapshot:
        raise HomeAssistantError("Ukendt section. Kald get_data uden section for at se mulighederne")
    value = snapshot[section]
    if isinstance(value, dict):
        result = {**page([{"key": k, "value": v} for k, v in sorted(value.items())], options), "kind": "mapping"}
    elif isinstance(value, list):
        result = {**page(value, options), "kind": "list"}
    else:
        result = {"value": value, "kind": "value"}
    return clean({"schema_version": 1, "section": section, **result,
                  "updated": manager.data.get("updated"), "last_error": manager.last_error})


def async_register_services(hass, manager):
    async def handle(call):
        return await async_query(hass, manager, call)
    for name, schema in SCHEMAS.items():
        hass.services.async_register(DOMAIN, name, handle, schema=schema, supports_response=SupportsResponse.ONLY)


def async_remove_services(hass):
    for name in SERVICE_NAMES:
        hass.services.async_remove(DOMAIN, name)
