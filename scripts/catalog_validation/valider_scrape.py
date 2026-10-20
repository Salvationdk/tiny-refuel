"""Collect auditable vehicle-capacity evidence; never overwrite catalog values.
Python 3.10+, pip install playwright; python -m playwright install chromium
python valider_scrape.py
Search pages discover URLs only. Human review is required for every candidate.
"""
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import re
import time
import random
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote, quote
import sys
import base64
import math
from email.utils import parsedate_to_datetime

AGENT = 'TinyRefuelEvidence/1.0'
SEARCH_HOSTS = ('google.', 'bing.', 'yahoo.', 'ecosia.', 'duckduckgo.', 'brave.', 'startpage.', 'qwant.', 'searx.', 'gibiru.', 'mojeek.')

def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.' + str(threading.get_ident()) + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)

def now():
    return datetime.now(timezone.utc).isoformat()

def norm(s):
    return re.sub(r'[^\w]+', ' ', s.casefold()).strip()

def contains(text, label):
    return bool(norm(label)) and (' ' + norm(label) + ' ') in (' ' + norm(text) + ' ')

def unwrap(url):
    for _ in range(3):
        parsed = urlparse(url)
        q = parse_qs(parsed.query)
        host = (parsed.hostname or '').lower()
        target = None
        if host.endswith('yahoo.com'):
            redirect=re.search(r'/RU=([^/]+)',parsed.path)
            if redirect:target=unquote(redirect.group(1))
        if any(x in host for x in SEARCH_HOSTS):
            for field in ('uddg', 'url', 'q', 'u', 'target'):
                value = q.get(field, [''])[0]
                if host.endswith('bing.com') and field == 'u' and value.startswith('a1'):
                    try:
                        value = base64.urlsafe_b64decode(value[2:]+'='*((-len(value[2:]))%4)).decode()
                    except (ValueError, UnicodeError):
                        continue
                if value.startswith(('https://','http://')):
                    target = value
                    break
        if not target or target == url:break
        url = target
    return url

def is_source(url):
    p = urlparse(url)
    return p.scheme in ('https', 'http') and bool(p.hostname) and not any(x in p.hostname for x in SEARCH_HOSTS)

def extract(text, make, model):
    """Conservative candidates with labels and local model context, not verification."""
    if not contains(text, make) or not contains(text, model):
        return []
    patterns = [
        ('tank_l', r'(?:fuel\s*tank(?:\s*capacity)?|tank\s*capacity|brændstoftank|tankvolumen|tankinhalt)[^\d\n]{0,35}(\d{1,4}(?:[.,]\d{1,2})?)\s*(?:litres?|liters?|liter|l)\b'),
        ('batteri_kwh', r'(?:battery(?:\s*(?:capacity|size))?|batteri(?:kapacitet)?|batteriekapazit[aä]t)[^\d\n]{0,45}(\d{1,4}(?:[.,]\d{1,2})?)\s*kwh\b')
    ]
    result = []
    for field, pattern in patterns:
        for match in re.finditer(pattern, text, re.I):
            excerpt = text[max(0, match.start()-350):match.end()+350].strip()
            if not contains(excerpt, model):
                continue
            value = float(match.group(1).replace(',', '.'))
            if value <= 0:
                continue
            basis = 'unspecified'
            if field == 'batteri_kwh':
                local = text[max(0,match.start()-60):match.end()+60].casefold()
                usable = bool(re.search(r'usable|netto|useable|brugbar', local))
                gross = bool(re.search(r'gross|brutto|total', local))
                if usable != gross:
                    basis = 'usable' if usable else 'gross'
            result.append({'field':field, 'value':value, 'unit':'L' if field=='tank_l' else 'kWh', 'battery_basis':basis if field=='batteri_kwh' else None, 'excerpt':excerpt, 'status':'needs_review', 'verified':False, 'scope':{'model_year':None, 'variant':None, 'market':None}, 'reason':'Model context found; exact year, variant, market and source authority require review.'})
    return result

def compact_label(value):
    return re.sub(r'[^a-z0-9]', '', value.casefold())

