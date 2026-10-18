"""Package a small model index with immutable model details loaded on demand."""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def write_asset(directory, value, suffix):
    text = compact(value) if not isinstance(value, str) else value
    name = hashlib.sha256(text.encode('utf-8')).hexdigest()[:24] + suffix
    directory.mkdir(exist_ok=True)
    (directory / name).write_text(text, encoding='utf-8')
    return directory.name + '/' + name


def package(source, target):
    data = json.loads(Path(source).read_text(encoding='utf-8'))
    base = deepcopy(data)
    target = Path(target)
    defaults = {'requires_fuel_selection': True, 'brændstof': None, 'tank_l': None}
    models = [m for b in data.get('brands', []) for m in b['modeller']]
    for field in ('source_url', 'specification_note'):
        counts = Counter(m[field] for m in models if isinstance(m.get(field), str))
        if counts: defaults[field] = counts.most_common(1)[0][0]
    base['catalog_schema'] = 2
    base['model_defaults'] = defaults
    for original, brand in zip(data.get('brands', []), base.get('brands', [])):
        brand['modeller'] = []
        brand['detail_files'] = []
        batch, start, batch_size = [], 0, 2

        def flush():
            nonlocal batch, start, batch_size
            if not batch: return
            file = write_asset(target.parent / 'catalog-details', batch, '.json')
            brand['detail_files'].append({'start': start, 'file': file})
            start += len(batch)
            batch, batch_size = [], 2

        for model in original['modeller']:
            uses_defaults = all(field in model and model[field] == value for field, value in defaults.items())
            entry = {k: deepcopy(v) for k, v in model.items()
                     if k in ('model', 'source_names', 'brændstof', 'tank_l', 'batteri_kwh', 'requires_fuel_selection', 'specification_note')}
            if uses_defaults:
                for field in defaults: entry.pop(field, None)
            else:
                entry['_no_defaults'] = True
            brand['modeller'].append(entry)
            detail = {k: deepcopy(v) for k, v in model.items() if k not in entry and (not uses_defaults or k not in defaults)}
            # Absent keys stay absent; all original detail values survive reconstruction.
            detail_size = len(compact(detail).encode('utf-8')) + 1
            if batch and batch_size + detail_size > 300000: flush()
            batch.append(detail)
            batch_size += detail_size
        flush()
    text = compact(base)
    parts = [write_asset(target.parent / 'catalog-parts', text[offset:offset + 350000], '.txt')
             for offset in range(0, len(text), 350000)]
    target.write_text(json.dumps({'catalog_parts': parts}, indent=2) + '\n', encoding='utf-8')
    # Delete only assets from this packager's own directories after the new index exists.
    keep = set(parts) | {item['file'] for b in base.get('brands', []) for item in b.get('detail_files', [])}
    for name in ('catalog-parts', 'catalog-details'):
        directory = target.parent / name
        if directory.exists():
            for asset in directory.iterdir():
                if directory.name + '/' + asset.name not in keep: asset.unlink()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('target')
    args = parser.parse_args()
    package(args.source, args.target)
