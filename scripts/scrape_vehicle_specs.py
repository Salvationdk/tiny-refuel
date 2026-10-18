#!/usr/bin/env python3
"""Inventory missing vehicle specifications and collect source-linked JSON-LD candidates.
Python 3.10+, standard library only. Never modifies the input catalog.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re
import time
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

USER_AGENT = 'TinyRefuelSpecs/1.0'
MAX_BYTES = 8 * 1024 * 1024
FUELS = {
    'benzin': 'Benzin', 'petrol': 'Benzin', 'gasoline': 'Benzin',
    'diesel': 'Diesel', 'el': 'El', 'electric': 'El', 'electricity': 'El',
    'hybrid': 'Hybrid', 'pluginhybrid': 'Plug-in hybrid', 'phev': 'Plug-in hybrid',
    'lpg': 'LPG', 'cng': 'CNG', 'hydrogen': 'Brint', 'brint': 'Brint',
}


def key(value):
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', str(value)).encode('ascii', 'ignore').decode().lower())


def identity(value):
    # Preserve punctuation: C4 and C 4 (or up and up!) may be distinct models.
    return ' '.join(unicodedata.normalize('NFKC', str(value)).casefold().split())


def positive(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def fuels(row):
    values = row.get('fuel_types', [])
    if isinstance(values, str):
        values = [values]
    values = list(values or []) + [row.get('brændstof', '')]
    return sorted({FUELS[key(v)] for v in values if key(v) in FUELS})


def missing(row):
    known = fuels(row)
    result = []
    if not known:
        result.append('brændstof')
    # Unknown fuel means that applicability must still be checked by a person.
    if not positive(row.get('tank_l')) and (not known or any(v != 'El' for v in known)):
        result.append('tank_l')
    if not positive(row.get('batteri_kwh')) and (not known or any(v in ('El', 'Hybrid', 'Plug-in hybrid') for v in known)):
        result.append('batteri_kwh')
    return result


def load_catalog(path):
    """Accept plain exports; refuse manifests rather than silently missing details."""
    data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if 'catalog_parts' in data:
        raise ValueError('Use the unfiltered, full JSON export, not the frontend manifest.')
    if not isinstance(data.get('brands'), list):
        raise ValueError('Catalog must contain a brands list.')
    return data


def inventory(data):
    rows = []
    for brand in data['brands']:
        for model in brand.get('modeller', []):
            kinds = model.get('vehicle_types', []) or []
            if not isinstance(kinds, list):
                kinds = [kinds]
            kinds = kinds + [model.get('koeretoejstype', ''), model.get('vehicle_type', '')]
            if any(key(v) in ('motorredskab', '12') for v in kinds):
                continue
            fields = missing(model)
            if fields:
                rows.append({'make': brand['mærke'], 'model': model['model'],
                             'missing': fields, 'known_fuels': fuels(model),
                             'model_years': model.get('model_years', []),
                             'variant_count': len(model.get('variants', [])),
                             'requires_year_variant_review': True})
    return rows


class JsonLdParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.active = False
        self.parts = []
        self.blocks = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'script':
            self.active = dict(attrs).get('type', '').split(';')[0].strip().lower() == 'application/ld+json'
            self.parts = []

    def handle_endtag(self, tag):
        if tag.lower() == 'script' and self.active:
            self.blocks.append(''.join(self.parts))
            self.active = False

    def handle_data(self, data):
        if self.active:
            self.parts.append(data)

    def handle_entityref(self, name):
        if self.active:
            self.parts.append('&' + name + ';')

    def handle_charref(self, name):
        if self.active:
            self.parts.append('&#' + name + ';')


def nodes(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from nodes(child)


def label(value):
    if isinstance(value, dict):
        return value.get('name', value.get('value', ''))
    return value


def quantity(value, kind):
    """Only explicitly identified units; never convert amp hours to kWh."""
    if not isinstance(value, dict):
        return None
    raw = value.get('value')
    try:
        number = float(str(raw).replace(',', '.')) if not isinstance(raw, bool) else 0
    except (ValueError, TypeError):
        return None
    unit = key(value.get('unitCode') or value.get('unitText') or '')
    factors = {'tank_l': {'ltr': 1, 'l': 1, 'litre': 1, 'liter': 1, 'litres': 1, 'liters': 1,
                          'gll': 3.785411784, 'gli': 4.54609},
               'batteri_kwh': {'kwh': 1, 'kwhr': 1, 'wh': 0.001}}
    if not positive(number) or unit not in factors[kind]:
        return None
    return round(number * factors[kind][unit], 6)


def extract(page, source):
    parser = JsonLdParser()
    parser.feed(page)
    found, warnings = [], []
    for block in parser.blocks:
        try:
            document = json.loads(block)
        except json.JSONDecodeError:
            warnings.append('invalid_json_ld')
            continue
        for node in nodes(document):
            types = node.get('@type', [])
            if not isinstance(types, list):
                types = [types]
            types = {str(v).rstrip('/').split('/')[-1] for v in types}
            if not types.intersection({'Vehicle', 'Car', 'Motorcycle', 'MotorizedBicycle', 'Bus'}):
                continue
            if identity(label(node.get('brand', node.get('manufacturer', '')))) != identity(source['make']):
                continue
            # The model property must match: a product title alone is ambiguous.
            if identity(label(node.get('model', ''))) != identity(source['model']):
                continue
            year = str(label(node.get('vehicleModelDate', node.get('modelDate', ''))))[:4]
            if source.get('year') and year != str(source['year']):
                continue
            variant = str(label(node.get('vehicleConfiguration', '')))
            if source.get('variant') and identity(variant) != identity(source['variant']):
                continue
            specs = {}
            fuel = node.get('fuelType', '')
            if not fuel:
                engines = node.get('vehicleEngine', [])
                engines = engines if isinstance(engines, list) else [engines]
                engine_fuels = {str(label(e.get('fuelType', ''))) for e in engines if isinstance(e, dict)} - {''}
                if len(engine_fuels) == 1:
                    fuel = engine_fuels.pop()
            canonical = FUELS.get(key(label(fuel)))
            if canonical:
                specs['brændstof'] = canonical
            capacity = node.get('fuelCapacity')
            for field in ('tank_l', 'batteri_kwh'):
                value = quantity(capacity, field)
                if value is not None:
                    specs[field] = value
            # additionalProperty is accepted only under explicit capacity names.
            properties = node.get('additionalProperty', [])
            properties = properties if isinstance(properties, list) else [properties]
            names = {'fueltankcapacity': 'tank_l', 'tankcapacity': 'tank_l', 'tankstorrelse': 'tank_l',
                     'batterycapacity': 'batteri_kwh', 'batterikapacitet': 'batteri_kwh',
                     'usablebatterycapacity': 'batteri_kwh', 'grossbatterycapacity': 'batteri_kwh'}
            basis = 'unspecified'
            for prop in properties:
                if not isinstance(prop, dict):
                    continue
                field = names.get(key(prop.get('name', '')))
                value = quantity(prop, field) if field else None
                if value is not None:
                    if field in specs and specs[field] != value:
                        warnings.append('conflicting_capacity_in_vehicle_node')
                        specs.pop(field, None)
                        # Entire node is ambiguous; discard it.
                        specs = {}
                        break
                    specs[field] = value
                    if field == 'batteri_kwh':
                        basis = 'usable' if key(prop.get('name', '')).startswith('usable') else 'gross' if key(prop.get('name', '')).startswith('gross') else 'unspecified'
            if specs:
                found.append({'make': source['make'], 'model': source['model'],
                              'year': year if year.isdigit() else None, 'variant': variant or None,
                              'specifications': specs, 'battery_basis': basis,
                              'source_url': source['url'], 'review_required': True})
    # Exact duplicates from repeated structured blocks are harmless.
    return list({json.dumps(v, sort_keys=True): v for v in found}.values()), sorted(set(warnings))


class Fetcher:
    def __init__(self, cache, delay):
        self.cache = Path(cache)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.delay = delay
        self.last = 0
        self.robots = {}

    def request(self, url):
        parsed = urlsplit(url)
        if parsed.scheme not in ('https', 'http') or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError('Source must be a public HTTP(S) URL without credentials.')
        time.sleep(max(0, self.delay - (time.monotonic() - self.last)))
        self.last = time.monotonic()
        request = Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'text/html,application/ld+json'})
        with urlopen(request, timeout=30) as response:
            if urlsplit(response.url).scheme not in ('http', 'https'):
                raise ValueError('Unsupported redirect scheme.')
            body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise ValueError('Response exceeds 8 MiB.')
            return body.decode(response.headers.get_content_charset() or 'utf-8', errors='replace')

    def get(self, url):
        parsed = urlsplit(url)
        if parsed.scheme not in ('https', 'http') or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError('Invalid source URL.')
        origin = parsed.scheme + '://' + parsed.netloc
        if origin not in self.robots:
            parser = RobotFileParser(origin + '/robots.txt')
            try:
                parser.parse(self.request(origin + '/robots.txt').splitlines())
            except HTTPError as exc:
                if exc.code not in (404, 410):
                    raise ValueError('robots.txt unavailable; skipping host.') from exc
                parser.parse([])
            self.robots[origin] = parser
        parser = self.robots[origin]
        if not parser.can_fetch(USER_AGENT, url):
            raise ValueError('robots.txt disallows this page.')
        self.delay = max(self.delay, parser.crawl_delay(USER_AGENT) or 0)
        path = self.cache / (sha256(url.encode()).hexdigest() + '.html')
        if path.exists():
            return path.read_text(encoding='utf-8')
        page = self.request(url)
        path.write_text(page, encoding='utf-8')
        return page


def run(args):
    data = load_catalog(args.catalog)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    rows = inventory(data)
    write = lambda name, value: (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    write('missing.json', rows)
    sources = json.loads(Path(args.sources).read_text(encoding='utf-8-sig')) if args.sources else []
    if not isinstance(sources, list):
        raise ValueError('Sources must be a JSON list.')
    wanted = {(identity(r['make']), identity(r['model'])): r for r in rows}
    candidates, status = [], []
    fetcher = Fetcher(output / 'cache', args.delay)
    for source in sources:
        try:
            if not isinstance(source, dict) or not all(isinstance(source.get(k), str) and source[k].strip() for k in ('make', 'model', 'url')):
                raise ValueError('Each source needs non-empty make, model and url strings.')
            pair = identity(source['make']), identity(source['model'])
            if pair not in wanted:
                status.append({'source': source, 'status': 'not_in_missing_inventory'})
                continue
            page = fetcher.get(source['url'])
            extracted, warnings = extract(page, source)
            for item in extracted:
                item['missing_fields_found'] = sorted(set(item['specifications']).intersection(wanted[pair]['missing']))
                item['retrieved_at'] = datetime.now(timezone.utc).isoformat()
                item['page_sha256'] = sha256(page.encode()).hexdigest()
            candidates.extend(extracted)
            status.append({'source': source, 'status': 'candidates' if extracted else 'no_matching_structured_specs', 'warnings': warnings})
        except (ValueError, OSError, URLError) as exc:
            status.append({'source': source, 'status': 'error', 'error': str(exc)})
        # Checkpoint after each source for resumable large batches; pages are cached.
        write('candidates.json', candidates)
        write('source-status.json', status)
    covered = {(identity(s.get('make', '')), identity(s.get('model', ''))) for s in sources if isinstance(s, dict)}
    write('without-source.json', [r for r in rows if (identity(r['make']), identity(r['model'])) not in covered])
    write('candidates.json', candidates)
    write('source-status.json', status)
    print(f'{len(rows)} models with missing data; {len(sources)} sources; {len(candidates)} candidates. Output: {output}')
    print('Input unchanged. Review year, variant, fuel and battery basis before importing any candidate.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', required=True, help='Unfiltered full JSON catalog')
    parser.add_argument('--sources', help='JSON list of make/model/url and optional year/variant')
    parser.add_argument('--output', default='vehicle-spec-results')
    parser.add_argument('--delay', type=float, default=2, help='Minimum seconds between requests (at least 1)')
    args = parser.parse_args()
    if not math.isfinite(args.delay) or args.delay < 1:
        parser.error('--delay must be at least 1 second')
    try:
        run(args)
    except (ValueError, OSError) as exc:
        parser.exit(1, str(exc) + '\n')


if __name__ == '__main__':
    main()