def extract_page(page, make, model):
    text=page.get('text','')
    host=(urlparse(page.get('final_url','')).hostname or '').lower()
    if host == 'auto-data.net' or host.endswith('.auto-data.net'):
        def cell(label):
            match=re.search(r'(?m)^'+re.escape(label)+r'\s*\n([^\n]+)',text)
            return match.group(1).strip() if match else None
        # Match explicit Brand and Model cells, not incidental mentions or related cars.
        if norm(cell('Brand') or '')!=norm(make) or norm(cell('Model') or '')!=norm(model):return []
        variant=cell('Modification (Engine)')
        start,end=cell('Start of production'),cell('End of production')
        if not variant:return []
        scope={'model_year':None,'year_start':int(start) if start and start.isdigit() else None,
               'year_end':int(end) if end and end.isdigit() else None,'variant':variant,'market':None,
               'year_basis':'production dates; not assumed to be model years'}
        found=[]
        for field,label,unit in [('tank_l','Fuel tank capacity','l'),('batteri_kwh','Gross battery capacity','kWh'),('batteri_kwh','Net (usable) battery capacity','kWh')]:
            match=re.search(r'(?m)^'+re.escape(label)+r'\s*\n(\d+(?:[.,]\d+)?)\s*'+unit+r'\b',text,re.I)
            if not match:continue
            value=float(match[1].replace(',','.'))
            if value<=0:continue
            found.append({'field':field,'value':value,'unit':'L' if field=='tank_l' else 'kWh',
                'battery_basis':None if field=='tank_l' else ('gross' if label.startswith('Gross') else 'usable'),
                'excerpt':match.group(0),'identity_evidence':{k:cell(k) for k in ['Brand','Model','Modification (Engine)','Start of production','End of production']},
                'scope':scope,'source_class':'secondary_specification_database','parser':'auto_data_labelled_cells_v1',
                'verified':False,'status':'needs_review','reason':'Labelled table value for this explicit variant and production period. Market and applicability to the catalog entry still require review.'})
        return found
    # Source-specific adapter: only this product's visible heading establishes model identity.
    if (urlparse(page.get('final_url','')).hostname or '').endswith('2twentyscooters.com'):
        heading=text[:650]
        if compact_label(model) not in compact_label(heading) or compact_label(make) not in compact_label(heading):
            return []
        matches=list(re.finditer(r'(\d+(?:[.,]\d+)?)\s*V\s*/\s*(\d+(?:[.,]\d+)?)\s*Ah\b',text,re.I))
        result=[];seen=set()
        for match in matches:
            voltage=float(match[1].replace(',','.'));ah=float(match[2].replace(',','.'))
            if (voltage,ah) in seen:continue
            seen.add((voltage,ah))
            excerpt=text[max(0,match.start()-180):match.end()+180].strip()
            per_pack=round(voltage*ah/1000,6)
            counts=[1,2] if re.search(r'1 or 2 batteries|one battery.*two batteries',text,re.I|re.S) else None
            result.append({'field':'batteri_kwh','value':per_pack,'unit':'kWh','battery_basis':'nominal_calculated_per_pack',
                'excerpt':excerpt,'verified':False,'status':'needs_review',
                'scope':{'model_year':None,'variant':None,'market':None},
                'parser':'2twenty_voltage_amp_hours_v1',
                'calculation':{'voltage_v':voltage,'capacity_ah':ah,'formula':'V * Ah / 1000','per_pack_kwh':per_pack},
                'battery_configurations':[{'battery_count':n,'nominal_total_kwh':round(n*per_pack,6)} for n in counts] if counts else [],
                'reason':'Nominal energy calculated per battery; installed battery count, usable/gross basis and year remain unresolved. Not a directly stated usable vehicle capacity.'})
        return result
    return extract(text,make,model)

def source_observations(page, make, model):
    text=page.get('text','')
    host=(urlparse(page.get('final_url','')).hostname or '').lower()
    observations=[]
    if not (host=='made-in-china.com' or host.endswith('.made-in-china.com')):return observations
    title=page.get('title','')
    if not contains(title,make) or not contains(title,model):return observations
    pattern=r'Battery\s+(\d+(?:[.,]\d+)?)\s*v\s*(\d+(?:[.,]\d+)?)\s*ah\s*[-–]\s*(\d+(?:[.,]\d+)?)\s*ah\s*\(optional\)'
    for m in re.finditer(pattern,text,re.I):
        volts,low,high=(float(x.replace(',','.')) for x in m.groups())
        if min(volts,low,high)<=0 or low>high:continue
        observations.append({'type':'optional_battery_range','field':'batteri_kwh',
            'source_url':page['final_url'],'source_title':title,'retrieved_at':page.get('checked_at'),
            'text_sha256':page.get('text_sha256'),'excerpt':m.group(0),
            'voltage_v':volts,'capacity_ah_range':[low,high],
            'nominal_kwh_range':[round(volts*low/1000,6),round(volts*high/1000,6)],
            'formula':'V * Ah / 1000','battery_basis':'nominal_calculated',
            'verified':False,'status':'needs_variant',
            'note':'Optional supplier configuration, not a verified installed battery. No intermediate capacities or scalar value inferred.'})
    return observations


