"""Build a directly readable Tiny Refuel catalog with conservative source defaults."""
from copy import deepcopy
import json
from pathlib import Path
from .build_supported_catalog import supported_catalog, positive
from .review_vehicle_specs import review, identity

FUEL = {'Benzin': 'benzin', 'Diesel': 'diesel', 'El': 'el', 'Hybrid': 'hybrid', 'Plug-in hybrid': 'plug_in_hybrid'}


def enrich_catalog(original, candidates):
    data = deepcopy(original)
    report = review(candidates)
    rows = {(identity(r['make']), identity(r['model'])): r for r in report['model-summary.json']}
    blocked = {(identity(r['make']), identity(r['model'])) for r in report['scope-conflicts.json']}
    by_model = {}
    for candidate in candidates:
        by_model.setdefault((identity(candidate['make']), identity(candidate['model'])), []).append(candidate)
    added_fields = 0
    enriched = 0
    for brand in data['brands']:
        for model in brand['modeller']:
            pair = identity(brand['mærke']), identity(model['model'])
            if pair not in rows or pair in blocked:
                continue
            observed = rows[pair]['observed_values']
            changed = []
            if not positive(model.get('tank_l')) and len(observed.get('tank_l', [])) == 1:
                model['tank_l'] = observed['tank_l'][0]
                changed.append('tank_l')
            # Prefer usable energy. Multiple usable values must not fall back to gross.
            if not positive(model.get('batteri_kwh')):
                for field, basis in [('battery_usable_kwh', 'usable'), ('battery_gross_kwh', 'gross'), ('battery_unspecified_kwh', 'unspecified')]:
                    if observed.get(field):
                        if len(observed[field]) == 1:
                            model['batteri_kwh'] = observed[field][0]
                            model['battery_basis'] = basis
                            changed.append('batteri_kwh')
                        break
            if not changed:
                continue
            if not model.get('brændstof'):
                known = set(model.get('fuel_types') or [])
                if len(observed.get('brændstof', [])) == 1:
                    known.add(observed['brændstof'][0])
                if len(known) == 1 and next(iter(known)) in FUEL:
                    model['brændstof'] = FUEL[next(iter(known))]
            model['requires_fuel_selection'] = not bool(model.get('brændstof'))
            sources = []
            for row in by_model[pair]:
                source = {'url': row.get('source_url') or row.get('dataset', {}).get('url'),
                    'dataset': row.get('dataset', {}).get('repository'), 'license': row.get('dataset', {}).get('license'),
                    'year': row.get('year'), 'year_start': row.get('year_start'), 'year_end': row.get('year_end'),
                    'variant': row.get('variant'), 'generation': row.get('generation'), 'trim': row.get('trim'),
                    'markets': row.get('markets', []), 'specifications': row.get('specifications'),
                    'battery_basis': row.get('battery_basis'), 'battery_capacities': row.get('battery_capacities'),
                    'primary_sources': row.get('sources', [])}
                if source not in sources:sources.append(source)
            model['capacity_sources'] = sources
            model['capacity_status'] = 'source_dataset_default_not_manufacturer_verified'
            model['specification_note'] = ('Kildedatasæt angiver denne kapacitet for de indsamlede varianter. '
                'Den er ikke verificeret for alle årgange/varianter. Kontrollér drivmiddel, tank og batteriets netto/brutto for dit køretøj.')
            enriched += 1
            added_fields += len(changed)
    result = supported_catalog(data)
    result['enrichment'] = {'source_candidate_rows': len(candidates), 'enriched_models_before_filter': enriched,
        'added_capacity_fields': added_fields, 'models_blocked_by_scope_conflict': len(blocked),
        'policy': 'Existing capacities preserved; unique observed values only; never assume coverage of all variants. Dataset defaults explicitly labelled.'}
    # Runtime catalog: identities, capacities, logos and short provenance only.
    licenses = {}
    for row in candidates:
        dataset = row.get('dataset', {})
        if dataset.get('repository'):
            licenses[dataset['repository']] = {'license': dataset.get('license'), 'license_url': dataset.get('license_url')}
    for brand in result['brands']:
        compact_models = []
        for model in brand['modeller']:
            fields = ('model', 'source_names', 'brændstof', 'tank_l', 'batteri_kwh', 'battery_basis',
                      'requires_fuel_selection', 'specification_note', 'source_url', 'capacity_status')
            compact_model = {k: deepcopy(model[k]) for k in fields if k in model}
            urls = sorted({r['url'] for r in model.get('capacity_sources', []) if r.get('url')})
            if urls:
                compact_model['capacity_source_urls'] = urls
            compact_models.append(compact_model)
        brand['modeller'] = compact_models
    result['data_sources'] = licenses
    result['note'] = 'Compact runtime catalog: no engine, generation or variant inventories. Check capacities for the concrete vehicle.'
    for key in ('dmr_catalog', 'catalog_cleanup', 'model_label_cleanup', 'logo_coverage'):
        result.pop(key, None)
    result['enrichment']['variant_lists_included'] = False
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', required=True)
    parser.add_argument('--candidates', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = enrich_catalog(json.loads(Path(args.catalog).read_text(encoding='utf-8-sig')),
                            json.loads(Path(args.candidates).read_text(encoding='utf-8-sig')))
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    print(json.dumps({'filter': result['capacity_filter'], 'enrichment': result['enrichment']}, ensure_ascii=False, indent=2))
