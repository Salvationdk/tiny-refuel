"""Tiny Refuel: petrol, diesel and EV charging through HACS."""
from datetime import timedelta
from pathlib import Path

from aiohttp import web, ClientError, ClientTimeout
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .price_history import FIELDS
from .catalog_store import CatalogStore, MAX_CATALOG_BYTES
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers import config_validation as cv

from .const import CARD_URL, CONF_SCAN_HOURS, DEFAULT_SCAN_HOURS, DOMAIN, STATIC_URL
from .manager import RefuelManager

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON]


class RefuelDataView(HomeAssistantView):
    url = "/api/tiny_refuel/data"
    name = "api:tiny_refuel:data"
    requires_auth = True

    def __init__(self, hass):
        self.hass = hass

    async def get(self, request):
        manager = self.hass.data.get(DOMAIN, {}).get("manager")
        if manager is None:
            return web.json_response({"message": "Tilføj Tiny Refuel under Enheder og tjenester"}, status=503)
        return web.json_response(manager.snapshot(), headers={"Cache-Control": "no-store"})


class RefuelCatalogView(HomeAssistantView):
    url = "/api/tiny_refuel/catalog/{vehicle_type}"
    name = "api:tiny_refuel:catalog"
    requires_auth = True

    def __init__(self, store):
        self.store = store

    async def get(self, request, vehicle_type):
        try:
            catalog = await self.store.get(vehicle_type)
        except ValueError:
            return web.json_response({"message": "Ukendt køretøjstype"}, status=400)
        return web.json_response(catalog, headers={"Cache-Control": "no-store"})


class RefuelStationsView(HomeAssistantView):
    url = "/api/tiny_refuel/stations"
    name = "api:tiny_refuel:stations"
    requires_auth = True

    def __init__(self, hass):
        self.hass = hass

    async def get(self, request):
        manager = self.hass.data.get(DOMAIN, {}).get("manager")
        if manager is None:
            return web.json_response({"message":"Tiny Refuel er ikke startet"},status=503)
        return web.json_response(manager.station_snapshot(),headers={"Cache-Control":"no-store"})


class RefuelHistoryView(RefuelStationsView):
    url = "/api/tiny_refuel/history/{station_id}"
    name = "api:tiny_refuel:history"

    async def get(self, request, station_id):
        manager = self.hass.data.get(DOMAIN, {}).get("manager")
        if manager is None:
            return web.json_response({"message":"Tiny Refuel er ikke startet"},status=503)
        try:
            if len(station_id)!=24 or any(c not in "0123456789abcdef" for c in station_id):
                raise ValueError("Invalid station")
            field=request.query.get("field","p95")
            days=int(request.query.get("days","7"))
            if field not in FIELDS or not 1<=days<=365:
                raise ValueError("Invalid history selection")
        except (ValueError,TypeError):
            return web.json_response({"message":"Ugyldigt historikvalg"},status=400)
        try:
            data=await self.hass.async_add_executor_job(manager.history.query,station_id,field,days)
        except Exception:
            return web.json_response({"message":"Historikken kunne ikke læses"},status=503)
        return web.json_response(data,headers={"Cache-Control":"no-store"})


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    state = hass.data.setdefault(DOMAIN, {})
    if not state.get("registered"):
        folder = str(Path(__file__).parent / "frontend")
        await hass.http.async_register_static_paths([StaticPathConfig(STATIC_URL, folder, False)])
        hass.http.register_view(RefuelDataView(hass))
        hass.http.register_view(RefuelStationsView(hass))
        hass.http.register_view(RefuelHistoryView(hass))

        async def fetch_catalog_bytes(url, limit):
            try:
                async with async_get_clientsession(hass).get(url, timeout=ClientTimeout(total=20)) as response:
                    response.raise_for_status()
                    chunks = bytearray()
                    async for chunk in response.content.iter_chunked(65536):
                        chunks.extend(chunk)
                        if len(chunks) > limit:
                            raise ValueError("Catalog response too large")
                    return bytes(chunks)
            except ClientError as exc:
                raise OSError("Catalog download failed") from exc

        state["catalogs"] = CatalogStore(
            Path(hass.config.path(".storage", DOMAIN, "catalogs")),
            fetch_catalog_bytes, Path(folder) / "katalog.json")
        hass.http.register_view(RefuelCatalogView(state["catalogs"]))
        add_extra_js_url(hass, CARD_URL)
        add_extra_js_url(hass, STATIC_URL + "/tiny-refuel-stations.js?v=0.2.2.1")
        state["registered"] = True
    return True


async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    state = hass.data.setdefault(DOMAIN, {})
    manager = RefuelManager(hass, Path(hass.config.path(".storage", DOMAIN)),
                            vehicles=getattr(entry, "options", {}).get("vehicles", []),
                            history_days=getattr(entry, "options", {}).get("history_days",90))
    await manager.async_load()
    state["manager"] = manager
    if state.get("catalogs"):
        await state["catalogs"].async_load_status()
    entry.runtime_data = manager

    async def refresh(call: ServiceCall):
        manager.start_refresh(getattr(call, "data", {}).get("fuel_types"))

    hass.services.async_register(DOMAIN, "refresh", refresh)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def scheduled_refresh(now):
        manager.start_refresh()

    entry.async_on_unload(async_track_time_interval(
        hass, scheduled_refresh, timedelta(hours=getattr(entry, "options", {}).get(CONF_SCAN_HOURS, entry.data.get(CONF_SCAN_HOURS, DEFAULT_SCAN_HOURS)))))
    if hasattr(entry, "add_update_listener"):
        entry.async_on_unload(entry.add_update_listener(async_update_options))
    manager.start_refresh()
    return True


async def async_update_options(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry) -> bool:
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    hass.services.async_remove(DOMAIN, "refresh")
    await entry.runtime_data.async_close()
    hass.data[DOMAIN].pop("manager", None)
    return True

