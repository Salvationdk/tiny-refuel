"""Merge reviewed manufacturer specifications into a catalog, preserving existing models."""
from copy import deepcopy
import json
from pathlib import Path

ADDITIONS = Path(__file__).parent / 'data' / 'vehicle-model-additions-2026-10-types.json'


def add_reviewed_models(catalog):
    data = deepcopy(catalog)
    brands = {b['mærke'].casefold(): b for b in data['brands']}
    additions = json.loads(ADDITIONS.read_text())['models']
    for row in additions:
        entry = deepcopy(row)
        make = entry.pop('make')
        brand = brands.get(make.casefold())
        if brand is None:
            brand = {'mærke': make, 'modeller': []}
            data['brands'].append(brand)
            brands[make.casefold()] = brand
        if not any(m['model'].casefold() == entry['model'].casefold() for m in brand['modeller']):
            brand['modeller'].append(entry)
            brand['modeller'].sort(key=lambda m: m['model'].casefold())
    data['brands'].sort(key=lambda b: b['mærke'].casefold())
    count = sum(len(b['modeller']) for b in data['brands'])
    if 'capacity_filter' in data:
        data['capacity_filter'].update(models=count, makes=len(data['brands']))
        data['capacity_filter']['note'] = 'Models/makes include reviewed additions; original/excluded counts describe the original source filter. Positive capacities are specific to the documented configuration.'
    data['reviewed_model_additions'] = {'source': ADDITIONS.name, 'reviewed_at': '2026-10-19',
        'models': len(additions), 'policy': 'Explicit configurations only; existing rows preserved.'}
    return data


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = add_reviewed_models(json.loads(Path(args.catalog).read_text(encoding='utf-8-sig')))
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n')
