"""Price and location calculations shared by the integration's entities."""
import math

FUELS = {"p95": "Benzin 95", "p100": "Benzin 100", "diesel": "Diesel", "kwh": "El"}
FUEL_FIELDS = {"benzin": ("p95", "p100"), "diesel": ("diesel",), "el": ("kwh",),
               "hybrid": ("p95", "p100"), "plug_in_hybrid": ("p95", "p100", "kwh")}
BRANDS = ("Circle K", "Ingo", "F24", "Q8", "Go'on", "Shell", "Uno-X", "OK", "OIL", "Clever", "E.ON", "IONITY")


def positive(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def coordinates(row):
    lat, lon = row.get("lat"), row.get("lon")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in (lat, lon)):
        return None
    if abs(lat) > 90 or abs(lon) > 180 or (lat == 0 and lon == 0):
        return None
    return lat, lon


def has_location(row):
    return bool(row.get("address") or row.get("location_id") or coordinates(row))


def price_rows(data, field, brand=None):
    """Return current local prices only; list prices and stale rows are excluded."""
    rows = data.get("ev" if field == "kwh" else "stations", [])
    return [row for row in rows if isinstance(row, dict) and positive(row.get(field))
            and not row.get("stale") and not row.get("liste")
            and (brand is None or str(row.get("brand", "")).casefold() == brand.casefold())
            and (field != "kwh" or (has_location(row) and not row.get("app_only")))]


def station_attributes(row, data):
    if row is None:
        return {"datagrundlag": "Aktuelle lokale priser; listepriser, generelle takster og gemte fejlramte data er udeladt"}
    return {"selskab": row.get("brand"), "station": row.get("name"), "adresse": row.get("address"),
            "latitude": row.get("lat"), "longitude": row.get("lon"), "kilde": row.get("source"),
            "pris_oplyst": row.get("lu"), "hentet": row.get("source_updated") or data.get("updated"),
            "gemte_data": bool(row.get("stale"))}


def distance_km(origin, destination):
    lat1, lon1 = map(math.radians, origin)
    lat2, lon2 = map(math.radians, destination)
    a = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6371 * 2 * math.asin(min(1, math.sqrt(a)))


def vehicle_origin(hass, vehicle):
    entity_id = vehicle.get("location_entity")
    state = hass.states.get(entity_id) if entity_id else None
    if state is None or state.state in ("unavailable", "unknown"):
        return None
    return coordinates({"lat": state.attributes.get("latitude"), "lon": state.attributes.get("longitude")})


def nearest_row(data, field, origin):
    if origin is None:
        return None, None
    rows = price_rows(data, field)
    # An EV location can be navigable even without a published local price.
    if field == "kwh":
        rows = [row for row in data.get("ev", []) if isinstance(row, dict)
                and not row.get("stale") and has_location(row)]
    candidates = [(row, distance_km(origin, coordinates(row))) for row in rows if coordinates(row)]
    return min(candidates, key=lambda item: item[1]) if candidates else (None, None)


def error_count(manager):
    data = manager.data
    return len(data.get("errors", [])) + len(data.get("benefit_errors", [])) + bool(manager.last_error)