def classify_result(row):
    if row.get('observations'):return 'needs_variant'
    if row.get('candidates'):
        if any(c.get('battery_configurations') for c in row['candidates']):return 'needs_variant'
        return 'needs_review'
    if any(p.get('status')=='fetched' for p in row.get('pages',[])):return 'source_without_capacity'
    successful_search=any(a.get('status')=='fetched' and a.get('result_blocks',0)>0 for a in row.get('discovery_attempts',[]))
    return 'no_relevant_sources' if successful_search else 'technical_failure'

# Only anchors inside engine-specific organic result structures qualify.
SEARCH_RESULT_SELECTORS = {
    'duckduckgo': 'a.result__a',
    'brave': '#results .snippet a.heading-serpresult, #results .snippet a[data-type="web"]',
    'qwant': '[data-testid="webResult"] a[href], [data-testid="webResultTitle"] a[href], article a[href]:has(h2), article h2 a[href]',
    'google': '#search a:has(h3)',
    'bing': '#b_results li.b_algo h2 a',
    'yahoo': '#web .algo a:has(h3), #web .algo h3 a',
    'ecosia': 'a.result__link, a[data-test-id="result-link"]',
    'startpage': '.w-gl__result-title',
    'gibiru': '.gsc-webResult .gs-title a.gs-title',
    'mojeek': '.results-standard .title a, .results-standard h2 a',
}
SEARCH_PARSER_VERSION = 6

def search_engine(url):
    host = (urlparse(url).hostname or '').lower()
    return next((name for name in SEARCH_RESULT_SELECTORS if name+'.' in host),None)

def read_search_results(page, url):
    engine = search_engine(url)
    if not engine:return []
    selector = SEARCH_RESULT_SELECTORS[engine]
    return page.locator(selector).evaluate_all("""els => els.map(a => ({
        url:a.href,
        title:a.innerText || a.textContent || '',
        context:(a.closest('article, li.b_algo, .algo, .result, .snippet, .gsc-webResult, .w-gl__result') || a.parentElement).textContent || ''
    }))""")

def relevant_results(records, make, model):
    result=[]
    for item in records:
        url=unwrap(item.get('url',''))
        if not is_source(url):continue
        context=item.get('title','')+' '+item.get('context','')+' '+unquote(url)
        # Reject navigation/company links, even if a search engine changes markup.
        if make.strip().isdigit():continue
        if not contains(context,make) or not contains(context,model):continue
        if re.search(r'\.(?:xlsx?|csv|docx?|pptx?|zip)(?:[?#]|$)',url,re.I):continue
        if url not in result:result.append(url)
    return result

class Fetcher:
    def __init__(self, page, cache, delay):
        self.page, self.cache, self.delay = page, Path(cache), delay
        self.cache.mkdir(parents=True, exist_ok=True)
        self.last = {}

    def get(self, url):
        key = hashlib.sha256(url.encode()).hexdigest()
        dest = self.cache / (key + '.json')
        if dest.exists():
            cached=json.loads(dest.read_text(encoding='utf-8'))
            if not search_engine(url) or cached.get('search_parser_version') == SEARCH_PARSER_VERSION:
                if not search_engine(url) and not cached.get('text','').strip():
                    return {**cached,'status':'empty_page'}
                return cached
            if cached.get('diagnostic_html') and search_engine(url)=='yahoo':
                self.page.route('**/*',lambda route:route.abort())
                try:
                    self.page.set_content(cached['diagnostic_html'],wait_until='domcontentloaded')
                    cached['search_results']=read_search_results(self.page,url)
                    cached['search_parser_version']=SEARCH_PARSER_VERSION
                    cached['reparsed_from_saved_html']=True
                    cached['status']='fetched' if cached['search_results'] else 'search_results_unavailable'
                    save(dest,cached)
                    return cached
                finally:
                    self.page.unroute('**/*')
        parsed = urlparse(url)
        origin = parsed.scheme+'://'+parsed.netloc
        try:
            time.sleep(self.delay + random.uniform(1.0, 2.5))
            
            response = self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            self.last[origin] = time.monotonic()
            code = response.status if response else 0
            
            if code in (403, 429):
                time.sleep(6.0)
                return {'url': url, 'status': 'host_paused', 'http_status': code, 'retry_after':response.headers.get('retry-after'), 'checked_at': now()}
                
            if not response or code >= 400:
                return {'url': url, 'status': 'http_error', 'http_status': code, 'checked_at': now()}
                
            if 'text/html' not in response.headers.get('content-type', ''):
                return {'url': url, 'status': 'unsupported_document_requires_review', 'checked_at': now()}
                
            text = self.page.locator('body').inner_text(timeout=10000)
            if re.search(r'unusual traffic|verify you are human|verifying your request|captcha|access denied', text[:6000], re.I):
                time.sleep(10.0)
                return {'url': url, 'status': 'challenge_host_paused', 'checked_at': now()}
                
            if not text.strip():
                return {'url':url,'status':'empty_page','checked_at':now()}
            links = self.page.locator('a[href]').evaluate_all('(els)=>els.map(e=>e.href)')
            result = {'url': url, 'final_url': self.page.url, 'title': self.page.title(), 'status': 'fetched', 'checked_at': now(), 'text': text, 'links': links, 'text_sha256': hashlib.sha256(text.encode()).hexdigest()}
            if search_engine(url):
                try:
                    self.page.locator(SEARCH_RESULT_SELECTORS[search_engine(url)]).first.wait_for(state='attached',timeout=5000)
                except Exception:
                    pass
                result['search_results']=read_search_results(self.page,url)
                result['search_parser_version']=SEARCH_PARSER_VERSION
                if not result['search_results']:
                    result['diagnostic_html']=self.page.content()
                    result['diagnostic_status']='no_result_blocks; may be changed markup, unrendered page or no results'
                    no_results=re.search(r'no results (?:found|for)|did not match any|ingen resultater|aucun r.sultat',result['text'],re.I)
                    if not no_results:result['status']='search_results_unavailable'
            save(dest, result)
            return result
        except Exception as exc:
            return {'url': url, 'status': 'fetch_error', 'error': str(exc), 'checked_at': now()}

