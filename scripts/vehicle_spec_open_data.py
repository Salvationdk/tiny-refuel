"""Download a versioned OpenEV Data export and match exact catalog identities.

No LLM calls, API keys or automatic catalog writes. Dataset values are candidates,
not manufacturer-verified facts. Preserve sources, license, markets and variants.
"""
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import unicodedata
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

REPOSITORY = 'open-ev-data/open-ev-data-dataset'
API = 'https://api.github.com/repos/' + REPOSITORY
MAX_BYTES = 32 * 1024 * 1024


def identity(value):
    return ' '.join(unicodedata.normalize('NFKC', str(value)).casefold().split())


def positive(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def download(url, max_bytes=MAX_BYTES):
    request = Request(url, headers={'User-Agent': 'TinyRefuelSpecs/1.1', 'Accept': 'application/json,text/plain'})
    with urlopen(request, timeout=45) as response:
        body = response.read(max_bytes + 1)
    if len(body) > max_bytes:
        raise ValueError('Open dataset response exceeds configured size limit')
    return body


def load_export(directory, offline=False):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / 'open-ev-data.json'
    metadata_path = directory / 'release.json'
    if offline:
        raw = path.read_bytes()
        meta = json.loads(metadata_path.read_text(encoding='utf-8'))
        if sha256(raw).hexdigest() != meta['sha256']:
            raise ValueError('OpenEV cache checksum mismatch')
        return json.loads(raw), meta
    release = json.loads(download(API + '/releases/latest'))
    tag = release['tag_name']
    if not isinstance(tag, str) or not __import__('re').fullmatch(r'v\d+\.\d+\.\d+', tag):
        raise ValueError('Unsupported OpenEV release tag')
    assets = [a for a in release['assets'] if a['name'] == f'open-ev-data-{tag}.json']
    if len(assets) != 1:
        raise ValueError('Expected one versioned OpenEV JSON export')
    asset = assets[0]
    url = asset['browser_download_url']
    if urlsplit(url).netloc != 'github.com' or not url.startswith('https://github.com/' + REPOSITORY + '/releases/download/' + tag + '/'):
        raise ValueError('Unexpected dataset download URL')
    if metadata_path.exists() and path.exists():
        cached = json.loads(metadata_path.read_text(encoding='utf-8'))
        raw = path.read_bytes()
        if cached.get('tag') == tag and cached.get('sha256') == sha256(raw).hexdigest():
            return json.loads(raw), cached
    raw = download(url)
    data = json.loads(raw)
    if not isinstance(data.get('vehicles'), list) or not data['vehicles']:
        raise ValueError('Unsupported or empty OpenEV export; cache unchanged')
    digest = sha256(raw).hexdigest()
    expected = asset.get('digest')
    if expected and expected != 'sha256:' + digest:
        raise ValueError('Dataset checksum mismatch; cache unchanged')
    license_url = f'https://raw.githubusercontent.com/{REPOSITORY}/{tag}/LICENCE'
    license_bytes = download(license_url)
    if b'Community Data License Agreement' not in license_bytes or b'2.0' not in license_bytes:
        raise ValueError('Dataset license changed; cache unchanged')
    meta = {'repository': REPOSITORY, 'tag': tag, 'url': url, 'sha256': digest,
            'license': 'CDLA-Permissive-2.0', 'license_url': license_url,
            'downloaded_at': datetime.now(timezone.utc).isoformat()}
    temp = path.with_suffix('.tmp')
    temp.write_bytes(raw)
    temp.replace(path)
    (directory / 'LICENCE.txt').write_bytes(license_bytes)
    metadata_path.write_text(json.dumps(meta, indent=2) + '\n', encoding='utf-8')
    return data, meta


def match_export(data, missing, metadata, aliases=None):
    if not isinstance(data.get('vehicles'), list):
        raise ValueError('OpenEV export must contain vehicles')
    index = {}
    for row in missing:
        index.setdefault((identity(row['make']), identity(row['model'])), []).append(row)
    reviewed = {}
    for alias in aliases or []:
        if alias.get('reviewed') is not True:
            raise ValueError('Alias mappings must be explicitly reviewed')
        pair = identity(alias['source_make']), identity(alias['source_model'])
        target = identity(alias['make']), identity(alias['model'])
        if pair in reviewed and reviewed[pair] != target:
            raise ValueError('Conflicting source alias')
        reviewed[pair] = target
    candidates, unmatched, ambiguous = [], [], []
    for vehicle in data['vehicles']:
        make = vehicle.get('make', {}).get('name')
        model = vehicle.get('model', {}).get('name')
        if not isinstance(make, str) or not isinstance(model, str):
            continue
        pair = identity(make), identity(model)
        target_pair = reviewed.get(pair, pair)
        targets = index.get(target_pair, [])
        if not targets:
            unmatched.append({'make': make, 'model': model})
            continue
        if len(targets) != 1:
            ambiguous.append({'make': make, 'model': model, 'reason': 'multiple_catalog_identities'})
            continue
        target = targets[0]
        battery = vehicle.get('battery', {})
        net, gross = battery.get('pack_capacity_kwh_net'), battery.get('pack_capacity_kwh_gross')
        if not positive(net) and not positive(gross):
            continue
        if positive(net) and positive(gross) and net > gross:
            ambiguous.append({'make': make, 'model': model, 'reason': 'net_capacity_exceeds_gross'})
            continue
        if 'batteri_kwh' not in target['missing']:
            continue
        sources = [s for s in vehicle.get('sources', []) if isinstance(s, dict) and urlsplit(s.get('url', '')).scheme in ('https', 'http')]
        # Generic homepages remain visible as weak evidence, never a verified spec page.
        specific = [s for s in sources if urlsplit(s['url']).path.strip('/')]
        capacities = {k: v for k, v in {'net_kwh': net, 'gross_kwh': gross}.items() if positive(v)}
        candidates.append({'make': target['make'], 'model': target['model'],
            'source_make': make, 'source_model': model,
            'year': vehicle.get('year'), 'variant': vehicle.get('variant', {}).get('name'),
            'trim': vehicle.get('trim', {}).get('name'), 'markets': vehicle.get('markets', []),
            'battery_capacities': capacities,
            'specifications': {'batteri_kwh': net if positive(net) else gross},
            'battery_basis': 'usable' if positive(net) else 'gross',
            'missing_fields_found': ['batteri_kwh'],
            'dataset': metadata, 'dataset_record': vehicle.get('unique_code'),
            'sources': sources, 'source_quality': 'specific_links_not_independently_checked' if specific else 'generic_or_missing_links',
            'review_required': True, 'manufacturer_verified': False,
            'mapping': 'reviewed_alias' if pair in reviewed else 'exact_name',
            'scope_note': 'Community dataset candidate. Check market, year, trim and primary source before import.'})
    unique = lambda rows: list({json.dumps(r, sort_keys=True): r for r in rows}.values())
    return unique(candidates), {'dataset_rows': len(data['vehicles']),
        'candidate_rows': len(unique(candidates)), 'matched_models': len({(r['make'], r['model']) for r in candidates}),
        'unmatched_source_models': unique(unmatched), 'rejected_ambiguous': unique(ambiguous),
        'note': 'Exact names or explicitly reviewed aliases only. Counts describe candidates, not completed catalog models.'}


def load_engine_export(directory, offline=False):
    """Single version-pinned bulk download, rather than thousands of page requests."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path, meta_path = directory / 'engines.json', directory / 'engines-release.json'
    if offline:
        raw = path.read_bytes()
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
        if sha256(raw).hexdigest() != meta['sha256']:
            raise ValueError('Engine dataset cache checksum mismatch')
        return json.loads(raw), meta
    repository = 'gor3a/vehicle-makes-models'
    commit = json.loads(download('https://api.github.com/repos/' + repository + '/commits/main'))['sha']
    if not __import__('re').fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('Unexpected engine dataset commit')
    if path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
        raw = path.read_bytes()
        if meta.get('commit') == commit and meta.get('sha256') == sha256(raw).hexdigest():
            return json.loads(raw), meta
    base = 'https://raw.githubusercontent.com/' + repository + '/' + commit + '/'
    print('Downloading engine dataset (approximately 85 MB, cached after first run)...', flush=True)
    license_bytes = download(base + 'LICENSE-DATA')
    if b'ODbL' not in license_bytes and b'Open Database License' not in license_bytes:
        raise ValueError('Engine dataset license changed')
    raw = download(base + 'data/json/all.json', 128 * 1024 * 1024)
    data = json.loads(raw)
    if not isinstance(data, list) or not data or not all(isinstance(v, dict) and isinstance(v.get('makes'), list) for v in data):
        raise ValueError('Unsupported engine dataset shape; cache unchanged')
    meta = {'repository': repository, 'commit': commit, 'url': base + 'data/json/all.json',
            'sha256': sha256(raw).hexdigest(), 'license': 'ODbL-1.0',
            'license_url': base + 'LICENSE-DATA', 'downloaded_at': datetime.now(timezone.utc).isoformat()}
    temp = path.with_suffix('.tmp')
    temp.write_bytes(raw)
    temp.replace(path)
    (directory / 'ENGINE-DATA-LICENSE.txt').write_bytes(license_bytes)
    meta_path.write_text(json.dumps(meta, indent=2) + '\n', encoding='utf-8')
    return data, meta


def match_engines(data, missing, metadata):
    import re
    index = {}
    for row in missing:
        index.setdefault((identity(row['make']), identity(row['model'])), []).append(row)
    fuels = {'gasoline': 'Benzin', 'diesel': 'Diesel', 'electric': 'El', 'electricity': 'El',
             'hybrid gasoline': 'Hybrid', 'hybrid diesel': 'Hybrid', 'hybrid': 'Hybrid',
             'plug-in hybrid': 'Plug-in hybrid', 'lpg': 'LPG', 'cng': 'CNG', 'hydrogen': 'Brint'}
    candidates, unmatched, rejects = [], [], []
    engine_count = 0
    for group in data:
        for make in group['makes']:
            for model in make.get('models', []):
                targets = index.get((identity(make['name']), identity(model['name'])), [])
                if not targets:
                    unmatched.append({'make': make['name'], 'model': model['name']})
                for generation in model.get('generations', []):
                    for engine in generation.get('engines', []):
                        engine_count += 1
                        if len(targets) != 1:
                            continue
                        target, specs, evidence = targets[0], {}, {}
                        raw_specs = engine.get('specs', {})
                        tank = raw_specs.get('ENGINE SPECS / Fuel capacity', '')
                        # Only explicit litres. Never guess which gallon unit was used.
                        amounts = {float(v.replace(',', '.')) for v in re.findall(r'(?<![\d.,])(\d+(?:[.,]\d+)?)\s*L\b', tank)}
                        amounts = {v for v in amounts if positive(v)}
                        if 'tank_l' in target['missing'] and len(amounts) == 1:
                            specs['tank_l'] = amounts.pop()
                            evidence['tank_l'] = tank
                        elif len(amounts) > 1:
                            rejects.append({'make': make['name'], 'model': model['name'], 'reason': 'conflicting_litre_values'})
                        fuel = fuels.get(identity(engine.get('fuelType', '')))
                        if 'brændstof' in target['missing'] and fuel:
                            specs['brændstof'] = fuel
                            evidence['brændstof'] = engine.get('fuelType')
                        if not specs:
                            continue
                        candidates.append({'make': target['make'], 'model': target['model'],
                            'generation': generation.get('name'), 'year_start': generation.get('yearStart'),
                            'year_end': generation.get('yearEnd'), 'variant': engine.get('label'),
                            'specifications': specs, 'evidence': evidence,
                            'source_url': 'https://github.com/' + metadata['repository'] + '/blob/' + metadata['commit'] + '/data/json/' + group['group'] + '.json',
                            'dataset': metadata, 'review_required': True, 'manufacturer_verified': False,
                            'mapping': 'exact_name', 'source_quality': 'community_compilation_not_independently_checked',
                            'scope_note': 'Keep engine and generation separate; do not assign this value to the whole model series.'})
    unique = lambda rows: list({json.dumps(v, sort_keys=True): v for v in rows}.values())
    candidates = unique(candidates)
    return candidates, {'dataset_engine_rows': engine_count, 'candidate_rows': len(candidates),
        'matched_models': len({(v['make'], v['model']) for v in candidates}),
        'unmatched_source_models': unique(unmatched), 'rejected': unique(rejects),
        'note': 'Community dataset candidates. ODbL attribution and share-alike terms must be preserved on redistribution.'}
