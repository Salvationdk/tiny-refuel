"""Attach scoped source evidence to a copy of a vehicle catalog and check linked pages.
Standard library only, Python 3.10+. No Wikipedia or automatic value changes.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit
import zipfile

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.verify_vehicle_catalog import PoliteFetcher, save, ROOT, FIELDS
from scripts.scrape_vehicle_specs import identity, positive, extract, load_catalog


class Title(HTMLParser):
    def __init__(self):
        super().__init__(); self.inside = False; self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag == 'title': self.inside = True
    def handle_endtag(self, tag):
        if tag == 'title': self.inside = False
    def handle_data(self, data):
        if self.inside: self.parts.append(data)


def allowed(url):
    p = urlsplit(url)
    host = (p.hostname or '').casefold()
    return p.scheme in ('http', 'https') and bool(host) and not p.username and not p.password and not (
        host == 'wikipedia.org' or host.endswith('.wikipedia.org') or
        host == 'wikimedia.org' or host.endswith('.wikimedia.org'))


def read_candidates(path):
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as zipped:
            if zipped.getinfo('all-candidates.json').file_size > 256 * 1024 * 1024:
                raise ValueError('Candidate JSON exceeds 256 MiB')
            rows = json.loads(zipped.read('all-candidates.json').decode('utf-8-sig'))
    else:
        rows = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if not isinstance(rows, list): raise ValueError('Expected candidate list')
    return rows


def attach(catalog, candidates):
    result = deepcopy(catalog)
    models = {}
    for b in result['brands']:
        for m in b.get('modeller', []): models.setdefault((identity(b['mærke']), identity(m['model'])), []).append(m)
    previous = result.get('source_review_data', {})
    sources, records = deepcopy(previous.get('sources', {})), deepcopy(previous.get('records', {}))
    # Existing documentation is preserved; the new namespace is reproducible.
    for row in candidates:
        pair = identity(row.get('make', '')), identity(row.get('model', ''))
        if pair not in models: continue
        links = []
        dataset = row.get('dataset') or {}
        if row.get('source_url'): links.append({'url': row['source_url'], 'role': 'candidate_source'})
        if dataset.get('url'): links.append({'url': dataset['url'], 'role': 'dataset_export'})
        for s in row.get('sources', []):
            if isinstance(s, dict) and s.get('url'):
                links.append({'url': s['url'], 'role': 'dataset_reference', 'title': s.get('title'),
                    'reported_type': s.get('type')})
        refs = []
        for link in links:
            url = link['url']
            sid = sha256(url.encode()).hexdigest()[:24]
            sources.setdefault(sid, {**link, 'url': url, 'status': 'not_checked',
                'primary_source_verified': False})
            if sid not in refs: refs.append(sid)
        if not refs: continue
        specs = dict(row.get('specifications') or {})
        caps = row.get('battery_capacities') or {}
        for label, basis in [('net_kwh', 'usable'), ('gross_kwh', 'gross')]:
            if positive(caps.get(label)): specs['battery_' + basis + '_kwh'] = caps[label]
        payload = {'make': row['make'], 'model': row['model'], 'specifications': specs,
            'battery_basis': row.get('battery_basis', 'unspecified'),
            'scope': {k: row.get(k) for k in ('year', 'year_start', 'year_end', 'generation', 'variant', 'trim', 'markets')},
            'scope_note': row.get('scope_note'), 'evidence': row.get('evidence'),
            'source_ids': refs, 'dataset': dataset, 'dataset_record': row.get('dataset_record'),
            'retrieved_at': row.get('retrieved_at'), 'page_sha256': row.get('page_sha256')}
        rid = sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:24]
        records[rid] = payload
        for model in models[pair]:
            docs = model.setdefault('source_review', {})
            for field in FIELDS:
                if field not in specs: continue
                entry = docs.setdefault(field, {'status': 'needs_review', 'verified': False, 'record_ids': []})
                if rid not in entry['record_ids']: entry['record_ids'].append(rid)
    result['source_review_data'] = {'format_version': 1, 'sources': sources, 'records': records,
        'note': 'Source references are not verification. Values are preserved; review variant, year, market and battery basis.'}
    return result


def check_pages(catalog, output, limit=100, offline=False):
    data = catalog['source_review_data']; fetcher = PoliteFetcher(output / 'cache/pages', delay=3, offline=offline)
    rules = json.loads((ROOT / 'scripts/data/vehicle-spec-sources.verified.json').read_text(encoding='utf-8'))
    linked = {}
    for record in data['records'].values():
        for sid in record['source_ids']:
            linked.setdefault(sid, set()).add((record['make'], record['model']))
    previous_path = output / 'page-checks.json'
    previous = json.loads(previous_path.read_text(encoding='utf-8')) if previous_path.exists() else {}
    count = 0
    extracted = []
    for sid, source in data['sources'].items():
        url = source['url']; path = urlsplit(url).path
        cached = previous.get(sid, {})
        if cached.get('url') == url and cached.get('status') in ('structured_specs_found_review_scope', 'page_fetched_no_matching_structured_specs'):
            source.update(cached)
            extracted.extend(source.get('extracted_candidates', []))
            continue
        if source['role'] in ('dataset_export', 'candidate_source') and ('github.com' in (urlsplit(url).hostname or '')):
            source['status'] = 'dataset_provenance'; continue
        if not allowed(url): source['status'] = 'excluded_url'; continue
        if not path.strip('/'):
            source['status'] = 'generic_homepage_requires_specific_source'; continue
        if path.casefold().endswith('.pdf'):
            source['status'] = 'pdf_requires_manual_or_pdf_parser_review'; continue
        if count >= limit: continue
        count += 1
        print(f'[{count}/{limit}] {url}', flush=True)
        try:
            page = fetcher.get(url); title = Title(); title.feed(page)
            source.update(status='page_fetched_no_matching_structured_specs',
                checked_at=datetime.now(timezone.utc).isoformat(),
                page_sha256=sha256(page.encode()).hexdigest(), page_title=' '.join(title.parts).strip())
            found = []
            for make, model in sorted(linked.get(sid, [])):
                matching = [r for r in rules if r['url'] == url and identity(r['make']) == identity(make) and identity(r['model']) == identity(model)]
                for rule in matching or [{'make': make, 'model': model, 'url': url}]:
                    rows, warnings = extract(page, rule)
                    for row in rows:
                        row.update(page_sha256=source['page_sha256'], retrieved_at=source['checked_at'])
                        found.append(row)
            if found:
                source['status'] = 'structured_specs_found_review_scope'
                source['extracted_candidates'] = found
                extracted.extend(found)
        except (OSError, ValueError, AssertionError) as exc:
            source.update(status='fetch_error', error=str(exc), checked_at=datetime.now(timezone.utc).isoformat())
        save(output / 'page-checks.json', data['sources'])
    save(output / 'page-checks.json', data['sources'])
    return extracted


def run(args):
    source = Path(args.input).resolve(); output = Path(args.output).resolve()
    if output == source.parent or output in source.parents: raise ValueError('Choose a separate output folder')
    output.mkdir(parents=True, exist_ok=True)
    raw = source.read_bytes(); digest = sha256(raw).hexdigest()
    candidates = read_candidates(args.results)
    catalog = attach(load_catalog(source), candidates)
    # First persist dataset documentation, even if online work is interrupted.
    save(output / 'katalog-med-kilder.json', catalog)
    found = [] if args.skip_online else check_pages(catalog, output, args.limit, args.offline)
    if found:
        catalog = attach(catalog, found)
    save(output / 'katalog-med-kilder.json', catalog)
    save(output / 'online-candidates.json', found)
    data = catalog['source_review_data']
    summary = {'input_sha256': digest, 'candidate_records': len(data['records']), 'unique_sources': len(data['sources']),
        'models_with_source_records': sum(bool(m.get('source_review')) for b in catalog['brands'] for m in b.get('modeller', [])),
        'new_online_candidates': len(found), 'values_changed': 0, 'automatically_verified': 0,
        'note': 'No free web search. Checks URLs in supplied evidence. Missing sources and PDF/variant review remain explicit.'}
    save(output / 'summary.json', summary)
    if sha256(source.read_bytes()).hexdigest() != digest: raise ValueError('Input changed during run')
    with zipfile.ZipFile(output / 'kilder-resultat.zip', 'w', zipfile.ZIP_DEFLATED) as zipped:
        for p in sorted(output.glob('*.json')): zipped.write(p, p.name)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print('FÆRDIG: ' + str(output / 'kilder-resultat.zip'))
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--results', required=True, help='kontrol-resultat.zip or all-candidates.json')
    parser.add_argument('--output', default='tiny-refuel-kilder')
    parser.add_argument('--limit', type=int, default=100, help='Maximum page attempts per run')
    parser.add_argument('--skip-online', action='store_true')
    parser.add_argument('--offline', action='store_true')
    args = parser.parse_args()
    if args.limit < 0: parser.error('--limit must be nonnegative')
    try: run(args)
    except KeyboardInterrupt: parser.exit(130, '\nAfbrudt. Genstart for at genbruge cachen.\n')
    except (OSError, ValueError) as exc: parser.exit(1, str(exc) + '\n')
