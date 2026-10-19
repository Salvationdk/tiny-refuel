#!/usr/bin/env python3
"""Review collected specifications locally; never approve or edit a catalog automatically."""
import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
import math
from pathlib import Path
import unicodedata


def identity(value):
    return ' '.join(unicodedata.normalize('NFKC', str(value or '')).casefold().split())


def number(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def scope(row):
    # Missing scope is unknown, never equivalent to all years or variants.
    return {'year': row.get('year'), 'year_start': row.get('year_start'), 'year_end': row.get('year_end'),
            'generation': row.get('generation'), 'variant': row.get('variant'), 'trim': row.get('trim'),
            'markets': sorted(row.get('markets') or [])}


def normalized_scope(value):
    return {k: sorted(identity(v) for v in item) if isinstance(item, list) else identity(item)
            for k, item in value.items()}


def review(rows):
    if not isinstance(rows, list):
        raise ValueError('Expected a JSON list of candidates')
    groups, models, provenance, rejected = {}, {}, {}, []
    duplicates = 0
    sources = Counter()
    for index, row in enumerate(rows):
        rid = 'candidate-' + str(index + 1)
        if not isinstance(row, dict) or not isinstance(row.get('make'), str) or not row['make'].strip() or not isinstance(row.get('model'), str) or not row['model'].strip():
            rejected.append({'candidate_id': rid, 'reason': 'missing_identity'})
            continue
        specs = row.get('specifications')
        if not isinstance(specs, dict):
            rejected.append({'candidate_id': rid, 'reason': 'invalid_specifications'})
            continue
        fields = {}
        for field, value in specs.items():
            if field in ('tank_l', 'batteri_kwh') and number(value):
                name = field if field == 'tank_l' else 'battery_' + str(row.get('battery_basis') or 'unspecified') + '_kwh'
                fields[name] = value
            elif field == 'brændstof' and value in ('Benzin', 'Diesel', 'El', 'Hybrid', 'Plug-in hybrid', 'LPG', 'CNG', 'Brint'):
                fields[field] = value
            else:
                rejected.append({'candidate_id': rid, 'field': field, 'reason': 'unsupported_or_invalid_value'})
        for label, value in row.get('battery_capacities', {}).items():
            if label in ('net_kwh', 'gross_kwh') and number(value):
                fields['battery_' + ('usable' if label == 'net_kwh' else 'gross') + '_kwh'] = value
        if not fields:
            continue
        if fields.get('battery_usable_kwh', 0) > fields.get('battery_gross_kwh', float('inf')):
            rejected.append({'candidate_id': rid, 'reason': 'net_exceeds_gross'})
            continue
        source = row.get('dataset', {}).get('repository') or row.get('parser') or 'unknown'
        sources[source] += 1
        provenance[rid] = {'input_index': index, 'source_url': row.get('source_url'),
            'sources': row.get('sources', []), 'dataset': row.get('dataset'),
            'source_quality': row.get('source_quality'), 'evidence': row.get('evidence'),
            'retrieved_at': row.get('retrieved_at'), 'page_sha256': row.get('page_sha256'),
            'scope_note': row.get('scope_note')}
        pair = identity(row['make']), identity(row['model'])
        current_scope = scope(row)
        sid = json.dumps([pair, normalized_scope(current_scope)], sort_keys=True)
        group = groups.setdefault(sid, {'make': row['make'], 'model': row['model'], 'scope': current_scope,
                'fields': {}, 'candidate_ids': [], 'review_status': 'pending', 'approved_for_import': False})
        already = {field: list(values) for field, values in group['fields'].items()}
        for field, value in fields.items():
            bucket = group['fields'].setdefault(field, [])
            if value not in bucket:
                bucket.append(value)
        # A repeated candidate adds provenance, not an extra proposed variant.
        if group['candidate_ids'] and already == group['fields']:
            duplicates += 1
        group['candidate_ids'].append(rid)
        model = models.setdefault(pair, {'make': row['make'], 'model': row['model'], 'observed_values': {},
                                         'candidate_count': 0, 'scope_count': 0})
        model['candidate_count'] += 1
        for field, value in fields.items():
            bucket = model['observed_values'].setdefault(field, [])
            if value not in bucket: bucket.append(value)
    conflicts, proposals = [], []
    for key, group in groups.items():
        group['scope_id'] = sha256(key.encode()).hexdigest()[:20]
        group['conflicting_fields'] = [field for field, values in group['fields'].items() if len(values) > 1]
        models[(identity(group['make']), identity(group['model']))]['scope_count'] += 1
        if group['conflicting_fields']:
            conflicts.append(group)
        else:
            proposals.append({**group, 'proposed_fields': {k: v[0] for k, v in group['fields'].items()}})
    model_rows = sorted(models.values(), key=lambda r: (identity(r['make']), identity(r['model'])))
    for model in model_rows:
        model['fields_with_multiple_observed_values'] = [k for k, values in model['observed_values'].items() if len(values) > 1]
        model['single_value_fields'] = {k: v[0] for k, v in model['observed_values'].items() if len(v) == 1}
        model['single_value_is_not_verified'] = True
    summary = {'input_rows': len(rows), 'models': len(models), 'scope_groups': len(groups),
        'non_conflicting_scope_groups': len(proposals), 'conflicting_scope_groups': len(conflicts),
        'rejected_field_or_row_issues': len(rejected), 'repeated_or_redundant_scope_rows': duplicates,
        'models_with_multiple_observed_values': sum(bool(m['fields_with_multiple_observed_values']) for m in model_rows),
        'models_with_only_single_observed_values': sum(not m['fields_with_multiple_observed_values'] for m in model_rows),
        'source_rows': dict(sources), 'approved_for_automatic_import': 0,
        'note': 'A single observed value is not proof for every year/variant. All proposals remain pending review.'}
    return {'summary.json': summary, 'variant-import-proposal.json': proposals, 'scope-conflicts.json': conflicts,
            'model-summary.json': model_rows, 'rejected.json': rejected, 'provenance.json': provenance}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', default='review-results')
    args = parser.parse_args()
    raw = Path(args.input).read_bytes()
    reports = review(json.loads(raw.decode('utf-8-sig')))
    reports['summary.json']['input_sha256'] = sha256(raw).hexdigest()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    for name, data in reports.items():
        (out / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(reports['summary.json'], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
