"""Tiny Refuel: petrol, diesel and EV charging through HACS."""
from datetime import timedelta
from pathlib import Path

from aiohttp import web
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.event import async_track_time_interval

from .const import CARD_URL, CONF_SCAN_HOURS, DEFAULT_SCAN_HOURS, DOMAIN, STATIC_URL
from .manager import RefuelManager

PLATFORMS = [Platform.SENSOR, Platform.BUTTON]


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


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    state = hass.data.setdefault(DOMAIN, {})
    if not state.get("registered"):
        folder = str(Path(__file__).parent / "frontend")
        await hass.http.async_register_static_paths([StaticPathConfig(STATIC_URL, folder, False)])
        hass.http.register_view(RefuelDataView(hass))
        add_extra_js_url(hass, CARD_URL)
        state["registered"] = True
    return True


async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    state = hass.data.setdefault(DOMAIN, {})
    manager = RefuelManager(hass, Path(hass.config.path(".storage", DOMAIN)))
    await manager.async_load()
    state["manager"] = manager
    entry.runtime_data = manager

    async def refresh(call: ServiceCall):
        manager.start_refresh()

    hass.services.async_register(DOMAIN, "refresh", refresh)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def scheduled_refresh(now):
        manager.start_refresh()

    entry.async_on_unload(async_track_time_interval(
        hass, scheduled_refresh, timedelta(hours=entry.data.get(CONF_SCAN_HOURS, DEFAULT_SCAN_HOURS))))
    manager.start_refresh()
    return True


async def async_unload_entry(hass: HomeAssistant, entry) -> bool:
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    hass.services.async_remove(DOMAIN, "refresh")
    await entry.runtime_data.async_close()
    hass.data[DOMAIN].pop("manager", None)
    return True
