"""Compare existing catalog values with cached external evidence; never edit the catalog.
Python 3.10+, standard library only. No Wikipedia requests.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
from urllib.error import HTTPError
from urllib.parse import urlsplit
import zipfile

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.scrape_vehicle_specs import Fetcher, extract, identity, positive, load_catalog
from scripts.vehicle_spec_open_data import load_export, match_export, load_engine_export, match_engines

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ('tank_l', 'batteri_kwh', 'brændstof')


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


class PoliteFetcher(Fetcher):
    """Stop requesting a host after throttling, including robots.txt failures."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.blocked = {}

    def request(self, url):
        host = urlsplit(url).netloc
        if host in self.blocked:
            raise ValueError('Host paused for this run: ' + self.blocked[host])
        try:
            return super().request(url)
        except HTTPError as exc:
            if exc.code in (403, 429, 503):
                self.blocked[host] = f'HTTP {exc.code}; Retry-After={exc.headers.get("Retry-After", "unspecified")}'
            raise


def targets(catalog):
    # Check filled fields too. Do not remove values from the original file.
    return [{'make': b['mærke'], 'model': m['model'], 'missing': list(FIELDS)}
            for b in catalog['brands'] for m in b.get('modeller', [])]


def compare(catalog, candidates):
    index = defaultdict(list)
    for row in candidates:
        if isinstance(row, dict):
            index[(identity(row.get('make', '')), identity(row.get('model', '')))].append(row)
    results, suspicious = [], []
    standards = Counter((identity(b['mærke']), f, m.get(f))
        for b in catalog['brands'] for m in b.get('modeller', [])
        for f in FIELDS[:2] if positive(m.get(f)))
    for brand in catalog['brands']:
        for model in brand.get('modeller', []):
            pair = identity(brand['mærke']), identity(model['model'])
            base = {'make': brand['mærke'], 'model': model['model']}
            flags = []
            kinds = model.get('vehicle_types') or []
            if isinstance(kinds, str): kinds = [kinds]
            if set(kinds) & {'motorcykel', 'knallert'} and positive(model.get('tank_l')) and model['tank_l'] > 40:
                flags.append('two_wheeler_tank_above_40_l_needs_review')
            fuel = identity(model.get('brændstof', ''))
            if fuel in ('el', 'electric') and positive(model.get('tank_l')):
                flags.append('electric_with_fuel_tank_needs_review')
            for field in FIELDS[:2]:
                value = model.get(field)
                if value is not None and not positive(value): flags.append(field + '_invalid_capacity')
                if positive(value) and standards[(pair[0], field, value)] >= 20:
                    flags.append(field + '_repeated_for_at_least_20_models_of_make')
            if flags: suspicious.append(dict(base, flags=flags))
            for field in FIELDS:
                current = model.get(field)
                evidence = []
                for candidate in index[pair]:
                    value = candidate.get('specifications', {}).get(field)
                    if value is None or (field != 'brændstof' and not positive(value)): continue
                    comparable = True
                    if field == 'batteri_kwh':
                        basis = model.get('battery_basis')
                        comparable = basis in ('usable', 'gross') and basis == candidate.get('battery_basis')
                    # Keep every scope visible. A different variant is not a proven contradiction.
                    same = (identity(current) == identity(value)) if field == 'brændstof' else (
                        positive(current) and comparable and abs(current - value) <= 0.05)
                    source_url = candidate.get('source_url')
                    if not source_url and not candidate.get('sources') and not candidate.get('dataset'):
                        continue
                    evidence.append({'value': value, 'value_agrees': bool(same),
                        'comparison_possible': comparable,
                        'source_url': source_url, 'sources': candidate.get('sources', []),
                        'dataset': candidate.get('dataset'), 'source_quality': candidate.get('source_quality'),
                        'evidence': candidate.get('evidence'), 'page_sha256': candidate.get('page_sha256'),
                        'retrieved_at': candidate.get('retrieved_at'),
                        'battery_basis': candidate.get('battery_basis') if field == 'batteri_kwh' else None,
                        'scope': {k: candidate.get(k) for k in ('year', 'year_start', 'year_end', 'generation', 'variant', 'trim', 'markets')},
                        'scope_note': candidate.get('scope_note')})
                if not evidence: status = 'no_evidence'
                elif current is None: status = 'missing_value_with_candidates'
                elif field != 'brændstof' and not positive(current): status = 'invalid_catalog_value'
                elif not any(e['comparison_possible'] for e in evidence): status = 'battery_basis_unresolved'
                elif any(e['comparison_possible'] and not e['value_agrees'] for e in evidence): status = 'possible_conflict_review_scope'
                else: status = 'value_agrees_review_scope'
                results.append(dict(base, field=field, catalog_value=current, status=status,
                    verified=False, evidence=evidence))
    return results, suspicious



