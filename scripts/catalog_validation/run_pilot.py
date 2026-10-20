"""Bounded offline and live Playwright pilot. Saves diagnostics, never edits a catalog."""
import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
from pathlib import Path
from urllib.parse import quote

ROOT=Path(__file__).resolve().parent
OUT=Path('catalog-validation-results');OUT.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('validator',ROOT/'valider_scrape.py')
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)

def offline():
    from playwright.sync_api import sync_playwright
    checks=[]
    page_data=json.loads((ROOT/'fixtures/roma-2900.json').read_text())
    cs=v.extract_page(page_data,'2 TWENTY','ROMA 2900')
    assert cs and cs[0]['value']==1.44 and cs[0]['battery_configurations'][1]['nominal_total_kwh']==2.88
    assert not cs[0]['verified'];checks.append('real cached Roma battery configurations')
    assert not v.extract_page(page_data,'2 TWENTY','ROMA 4800');checks.append('different model rejected')
    source=json.loads((ROOT/'fixtures/auto-data-up.json').read_text())
    candidates=v.extract_page(source,'Volkswagen','up!')
    assert len(candidates)==1 and candidates[0]['value']==35 and candidates[0]['field']=='tank_l'
    assert candidates[0]['scope']['variant']=='1.0 (60 Hp)' and candidates[0]['scope']['year_start']==2012 and candidates[0]['scope']['year_end']==2016
    assert not candidates[0]['verified'];checks.append('actual Auto-Data table: 35 L, explicit variant and production years')
    assert not v.extract_page(source,'Volkswagen','e-up!');checks.append('electric variant rejected for petrol source')
    with sync_playwright() as p:
        browser=p.chromium.launch()
        context=browser.new_context(java_script_enabled=True)
        context.route('**/*',lambda route:route.abort())
        page=context.new_page()
        page.set_content((ROOT/'fixtures/yahoo-results.html').read_text())
        results=v.read_search_results(page,'https://search.yahoo.com/search?p=test')
        assert len(results)>=2;checks.append('actual Yahoo DOM selector in Chromium')
        assert all(v.is_source(v.unwrap(r['url'])) for r in results);checks.append('Yahoo redirect decoding')
        page.screenshot(path=str(OUT/'offline-yahoo.png'),full_page=True)
        page.set_content('<nav><a href="https://www.qwantjunior.com/">Junior</a><a href="https://www.welcometothejungle.com/en/companies/qwant">Jobs</a></nav>')
        for engine in v.SEARCH_RESULT_SELECTORS:
            assert not v.read_search_results(page,f'https://www.{engine}.com/search')
        checks.append('navigation rejected for all ten engine selectors')
        browser.close()
    assert not v.relevant_results([{'url':'https://example.com','title':'10279 Austral'}],'10279','Austral');checks.append('numeric make rejected')
    assert v.classify_result({'pages':[{'status':'fetched'}]})=='source_without_capacity';checks.append('missing capacity distinguished from technical failure')
    assert v.classify_result({'pages':[]})=='technical_failure';checks.append('technical failure classified')
    report={'status':'passed','checks':checks,'network_requests':0}
    v.save(OUT/'offline-report.json',report)
    print(json.dumps(report),flush=True)

ENGINES={
'DuckDuckGo':'https://html.duckduckgo.com/html/?q=',
'Brave':'https://search.brave.com/search?q=',
'Qwant':'https://www.qwant.com/?q=',
'Google':'https://www.google.com/search?q=',
'Bing':'https://www.bing.com/search?q=',
'Yahoo':'https://search.yahoo.com/search?p=',
'Ecosia':'https://www.ecosia.org/search?q=',
'Startpage':'https://www.startpage.com/do/search?query=',
'Gibiru':'https://gibiru.com/results.html?q=',
'Mojeek':'https://www.mojeek.com/search?q=',
}

def probe(engine,base):
    from playwright.sync_api import sync_playwright
    report={'engine':engine,'query_make':'Volkswagen','query_model':'up!','status':'started'}
    folder=OUT/engine.lower();folder.mkdir(exist_ok=True)
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch()
            try:
                context=browser.new_context(user_agent=v.AGENT,viewport={'width':1280,'height':900})
                page=context.new_page()
                fetch=v.ThreadFetcher(page,folder/'cache',3)
                url=base+quote('"Volkswagen" "up!" fuel tank capacity specifications')
                response=fetch.get(url)
                report.update({k:val for k,val in response.items() if k not in ('text','links','diagnostic_html','search_results')})
                rows=response.get('search_results',[])
                links=v.relevant_results(rows,'Volkswagen','up!')
                report['result_blocks']=len(rows);report['relevant_links']=links
                v.save(folder/'search-results.json',rows)
                # Public unauthenticated pages only; no credentials/cookies/traces in artifact.
                (folder/'page.html').write_text(page.content(),encoding='utf-8')
                page.screenshot(path=str(folder/'page.png'),full_page=True,timeout=15000)
                report['sources']=[]
                # At most one concrete source per engine; no retries after limits/challenges.
                if links:
                    source=fetch.get(links[0])
                    report['sources'].append({k:val for k,val in source.items() if k not in ('text','links','diagnostic_html')})
                    if source.get('status')=='fetched':
                        report['capacity_candidates']=v.extract_page(source,'Volkswagen','up!')
            finally:browser.close()
    except Exception as exc:
        report['status']='probe_error';report['error']=str(exc)
    finally:
        v.save(folder/'report.json',report)
    print(engine,report['status'],report.get('result_blocks',0),flush=True)
    return report

def live():
    reports=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(probe,name,url) for name,url in ENGINES.items()]
        for future in concurrent.futures.as_completed(futures):
            reports.append(future.result());v.save(OUT/'live-report.json',{'reports':reports,'note':'A fetched search page or link does not validate a vehicle capacity.'})
    print('Live probes completed. Results may include access restrictions.',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['offline','live']);args=parser.parse_args()
    if args.mode=='offline':offline()
    else:live()
