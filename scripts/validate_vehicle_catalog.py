#!/usr/bin/env python3
"""Validate one standalone Tiny Refuel catalog; no network required."""
import argparse
import json
import math
from pathlib import Path


def validate_catalog(data):
    if not isinstance(data, dict) or not isinstance(data.get('brands'), list):
        raise ValueError('Expected an object containing a brands list')
    if any(k in data for k in ('catalog_parts', 'catalog_schema', 'model_defaults')):
        raise ValueError('Use a single, expanded JSON catalog, not an old packaging manifest')
    makes, models, capacities = set(), 0, 0
    for brand in data['brands']:
        name = brand.get('mærke') if isinstance(brand, dict) else None
        if not isinstance(name, str) or not name.strip() or not isinstance(brand.get('modeller'), list):
            raise ValueError('Each brand needs mærke and a modeller list')
        make = name.strip().casefold()
        if make in makes: raise ValueError('Duplicate make: ' + name)
        makes.add(make)
        seen = set()
        for model in brand['modeller']:
            label = model.get('model') if isinstance(model, dict) else None
            if not isinstance(label, str) or not label.strip(): raise ValueError('Missing model in ' + name)
            key = label.strip().casefold()
            if key in seen: raise ValueError('Duplicate model: ' + name + ' ' + label)
            seen.add(key)
            known = False
            for field in ('tank_l', 'batteri_kwh'):
                value = model.get(field)
                if value is not None:
                    if not isinstance(value, (float, int)) or isinstance(value, bool) or not math.isfinite(value) or value <= 0:
                        raise ValueError('Invalid ' + field + ': ' + name + ' ' + label)
                    known = True
            if model.get('brændstof') not in (None, '', 'benzin', 'diesel', 'el', 'hybrid', 'plug_in_hybrid'):
                raise ValueError('Use a supported lowercase brændstof value, or leave it empty')
            if model.get('requires_fuel_selection') is False and not model.get('brændstof'):
                raise ValueError('requires_fuel_selection=false needs a known brændstof')
            if model.get('variants') is not None and not isinstance(model['variants'], list):
                raise ValueError('variants must be a list when present')
            models += 1
            capacities += bool(known)
    return {'makes': len(makes), 'models': models, 'models_with_capacity': capacities}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', help='Optionally write a validated compact single JSON file')
    args = parser.parse_args()
    try:
        data = json.loads(Path(args.input).read_text(encoding='utf-8-sig'))
        summary = validate_catalog(data)
        if args.output:
            Path(args.output).write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
        print(json.dumps(summary, ensure_ascii=False))
    except (ValueError, OSError) as exc:
        parser.exit(1, str(exc) + '\n')


if __name__ == '__main__':main()