def compare(current, candidate):
    value = current.get(candidate['field'])
    if value is None:
        return 'proposal_for_missing_value'
    if candidate['field']=='batteri_kwh' and (candidate['battery_basis']=='unspecified' or current.get('battery_basis') != candidate['battery_basis']):
        return 'battery_basis_unresolved'
    return 'same_number_scope_unresolved' if abs(float(value)-candidate['value']) < .01 else 'possible_conflict_scope_unresolved'

INPUT_FIL = "katalog_renset_og_optimeret.json"
OUTPUT_FIL = "bilkatalog_maalstruktur_valideret.json"
LOG_FIL = "validering_fejl.log"
ANTAL_TRAADE = 3

fil_lock = threading.Lock()
print_lock = threading.Lock()
host_locks = {}
host_guard = threading.Lock()

active_threads_status = {}
thread_slots = {}
slot_lock = threading.Lock()

engine_cooldowns = {}
cooldown_lock = threading.Lock()
blocked_sources = set()

total_fundet = 0
antal_succes = 0
antal_ingen_data = 0
antal_fejlede = 0

def get_my_slot():
    ident = threading.get_ident()
    with slot_lock:
        if ident not in thread_slots:
            used_slots = set(thread_slots.values())
            for s in range(1, ANTAL_TRAADE + 1):
                if s not in used_slots:
                    thread_slots[ident] = s
                    break
            if ident not in thread_slots:
                thread_slots[ident] = 1
        return thread_slots[ident]

def update_thread_status(text):
    slot = get_my_slot()
    with print_lock:
        active_threads_status[slot] = f"\033[36mTråd {slot:2d}\033[0m │ {text}"

def log_error(make, model, message):
    with fil_lock:
        with open(LOG_FIL, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] Mærke: {make} | Model: {model}\n")
            f.write(f"   -> Fejl: {message}\n" + "-"*50 + "\n")

class ThreadFetcher(Fetcher):
    def get(self, url):
        host = urlparse(url).netloc
        with host_guard:
            lock = host_locks.setdefault(host, threading.Lock())
        with lock:
            if host in blocked_sources:
                return {'url':url,'status':'host_paused','checked_at':now()}
            result = super().get(url)
            if result.get('status') in ('host_paused','challenge_host_paused'):
                blocked_sources.add(host)
            return result

