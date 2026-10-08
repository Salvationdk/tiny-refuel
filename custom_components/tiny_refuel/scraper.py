#!/usr/bin/env python3
"""Tiny Refuel v0.1 – self-scraped petrol, diesel and EV charging data.

Sources (all keyless):
  Circle K + Ingo : official public API  https://api.circlek.com/eu/prices
                    (X-App-Name: PRICES) + coords joined from circlek.dk/station-search
  F24 + Q8        : their own JSON endpoint (/Station/GetStationPrices) incl. HPC kWh
  Go'on           : server-rendered price table (Blyfri 92/95/Diesel)
  Shell           : pump-price PDF (URL discovered from shellservice.dk/pumpepriser)
  OK              : chain list prices + change date (HTML) + charger kWh prices
  OIL             : chain business prices (HTML table)
Coordinates for address-only stations via Nominatim, cached in adresse-cache.json
(max 30 new lookups per run). Writes .storage/tiny_refuel/priser-og-ladesteder.json (no secret).

Intended schedule: every 6 hours (providers switch prices ~00:00).
"""
import html
from collections import deque
import json
import math
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser

ROOT = os.environ.get("TINY_REFUEL_ROOT", "/config")
WWW_DIR = os.path.join(ROOT, ".storage", "tiny_refuel")
OUT = os.path.join(WWW_DIR, "priser-og-ladesteder.json")
ADDRESS_CACHE = os.path.join(WWW_DIR, "adresse-cache.json")
STATION_CACHE = os.path.join(WWW_DIR, "stations-cache.json")

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
GEO_UA = "TinyRefuel/0.1 (Home Assistant integration)"
NOM_MAX_NEW = 30
NOM_SLEEP = 1.2

CK_API = "https://api.circlek.com/eu/prices/v1/fuel/countries/DK"
CK_SEARCH = "https://circlek.dk/station-search"
F24_URLS = [
    "https://www.f24.dk/Station/GetStationPrices?page=1&pageSize=500",
    "https://www.q8.dk/Station/GetStationPrices?page=1&pageSize=500",
]
Q8_EL_URL = "https://www.q8.dk/erhverv/priser/"
GOON_URL = "https://goon.nu/aktuelle-standerpriser/"
UNOX_URL = "https://unoxmobility.dk/privat/braendstofpriser"
SHELL_PAGE = "https://shellservice.dk/pumpepriser"
OK_URL = "https://www.ok.dk/privat/produkter/priser/seneste-prisaendring"
OK_EL_URL = "https://www.ok.dk/privat/produkter/opladning/ude/ladestander-priser"
OIL_URL = "https://www.oil-tankstationer.dk/priser-erhverv/gaeldende-priser/"
SHELL_ERHVERV_URL = "https://shellservice.dk/erhverv/braendstofpriser"
CLEVER_LOCATIONS_URL = "https://clever.dk/api/v2/chargers/locations"
EON_LOCATIONS_URL = "https://www.edri.com/api/stations"
TESLA_LOCATIONS_URL = "https://www.tesla.com/da_DK/findus/list/superchargers/Denmark"
# Linked by IONITY's own network page (www.ionity.eu/network).
IONITY_LOCATIONS_URL = "https://wf-assets.com/ionity/mapdata.json"
OK_FUEL_API = "https://mobility-prices.ok.dk/api/v1/fuel-prices"
OIL_FUEL_API = "https://apim-fuel-prices-prod.azure-api.net/Oil-FuelPrices/prices"
OK_LOCATIONS_API = "https://geo-emobility.okcloud.dk/api/v2/locations/nearby"
OIL_STATIONS_PAGE = "https://www.oil-tankstationer.dk/tankstationer-find-din-station/"
CK_CHARGING_API = "https://map-prod-public.evmaps-prod.alpaque.net/api/v4/locations"
SHELL_CHARGING_API = "https://shellretaillocator.geoapp.me/api/v2/locations/nearest_to"


def get(url, headers=None, timeout=45):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def get_text(url, headers=None, timeout=45):
    return get(url, headers, timeout).decode("utf-8", errors="replace")


