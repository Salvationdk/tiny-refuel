"""On-demand, validated vehicle catalogs with persistent offline cache."""
import asyncio
import hashlib
import json
import math
import time
from pathlib import Path

CATALOG_FILES = {'personbil': 'car.json', 'varebil': 'van.json', 'lastbil': 'truck.json',
                 'motorcykel': 'motorcycle.json', 'knallert': 'moped.json',
                 'bus': 'bus.json', 'traktor': 'tractor.json', 'andet': 'other.json'}
CATALOG_BASE = 'https://raw.githubusercontent.com/Salvationdk/tiny-refuel/main/catalogs/v1/'
MAX_CATALOG_BYTES = 20 * 1024 * 1024


def validate_catalog(data):
    if not isinstance(data, dict) or not isinstance(data.get('brands'), list):
        raise ValueError('Invalid catalog structure')
    makes = set()
    for brand in data['brands']:
        if not isinstance(brand, dict):raise ValueError('Invalid make')
        name = brand.get('mærke')
        if not isinstance(name, str) or not name.strip() or name.casefold() in makes:
            raise ValueError('Invalid or repeated make')
        makes.add(name.casefold())
        if not isinstance(brand.get('modeller'), list):raise ValueError('Invalid models')
        seen = set()
        for model in brand['modeller']:
            if not isinstance(model, dict):raise ValueError('Invalid model')
            label = model.get('model')
            if not isinstance(label, str) or not label.strip() or label.casefold() in seen:
                raise ValueError('Invalid or repeated model')
            seen.add(label.casefold())
            for field in ('tank_l', 'batteri_kwh'):
                value = model.get(field)
                if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0):
                    raise ValueError('Invalid capacity')
    return data


class CatalogStore:
    def __init__(self, directory, fetch_bytes, bundled_catalog, base_url=CATALOG_BASE):
        self.directory = Path(directory)
        self.fetch_bytes = fetch_bytes
        self.bundled_catalog = Path(bundled_catalog)
        self.base_url = base_url
        self.locks = {}
        self.index_lock = asyncio.Lock()
        self.index = None
        self.index_at = -86401
        self.memory = {}
        self.checked = {}

    async def _read(self, path):
        def read():
            if path.stat().st_size > MAX_CATALOG_BYTES:raise ValueError('Oversized catalog')
            return json.loads(path.read_text(encoding='utf-8'))
        return await asyncio.to_thread(read)

    async def _write(self, path, data):
        def write():
            path.parent.mkdir(parents=True, exist_ok=True)
            temp = path.with_suffix('.tmp')
            temp.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
            temp.replace(path)
        await asyncio.to_thread(write)

    async def _index(self):
        async with self.index_lock:
            if time.monotonic() - self.index_at < 86400:
                if self.index is None:raise ValueError('Catalog index unavailable')
                return self.index
            self.index_at = time.monotonic()
            try:
                raw = await self.fetch_bytes(self.base_url + 'index.json', 256 * 1024)
                data = json.loads(raw)
            except (OSError, ValueError, TimeoutError):
                self.index_at = time.monotonic() - 86400 + 300
                raise
            if not isinstance(data, dict) or data.get('schema_version') != 1 or not isinstance(data.get('catalogs'), dict):raise ValueError('Invalid index')
            self.index = data
            return data

    async def get(self, vehicle_type):
        if vehicle_type == 'varevogn':vehicle_type = 'varebil'
        if vehicle_type not in CATALOG_FILES:raise ValueError('Unknown vehicle type')
        async with self.locks.setdefault(vehicle_type, asyncio.Lock()):
            path = self.directory / CATALOG_FILES[vehicle_type]
            current = self.memory.get(vehicle_type)
            if current is None:
                try:current = validate_catalog(await self._read(path))
                except (OSError, ValueError, TypeError):pass
            if time.monotonic() - self.checked.get(vehicle_type, -86401) < 86400 and current:
                return current
            self.checked[vehicle_type] = time.monotonic()
            try:
                index = await self._index()
                descriptor = index['catalogs'][vehicle_type]
                filename = CATALOG_FILES[vehicle_type]
                if descriptor['file'] != filename:raise ValueError('Invalid catalog path')
                digest = descriptor['sha256']
                if current and current.get('_download', {}).get('sha256') == digest:
                    current['_download']['stale'] = False
                else:
                    raw = await self.fetch_bytes(self.base_url + filename, MAX_CATALOG_BYTES)
                    if len(raw) != descriptor['size_bytes'] or hashlib.sha256(raw).hexdigest() != digest:
                        raise ValueError('Catalog integrity check failed')
                    data = validate_catalog(json.loads(raw))
                    if data.get('vehicle_type') != vehicle_type:raise ValueError('Wrong catalog type')
                    data['_download'] = {'sha256': digest, 'version': index['version'], 'source': 'github', 'stale': False}
                    await self._write(path, data)
                    current = data
            except (OSError, ValueError, TypeError, KeyError, TimeoutError):
                if current:
                    current = {**current, '_download': {**current.get('_download', {}), 'stale': True}}
                else:
                    try:
                        bundled = validate_catalog(await self._read(self.bundled_catalog))
                    except (OSError, ValueError, TypeError):bundled = {'brands': []}
                    brands = []
                    for brand in bundled['brands']:
                        models = [m for m in brand['modeller'] if vehicle_type in [('varebil' if t == 'varevogn' else t) for t in m.get('vehicle_types', [])]]
                        if models:brands.append({**brand, 'modeller': models})
                    current = {'brands': brands, 'vehicle_type': vehicle_type, '_download': {'source': 'bundled', 'stale': True}}
                # Retry temporary failures after five minutes rather than every render.
                self.checked[vehicle_type] = time.monotonic() - 86400 + 300
            self.memory[vehicle_type] = current
            return current
