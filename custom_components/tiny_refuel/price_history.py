"""Local price observations; no vehicle, position or account data is stored."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

from .entity_data import coordinates, positive

FIELDS = ("p95", "p100", "diesel", "kwh")


def station_id(row, kind):
    """Prefer provider IDs, then addresses; geocoding must not change an address ID."""
    def norm(value):
        return " ".join(str(value or "").casefold().split())
    location = row.get("location_id") or row.get("station_id")
    if location:
        location = ["id", str(location)]
    elif row.get("address"):
        location = ["address", norm(row["address"])]
    elif coordinates(row):
        location = ["coordinates", *coordinates(row)]
    else:
        return None
    identity = [kind, norm(row.get("brand")), location]
    if kind == "ev":
        identity.append(norm(row.get("kind")))
    return hashlib.sha256(json.dumps(identity, ensure_ascii=False).encode()).hexdigest()[:24]


def station_rows(data, failed=False):
    result = []
    for kind, source in (("fuel", "stations"), ("ev", "ev")):
        for row in data.get(source, []):
            if not isinstance(row, dict) or not row.get("brand") or row.get("liste"):
                continue
            uid = station_id(row, kind)
            if uid is None:
                continue  # Generic company tariffs have no physical station identity.
            current = not (failed or row.get("stale") or row.get("liste"))
            prices = {field: row[field] for field in FIELDS if positive(row.get(field))
                      and (field != "kwh" or not row.get("app_only"))}
            position = coordinates(row)
            result.append({"id": uid, "kind": kind, "brand": row["brand"],
                           "name": row.get("name") or row.get("address") or row["brand"],
                           "address": row.get("address"), "lat": position[0] if position else None, "lon": position[1] if position else None,
                           "charger_kind": row.get("kind"), "prices": prices, "current": current,
                           "updated": row.get("source_updated") or data.get("updated"),
                           "price_updated": row.get("lu"), "source": row.get("source")})
    # Duplicated rows may disagree. Never silently choose one as a local truth.
    grouped = {}
    for row in result:
        old = grouped.get(row['id'])
        if old is None:
            grouped[row['id']] = row
        else:
            if old['prices'] != row['prices'] or old['current'] != row['current']:
                old['current'] = False
                old['ambiguous'] = True
    return list(grouped.values())


class PriceHistory:
    def __init__(self, path, days=90):
        self.path = Path(path)
        self.days = max(0, min(365, int(days)))

    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=10)
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('''CREATE TABLE IF NOT EXISTS prices (
            station TEXT NOT NULL, field TEXT NOT NULL, at TEXT NOT NULL,
            value REAL NOT NULL, PRIMARY KEY(station,field,at))''')
        db.execute('CREATE INDEX IF NOT EXISTS prices_time ON prices(at)')
        return db

    def record(self, data, now=None):
        if not self.days:
            return
        now = now or datetime.now(timezone.utc)
        stamp = now.isoformat()
        cutoff = (now - timedelta(days=self.days)).isoformat()
        with closing(self._connect()) as db, db:
            for row in station_rows(data):
                if not row['current']:
                    continue
                for field, value in row['prices'].items():
                    previous = db.execute('SELECT value,at FROM prices WHERE station=? AND field=? ORDER BY at DESC LIMIT 1',
                                          (row['id'],field)).fetchone()
                    if previous is None or previous[0] != value:
                        db.execute('INSERT OR IGNORE INTO prices VALUES (?,?,?,?)', (row['id'],field,stamp,value))
            # Keep one earlier baseline per series so unchanged prices remain queryable.
            db.execute('''DELETE FROM prices WHERE at < ? AND at < (
                SELECT MAX(p.at) FROM prices p WHERE p.station=prices.station
                AND p.field=prices.field AND p.at < ?)''', (cutoff,cutoff))

    def query(self, station, field, days=7, now=None):
        now = now or datetime.now(timezone.utc)
        days = max(1, min(self.days or 1, int(days)))
        start = (now - timedelta(days=days)).isoformat()
        result = {"station_id":station,"field":field,"days":days,"enabled":bool(self.days),
                  "retention_days":self.days,"points":[],"truncated":False}
        if not self.days or not self.path.exists():
            return result
        with closing(self._connect()) as db, db:
            baseline = db.execute('SELECT at,value FROM prices WHERE station=? AND field=? AND at<? ORDER BY at DESC LIMIT 1',
                                  (station,field,start)).fetchone()
            rows = db.execute('SELECT at,value FROM prices WHERE station=? AND field=? AND at>=? ORDER BY at LIMIT 2001',
                              (station,field,start)).fetchall()
        points = [{"at":at,"value":value} for at,value in rows[:2000]]
        if baseline:
            points.insert(0,{"at":start,"value":baseline[1],"baseline":True,"observed_at":baseline[0]})
        result.update(points=points,truncated=len(rows)>2000)
        return result