def to_float(value):
    if value is None:
        return None
    try:
        result = float(str(value).replace(",", "."))
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def norm_addr(addr):
    t = re.sub(r"danmark", " ", str(addr or "").lower())
    t = re.sub(r"[^a-z0-9æøå]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def save_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)


# Public feeds used by the providers' own maps. No API keys or extra packages.
# These feeds describe locations, not live availability or charging tariffs.
def dk_coordinates(lat, lon):
    lat, lon = to_float(lat), to_float(lon)
    if lat is None or lon is None or not (54 <= lat <= 58 and 7 <= lon <= 16):
        return None
    return lat, lon


def dict_values(value):
    if isinstance(value, dict):
        return list(value.values())
    return value if isinstance(value, list) else []


def normalize_clever_locations(payload):
    if not isinstance(payload, (dict, list)):
        raise ValueError("Clever: unexpected response format")
    rows = []
    for location in dict_values(payload):
        if not isinstance(location, dict) or location.get("state") != "Active":
            continue
        address = location.get("address") or {}
        if address.get("countryCode") != "DK":
            continue
        access = location.get("publicAccess") or {}
        if access.get("visibility") != "Always":
            continue
        coordinates = location.get("coordinates") or {}
        coords = dk_coordinates(coordinates.get("lat"), coordinates.get("lng"))
        if not coords or not address.get("address") or not location.get("locationId"):
            continue
        # Aggregate each AC/DC option separately so a nearby AC site does not
        # hide a fast charger from the same provider in the card.
        options = {}
        for evse in dict_values(location.get("evses")):
            if not isinstance(evse, dict):
                continue
            for connector in dict_values(evse.get("connectors")):
                if not isinstance(connector, dict):
                    continue
                power = to_float(connector.get("maxPowerKw"))
                if power is None or power <= 0:
                    continue
                kind = "DC" if str(connector.get("powerType", "")).upper().startswith("DC") else "AC"
                option = options.setdefault(kind, {"power": 0, "types": set(), "evses": set()})
                option["power"] = max(option["power"], power)
                if connector.get("plugType"):
                    option["types"].add(str(connector["plugType"]))
                if evse.get("evseId"):
                    option["evses"].add(str(evse["evseId"]))
        for kind, option in options.items():
            rows.append({"brand": "Clever", "name": location.get("name") or "Clever",
                         "address": " ".join(str(address[k]) for k in ("address", "postalCode", "city") if address.get(k)),
                         "lat": coords[0], "lon": coords[1], "kind": kind,
                         "power_kw": round(option["power"], 2), "connector_types": sorted(option["types"]),
                         "plugs": len(option["evses"]), "kwh": None, "app_only": True,
                         "lu": None, "source": "clever.dk", "location_id": str(location["locationId"]),
                         "source_url": CLEVER_LOCATIONS_URL})
    return rows


def normalize_eon_locations(payload):
    if not isinstance(payload, list):
        raise ValueError("E.ON: unexpected response format")
    rows = []
    for location in payload:
        if not isinstance(location, dict) or location.get("countryCode") != "DK":
            continue
        if location.get("chargingUseCase") == "Truck":
            continue
        coords = dk_coordinates(location.get("latitude"), location.get("longitude"))
        if not coords or not location.get("address") or not location.get("locationId"):
            continue
        options = {}
        for evse in dict_values(location.get("evses")):
            if not isinstance(evse, dict) or evse.get("adminStatus") != "in-service":
                continue
            for connector in dict_values(evse.get("connectors")):
                if not isinstance(connector, dict):
                    continue
                power = to_float(connector.get("power"))
                kind = connector.get("currentType")
                if power is None or power <= 0 or kind not in ("AC", "DC"):
                    continue
                option = options.setdefault(kind, {"power": 0, "types": set(), "evses": set()})
                option["power"] = max(option["power"], power)
                if connector.get("type"):
                    option["types"].add(str(connector["type"]))
                if evse.get("stationId") is not None:
                    option["evses"].add(str(evse["stationId"]))
        for kind, option in options.items():
            rows.append({"brand": "E.ON", "name": location.get("name") or "E.ON Drive",
                         "address": " ".join(str(location[k]) for k in ("address", "postalCode", "city") if location.get(k)),
                         "lat": coords[0], "lon": coords[1], "kind": kind,
                         "power_kw": round(option["power"], 2), "connector_types": sorted(option["types"]),
                         "plugs": len(option["evses"]), "kwh": None, "app_only": True,
                         "lu": None, "source": "edri.com", "location_id": str(location["locationId"]),
                         "source_url": EON_LOCATIONS_URL})
    return rows


class TeslaPageData(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inside = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "script" and dict(attrs).get("id") == "__NEXT_DATA__":
            self.inside = True

    def handle_endtag(self, tag):
        if tag == "script":
            self.inside = False

    def handle_data(self, data):
        if self.inside:
            self.parts.append(data)


def normalize_tesla_locations(page):
    document = TeslaPageData()
    document.feed(page)
    payload = json.loads("".join(document.parts))
    locations = payload.get("props", {}).get("pageProps", {}).get("data")
    if not isinstance(locations, list):
        raise ValueError("Tesla: unexpected location format")
    rows = []
    for location in locations:
        if not isinstance(location, dict):
            continue
        data = location.get("_source") or {}
        charger = data.get("supercharger_function") or {}
        address = (data.get("key_data") or {}).get("address") or {}
        # Include only confirmed public, open Superchargers, never planned sites.
        if (address.get("country") != "DK" or charger.get("site_status") != "open"
                or charger.get("project_status") != "Open" or charger.get("access_type") != "Public"):
            continue
        coords = dk_coordinates(charger.get("actual_latitude"), charger.get("actual_longitude"))
        formatted = address.get("formatted_address")
        if not coords or not isinstance(formatted, list) or not formatted or not location.get("uuid"):
            continue
        name = (data.get("marketing") or {}).get("display_name") or "Tesla Supercharger"
        others = charger.get("open_to_non_tesla")
        rows.append({"brand": "Tesla", "name": name, "address": " ".join(str(v) for v in formatted if v),
                     "lat": coords[0], "lon": coords[1], "kind": "DC", "kwh": None,
                     "app_only": True, "lu": None, "source": "tesla.com",
                     "location_id": str(location["uuid"]), "source_url": TESLA_LOCATIONS_URL,
                     "access_note": "Åben for andre elbiler; kontrollér stik og bil i Tesla-appen" if others is True
                     else "Kun Tesla" if others is False else "Adgang for andre bilmærker ikke oplyst"})
    return rows


def normalize_ionity_locations(payload):
    locations = payload.get("LocationDetails") if isinstance(payload, dict) else None
    if not isinstance(locations, list):
        raise ValueError("IONITY: unexpected response format")
    rows = []
    for location in locations:
        if (not isinstance(location, dict) or str(location.get("country", "")).lower() != "denmark"
                or location.get("state") != "active" or not location.get("name")):
            continue
        coords = dk_coordinates(location.get("latitude"), location.get("longitude"))
        if not coords:
            continue
        power_counts = [(power, to_float(location.get("connectors%dkw" % power)) or 0)
                        for power in (50, 200, 350, 400, 500, 600)]
        # Only report powers and counts explicitly present in the source.
        dc_count = sum(count for _, count in power_counts)
        if dc_count > 0:
            rows.append({"brand": "Ionity", "name": location["name"], "address": "",
                         "lat": coords[0], "lon": coords[1], "kind": "DC", "kwh": None,
                         "power_kw": max(power for power, count in power_counts if count > 0),
                         "plugs": int(dc_count), "app_only": True, "lu": None, "source": "ionity.eu",
                         "location_id": "%s|%s|%s" % (location["name"], coords[0], coords[1]),
                         "source_url": IONITY_LOCATIONS_URL})
        ac_count = to_float(location.get("connectorsAC")) or 0
        if ac_count > 0:
            rows.append({"brand": "Ionity", "name": location["name"], "address": "",
                         "lat": coords[0], "lon": coords[1], "kind": "AC", "kwh": None,
                         "plugs": int(ac_count), "app_only": True, "lu": None, "source": "ionity.eu",
                         "location_id": "%s|%s|%s" % (location["name"], coords[0], coords[1]),
                         "source_url": IONITY_LOCATIONS_URL})
    return rows


def load_ok_locations():
    # Public read operation, documented in this service's OpenAPI schema.
    # A fixed centre and radius cover Denmark; no user's position is sent.
    payload = {"latitude": 56.26392, "longitude": 9.501785, "distanceM": 500000,
               "maxLocations": 10000, "filters": {"locationSources": ["OK"]}}
    req = urllib.request.Request(OK_LOCATIONS_API, data=json.dumps(payload).encode("utf-8"),
                                 headers={"User-Agent": UA, "Content-Type": "application/json",
                                          "Accept": "application/json", "caller": "ansf_test"})
    with urllib.request.urlopen(req, timeout=45) as response:
        data = json.load(response)
    if (not isinstance(data, dict) or not isinstance(data.get("locations"), list)
            or len(data["locations"]) >= payload["maxLocations"]
            or to_float(data.get("nextDistanceM")) != payload["distanceM"]):
        raise ValueError("OK: incomplete location response")
    return data


def normalize_ok_locations(payload):
    locations = payload.get("locations") if isinstance(payload, dict) else None
    if not isinstance(locations, list):
        raise ValueError("OK: unexpected charging location response")
    rows = []
    for location in locations:
        if (not isinstance(location, dict) or location.get("source") != "OK"
                or not location.get("locationId") or not location.get("address")):
            continue
        coords = dk_coordinates(location.get("latitude"), location.get("longitude"))
        if not coords:
            continue
        row = {"brand": "OK", "name": location.get("name") or "OK ladested", "address": location["address"],
               "lat": coords[0], "lon": coords[1], "kwh": None, "app_only": True, "lu": None,
               "source": "geo-emobility.okcloud.dk", "location_id": str(location["locationId"]),
               "source_url": OK_LOCATIONS_API,
               "access_note": "Kontrollér adgang og driftsstatus i OK-appen"}
        # This feed identifies speed categories, not the electrical current type.
        kind = {"Normal": "Normal", "Fast": "Hurtig", "Super": "Lyn"}.get(location.get("chargingSpeed"))
        if kind:
            row["kind"] = kind
        power = to_float(location.get("power"))
        if power is not None and power > 0:
            row["power_kw"] = power
        rows.append(row)
    return rows


def load_oil_charging():
    page = get_text(OIL_STATIONS_PAGE)
    endpoint = re.search(r'data-markers="([^"]+)"', page)
    services = re.search(r'data-services-charging-dk="([^"]+)"', page, re.I)
    if not endpoint or not services:
        raise ValueError("OIL: charging feed settings not found")
    url = urllib.parse.urljoin(OIL_STATIONS_PAGE, html.unescape(endpoint.group(1)))
    if urllib.parse.urlparse(url).netloc != "www.oil-tankstationer.dk":
        raise ValueError("OIL: unexpected station source")
    return {"stations": json.loads(get_text(url)),
            "charging_ids": [int(v) for v in services.group(1).split(",") if v.strip()], "url": url}


def normalize_oil_charging(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("stations"), list) or not payload.get("charging_ids"):
        raise ValueError("OIL: unexpected charging station response")
    rows = []
    ids = set(payload["charging_ids"])
    for station in payload["stations"]:
        if not isinstance(station, dict) or station.get("country") != "DK" or not station.get("street"):
            continue
        coords = dk_coordinates(station.get("latitude"), station.get("longitude"))
        if not coords or not station.get("uid"):
            continue
        chargers = [a for a in station.get("articles", []) if isinstance(a, dict) and a.get("active") is True
                    and isinstance(a.get("article"), dict) and a["article"].get("id") in ids]
        if not chargers:
            continue
        row = {"brand": "OIL", "name": "OIL! tank & go " + str(station.get("suffix") or station.get("city") or ""),
                     "address": " ".join(str(station[k]) for k in ("street", "houseNo", "zip", "city") if station.get(k)),
                     "lat": coords[0], "lon": coords[1], "kwh": None, "app_only": True,
                     "lu": None, "source": "oil-charging", "location_id": str(station["uid"]),
                     "source_url": payload.get("url") or OIL_STATIONS_PAGE,
                     "access_note": "Pris, ladeoperatør og driftsstatus skal kontrolleres ved ladestedet"}
        if all("lyn" in str(a["article"].get("name", "")).lower() for a in chargers):
            row["kind"] = "Lyn"
        rows.append(row)
    return rows


def geo_distance_km(lat1, lon1, lat2, lon2):
    lat1, lat2 = math.radians(lat1), math.radians(lat2)
    delta_lat, delta_lon = lat2 - lat1, math.radians(lon2 - lon1)
    value = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    return 6371 * 2 * math.asin(min(1, math.sqrt(value)))


def load_shell_charging():
    # The public Shell map caps nearest searches at 50. Subdivide Denmark only
    # when the last returned site's distance cannot cover the whole query box.
    # This avoids treating a truncated nearest list as the complete network.
    pending, records = [(54, 7, 58, 16, 0)], {}
    requests = 0
    while pending:
        south, west, north, east, depth = pending.pop()
        latitude, longitude = (south + north) / 2, (west + east) / 2
        requests += 1
        if requests > 41 or depth > 4:
            raise ValueError("Shell: unable to verify complete charging coverage")
        params = {"lat": "%.6f" % latitude, "lng": "%.6f" % longitude, "limit": 50,
                  "with_all[fuels][]": "shell_recharge", "with_any[country_code][]": "DK",
                  "locale": "da_DK", "format": "json"}
        data = json.loads(get_text(SHELL_CHARGING_API + "?" + urllib.parse.urlencode(params), timeout=30))
        if not isinstance(data, dict) or not isinstance(data.get("locations"), list) or data.get("clusters"):
            raise ValueError("Shell: unexpected or clustered charging response")
        rows = data["locations"]
        distances = []
        for row in rows:
            if (not isinstance(row, dict) or row.get("country_code") != "DK"
                    or "shell_recharge" not in row.get("fuels", []) or not row.get("id")):
                raise ValueError("Shell: charging filters were not honoured")
            coords = dk_coordinates(row.get("lat"), row.get("lng"))
            if not coords:
                raise ValueError("Shell: invalid charging coordinates")
            records[str(row["id"])] = row
            distances.append(geo_distance_km(latitude, longitude, *coords))
        radius = max(geo_distance_km(latitude, longitude, a, b)
                     for a in (south, north) for b in (west, east))
        if any(a > b + 0.001 for a, b in zip(distances, distances[1:])):
            raise ValueError("Shell: nearest list is not ordered by distance")
        if len(rows) >= 50 and max(distances) < radius + 0.2:
            pending.extend((a, b, c, d, depth + 1) for a, c in ((south, latitude), (latitude, north))
                           for b, d in ((west, longitude), (longitude, east)))
    return list(records.values())


def normalize_shell_charging(payload):
    if not isinstance(payload, list):
        raise ValueError("Shell: unexpected charging payload")
    rows = []
    for location in payload:
        if (not isinstance(location, dict) or location.get("country_code") != "DK"
                or location.get("brand") != "Shell" or location.get("inactive") is not False
                or "shell_recharge" not in location.get("fuels", []) or not location.get("address")
                or not location.get("id")):
            continue
        coords = dk_coordinates(location.get("lat"), location.get("lng"))
        if not coords:
            continue
        rows.append({"brand": "Shell", "name": location.get("name") or "Shell Recharge",
                     "address": " ".join(str(location[k]) for k in ("address", "postcode", "city") if location.get(k)),
                     "lat": coords[0], "lon": coords[1], "kwh": None, "app_only": True, "lu": None,
                     "source": "shell-charging", "location_id": str(location["id"]),
                     "source_url": location.get("website_url") or SHELL_CHARGING_API,
                     "access_note": "Shell Recharge ved Shell-station; kontrollér pris og adgang hos operatøren"})
    return rows


def load_circlek_charging():
    params = {"latitude": 56.26392, "longitude": 9.501785, "distance": 500000,
              "zoomLevel": 20, "cpoNames": "CIRCLEK"}
    data = json.loads(get_text(CK_CHARGING_API + "?" + urllib.parse.urlencode(params)))
    if (not isinstance(data, dict) or not isinstance(data.get("evsePools"), list)
            or data.get("clusters") or len(data["evsePools"]) > 1000):
        raise ValueError("Circle K: incomplete charging pool response")
    pools = {str(row["id"]): row for row in data["evsePools"] if isinstance(row, dict)
             and row.get("cpoName") == "CIRCLEK" and row.get("id") and dk_coordinates(row.get("lat"), row.get("lon"))
             and to_float(row.get("lat")) >= 54.5}
    records, started = [], time.monotonic()

    def detail(pool_id):
        url = CK_CHARGING_API + "/" + urllib.parse.quote(pool_id, safe="") + "?cpoNames=CIRCLEK"
        payload = json.loads(get_text(url, timeout=20))
        if not isinstance(payload, dict) or str(payload.get("id")) != pool_id or not isinstance(payload.get("evses"), list):
            raise ValueError("Circle K: missing or mismatched charging detail")
        return payload

    with ThreadPoolExecutor(max_workers=6) as executor:
        ids = list(pools)
        for index in range(0, len(ids), 6):
            if time.monotonic() - started > 360:
                raise ValueError("Circle K: detail download time limit reached")
            records.extend(executor.map(detail, ids[index:index + 6]))
    return records


def normalize_circlek_charging(payload):
    if not isinstance(payload, list):
        raise ValueError("Circle K: unexpected charging payload")
    rows = []
    for location in payload:
        if not isinstance(location, dict):
            continue
        address = location.get("address") or {}
        geo = location.get("geoCoordinates") or {}
        coords = dk_coordinates(geo.get("latitude"), geo.get("longitude"))
        if address.get("countryCode") != "DK" or not address.get("details") or not coords or not location.get("id"):
            continue
        options = {}
        for evse in location.get("evses", []):
            if not isinstance(evse, dict) or evse.get("cpoName") != "CIRCLEK":
                continue
            power = to_float(evse.get("maxKw"))
            if power is None or power <= 0:
                continue
            for connector in evse.get("connectors", []):
                connector_type = connector.get("type") if isinstance(connector, dict) else None
                kind = {"CCS": "DC", "CHADEMO": "DC", "TYPE_1": "AC", "TYPE_2": "AC"}.get(connector_type)
                if not kind:
                    continue
                option = options.setdefault(kind, {"power": 0, "types": set(), "ids": set()})
                option["power"] = max(option["power"], power)
                option["types"].add(connector_type)
                if evse.get("id"):
                    option["ids"].add(str(evse["id"]))
        for kind, option in options.items():
            rows.append({"brand": "Circle K", "name": location.get("displayName") or "Circle K ladested",
                         "address": " ".join(str(address[k]) for k in ("details", "postalCode", "city") if address.get(k)),
                         "lat": coords[0], "lon": coords[1], "kind": kind, "power_kw": option["power"],
                         "connector_types": sorted(option["types"]), "plugs": len(option["ids"]),
                         "kwh": None, "app_only": True, "lu": None, "source": "circlek-charging",
                         "location_id": str(location["id"]), "source_url": CK_CHARGING_API,
                         "access_note": "Kontrollér pris og driftsstatus i Circle K Charge"})
    return rows


def fetch_public_ev_locations(url, parser, source, previous, errors, json_feed=True, payload_loader=None):
    try:
        if payload_loader:
            payload = payload_loader()
        else:
            raw = get_text(url, timeout=45)
            payload = json.loads(raw) if json_feed else raw
        rows = parser(payload)
        if not rows:
            raise ValueError("no usable Danish charging locations")
        fetched = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        for row in rows:
            row["source_updated"] = fetched
        return rows, {"status": "ok", "updated": fetched, "records": len(rows), "prices_available": False}
    except Exception as exc:
        rows = [dict(row, stale=True) for row in previous
                if isinstance(row, dict) and row.get("source") == source]
        errors.append({"source": source, "error": str(exc), "stale_reused": len(rows)})
        return rows, {"status": "stale" if rows else "error", "records": len(rows), "prices_available": False}


# ---------- Circle K + Ingo official API ----------

def fetch_ck_ingo(errors):
    """Return (stations, ok). Coords joined from cached station-search master data."""
    try:
        raw = get(CK_API, {"User-Agent": UA, "X-App-Name": "PRICES"})
        try:
            data = json.loads(raw.decode("utf-8"))
        except UnicodeDecodeError:
            import gzip
            data = json.loads(gzip.decompress(raw).decode("utf-8"))
        sites = data.get("sites") or []
    except Exception as exc:  # noqa: BLE001
        errors.append({"ck_api": str(exc)[:120]})
        return [], False
    coords = load_station_cache(errors)
    stations = []
    for site in sites:
        name = site.get("name") or ""
        brand = "Ingo" if "INGO" in name.upper() else "Circle K"
        addr = site.get("address") or {}
        address = " ".join(x for x in [addr.get("street"), addr.get("postalCode"),
                                       addr.get("city")] if x)
        # tolerant matching: legacy stations use old capitalisation
        # (MILES 95, milesPLUS95, ...). miles+/UPGRADE are premium 95
        # (additives), NOT 100 octane - they go to alt, never p100.
        norm = {}
        for p in site.get("fuelPrices") or []:
            pname = p.get("displayName")
            if pname:
                norm[str(pname).lower().replace(" ", "").replace("+", "plus")] = p
        alt = {}
        if brand == "Circle K":
            p95 = norm.get("miles95", {})
            diesel = norm.get("milesdiesel", norm.get("diesel", {}))
            for k, label in (("milesplus95", "miles+ 95"),
                             ("milesplusdiesel", "miles+ diesel"),
                             ("milesplusdi", "miles+ diesel")):
                if k in norm:
                    pr = to_float(norm[k].get("price"))
                    if pr is not None:
                        alt[label] = pr
        else:
            p95 = norm.get("benzin95", {})
            diesel = norm.get("diesel", {})
            if "upgrade95" in norm:
                pr = to_float(norm["upgrade95"].get("price"))
                if pr is not None:
                    alt["UPGRADE 95"] = pr
        lat, lon = coords.get(str(site.get("id")), (None, None))
        stations.append({
            "brand": brand,
            "name": name, "address": address,
            "lat": lat, "lon": lon,
            "p95": to_float(p95.get("price")),
            "p100": None,
            "diesel": to_float(diesel.get("price")),
            "kwh": None,
            "alt": alt or None,
            "lu": p95.get("lastUpdated"),
            "source": "api.circlek.com",
        })
    return stations, True


def load_station_cache(errors):
    """id -> (lat, lon) from circlek.dk station-search, cached 7 days."""
    cache = load_json(STATION_CACHE, None)
    now = time.time()
    if cache and now - cache.get("updated_epoch", 0) < 7 * 86400:
        return {k: tuple(v) for k, v in cache["coords"].items()}
    try:
        page = get_text(CK_SEARCH)
        pairs = re.findall(
            r'"(1\d{4})":\{.*?/location":\{"lat":"([0-9.]+)","lng":"([0-9.]+)"', page)
        coords = {sid: (round(float(la), 5), round(float(lo), 5))
                  for sid, la, lo in pairs}
        if not coords:
            raise ValueError("no coords parsed")
        save_json(STATION_CACHE, {"updated_epoch": now, "coords": coords})
        return coords
    except Exception as exc:  # noqa: BLE001
        errors.append({"stations_cache": str(exc)[:120]})
        if cache:
            return {k: tuple(v) for k, v in cache["coords"].items()}
        return {}


# ---------- F24 + Q8 ----------

def fetch_f24q8(errors):
    last_exc = "no URLs tried"
    for url in F24_URLS:
        for _ in (1, 2):
            try:
                data = json.loads(get_text(url))
                recs = (data.get("data") or {}).get("stationsPrices") or []
                if recs:
                    return [parse_f24(r) for r in recs], True
                last_exc = "empty stationsPrices"
            except Exception as exc:  # noqa: BLE001
                last_exc = str(exc)[:120]
                time.sleep(2)
    errors.append({"f24q8": last_exc})
    return [], False


def parse_f24(rec):
    products = {p.get("productName"): p for p in rec.get("products") or []}
    p95 = products.get("GoEasy 95 E10", {})
    diesel = products.get("GoEasy Diesel", {})
    hpc = products.get("HPC", {})
    brand = "Q8" if "q8" in (rec.get("stationName") or "").lower() else "F24"
    alt = {}
    for label in ("GoEasy 95 Extra E5", "GoEasy Diesel Extra",
                  "Neste MY (HVO100)", "AdBlue"):
        pr = to_float((products.get(label) or {}).get("price"))
        if pr is not None:
            alt[label] = pr
    return {
        "brand": brand,
        "name": "%s %s" % (brand, rec.get("stationId") or ""),
        "address": rec.get("address") or "",
        "lat": None, "lon": None,
        "p95": to_float(p95.get("price")),
        "p100": None,
        "diesel": to_float(diesel.get("price")),
        "kwh": to_float(hpc.get("price")),
        "alt": alt or None,
        "lu": p95.get("priceChangeDate"),
        "kwh_lu": hpc.get("priceChangeDate"),
        "source": "f24.dk",
    }


# ---------- Go'on ----------

def fetch_q8_el(errors):
    """Chain-level Q8 charging tariffs (lyn 150 kW / 22 kW)."""
    try:
        page = get_text(Q8_EL_URL)
        i = page.find("Vores Ladepriser til elbil")
        if i < 0:
            raise ValueError("no ladepriser block")
        seg = page[i:i + 3000]
        vals = re.findall(r'"text":"\s*([\d,]+)\s*kr/kWh', seg)
        if len(vals) < 2:
            raise ValueError("no kwh prices parsed")
        return [{"brand": "Q8", "kind": "Lyn (150 kW)",
                 "kwh": to_float(vals[0]), "source": "q8.dk"},
                {"brand": "Q8", "kind": "Normal (22 kW)",
                 "kwh": to_float(vals[1]), "source": "q8.dk"}]
    except Exception as exc:  # noqa: BLE001
        errors.append({"q8_el": str(exc)[:120]})
        return []


def fetch_unox(errors):
    """Uno-X stations with live prices from their own price page (DK only)."""
    try:
        page = get_text(UNOX_URL)
        u = page.replace('\\"', '"')
        i = u.rfind('initialStations":[{')
        if i < 0:
            raise ValueError("no station data found")
        start = u.find("[", i)
        depth = 0
        instr = False
        esc = False
        end = None
        for j in range(start, len(u)):
            ch = u[j]
            if instr:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    instr = False
            elif ch == '"':
                instr = True
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    end = j + 1
                    break
        if end is None:
            raise ValueError("station JSON not closed")
        sites = json.loads(u[start:end])
    except Exception as exc:  # noqa: BLE001
        errors.append({"unox": str(exc)[:120]})
        return [], False
    stations = []
    chargers = []
    for site in sites:
        if site.get("country") != "DK":
            continue
        prods = {p.get("productName"): p
                 for p in site.get("fuelProducts") or [] if p.get("productName")}
        p95 = prods.get("Blyfri 95 E10", {})
        p100 = prods.get("Blyfri 100 E5", {})
        diesel = prods.get("Diesel", {})
        if p95.get("currency") != "DKK" and p95.get("price") is not None:
            continue
        address = " ".join(x for x in [site.get("stationAddress"),
                                       site.get("stationZipcode"),
                                       site.get("stationCity")] if x)
        lat = to_float(site.get("latitude"))
        lon = to_float(site.get("longitude"))
        stations.append({
            "brand": "Uno-X",
            "name": "Uno-X %s" % (site.get("stationName") or site.get("stationNumber") or ""),
            "address": address,
            "lat": lat, "lon": lon,
            "p95": to_float(p95.get("price")),
            "p100": to_float(p100.get("price")),
            "diesel": to_float(diesel.get("price")),
            "kwh": None,
            "alt": None,
            "lu": p95.get("lastUpdated"),
            "source": "unoxmobility.dk",
        })
        if (site.get("chargePointCount") or 0) > 0:
            chargers.append({
                "brand": "Uno-X",
                "name": "Uno-X %s" % (site.get("stationName") or ""),
                "address": address,
                "lat": lat, "lon": lon,
                "kwh": None,
                "plugs": site.get("chargePointPlugs"),
                "app_only": True,
                "lu": None,
                "source": "unoxmobility.dk",
            })
    if not stations:
        errors.append({"unox": "no DK stations parsed"})
        return [], False
    return (stations, chargers), True


def fetch_goon(errors):
    try:
        page = get_text(GOON_URL)
    except Exception as exc:  # noqa: BLE001
        errors.append({"goon": str(exc)[:120]})
        return [], False
    table = re.search(r"<table[^>]*station-price-table.*?</table>", page, re.S | re.I)
    if not table:
        errors.append({"goon": "station-price-table not found"})
        return [], False
    stations = []
    for row in re.findall(r"<tr.*?</tr>", table.group(0), re.S | re.I):
        cells = re.findall(r"<t[dh].*?</t[dh]>", row, re.S | re.I)
        if len(cells) != 4:
            continue
        name_addr = html.unescape(re.sub(r"<[^>]+>", "", cells[0])).strip()
        p92 = to_float(html.unescape(re.sub(r"<[^>]+>", "", cells[1])).strip())
        p95 = to_float(html.unescape(re.sub(r"<[^>]+>", "", cells[2])).strip())
        diesel = to_float(html.unescape(re.sub(r"<[^>]+>", "", cells[3])).strip())
        if p95 is None and diesel is None:
            continue
        parts = [p.strip() for p in re.split(r"\n", name_addr) if p.strip()]
        stations.append({
            "brand": "Go'on",
            "name": parts[0] if parts else name_addr,
            "address": parts[1] if len(parts) > 1 else "",
            "lat": None, "lon": None,
            "p95": p95, "p100": None, "diesel": diesel, "kwh": None,
            "alt": {"Blyfri 92": p92} if p92 is not None else None,
            "lu": None, "source": "goon.nu",
        })
    if not stations:
        errors.append({"goon": "no station rows parsed"})
        return [], False
    return stations, True


# ---------- Shell PDF ----------

def fetch_shell(errors):
    try:
        page = get_text(SHELL_PAGE)
        pdfs = re.findall(r'href="([^"]*dk-priser-[\d.]+\.pdf)"', page)
        if not pdfs:
            raise ValueError("no price PDF link found")
        pdf_url = pdfs[0] if pdfs[0].startswith("http") else \
            "https://shellservice.dk" + pdfs[0]
        raw = get(pdf_url, timeout=90)
    except Exception as exc:  # noqa: BLE001
        errors.append({"shell_pdf": str(exc)[:120]})
        return shell_fallback(errors)
    try:
        rows = parse_shell_rows(raw)
        if len(rows) < 100:
            raise ValueError("only %d Shell rows parsed" % len(rows))
        stations = []
        for cols in rows:
            prices = [to_float(c) for c in cols[4:-1] if to_float(c) is not None]
            alt = None
            if len(prices) == 4:
                p95, p100, diesel = prices[0], prices[1], prices[2]
                alt = {"V-Power Diesel": prices[3]}
            elif len(prices) == 3:
                p95, p100, diesel = prices[0], None, prices[1]
                alt = {"V-Power Diesel": prices[2]}
            elif len(prices) == 2:
                p95, p100, diesel = prices[0], None, prices[1]
            else:
                continue
            stations.append({
                "brand": "Shell", "name": cols[0],
                "address": "%s %s %s" % (cols[1], cols[2], cols[3]),
                "lat": None, "lon": None,
                "p95": p95, "p100": p100, "diesel": diesel, "kwh": None,
                "alt": alt,
                "lu": "%s-%s-%sT%s" % (cols[-1][6:10], cols[-1][3:5],
                                       cols[-1][0:2], cols[-1][11:19]),
                "source": "shellservice.dk",
            })
        if not stations:
            raise ValueError("no Shell stations mapped")
        return stations, True
    except Exception as exc:  # noqa: BLE001
        errors.append({"shell_pdf": str(exc)[:120]})
        return shell_fallback(errors)


def pdf_extract_cells(raw):
    """Minimal stdlib PDF text extraction for Shell's price tables.

    Shell's PDFs use WinAnsi-encoded TJ arrays with one BT/ET block per table
    cell positioned via Tm. Returns [(x, y, text)] in PDF points.
    """
    import zlib

    def unesc(s):
        out = bytearray()
        i = 0
        while i < len(s):
            c = s[i:i + 1]
            if c == b"\\":
                nxt = s[i + 1:i + 2]
                mp = {b"n": b"\n", b"r": b"\r", b"t": b"\t",
                      b"\\": b"\\", b"(": b"(", b")": b")"}
                if nxt in mp:
                    out += mp[nxt]
                    i += 2
                elif nxt.isdigit():
                    out += bytes([int(s[i + 1:i + 4], 8) & 255])
                    i += 4
                else:
                    out += nxt
                    i += 2
            else:
                out += c
                i += 1
        return bytes(out)

    per_page = []
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", raw, re.S):
        try:
            dec = zlib.decompress(m.group(1))
        except Exception:
            continue
        if b"MCID" not in dec:
            continue
        cells = []
        for b in re.finditer(rb"BT(.*?)ET", dec, re.S):
            blk = b.group(1)
            tm = re.search(rb"([\d.]+) ([\d.]+) Tm", blk)
            if not tm:
                continue
            txt = b""
            for tj in re.finditer(rb"\[(.*?)\]\s*TJ", blk, re.S):
                for s in re.findall(rb"\((?:[^()\\]|\\.)*?\)", tj.group(1)):
                    txt += unesc(s[1:-1])
            try:
                text = txt.decode("cp1252").strip()
            except Exception:
                continue
            if text:
                cells.append((float(tm.group(2)), float(tm.group(1)), text))
        if cells:
            per_page.append(cells)
    return per_page


def parse_shell_rows(raw):
    """Turn Shell PDF cells into [name, addr, zip, city, prices..., datetime]."""
    stations = []
    for cells in pdf_extract_cells(raw):
        names = sorted([(y, x, t) for y, x, t in cells
                        if t.startswith("Shell ")])
        for y0, x0, t0 in names:
            nxt = [x for y, x, t in names if abs(y - y0) < 2 and x > x0 + 1]
            bound = min(nxt) if nxt else 1e9
            row = sorted([(x, t) for y, x, t in cells
                          if abs(y - y0) < 2 and x0 + 1 < x < bound - 0.5])
            cols = [t0] + [t for _, t in row]
            if (len(cols) >= 7 and
                    re.search(r"\d{2}/\d{2}/\d{4}", cols[-1]) and
                    any(re.fullmatch(r"\d{4}", c) for c in cols)):
                stations.append(cols)
    return stations


def shell_fallback(errors):
    """Chain-level business list prices if the PDF is unreachable."""
    try:
        page = get_text(SHELL_ERHVERV_URL)
        found = {}
        for prod in ["FuelSave 95", "V-Power", "FuelSave Diesel"]:
            m = re.search(re.escape(prod) + r"[^0-9]{0,40}(\d+[.,]\d+)", page)
            if m:
                found[prod] = to_float(m.group(1))
        if not found:
            raise ValueError("no erhverv prices parsed")
        return [{"brand": "Shell-liste", "name": "Shell listepris (erhverv)",
                 "address": "", "lat": None, "lon": None,
                 "p95": found.get("FuelSave 95"), "p100": found.get("V-Power"),
                 "diesel": found.get("FuelSave Diesel"), "kwh": None,
                 "lu": None, "source": "shellservice.dk"}][0:1], True
    except Exception as exc:  # noqa: BLE001
        errors.append({"shell": str(exc)[:120]})
        return [], False


# ---------- OK + OIL (chain level) ----------

def normalize_ok_fuel(payload):
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        raise ValueError("OK: unexpected fuel response")
    rows = []
    for item in items:
        if not isinstance(item, dict) or not item.get("street"):
            continue
        coordinates = item.get("coordinates") or {}
        coords = dk_coordinates(coordinates.get("latitude"), coordinates.get("longitude"))
        if not coords:
            continue
        prices = {p.get("product_name"): to_float(p.get("price"))
                  for p in item.get("prices", []) if isinstance(p, dict)}
        row = {"brand": "OK", "name": "OK " + str(item.get("city") or ""),
               "address": " ".join(str(item[k]) for k in ("street", "house_number", "postal_code", "city") if item.get(k)),
               "lat": coords[0], "lon": coords[1], "p95": prices.get("Blyfri 95"),
               "p100": prices.get("Oktan 100"), "diesel": prices.get("Svovlfri Diesel"),
               "kwh": None, "lu": item.get("last_updated_time"), "source": "mobility-prices.ok.dk",
               "location_id": str(item.get("facility_number"))}
        if any(isinstance(row[k], (int, float)) and row[k] > 0 for k in ("p95", "p100", "diesel")):
            rows.append(row)
    return rows


def fetch_ok_fuel(errors):
    try:
        rows = normalize_ok_fuel(json.loads(get_text(OK_FUEL_API)))
        if not rows:
            raise ValueError("OK: no usable station prices")
        return rows, True
    except Exception as exc:
        errors.append({"ok_fuel_api": str(exc)[:160]})
        return [], False


def normalize_oil_fuel(payloads):
    rows = {}
    for field, fuel in (("p95", "95E10"), ("diesel", "DieselB7")):
        payload = payloads[fuel]
        if not isinstance(payload, list):
            raise ValueError("OIL: unexpected fuel response")
        for item in payload:
            if not isinstance(item, dict) or not item.get("address") or not item.get("station_id"):
                continue
            numbers = re.findall(r"[+-]?\d+(?:\.\d+)?", str(item.get("gps", "")))
            coords = dk_coordinates(*numbers[:2]) if len(numbers) == 2 else None
            price = to_float(item.get(fuel))
            if not coords or price is None or price <= 0:
                continue
            key = str(item["station_id"])
            row = rows.setdefault(key, {"brand": "OIL", "name": item.get("station_name") or "OIL! tank & go",
                                       "address": item["address"], "lat": coords[0], "lon": coords[1],
                                       "p95": None, "p100": None, "diesel": None, "kwh": None,
                                       "lu": item.get("updated"), "source": "oil-fuel-api",
                                       "location_id": key})
            # Reject mismatched identity instead of attaching a price to another place.
            if norm_addr(row["address"]) != norm_addr(item["address"]):
                raise ValueError("OIL: conflicting addresses for station " + key)
            row[field] = price
    return list(rows.values())


def fetch_oil_fuel(errors):
    try:
        payloads = {}
        for fuel in ("95E10", "DieselB7"):
            values = []
            for offset in range(0, 10000, 1000):
                url = OIL_FUEL_API + "?" + urllib.parse.urlencode({"fuelType": fuel, "limit": 1000, "offset": offset})
                page = json.loads(get_text(url))
                if not isinstance(page, list):
                    raise ValueError("OIL: unexpected fuel page")
                values.extend(page)
                if len(page) < 1000:
                    break
            else:
                raise ValueError("OIL: pagination limit reached")
            payloads[fuel] = values
        rows = normalize_oil_fuel(payloads)
        if not rows:
            raise ValueError("OIL: no usable station prices")
        return rows, True
    except Exception as exc:
        errors.append({"oil_fuel_api": str(exc)[:160]})
        return [], False

def fetch_ok(errors):
    out = []
    try:
        page = get_text(OK_URL)
        liste = re.search(r"listepriser er herefter:.*?<div[^>]*pv__liste[^>]*>(.*?)</div>\s*</div>",
                          page, re.S)
        body = liste.group(1) if liste else ""
        vals = {}
        for prod in ["Diesel", "Blyfri 92", "Blyfri 95"]:
            m = re.search(re.escape(prod) + r":\s*([\d.,]+)", body)
            if m:
                vals[prod] = to_float(m.group(1))
        if "Blyfri 95" not in vals:
            raise ValueError("no listepriser parsed")
        dm = re.search(r"Fra (\w+ den \d+\. \w+ \d{4})", page)
        out.append({"brand": "OK", "name": "OK listepris",
                    "address": "", "lat": None, "lon": None,
                    "p95": vals.get("Blyfri 95"), "p100": None,
                    "diesel": vals.get("Diesel"),
                    "kwh": None, "lu": dm.group(1) if dm else None,
                    "liste": True, "source": "ok.dk"})
        ok = True
    except Exception as exc:  # noqa: BLE001
        errors.append({"ok": str(exc)[:120]})
        ok = False
    ev = []
    try:
        el_raw = get_text(OK_EL_URL)
        el = re.sub(r"<[^>]+>", " ", el_raw)
        el = html.unescape(re.sub(r"\s+", " ", el))
        for label, kind in [("Normallader", "Normal"), ("Hurtiglader", "Hurtig"),
                            ("Lynlader", "Lyn")]:
            m = re.search(re.escape(label) + r"\s*\([^)]*\)\s*([\d,]+)\s*kr", el)
            if m:
                ev.append({"brand": "OK", "kind": kind,
                           "kwh": to_float(m.group(1)), "source": "ok.dk"})
    except Exception as exc:  # noqa: BLE001
        errors.append({"ok_el": str(exc)[:120]})
    return out, ev, ok


def fetch_oil(errors):
    try:
        page = get_text(OIL_URL)
        table = re.search(r"<table.*?</table>", page, re.S | re.I)
        vals = {}
        for row in re.findall(r"<tr.*?</tr>", table.group(0), re.S | re.I):
            cells = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip()
                     for c in re.findall(r"<t[dh].*?</t[dh]>", row, re.S | re.I)]
            if len(cells) >= 2:
                vals[cells[0]] = to_float(cells[1])
        if "95 E10" not in vals:
            raise ValueError("no priser parsed: %s" % sorted(vals)[:6])
        return [{"brand": "OIL", "name": "OIL listepris (erhverv)",
                 "address": "", "lat": None, "lon": None,
                 "p95": vals.get("95 E10"), "p100": None,
                 "diesel": vals.get("Diesel"),
                 "kwh": None, "lu": None,
                 "liste": True, "source": "oil-tankstationer.dk"}], True
    except Exception as exc:  # noqa: BLE001
        errors.append({"oil": str(exc)[:120]})
        return [], False


# ---------- Nominatim geocoding (cached, bounded) ----------

def geocode_new(addresses, errors, brands=None):
    cache = load_json(ADDRESS_CACHE, {})
    now = int(time.time())
    fresh = dict(cache)
    # Filter cached and duplicate addresses before sharing the budget fairly.
    queues = {}
    seen = set()
    for i, addr in enumerate(addresses):
        key = norm_addr(addr)
        if not key or key in seen:
            continue
        seen.add(key)
        hit = cache.get(key)
        if hit and (hit.get("lat") or now - hit.get("ts", 0) < 7 * 86400):
            continue
        brand = brands[i] if brands is not None else "all"
        queues.setdefault(brand, deque()).append(addr)
    pending = []
    active = deque(queues.values())
    while active and len(pending) < NOM_MAX_NEW:
        queue = active.popleft()
        pending.append(queue.popleft())
        if queue:
            active.append(queue)
    made = 0
    for addr in pending:
        if made >= NOM_MAX_NEW:
            break
        key = norm_addr(addr)
        hit = cache.get(key)
        if hit and (hit.get("lat") or now - hit.get("ts", 0) < 7 * 86400):
            continue
        q = re.sub(r"\s*danmark\s*$", "", addr.strip(), flags=re.I) + ", Danmark"
        params = urllib.parse.urlencode(
            {"q": q, "format": "json", "limit": 1, "countrycodes": "dk"})
        try:
            req = urllib.request.Request(
                "https://nominatim.openstreetmap.org/search?" + params,
                headers={"User-Agent": GEO_UA})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data:
                fresh[key] = {"lat": round(float(data[0]["lat"]), 5),
                              "lon": round(float(data[0]["lon"]), 5),
                              "ts": now}
            else:
                fresh[key] = {"none": True, "ts": now}
            made += 1
        except Exception as exc:  # noqa: BLE001
            errors.append({"geocode": str(exc)[:100]})
            break
        time.sleep(NOM_SLEEP)
    if made:
        save_json(ADDRESS_CACHE, fresh)
    return fresh


# ---------- main ----------

def _collect():
    errors = []
    prev = load_json(OUT, {})
    prev_prices = {}
    prev_hist = {}
    for s in prev.get("stations", []):
        key = s["brand"] + "|" + norm_addr(s.get("address"))
        if s.get("p95") is not None:
            prev_prices[key] = s["p95"]
        if isinstance(s.get("h95"), list):
            prev_hist[key + "|95"] = s["h95"][-30:]
        if isinstance(s.get("h100"), list):
            prev_hist[key + "|100"] = s["h100"][-30:]
    today = time.strftime("%Y-%m-%d", time.gmtime())

    ck_ingo, ck_ok = fetch_ck_ingo(errors)
    f24q8, fq_ok = fetch_f24q8(errors)
    goon, go_ok = fetch_goon(errors)
    (unox, unox_chargers), ux_ok = fetch_unox(errors)
    shell, sh_ok = fetch_shell(errors)
    ok_list, ok_ev, ok_list_ok = fetch_ok(errors)
    ok_rows, ok_ok = fetch_ok_fuel(errors)
    if not ok_rows:
        ok_rows = ok_list
    q8_ev = fetch_q8_el(errors)
    oil_rows, oil_ok = fetch_oil_fuel(errors)
    oil_list_ok = True
    if not oil_rows:
        oil_rows, oil_list_ok = fetch_oil(errors)
    clever_ev, clever_status = fetch_public_ev_locations(
        CLEVER_LOCATIONS_URL, normalize_clever_locations, "clever.dk", prev.get("ev", []), errors)
    eon_ev, eon_status = fetch_public_ev_locations(
        EON_LOCATIONS_URL, normalize_eon_locations, "edri.com", prev.get("ev", []), errors)
    tesla_ev, tesla_status = fetch_public_ev_locations(
        TESLA_LOCATIONS_URL, normalize_tesla_locations, "tesla.com", prev.get("ev", []), errors, json_feed=False)
    ionity_ev, ionity_status = fetch_public_ev_locations(
        IONITY_LOCATIONS_URL, normalize_ionity_locations, "ionity.eu", prev.get("ev", []), errors)
    ok_locations, ok_status = fetch_public_ev_locations(
        OK_LOCATIONS_API, normalize_ok_locations, "geo-emobility.okcloud.dk", prev.get("ev", []), errors,
        payload_loader=load_ok_locations)
    oil_locations, oil_status = fetch_public_ev_locations(
        OIL_STATIONS_PAGE, normalize_oil_charging, "oil-charging", prev.get("ev", []), errors,
        payload_loader=load_oil_charging)
    shell_locations, shell_status = fetch_public_ev_locations(
        SHELL_CHARGING_API, normalize_shell_charging, "shell-charging", prev.get("ev", []), errors,
        payload_loader=load_shell_charging)
    circlek_locations, circlek_status = fetch_public_ev_locations(
        CK_CHARGING_API, normalize_circlek_charging, "circlek-charging", prev.get("ev", []), errors,
        payload_loader=load_circlek_charging)

    # resilience: keep previous stations for sources that failed this run
    prev_by_src = {}
    for s in prev.get("stations", []):
        prev_by_src.setdefault(s.get("source"), []).append(s)
    src_ok = {"api.circlek.com": ck_ok, "f24.dk": fq_ok,
              "goon.nu": go_ok, "unoxmobility.dk": ux_ok,
              "shellservice.dk": sh_ok,
              "ok.dk": ok_list_ok, "oil-tankstationer.dk": oil_list_ok,
              "mobility-prices.ok.dk": ok_ok, "oil-fuel-api": oil_ok}
    fresh = ck_ingo + f24q8 + goon + unox + shell + ok_rows + oil_rows
    have_src = {s.get("source") for s in fresh}
    for src, ok in src_ok.items():
        if not ok and src in prev_by_src:
            for s in prev_by_src[src]:
                s = dict(s)
                s["stale"] = True
                fresh.append(s)
            errors.append({"stale_reused": src})

    missing_coords = [s for s in fresh if s.get("address") and s.get("lat") is None]
    cache = geocode_new([s["address"] for s in missing_coords], errors,
                        brands=[s["brand"] for s in missing_coords])
    stations = []
    for s in fresh:
        if s.get("lat") is None and s.get("address"):
            hit = cache.get(norm_addr(s["address"]), {})
            if hit.get("lat"):
                s["lat"], s["lon"] = hit["lat"], hit["lon"]
        key = s["brand"] + "|" + norm_addr(s.get("address"))
        if key in prev_prices and s.get("p95") is not None:
            s["prev95"] = prev_prices[key]
        for suffix, price in (("95", s.get("p95")), ("100", s.get("p100"))):
            if price is None:
                continue
            hist = [list(p) for p in prev_hist.get(key + "|" + suffix, [])]
            if hist and hist[-1][0] == today:
                hist[-1][1] = round(price, 2)
            elif not hist or abs(hist[-1][1] - price) > 0.0005:
                hist.append([today, round(price, 2)])
            s["h" + suffix] = hist[-30:]
        stations.append(s)

    ev = []
    for s in fresh:
        if s.get("kwh") is not None:
            ev.append({"brand": s["brand"], "name": s["name"],
                       "address": s["address"], "lat": s.get("lat"),
                       "lon": s.get("lon"), "kwh": s["kwh"],
                       "lu": s.get("kwh_lu") or s.get("lu")})
    for e in ok_ev:
        ev.append({"brand": "OK", "name": e["kind"] + "lader",
                   "address": "", "lat": None, "lon": None,
                   "kwh": e["kwh"], "lu": None})
    for e in q8_ev:
        ev.append({"brand": "Q8", "name": "Q8 " + e["kind"],
                   "address": "", "lat": None, "lon": None,
                   "kwh": e["kwh"], "lu": None})
    for c in unox_chargers:
        ev.append({"brand": c["brand"], "name": c["name"],
                   "address": c["address"], "lat": c["lat"], "lon": c["lon"],
                   "kwh": None, "plugs": c.get("plugs"),
                   "app_only": True, "lu": None})
    ev.extend(clever_ev)
    ev.extend(eon_ev)
    ev.extend(tesla_ev)
    ev.extend(ionity_ev)
    ev.extend(ok_locations)
    ev.extend(oil_locations)
    ev.extend(shell_locations)
    ev.extend(circlek_locations)

    def mean(vals):
        vals = [v for v in vals if v is not None]
        return {"v": round(sum(vals) / len(vals), 2), "n": len(vals)} if vals else None

    pump = [s for s in stations if not s.get("liste")]
    snittet = {
        "p95": mean([s.get("p95") for s in pump]),
        "p100": mean([s.get("p100") for s in pump]),
        "diesel": mean([s.get("diesel") for s in pump]),
        "kwh": mean([s.get("kwh") for s in pump]),
    }

    save_json(OUT, {
        "project": "Tiny Refuel",
        "scraper_version": "v0.1",
        "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "errors": errors,
        "snittet": snittet,
        "stations": stations,
        "ev": ev,
        "ev_sources": {"clever": clever_status, "eon": eon_status,
                       "tesla": tesla_status, "ionity": ionity_status, "ok": ok_status, "oil": oil_status,
                       "shell": shell_status, "circle_k": circlek_status},
    })
    # Partial errors must not fail the sensor: data is still written and the
    # errors array inside priser-og-ladesteder.json shows what missed. Only fail on no data.
    return 0 if stations or ev else 1


def collect(data_dir):
    """Called only in the integration's executor job, never on HA's event loop."""
    global WWW_DIR, OUT, ADDRESS_CACHE, STATION_CACHE
    WWW_DIR = str(data_dir)
    OUT = os.path.join(WWW_DIR, "priser-og-ladesteder.json")
    ADDRESS_CACHE = os.path.join(WWW_DIR, "adresse-cache.json")
    STATION_CACHE = os.path.join(WWW_DIR, "stations-cache.json")
    if _collect() != 0:
        raise ValueError("Ingen brugbare priser eller ladesteder")
    return load_json(OUT, {})
