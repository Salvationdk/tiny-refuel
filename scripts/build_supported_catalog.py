"""Build the bundled catalog from models with a known capacity, excluding motor tools."""
import argparse
from copy import deepcopy
import json
import math
import unicodedata
import tempfile
from pathlib import Path

if __package__:
    from .vehicle_catalog import load_catalog
    from .package_vehicle_catalog import package
else:
    from vehicle_catalog import load_catalog
    from package_vehicle_catalog import package


def positive(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def supported_catalog(data):
    result = deepcopy(data)
    original_models = sum(len(b['modeller']) for b in data['brands'])
    removed_missing = removed_tools = 0
    kept = []
    for brand in result['brands']:
        models = []
        for model in brand['modeller']:
            types = model.get('vehicle_types', []) or []
            if not isinstance(types, list): types = [types]
            types = list(types) + [model.get('koeretoejstype', ''), model.get('vehicle_type', '')]
            if any(str(t).strip().casefold() in ('motorredskab', '12') for t in types):
                removed_tools += 1
                continue
            if not any(positive(model.get(field)) for field in ('tank_l', 'batteri_kwh')):
                removed_missing += 1
                continue
            models.append(model)
        if models:
            brand['modeller'] = models
            kept.append(brand)
    result['brands'] = kept
    norm = lambda value: ''.join(c for c in unicodedata.normalize('NFKD', value).casefold() if c.isalnum())
    assets = {norm(name): name for field in ('logos', 'logo_pngs', 'logo_urls') for name in result.get(field, {})}
    for alias, target in result.get('logo_aliases', {}).items():
        if norm(target) in assets: assets[norm(alias)] = target
    covered = sum(norm(brand['mærke']) in assets for brand in kept)
    pending_combined = sum(norm(brand['mærke']) not in assets and '/' in brand['mærke'] for brand in kept)
    result['logo_coverage'] = dict(result.get('logo_coverage', {}), scope='Capacity-filtered bundled catalog',
        register_makes=len(kept), covered=covered, pending=len(kept) - covered,
        pending_combined=pending_combined, pending_single_names=len(kept) - covered - pending_combined)
    result['capacity_filter'] = {'original_models': original_models, 'models': sum(len(b['modeller']) for b in kept),
        'makes': len(kept), 'excluded_missing_capacity': removed_missing, 'excluded_motor_tools': removed_tools,
        'note': 'Only models with a positive catalog tank_l or batteri_kwh. Values remain model-level and require checking for the exact year/variant.'}
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = supported_catalog(load_catalog(args.input))
    with tempfile.TemporaryDirectory() as directory:
        plain = Path(directory) / 'supported-catalog-source.json'
        plain.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
        package(plain, args.output)
    print(json.dumps(result['capacity_filter'], ensure_ascii=False))