def investigate(make, model, output_dir):
    slot = get_my_slot()
    update_thread_status(f"\033[1m{make} {model['model']}\033[0m \033[90m(Forbereder)\033[0m")

    from playwright.sync_api import sync_playwright
    row = {'make':make, 'model':model['model'], 'checked_at':now(),
           'original_values':{k:model.get(k) for k in ('tank_l','batteri_kwh','brændstof','battery_basis')},
           'pages':[], 'candidates':[], 'observations':[], 'status':'unresolved'}
    
    base_search_engines = [
        ("DuckDuckGo", lambda q: f"https://html.duckduckgo.com/html/?q={q}"),
        ("Brave", lambda q: f"https://search.brave.com/search?q={q}"),
        ("Qwant", lambda q: f"https://www.qwant.com/?q={q}"),
        ("Google", lambda q: f"https://www.google.com/search?q={q}"),
        ("Bing", lambda q: f"https://www.bing.com/search?q={q}"),
        ("Yahoo", lambda q: f"https://search.yahoo.com/search?p={q}"),
        ("Ecosia", lambda q: f"https://www.ecosia.org/search?q={q}"),
        ("Startpage", lambda q: f"https://www.startpage.com/do/search?query={q}"),
        ("Gibiru", lambda q: f"https://gibiru.com/results.html?q={q}"),
        ("Mojeek", lambda q: f"https://www.mojeek.com/search?q={q}")
    ]

    shift = (slot - 1) % len(base_search_engines)
    search_engines = base_search_engines[shift:] + base_search_engines[:shift]

    if make.strip().isdigit():
        row['status']='invalid_identity'
        row['error']='Numeric register make requires manual identification; no search attempted.'
        return row
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                context = browser.new_context(user_agent=AGENT)
                fetch = ThreadFetcher(context.new_page(), output_dir/'cache', 3)
                row['discovery_attempts']=[]
                checked=set()
                def check_sources(urls):
                    for idx,url in enumerate(list(dict.fromkeys(urls))[:3]):
                        if url in checked:continue
                        checked.add(url)
                        update_thread_status(f"{make} {model['model']} [Henter kilde {idx+1}]")
                        page=fetch.get(url)
                        row['pages'].append({k:v for k,v in page.items() if k not in ('text','links','search_results')})
                        if page.get('status')!='fetched':
                            log_error(make,model['model'],f"Kilde {url}: {page.get('status')} | {page.get('error','')}")
                            continue
                        if not is_source(page.get('final_url','')):continue
                        row['observations'].extend(source_observations(page,make,model['model']))
                        for candidate in extract_page(page,make,model['model']):
                            candidate.update({'source_url':page['final_url'],'source_title':page['title'],
                                'retrieved_at':page['checked_at'],'text_sha256':page['text_sha256'],
                                'comparison':compare(model,candidate)})
                            row['candidates'].append(candidate)
                urls=[u for u in model.get('capacity_source_urls',[]) if is_source(u)]
                if is_source(model.get('source_url','')):urls.append(model['source_url'])
                check_sources(urls)
                query=quote(f'"{make}" "{model["model"]}" technical specifications fuel tank battery capacity')
                for engine_name,url_builder in search_engines:
                    if row['candidates']:break
                    with cooldown_lock:
                        cooling=time.time()<engine_cooldowns.get(engine_name,0)
                    if cooling:
                        row['discovery_attempts'].append({'engine':engine_name,'status':'cooldown_skipped'})
                        continue
                    update_thread_status(f"{make} {model['model']} [Søger: {engine_name}]")
                    result=fetch.get(url_builder(query))
                    links=relevant_results(result.get('search_results',[]),make,model['model'])
                    attempt={'engine':engine_name,'status':result['status'],'matching_results':len(links),
                             'result_blocks':len(result.get('search_results',[])), 'error':result.get('error')}
                    row['discovery_attempts'].append(attempt)
                    row['discovery_status']=result['status']
                    log_error(make,model['model'],f"Søgning {engine_name}: {result['status']}; relevante resultater={len(links)}; {result.get('error','')}")
                    if result['status'] in ('host_paused','challenge_host_paused','fetch_error'):
                        with cooldown_lock:engine_cooldowns[engine_name]=time.time()+90
                        continue
                    check_sources(links)
                row['status']=classify_result(row)
            finally:
                browser.close()
    except Exception as exc:
        row['error'] = str(exc)
        row['status'] = 'paused'
        log_error(make, model['model'], f"Kritisk tråd-fejl: {str(exc)}")
    
    update_thread_status(f"\033[1m{make} {model['model']}\033[0m \033[32m✔ Færdig\033[0m")
    return row


