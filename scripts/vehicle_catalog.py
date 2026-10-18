#!/usr/bin/env python3
"""Fetch model-name candidates and merge reviewed names without guessing specs."""
import argparse
from copy import deepcopy
from datetime import date
import html
import json
from pathlib import Path
import tempfile
import urllib.request

CATALOG = Path(__file__).resolve().parents[1] / 'custom_components/tiny_refuel/frontend/bilkatalog.json'
TOYOTA_URL = 'https://www.toyota.dk/nye-biler'


def load_catalog(path, details=True):
    """Read a plain catalog or its packaged, relative chunk manifest."""
    path = Path(path)
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    if 'catalog_parts' not in data:
        return data
    parts = data['catalog_parts']
    if not isinstance(parts, list) or not 1 <= len(parts) <= 256:
        raise ValueError('Invalid catalog parts')
    directory = path.parent.resolve()
    chunks = []
    for part in parts:
        if not isinstance(part, str) or __import__('re').fullmatch(r'catalog-parts/[a-f0-9]+\.txt', part) is None:
            raise ValueError('Invalid catalog part path')
        chunk = (directory / part).resolve()
        if not chunk.is_relative_to(directory):
            raise ValueError('Invalid catalog part path')
        chunks.append(chunk.read_text(encoding='utf-8'))
    data = json.loads(''.join(chunks))
    if data.get('catalog_schema') != 2: return data
    defaults = data.pop('model_defaults')
    data.pop('catalog_schema')
    for brand in data.get('brands', []):
        references = brand.pop('detail_files', [])
        for model in brand['modeller']:
            if not model.pop('_no_defaults', False):
                for field, value in defaults.items(): model.setdefault(field, deepcopy(value))
        if details:
            expected_start = 0
            for reference in references:
                file = reference['file']
                if not isinstance(file, str) or __import__('re').fullmatch(r'catalog-details/[a-f0-9]+\.json', file) is None:
                    raise ValueError('Invalid model detail path')
                asset = (directory / file).resolve()
                if not asset.is_relative_to(directory): raise ValueError('Invalid model detail path')
                rows = json.loads(asset.read_text(encoding='utf-8'))
                start = reference['start']
                if start != expected_start or not isinstance(rows, list) or start + len(rows) > len(brand['modeller']):
                    raise ValueError('Invalid model detail range')
                for index, row in enumerate(rows):
                    if not isinstance(row, dict): raise ValueError('Invalid model details')
                    brand['modeller'][start + index].update(row)
                expected_start += len(rows)
            if expected_start != len(brand['modeller']): raise ValueError('Incomplete model details')
    return data


def toyota_candidates(page):
    """Read Toyota Denmark's structured modelMap, not navigation/customer text."""
    text = page if '"modelMap"' in page else html.unescape(page)
    decoder = json.JSONDecoder()
    mapping = None
    start = 0
    while (marker := text.find('"modelMap"', start)) >= 0:
        colon = text.find(':', marker + 10)
        try:
            value, _ = decoder.raw_decode(text[colon + 1:].lstrip())
        except (ValueError, json.JSONDecodeError):
            start = marker + 10
            continue
        rows = list(value.values()) if isinstance(value, dict) else value
        if isinstance(rows, list) and rows and all(isinstance(row, dict) for row in rows):
            mapping = rows
            break
        start = marker + 10
    if mapping is None:
        raise ValueError('Toyota modelMap not found; review the source adapter before updating')
    names = set()
    for row in mapping:
        row = row.get("model") if isinstance(row.get("model"), dict) else row
        for item in [row] + (row.get('subModels') or []):
            name = item.get('name')
            if isinstance(name, str):
                name = name.removeprefix('Toyota ').strip()
                if name and len(name) <= 80:
                    names.add(name)
    if not names:
        raise ValueError('No model names found; existing catalog left untouched')
    return {'reviewed': False, 'fetched_on': date.today().isoformat(),
            'note': 'Review names, Danish availability and duplicates before setting reviewed=true. No fuel or capacity data is imported.',
            'brands': [{'mærke': 'Toyota', 'source_url': TOYOTA_URL, 'models': sorted(names, key=str.casefold)}]}


def merge_reviewed(catalog, candidates):
    """Add names only, never remove models, capacities, logos or custom metadata."""
    if candidates.get('reviewed') is not True:
        raise ValueError('Candidate names must be reviewed before merging')
    result = deepcopy(catalog)
    brands = {row['mærke']: row for row in result['brands']}
    additions = []
    for group in candidates['brands']:
        brand, source = group['mærke'], group['source_url']
        if brand not in brands:
            raise ValueError(f'Unknown make {brand}: add and review the make separately')
        if not isinstance(source, str) or not source.startswith('https://'):
            raise ValueError('Each reviewed group needs an HTTPS source URL')
        models = brands[brand]['modeller']
        seen = {row['model'].strip().casefold() for row in models}
        for value in group['models']:
            if not isinstance(value, str) or not value.strip() or len(value) > 80:
                raise ValueError('Invalid model name')
            name = value.strip()
            if name.casefold() in seen:
                continue
            models.append({'model': name, 'brændstof': None, 'tank_l': None,
                           'requires_fuel_selection': True, 'source_url': source,
                           'specification_note': 'Vælg drivmiddel og kontrollér tank/batteri for din årgang og variant.'})
            seen.add(name.casefold())
            additions.append(f'{brand} {name}')
        models.sort(key=lambda row: row['model'].casefold())
    return result, additions


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        try:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    scrape = commands.add_parser('scrape', help='Fetch candidates; never updates the shipped catalog')
    scrape.add_argument('--source', choices=['toyota-dk'], required=True)
    scrape.add_argument('--html', type=Path, help='Use a saved page for offline checking')
    scrape.add_argument('--output', type=Path, required=True)
    merge = commands.add_parser('merge', help='Merge reviewed model names; dry run unless --write')
    merge.add_argument('--input', type=Path, required=True)
    merge.add_argument('--catalog', type=Path, default=CATALOG)
    merge.add_argument('--write', action='store_true')
    args = parser.parse_args()
    if args.command == 'scrape':
        if args.output.resolve() == CATALOG.resolve():
            parser.error('Candidate output must not overwrite the shipped catalog')
        if args.html:
            page = args.html.read_text(encoding='utf-8')
        else:
            request = urllib.request.Request(TOYOTA_URL, headers={'User-Agent': 'TinyRefuel-Catalog/1.0 (+https://github.com/Salvationdk/tiny-refuel)'})
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read(8_000_001)
            if len(raw) > 8_000_000:
                raise ValueError('Source page exceeds size limit')
            page = raw.decode('utf-8')
        data = toyota_candidates(page)
        save_json(args.output, data)
        print(f"Saved {len(data['brands'][0]['models'])} unreviewed candidates to {args.output}")
    else:
        catalog = load_catalog(args.catalog)
        candidates = json.loads(args.input.read_text(encoding='utf-8'))
        updated, additions = merge_reviewed(catalog, candidates)
        if args.write:
            save_json(args.catalog, updated)
        print(f"{'Added' if args.write else 'Would add'} {len(additions)} models")
        for model in additions:
            print(model)


if __name__ == '__main__':
    main()
