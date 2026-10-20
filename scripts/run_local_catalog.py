"""Run the catalog preparation and specification collection locally, without external Python packages."""
import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import zipfile

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.clean_vehicle_catalog import clean_model_labels
from scripts.dmr_catalog import deduplicate_catalog
from scripts.catalog_inventory import inventory
from scripts.build_enriched_vehicle_catalog import enrich_catalog
from scripts.scrape_vehicle_specs import inventory as missing_inventory, run as scrape
from scripts.review_vehicle_specs import review
from scripts.wiki_vehicle_specs import collect, save

ROOT = Path(__file__).resolve().parents[1]


def prepare(source, output):
    cleaned, cleanup, excluded = clean_model_labels(source)
    known = json.loads((ROOT / 'custom_components/tiny_refuel/frontend/katalog.json').read_text(encoding='utf-8'))
    merged = deepcopy(known)
    merged['brands'] += cleaned['brands']
    merged, conflicts = deduplicate_catalog(merged)
    merged['dmr_catalog'] = source.get('dmr_catalog', {})
    merged.pop('capacity_filter', None)
    merged.pop('enrichment', None)
    save(output / 'master.json', merged)
    save(output / 'cleanup.json', cleanup)
    save(output / 'excluded.json', excluded)
    save(output / 'merge-review.json', conflicts)
    report = inventory(merged)
    save(output / 'inventory.json', report['summary'])
    save(output / 'missing.json', report['missing'])
    save(output / 'unclassified.json', report['unclassified'])
    for kind, rows in report['categories'].items(): save(output / 'categories' / (kind + '.json'), rows)
    overlaps = [r for rows in report['categories'].values() for r in rows
                if len(r['vehicle_types']) > 1 and set(r['vehicle_types']) & {'bus', 'lastbil'}]
    save(output / 'type-overlap-review.json', list({(r['make'], r['model']): r for r in overlaps}.values()))
    # Collected internet candidates are deliberately not applied without review.
    draft = enrich_catalog(merged, [])
    save(output / 'katalog-kladde.json', draft)
    return merged, report['summary']


def run(args):
    source = Path(args.input).resolve(); output = Path(args.output).resolve()
    if output == source.parent or output in source.parents:
        raise ValueError('Choose a separate output subfolder, never the input folder itself')
    output.mkdir(parents=True, exist_ok=True)
    original = source.read_bytes(); original_hash = sha256(original).hexdigest()
    print('1/4: Renser, samler kategorier og bevarer kendte specifikationer...', flush=True)
    merged, summary = prepare(json.loads(original.decode('utf-8-sig')), output)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    stages = {}
    if not args.skip_online:
        print('2/4: Indsamler producent- og datasætkandidater. Cache genbruges ved genstart.', flush=True)
        for name, options in [('manufacturer', {'official_batch': True}), ('open-ev', {'open_ev': True}), ('engine-data', {'engine_data': True})]:
            try:
                scrape(SimpleNamespace(catalog=str(output / 'master.json'), output=str(output / 'online' / name),
                    sources=None, delay=2, offline=args.offline, aliases=None,
                    official_batch=options.get('official_batch', False), open_ev=options.get('open_ev', False),
                    engine_data=options.get('engine_data', False)))
                stages[name] = 'completed'
            except (OSError, ValueError) as exc:
                stages[name] = 'error: ' + str(exc)
                print(name + ': ' + stages[name], flush=True)
        print('3/4: Wikipedia-opslag med præcise navne; uklare kapaciteter springes over.', flush=True)
        rows = missing_inventory(merged)
        priority = {'lastbil': 0, 'bus': 1, 'motorcykel': 2, 'knallert': 3, 'traktor': 4, 'andet': 5, 'varebil': 6, 'personbil': 7}
        kinds = {(b['mærke'], m['model']): m.get('vehicle_types', []) for b in merged['brands'] for m in b['modeller']}
        rows.sort(key=lambda r: (min((priority.get(t, 8) for t in kinds.get((r['make'], r['model']), [])), default=8), r['make'].casefold(), r['model'].casefold()))
        collect(rows, output / 'online/wiki', limit=args.wiki_limit, offline=args.offline)
        stages['wikipedia'] = 'completed'
    candidates = []
    if args.candidates: candidates += json.loads(Path(args.candidates).read_text(encoding='utf-8-sig'))
    for path in sorted((output / 'online').glob('*/all-candidates.json')):
        candidates += json.loads(path.read_text(encoding='utf-8'))
    wiki = output / 'online/wiki/candidates.json'
    if wiki.exists(): candidates += json.loads(wiki.read_text(encoding='utf-8'))
    save(output / 'all-candidates.json', candidates)
    print('4/4: Skriver gennemgang og resultatpakke...', flush=True)
    for name, value in review(candidates).items(): save(output / 'review' / name, value)
    summary = {'input_sha256': original_hash, 'inventory': summary, 'candidate_rows': len(candidates),
        'stages': stages, 'status': 'needs_review', 'automatically_imported_online_candidates': 0,
        'note': 'Sources, conflicts and missing data remain explicit. This is a review package, not a finished release catalog.'}
    save(output / 'summary.json', summary)
    if sha256(source.read_bytes()).hexdigest() != original_hash: raise ValueError('Input changed during execution')
    archive = output / 'send-til-gennemgang.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zipped:
        for path in sorted(output.rglob('*.json')):
            relative = path.relative_to(output)
            if 'cache' in relative.parts or 'open-data-cache' in relative.parts: continue
            zipped.write(path, relative.as_posix())
    print('\nFÆRDIG: ' + str(archive), flush=True)
    print('Originalen er bevaret. Upload kun send-til-gennemgang.zip. Mangler og forslag er ikke automatisk godkendt.', flush=True)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', default='tiny-refuel-resultat')
    parser.add_argument('--candidates', help='Reuse a previously collected all-candidates.json')
    parser.add_argument('--skip-online', action='store_true', help='Preparation and review only')
    parser.add_argument('--offline', action='store_true', help='Use existing caches only')
    parser.add_argument('--wiki-limit', type=int, default=0, help='0 checks all missing models; cached batches are reused')
    args = parser.parse_args()
    if args.wiki_limit < 0: parser.error('--wiki-limit must be zero or positive')
    try: run(args)
    except KeyboardInterrupt: print('\nAfbrudt. Kør samme kommando igen for at genbruge cachen.', flush=True); sys.exit(130)
    except (OSError, ValueError) as exc: parser.exit(1, str(exc) + '\n')
