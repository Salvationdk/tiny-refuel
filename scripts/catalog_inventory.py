"""Inventory unique make/model pairs by explicit type and list missing specifications."""
import argparse
from collections import Counter
import json
from pathlib import Path
from .dmr_catalog import deduplicate_catalog
from .build_supported_catalog import positive
from .vehicle_type_names import CODES, NAMES

KINDS = ('personbil', 'varebil', 'lastbil', 'bus', 'motorcykel', 'knallert', 'traktor', 'andet')


def inventory(catalog):
    catalog, cleanup = deduplicate_catalog(catalog)
    groups = {kind: [] for kind in KINDS}
    unclassified, missing = [], []
    known_capacity = 0
    for brand in catalog['brands']:
        for model in brand['modeller']:
            raw = model.get('vehicle_types') or model.get('vehicle_type') or model.get('koeretoejstype') or []
            if not isinstance(raw, list): raw = [raw]
            types = sorted({NAMES.get(str(t).strip().casefold(), CODES.get(str(t).strip(), str(t).strip().casefold())) for t in raw} & set(KINDS))
            row = {'make': brand['mærke'], 'model': model['model'], 'vehicle_types': types}
            for key in ('tank_l', 'batteri_kwh', 'brændstof', 'source_url', 'capacity_status', 'capacity_scope'):
                if model.get(key) is not None: row[key] = model[key]
            fields = []
            fuel = model.get('brændstof')
            if not fuel: fields.append('brændstof')
            if fuel in ('benzin', 'diesel', 'hybrid', 'plug_in_hybrid') and not positive(model.get('tank_l')): fields.append('tank_l')
            if fuel in ('el', 'hybrid', 'plug_in_hybrid') and not positive(model.get('batteri_kwh')): fields.append('batteri_kwh')
            has_capacity = any(positive(model.get(k)) for k in ('tank_l', 'batteri_kwh'))
            known_capacity += has_capacity
            if not fuel and not has_capacity: fields.append('tank_l_or_batteri_kwh')
            if not types: unclassified.append(row)
            for kind in types: groups[kind].append(row)
            if fields: missing.append(dict(row, missing_fields=fields))
    summary = {'unique_models': sum(len(b['modeller']) for b in catalog['brands']),
               'makes': len(catalog['brands']), 'by_type': {k: len(v) for k, v in groups.items()},
               'unclassified_models': len(unclassified), 'models_with_capacity': known_capacity,
               'models_with_missing_fields': len(missing),
               'missing_fields': dict(Counter(k for row in missing for k in row['missing_fields'])),
               'cleanup_requires_review': cleanup['requires_review'],
               'note': 'Unique normalized make/model pairs, not register records. Models may occur in multiple categories.'}
    return {'summary': summary, 'categories': groups, 'unclassified': unclassified, 'missing': missing}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--require-types', action='store_true')
    args = parser.parse_args()
    result = inventory(json.loads(args.input.read_text(encoding='utf-8-sig')))
    args.output.mkdir(parents=True, exist_ok=True)
    for name in ('summary', 'unclassified', 'missing'):
        (args.output / (name + '.json')).write_text(json.dumps(result[name], ensure_ascii=False, indent=2) + '\n')
    for name, rows in result['categories'].items():
        (args.output / (name + '.json')).write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result['summary'], ensure_ascii=False, indent=2))
    if args.require_types and result['summary']['unclassified_models']:
        raise SystemExit('Missing explicit model types; inspect unclassified.json instead of guessing.')