def compare_register(catalog, register):
    index = {(identity(b['mærke']), identity(m['model'])): m
             for b in register['brands'] for m in b.get('modeller', [])}
    rows = []
    for brand in catalog['brands']:
        for model in brand.get('modeller', []):
            registered = index.get((identity(brand['mærke']), identity(model['model'])))
            rows.append({'make': brand['mærke'], 'model': model['model'],
                'identity_found_in_extract': registered is not None,
                'registered_fuels': registered.get('fuel_types', []) if registered else [],
                'registered_types': registered.get('vehicle_types', []) if registered else [],
                'registered_model_years': registered.get('model_years', []) if registered else [],
                'capacity_verified_by_dmr': False})
    return rows


def run(args):
    source, output = Path(args.input).resolve(), Path(args.output).resolve()
    if output == source.parent or output in source.parents:
        raise ValueError('Choose a separate output folder')
    output.mkdir(parents=True, exist_ok=True)
    raw = source.read_bytes(); digest = sha256(raw).hexdigest()
    catalog = load_catalog(source)
    wanted = targets(catalog)
    candidates, stages = [], {}
    if not args.skip_online:
        source_file = Path(args.sources) if args.sources else ROOT / 'scripts/data/vehicle-spec-sources.verified.json'
        sources = json.loads(source_file.read_text(encoding='utf-8-sig'))
        pairs = {(identity(r['make']), identity(r['model'])) for r in wanted}
        fetcher = PoliteFetcher(output / 'cache/manufacturer', delay=3, offline=args.offline)
        status = []
        for item in sources:
            if (identity(item['make']), identity(item['model'])) not in pairs: continue
            try:
                page = fetcher.get(item['url'])
                rows, warnings = extract(page, item)
                for row in rows:
                    row.update(retrieved_at=datetime.now(timezone.utc).isoformat(), page_sha256=sha256(page.encode()).hexdigest())
                candidates.extend(rows)
                status.append({'url': item['url'], 'candidate_rows': len(rows), 'warnings': warnings})
            except (OSError, ValueError) as exc:
                status.append({'url': item['url'], 'error': str(exc)})
            save(output / 'manufacturer-status.json', status)
            save(output / 'manufacturer-candidates.json', candidates)
        stages['manufacturer'] = {'sources_checked': len(status), 'errors': sum('error' in r for r in status), 'paused_hosts': fetcher.blocked}
        for name, loader, matcher in [('open-ev', load_export, match_export), ('engine-data', load_engine_export, match_engines)]:
            print('Indlæser ' + name + ' (lokal cache genbruges)...', flush=True)
            try:
                data, meta = loader(output / 'cache' / name, offline=args.offline)
                rows, report = matcher(data, wanted, meta)
                candidates.extend(rows)
                save(output / (name + '-candidates.json'), rows)
                save(output / (name + '-report.json'), report)
                stages[name] = {'status': 'completed', 'candidates': len(rows)}
            except (OSError, ValueError, KeyError) as exc:
                stages[name] = {'status': 'error', 'error': str(exc)}
    for filename in args.candidates:
        rows = json.loads(Path(filename).read_text(encoding='utf-8-sig'))
        if not isinstance(rows, list): raise ValueError('Candidate file must contain a list')
        candidates.extend(rows)
    results, suspicious = compare(catalog, candidates)
    if getattr(args, 'dmr_catalog', None):
        register_path = Path(args.dmr_catalog)
        register = compare_register(catalog, load_catalog(register_path))
        save(output / 'dmr-check.json', register)
        stages['dmr'] = {'input_sha256': sha256(register_path.read_bytes()).hexdigest(),
            'identity_matches': sum(r['identity_found_in_extract'] for r in register),
            'capacity_verification': False}
    save(output / 'all-candidates.json', candidates)
    save(output / 'verification.json', results)
    save(output / 'suspicious.json', suspicious)
    counts = dict(Counter(row['status'] for row in results))
    summary = {'input_sha256': digest, 'models': len(wanted), 'candidate_rows': len(candidates),
        'field_status_counts': counts, 'suspicious_models': len(suspicious), 'stages': stages,
        'automatically_verified': 0, 'input_modified': False,
        'note': 'Agreement is not verification for every variant. Review year, variant, market and battery basis. No Wikipedia requests.'}
    save(output / 'summary.json', summary)
    if sha256(source.read_bytes()).hexdigest() != digest: raise ValueError('Input changed during execution')
    archive = output / 'kontrol-resultat.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zipped:
        for path in sorted(output.glob('*.json')): zipped.write(path, path.name)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print('FÆRDIG: ' + str(archive))
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', default='tiny-refuel-kontrol')
    parser.add_argument('--dmr-catalog', help='Existing typed DMR JSON export, not the raw ZIP')
    parser.add_argument('--sources', help='Additional/custom source-list JSON, replacing bundled manufacturer list')
    parser.add_argument('--candidates', action='append', default=[], help='Existing candidate file; repeat for several files')
    parser.add_argument('--offline', action='store_true', help='Use cached sources only')
    parser.add_argument('--skip-online', action='store_true', help='Only plausibility checks and supplied candidates')
    options = parser.parse_args()
    try: run(options)
    except KeyboardInterrupt: parser.exit(130, '\nAfbrudt. Genstart samme kommando for at genbruge cachen.\n')
    except (OSError, ValueError) as exc: parser.exit(1, str(exc) + '\n')
