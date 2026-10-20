"""Collect exact-name Wikipedia capacity candidates with revision links and resumable caching."""
from datetime import datetime, timezone
from hashlib import sha256
import html
import json
import math
from pathlib import Path
import re
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API = 'https://en.wikipedia.org/w/api.php'
USER_AGENT = 'TinyRefuelCatalog/1.0 (https://github.com/Salvationdk/tiny-refuel)'


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    temporary.replace(path)


def split_fields(text):
    parts, start, braces, links, i = [], 0, 0, 0, 0
    while i < len(text):
        pair = text[i:i+2]
        if pair == '{{': braces += 1; i += 2; continue
        if pair == '}}': braces -= 1; i += 2; continue
        if pair == '[[': links += 1; i += 2; continue
        if pair == ']]': links -= 1; i += 2; continue
        if text[i] == '|' and braces == links == 0:
            parts.append(text[start:i]); start = i + 1
        i += 1
    parts.append(text[start:])
    return parts


def infoboxes(text):
    for match in re.finditer(r'\{\{\s*[Ii]nfobox[ _][^|\n{}]+', text):
        depth, i = 1, match.end()
        while depth and i < len(text) - 1:
            pair = text[i:i+2]
            if pair == '{{': depth += 1; i += 2
            elif pair == '}}': depth -= 1; i += 2
            else: i += 1
        if depth: continue
        parts = split_fields(text[match.start()+2:i-2])
        fields = {}
        for part in parts[1:]:
            if '=' in part:
                name, value = part.split('=', 1)
                fields[re.sub(r'[ _-]', '', name.strip().lower())] = value.strip()
        yield fields


def plain(value):
    value = re.sub(r'<ref\b[^>]*(?:/>|>.*?</ref\s*>)', '', value, flags=re.I|re.S)
    value = re.sub(r'\[\[([^\]|]+)\|([^\]]+)\]\]', r'\2', value)
    value = re.sub(r'\[\[([^\]]+)\]\]', r'\1', value)
    value = re.sub(r'<[^>]+>', ' ', value)
    return html.unescape(value.replace("''", '')).strip()


def key(value):
    return ' '.join(plain(value).casefold().split())


def capacity(value, battery=False):
    value = plain(value)
    # A labelled reserve is already part of the total; never add it twice.
    value = re.split(r'\s*\(\s*(?:reserve|incl(?:uding|\.)?\s+(?:the\s+)?reserve)\b', value, maxsplit=1, flags=re.I)[0].strip()
    converted = re.fullmatch(r'\{\{(?:convert|cvt)\|\s*(\d+(?:\.\d+)?)\s*\|\s*([A-Za-z]+)\s*(?:\|[^{}]*)?\}\}', value, flags=re.I)
    literal = re.fullmatch(r'(\d+(?:\.\d+)?)\s*(kWh|Wh|L|litres?|liters?|usgal|impgal)', value, flags=re.I)
    match = converted or literal
    if not match: return None
    number, unit = float(match[1]), match[2].lower()
    factors = {'kwh': 1, 'wh': 0.001} if battery else {'l': 1, 'litre': 1, 'litres': 1, 'liter': 1, 'liters': 1, 'usgal': 3.785411784, 'impgal': 4.54609}
    if unit not in factors: return None
    result = number * factors[unit]
    return round(result, 6) if math.isfinite(result) and 0 < result <= 5000 else None


