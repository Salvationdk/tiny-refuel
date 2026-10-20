"""Background collection with one shared job and persistent private data."""
import asyncio
from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Callable

from .dashboard_data import general_tariffs
from .price_history import PriceHistory, station_rows
from . import scraper
from .const import CARD_VERSION, VERSION
from .entity_data import nearest_row, price_rows

_LOGGER = logging.getLogger(__name__)


class RefuelManager:
    def __init__(self, hass, data_dir: Path, collector=None, vehicles=None, history_days=90):
        self.hass = hass
        self.vehicles = list(vehicles or [])
        self.history = PriceHistory(data_dir / "price-history.sqlite3", history_days)
        self.history_error = None
        self.data_dir = data_dir
        self.collector = collector or scraper.collect
        # Injected collectors are commonly small test doubles with the historic
        # one argument signature. The built-in scraper receives progress updates.
        self._collector_supports_progress = collector is None
        self.data = {"project": "Tiny Refuel", "scraper_version": CARD_VERSION,
                     "stations": [], "ev": [], "errors": [], "ev_sources": {}}
        self.refreshing = False
        self.last_error = None
        self.last_attempt = None
        self.progress = None
        self.task = None
        self.closed = False
        self.listeners: set[Callable] = set()

    async def async_load(self):
        cached = await self.hass.async_add_executor_job(
            scraper.load_json, str(self.data_dir / "priser-og-ladesteder.json"), {})
        if isinstance(cached, dict) and cached.get("project") == "Tiny Refuel":
            cached["ev"] = [row for row in cached.get("ev", [])
                            if isinstance(row, dict) and row.get("brand") != "Tesla"]
            if isinstance(cached.get("ev_sources"), dict):
                cached["ev_sources"].pop("tesla", None)
            if isinstance(cached.get("benefits"), dict):
                cached["benefits"].pop("tesla", None)
            self.data = cached

    def subscribe(self, listener):
        self.listeners.add(listener)
        return lambda: self.listeners.discard(listener)

    def _notify(self):
        for listener in tuple(self.listeners):
            try:
                listener()
            except Exception:  # One entity must not break the collection job.
                _LOGGER.exception("Tiny Refuel listener failed")

    def start_refresh(self, fuel_types=None):
        """Schedule once; repeated button/service calls share the running job."""
        if self.closed or self.refreshing:
            return
        if fuel_types is not None:
            allowed = {"benzin", "diesel", "el"}
            if not isinstance(fuel_types, (list, tuple, set)):
                fuel_types = None
            else:
                fuel_types = sorted(set(fuel_types) & allowed)
            if not fuel_types:
                fuel_types = None
        self._requested_fuel_types = fuel_types
        self.refreshing = True
        self.progress = {"phase": "starting", "provider": "Tiny Refuel", "station": None}
        self.last_error = None
        self.last_attempt = datetime.now(timezone.utc).isoformat()
        self._notify()
        self.task = self.hass.async_create_background_task(self._refresh(), "Tiny Refuel scrape")

    async def _refresh(self):
        try:
            if self._collector_supports_progress:
                data = await self.hass.async_add_executor_job(
                    self.collector, self.data_dir, self._update_progress,
                    getattr(self, "_requested_fuel_types", None))
            else:
                data = await self.hass.async_add_executor_job(self.collector, self.data_dir)
            if not isinstance(data, dict) or not data.get("updated") or not (data.get("stations") or data.get("ev")):
                raise ValueError("Ingen brugbare priser eller ladesteder i hentningen")
            self.data = data
            try:
                await self.hass.async_add_executor_job(self.history.record, data)
                self.history_error = None
            except Exception:
                self.history_error = "Prishistorikken kunne ikke gemmes"
                _LOGGER.exception("Tiny Refuel history write failed")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.last_error = str(exc)
            _LOGGER.exception("Tiny Refuel collection failed")
        finally:
            self.refreshing = False
            self.progress = None
            if not self.closed:
                if getattr(self, "_station_entities_enabled", False):
                    from .station_entities import refresh_station_index
                    await self.hass.async_add_executor_job(refresh_station_index, self)
                self._notify()

    def station_snapshot(self):
        data = self.data
        failed = bool(self.last_error)
        cached = getattr(self,"_station_cache",None)
        if cached is not None and cached[0] is data and cached[1] == failed:
            rows = cached[2]
        else:
            rows = station_rows(data,failed)
            self._station_cache = (data,failed,rows)
        return {"stations":rows,"updated":data.get("updated"),"refreshing":self.refreshing,
                "last_error":self.last_error,"history_days":self.history.days,
                "history_error":self.history_error,
                "tariffs":general_tariffs(data,failed)}

    def snapshot(self):
        return {**self.data, "vehicles": self.vehicles, "version": VERSION, "refreshing": self.refreshing,
                "last_error": self.last_error, "last_attempt": self.last_attempt,
                "progress": self.progress}

    def _update_progress(self, progress):
        """Called from the executor thread; snapshots read this small immutable value."""
        if isinstance(progress, dict):
            self.progress = dict(progress)

    async def async_close(self):
        # Do not cancel an executor job and then start another writer during reload.
        self.closed = True
        if self.task is not None and not self.task.done():
            await asyncio.shield(self.task)
        self.listeners.clear()

    def current_price_rows(self, field, brand=None):
        return [] if self.last_error else price_rows(self.data, field, brand)

    def nearest(self, field, origin):
        """Share an expensive distance scan across a vehicle's related entities."""
        if self.last_error:
            return None, None
        if getattr(self, "_nearest_data", None) is not self.data:
            self._nearest_data = self.data
            self._nearest_results = {}
        key = (field, origin)
        if key not in self._nearest_results:
            if len(self._nearest_results) >= 64:
                self._nearest_results.clear()
            self._nearest_results[key] = nearest_row(self.data, field, origin)
        return self._nearest_results[key]

    def counts(self):
        sites, priced = set(), set()
        for row in self.data.get("ev", []):
            if not isinstance(row, dict) or not row.get("brand"):
                continue
            if row.get("location_id"):
                location = str(row["location_id"])
            elif row.get("lat") is not None and row.get("lon") is not None:
                location = str(row["lat"]) + "," + str(row["lon"])
            elif row.get("address"):
                location = str(row["address"]).lower().strip()
            else:
                continue
            key = (row["brand"], location)
            sites.add(key)
            value = row.get("kwh")
            if (not row.get("app_only") and isinstance(value, (int, float))
                    and not isinstance(value, bool) and value > 0):
                priced.add(key)
        return len(sites), len(priced)