def enrich_candidates(row, model):
    for c in row['candidates']:
        c['make'], c['model'] = row['make'], row['model']
        c['scope_hints'] = {
            'years_in_excerpt':sorted(set(re.findall(r'\b(?:19|20)\d{2}\b',c['excerpt']))),
            'catalog_variants_in_excerpt':[v['name'] for v in model.get('variants',[]) if v.get('name') and contains(c['excerpt'],v['name'])],
            'note':'Hints only; these do not establish applicability.'}
        stable = {k:c.get(k) for k in ('make','model','field','value','battery_basis','source_url','text_sha256','excerpt')}
        c['candidate_id'] = hashlib.sha256(json.dumps(stable,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        c['verified'] = False


def export_review(report, output_dir):
    save(output_dir/'source-observations.json',[o for r in report['models'].values() for o in r.get('observations',[])])
    candidates = [c for r in report['models'].values() for c in r.get('candidates',[]) if c.get('candidate_id')]
    save(output_dir/'review-candidates.json',candidates)
    template = output_dir/'approval-template.json'
    save(template, {'instructions':'Copy to approvals.json. Inspect the actual source, exact vehicle scope and unit. Set approved=true only after review. Never approve solely from a search result or numeric agreement. all_model_years_and_variants=true permits a model-level value; otherwise specify existing variant and model_years. Missing applicability never becomes verified.',
        'approvals':[{'candidate_id':c['candidate_id'],'make':c['make'],'model':c['model'],'field':c['field'],'value':c['value'],'source_url':c['source_url'],'approved':False,'reviewer':'','reviewed_at':'','scope':{'all_model_years_and_variants':False,'variant':None,'model_years':[],'market':None},'battery_basis':c.get('battery_basis')} for c in candidates]})


def apply_approved():
    root = Path('tiny-refuel-validering')
    report = json.loads((root/'evidence-results.json').read_text(encoding='utf-8'))
    approvals = json.loads((root/'approvals.json').read_text(encoding='utf-8'))['approvals']
    working = Path(OUTPUT_FIL) if Path(OUTPUT_FIL).exists() else Path(INPUT_FIL)
    original = working.read_bytes()
    catalog = json.loads(original.decode('utf-8-sig'))
    models = {(b['mærke'],m['model']):m for b in catalog['brands'] for m in b['modeller']}
    candidates = {c['candidate_id']:c for r in report['models'].values() for c in r.get('candidates',[]) if c.get('candidate_id')}
    plans=[]; errors=[]; targets={}
    for a in approvals:
        if a.get('approved') is not True:continue
        try:
            c=candidates[a['candidate_id']]
            if any(a.get(k)!=c.get(k) for k in ('make','model','field','value','source_url')):
                raise ValueError('Approval differs from evidence record')
            if not a.get('reviewer') or not a.get('reviewed_at'):
                raise ValueError('Reviewer and reviewed_at required')
            datetime.fromisoformat(a['reviewed_at'])
            if not is_source(c['source_url']):raise ValueError('Concrete source URL required')
            if c['field'] not in ('tank_l','batteri_kwh') or not math.isfinite(c['value']) or c['value']<=0:
                raise ValueError('Invalid capacity')
            # Check that quoted evidence is still in the saved page, rather than trusting editable reports.
            cached = None
            for page_path in (root/'cache').glob('*.json'):
                page = json.loads(page_path.read_text(encoding='utf-8'))
                if page.get('final_url')==c['source_url'] and page.get('text_sha256')==c['text_sha256']:
                    text=page.get('text','')
                    if hashlib.sha256(text.encode()).hexdigest()==c['text_sha256'] and c['excerpt'] in text:
                        cached=page;break
            if not cached:raise ValueError('Saved source evidence is missing or changed')
            if not any(x['field']==c['field'] and x['value']==c['value'] for x in extract_page(cached,c['make'],c['model'])):
                raise ValueError('Capacity cannot be reproduced from saved source')
            m=models[(c['make'],c['model'])];scope=a.get('scope',{})
            if not scope.get('market'):raise ValueError('Explicit market required')
            target=m
            if scope.get('all_model_years_and_variants') is not True:
                variant=scope.get('variant'); years=scope.get('model_years',[])
                if not variant or not years:raise ValueError('Exact variant and years required, or explicit whole-model approval')
                if any(not re.fullmatch(r'(?:19|20)\d{2}',str(y)) for y in years):raise ValueError('Invalid model years')
                matches=[v for v in m.get('variants',[]) if v.get('name')==variant]
                if len(matches)!=1:raise ValueError('Variant must match exactly one catalog entry')
                target=matches[0]
                if sorted(map(str,target.get('model_years',[])))!=sorted(map(str,years)):
                    raise ValueError('Variant years must already match exactly; split variants before applying')
            if c['field']=='batteri_kwh':
                basis=a.get('battery_basis')
                if basis not in ('usable','gross') or basis!=c.get('battery_basis'):
                    raise ValueError('Battery gross/usable basis must be explicit in evidence')
            identity=(id(target),c['field'])
            if identity in targets and targets[identity]!=c['value']:raise ValueError('Conflicting approvals for same field')
            targets[identity]=c['value'];plans.append((target,c,a))
        except (KeyError,ValueError,TypeError) as exc:
            errors.append({'candidate_id':a.get('candidate_id'),'error':str(exc)})
    if errors:
        save(root/'approval-errors.json',errors)
        raise SystemExit('No values applied. Correct approval-errors.json first.')
    changes=[]
    for target,c,a in plans:
        old=target.get(c['field']);target[c['field']]=c['value']
        target.setdefault('capacity_documentation',{})[c['field']]={**c,'verified':True,'status':'reviewer_verified','reviewer':a['reviewer'],'reviewed_at':a['reviewed_at'],'scope':a['scope']}
        target['capacity_source_urls']=list(dict.fromkeys(target.get('capacity_source_urls',[])+[c['source_url']]))
        if c['field']=='batteri_kwh':target['battery_basis']=a['battery_basis']
        # Do not mark the entire model as verified: other fields can remain unresolved.
        changes.append({'candidate_id':c['candidate_id'],'field':c['field'],'old':old,'new':c['value'],'scope':a['scope']})
    if not plans:
        print('No approved evidence. Catalog unchanged.');return
    backup=Path(str(working)+'.before-approval-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.bak')
    backup.write_bytes(original)
    save(root/('applied-changes-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json'),changes)
    save(OUTPUT_FIL,catalog)
    print(f'Applied {len(plans)} reviewed field values. Backup: {backup}')

def main():
    global total_fundet, antal_succes, antal_ingen_data, antal_fejlede
    parser=argparse.ArgumentParser()
    parser.add_argument("--limit",type=int,default=None,help="Maximum models in this run")
    parser.add_argument("--make",help="Only inspect this make, case insensitive")
    parser.add_argument("--retry-paused",action="store_true",help="Retry only previously unresolved or failed models")
    options=parser.parse_args()
    if options.limit is not None and options.limit<1:parser.error('--limit must be positive')
    working = Path(OUTPUT_FIL) if Path(OUTPUT_FIL).exists() else Path(INPUT_FIL)
    if not working.exists():
        raise SystemExit(f"Input mangler: {INPUT_FIL}")
    catalog = json.loads(working.read_text(encoding='utf-8-sig'))
    output_dir = Path('tiny-refuel-validering'); output_dir.mkdir(exist_ok=True)
    report_path = output_dir/'evidence-results.json'
    report = json.loads(report_path.read_text(encoding='utf-8')) if report_path.exists() else {
        'models':{}, 'note':'Concrete source evidence; no automatic capacity verification. Search snippets are never capacity evidence.'}
    
    inventory = [[b['mærke'],m['model']] for b in catalog.get('brands',[]) for m in b.get('modeller',[])]
    fingerprint = hashlib.sha256(json.dumps(inventory,ensure_ascii=False).encode()).hexdigest()
    if report.get('inventory_sha256',fingerprint) != fingerprint:
        raise SystemExit('Modeludvalget er ændret. Flyt tiny-refuel-validering til en backupmappe før en ny kørsel.')
    report['inventory_sha256'] = fingerprint
    
    jobs = []
    for b in catalog.get('brands',[]):
        for m in b.get('modeller',[]):
            identity = json.dumps([b['mærke'],m['model']],ensure_ascii=False)
            value_hash = hashlib.sha256(json.dumps({k:m.get(k) for k in ('tank_l','batteri_kwh','brændstof','battery_basis')},sort_keys=True).encode()).hexdigest()
            previous = report['models'].get(identity)
            
            unchanged=previous and previous.get('catalog_value_sha256')==value_hash
            if options.retry_paused:
                if not unchanged or previous.get('status') not in ('paused','technical_failure','no_relevant_sources','source_without_capacity'):continue
            elif unchanged:
                continue
            jobs.append((b['mærke'],m,identity,value_hash))

    if options.make:jobs=[j for j in jobs if norm(j[0])==norm(options.make)]
    if options.limit is not None:jobs=jobs[:options.limit]
    total_jobs = len(jobs)
    print(f"\033[1;36m[i] Starter {ANTAL_TRAADE} tråde. {total_jobs} modeller mangler kontrol.\033[0m")
    time.sleep(2)

    executor = ThreadPoolExecutor(max_workers=ANTAL_TRAADE)
    pending = {}; position = 0; completed = 0

    def submit_next():
        nonlocal position
        if position < len(jobs):
            job = jobs[position]; position += 1
            fut = executor.submit(investigate, job[0], dict(job[1]), output_dir)
            pending[fut] = job

    try:
        for _ in range(ANTAL_TRAADE): 
            submit_next()

        while pending:
            future = next(as_completed(list(pending)))
            make, model, identity, value_hash = pending.pop(future)
            row = future.result(); row['catalog_value_sha256'] = value_hash; row['validator_version'] = 7
            enrich_candidates(row, model)
            report['models'][identity] = row
            
            if row.get('status') in ('paused','technical_failure','invalid_identity'):
                antal_fejlede += 1
            else:
                model['capacity_status'] = 'needs_review'
                model['specification_note'] = {'needs_variant':'Kilde fundet; vælg konkret batteri/variant','source_without_capacity':'Kilde fundet; kapacitet ikke dokumenteret','no_relevant_sources':'Ingen relevante kilder fundet'}.get(row['status'],'Kilde fundet; mangler validering' if row['candidates'] else 'DMR-import mangler tjek')
                if not model.get('brændstof'):
                    model['requires_fuel_selection'] = True
                
                if row.get('error'):
                    antal_fejlede += 1
                elif row['candidates']:
                    antal_succes += 1
                    total_fundet += len(row['candidates'])
                else:
                    antal_ingen_data += 1

            row['status_label']={'needs_variant':'Variant/batteri skal afklares','needs_review':'Forslag til gennemgang','source_without_capacity':'Kilde uden dokumenteret kapacitet','no_relevant_sources':'Ingen relevante kilder','technical_failure':'Teknisk fejl','invalid_identity':'Mærke/model skal afklares'}.get(row['status'],row['status'])
            completed += 1
            save(report_path, report)
            if completed % 20 == 0: 
                save(OUTPUT_FIL, catalog)

            procent = (completed / total_jobs) * 100 if total_jobs > 0 else 100
            udfyldt = int(35 * completed / total_jobs) if total_jobs > 0 else 35
            bar = '\033[32m' + '█' * udfyldt + '\033[90m' + '-' * (35 - udfyldt) + '\033[0m'

            with print_lock:
                sys.stdout.write("\033[H\033[J")
                print("\033[1;36m╔═══════════════════════════════════════════════════════════════════╗\033[0m")
                print("\033[1;36m║\033[0m                 \033[1;92mTINY REFUEL\033[0m \033[1m-- EVIDENCE VALIDERING\033[0m                 \033[1;36m║\033[0m")
                print("\033[1;36m╚═══════════════════════════════════════════════════════════════════╝\033[0m")
                print(f" \033[90mStatistik:\033[0m 🟢 Forslag: \033[32m{antal_succes}\033[0m  │  🟡 Ingen data: \033[33m{antal_ingen_data}\033[0m  │  🔴 Pauset/Fejl: \033[31m{antal_fejlede}\033[0m")
                print(f" \033[90mTotal fundne værdier:\033[0m \033[1;36m{total_fundet}\033[0m\n")
                print(f" Fremskridt: [{bar}] \033[1m{procent:.1f}%\033[0m \033[90m({completed}/{total_jobs})\033[0m\n")
                print("\033[1m Aktive Tråde Status:\033[0m")
                print("\033[90m" + "─" * 67 + "\033[0m")
                for t_id in range(1, ANTAL_TRAADE + 1):
                    status_str = active_threads_status.get(t_id, f"\033[36mTråd {t_id:2d}\033[0m │ \033[90mAfventer job...\033[0m")
                    print(f" {status_str}")
                print("\033[90m" + "─" * 67 + "\033[0m")
                print(" \033[2mTryk Ctrl+C for at afbryde sikkert og gemme fremskridt.\033[0m")
                sys.stdout.flush()

            print(f" Seneste: {make} {model['model']} — {row['status_label']}",flush=True)
            submit_next()

    except KeyboardInterrupt:
        print('\n\n\033[1;33m[!] Stopper efter aktive forespørgsler. Alle data er gemt sikkert.\033[0m')
        for future in pending: future.cancel()
    finally:
        save(report_path, report)
        save(OUTPUT_FIL, catalog)
        export_review(report, output_dir)
        executor.shutdown(wait=True, cancel_futures=True)
    export_review(report, output_dir)
    print(f"\n\033[1;32m[✔] FÆRDIG!\033[0m\nKatalog: {OUTPUT_FIL}\nRapport: {report_path}", flush=True)

if __name__ == '__main__':
    if '--apply-approved' in sys.argv:
        apply_approved()
    else:
        main()