def extract(page, make, model):
    revisions = page.get('revisions') or []
    if not revisions: return [], 'missing_page'
    revision = revisions[0]
    text = revision.get('slots', {}).get('main', {}).get('*', '')
    candidates = []
    for box in infoboxes(text):
        # Reject redirects to model families and ambiguous infoboxes. No fuzzy match.
        name = box.get('name', '')
        manufacturer = key(box.get('manufacturer', ''))
        full = key(make + ' ' + model)
        if not (key(name) == full or (key(name) == key(model) and re.search(r'(?<!\w)' + re.escape(key(make)) + r'(?!\w)', manufacturer))):
            continue
        specs, evidence = {}, {}
        for field, names in [('tank_l', ('fuelcapacity', 'fueltankcapacity')), ('batteri_kwh', ('batterycapacity', 'battery'))]:
            values = []
            for label in names:
                if label in box:
                    value = capacity(box[label], battery=field == 'batteri_kwh')
                    if value is not None:
                        values.append(value)
                        evidence[field] = plain(box[label])[:100]
            if len(set(values)) == 1: specs[field] = values[0]
        if not specs: continue
        candidates.append({'make': make, 'model': model, 'specifications': specs,
            'source_url': 'https://en.wikipedia.org/w/index.php?oldid=' + str(revision['revid']),
            'parser': 'wikipedia_exact_infobox', 'source_quality': 'community_secondary_pending_review',
            'retrieved_at': datetime.now(timezone.utc).isoformat(), 'evidence': evidence,
            'battery_basis': 'unspecified', 'reviewed': False,
            'scope_note': 'Exact infobox identity only. Year, market, variant and capacity basis require review; not a model-wide specification.',
            'dataset': {'repository': 'en.wikipedia.org', 'license': 'CC-BY-SA-4.0',
                        'license_url': 'https://creativecommons.org/licenses/by-sa/4.0/'}})
    return candidates, 'candidates' if candidates else 'no_exact_identity_or_unambiguous_capacity'


def collect(rows, output, limit=0, offline=False, delay=1.0):
    output = Path(output); cache = output / 'cache'; cache.mkdir(parents=True, exist_ok=True)
    if limit: rows = rows[:limit]
    candidates, statuses = [], []
    failed_batches = 0
    for offset in range(0, len(rows), 20):
        batch = rows[offset:offset+20]
        titles = [r['make'] + ' ' + r['model'] for r in batch]
        token = sha256(json.dumps(titles, ensure_ascii=False).encode()).hexdigest()
        cached = cache / (token + '.json')
        print(f'Wikipedia: {min(offset+20, len(rows))}/{len(rows)}', flush=True)
        try:
            if cached.exists(): data = json.loads(cached.read_text(encoding='utf-8'))
            elif offline: raise FileNotFoundError('Batch absent from offline cache')
            else:
                url = API + '?' + urlencode({'action': 'query', 'titles': '|'.join(titles), 'prop': 'revisions', 'rvprop': 'ids|content', 'rvslots': 'main', 'redirects': 1, 'maxlag': 5, 'format': 'json'})
                for attempt in range(3):
                    try:
                        with urlopen(Request(url, headers={'User-Agent': USER_AGENT}), timeout=45) as response:
                            raw = response.read(12*1024*1024 + 1)
                        if len(raw) > 12*1024*1024: raise ValueError('Wikipedia batch exceeds size limit')
                        data = json.loads(raw)
                        if 'error' in data: raise ValueError(str(data['error']))
                        save(cached, data); break
                    except (OSError, ValueError) as exc:
                        if attempt == 2: raise
                        wait = min(120, max(2, int(exc.headers.get('Retry-After', 5)))) if isinstance(exc, HTTPError) else 5
                        time.sleep(wait)
                time.sleep(max(1.0, delay))
            failed_batches = 0
            aliases = {x['from']: x['to'] for field in ('normalized', 'redirects') for x in data.get('query', {}).get(field, [])}
            pages = {x['title']: x for x in data.get('query', {}).get('pages', {}).values()}
            for row, title in zip(batch, titles):
                for _ in range(10):
                    if title not in aliases: break
                    title = aliases[title]
                found, status = extract(pages.get(title, {}), row['make'], row['model'])
                candidates.extend(found)
                statuses.append({'make': row['make'], 'model': row['model'], 'status': status})
        except (OSError, ValueError) as exc:
            failed_batches += 1
            statuses.extend({'make': r['make'], 'model': r['model'], 'status': 'error', 'error': str(exc)} for r in batch)
        save(output / 'candidates.json', candidates)
        save(output / 'source-status.json', statuses)
        if failed_batches >= 3:
            print('Wikipedia: tre mislykkede batches i træk; stopper denne kilde. Genstart for at prøve igen.', flush=True)
            break
    save(output / 'candidates.json', candidates)
    return candidates
