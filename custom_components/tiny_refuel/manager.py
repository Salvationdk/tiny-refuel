"""Background collection with one shared job and persistent private data."""
import asyncio
from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Callable

from . import scraper
from .const import CARD_VERSION

_LOGGER = logging.getLogger(__name__)


class RefuelManager:
    def __init__(self, hass, data_dir: Path, collector=None):
        self.hass = hass
        self.data_dir = data_dir
        self.collector = collector or scraper.collect
        self.data = {"project": "Tiny Refuel", "scraper_version": CARD_VERSION,
                     "stations": [], "ev": [], "errors": [], "ev_sources": {}}
        self.refreshing = False
        self.last_error = None
        self.last_attempt = None
        self.task = None
        self.closed = False
        self.listeners: set[Callable] = set()

    async def async_load(self):
        cached = await self.hass.async_add_executor_job(
            scraper.load_json, str(self.data_dir / "priser-og-ladesteder.json"), {})
        if isinstance(cached, dict) and cached.get("project") == "Tiny Refuel":
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

    def start_refresh(self):
        """Schedule once; repeated button/service calls share the running job."""
        if self.closed or self.refreshing:
            return
        self.refreshing = True
        self.last_error = None
        self.last_attempt = datetime.now(timezone.utc).isoformat()
        self._notify()
        self.task = self.hass.async_create_background_task(self._refresh(), "Tiny Refuel scrape")

    async def _refresh(self):
        try:
            data = await self.hass.async_add_executor_job(self.collector, self.data_dir)
            if not isinstance(data, dict) or not data.get("updated") or not (data.get("stations") or data.get("ev")):
                raise ValueError("Ingen brugbare priser eller ladesteder i hentningen")
            self.data = data
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.last_error = str(exc)
            _LOGGER.exception("Tiny Refuel collection failed")
        finally:
            self.refreshing = False
            if not self.closed:
                self._notify()

    def snapshot(self):
        return {**self.data, "refreshing": self.refreshing,
                "last_error": self.last_error, "last_attempt": self.last_attempt}

    async def async_close(self):
        # Do not cancel an executor job and then start another writer during reload.
        self.closed = True
        if self.task is not None and not self.task.done():
            await asyncio.shield(self.task)
        self.listeners.clear()

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
            if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0 and not row.get("app_only"):
                priced.add(key)
        return len(sites), len(priced)
