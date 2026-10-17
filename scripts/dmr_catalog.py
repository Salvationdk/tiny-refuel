#!/usr/bin/env python3
"""Build a bundled make/model catalog from DMR XML/ZIP, without vehicle identifiers."""
import argparse
from contextlib import contextmanager
from copy import deepcopy
from datetime import date
from ftplib import FTP, error_perm
import json
from pathlib import Path
import re
import sys
import tempfile
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

if __package__:
    from .vehicle_catalog import CATALOG, save_json
else:
    from vehicle_catalog import CATALOG, save_json

SOURCE = 'https://motorst.dk/erhverv/motorregistret-for-virksomheder/faa-adgang-til-motorregistret/andre-adgange'
# Shared public download credentials published by Motorstyrelsen, not a user account.
FTP_HOST = '5.44.137.84'
FTP_USER = 'dmr-ftp-user'
FTP_PASSWORD = 'dmrpassword'
# Code/name pairs verified against the full 2026-10-07 extract inspection.
KINDS = {'1', '2', '3', '4', '7', '8', '12', '16', '17', '91'}
KIND_NAMES = {'personbil', 'bus', 'varebil', 'lastbil', 'stor personbil',
              'motorcykel', 'knallert', 'stor knallert', 'lille knallert',
              'traktor', 'motorredskab', 'motorkøretøj', 'atv', 'motordrevet blokvogn'}
# Retain raw values and field names until their units and structure are verified.
TECHNICAL_FIELDS = {
    'KoeretoejOplysningModelAar', 'KoeretoejOplysningEUVariant',
    'KoeretoejOplysningEUVersion', 'KoeretoejMotorElektriskForbrug',
    'KoeretoejMotorKmPerLiter', 'KoeretoejMotorMaaleNormTypeNavn',
    'KoeretoejMotorMaaleNormTypeNummer', 'KoeretoejMotorStoersteEffekt',
    'KoeretoejMotorSlagVolumen', 'KoeretoejMotorCylinderAntal',
    'KoeretoejMotorDrivmiddelPrimaer', 'NormTypeNavn', 'NormTypeNummer',
}
FIELDS = TECHNICAL_FIELDS | {
    'KoeretoejMaerkeTypeNavn', 'KoeretoejModelTypeNavn', 'KoeretoejVariantTypeNavn',
    'KoeretoejArtNummer', 'KoeretoejArtNavn', 'DrivkraftTypeNavn',
}


def powered_kind(row):
    names = {name.casefold() for name in row.get('KoeretoejArtNavn', ())}
    # A trailer can have an auxiliary engine; a fuel field alone is insufficient.
    if any(word in name for name in names for word in
           ('påhæng', 'paahaeng', 'sættevogn', 'saettevogn', 'campingvogn', 'sidevogn')):
        return False
    return bool(row.get('KoeretoejArtNummer', set()) & KINDS or names & KIND_NAMES)

ALIASES = {'vw': 'Volkswagen', 'volkswagen': 'Volkswagen', 'mercedesbenz': 'Mercedes',
           'mercedes': 'Mercedes', 'ds': 'DS Automobiles', 'kgmobility': 'KGM'}


def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value).casefold() if c.isalnum())


def clean(value):
    return re.sub(r'\s+', ' ', value or '').strip()


def name_key(value):
    """Ignore case/spacing only; punctuation and accented letters distinguish models."""
    return clean(unicodedata.normalize('NFC', value)).casefold()


def make_key(value):
    # Only the explicit manufacturer aliases may discard punctuation.
    return name_key(ALIASES.get(normalized(value), value))


def merge_metadata(target, incoming, conflicts, context):
    """Preserve curated values; record every incompatible scalar without guessing."""
    for field, value in incoming.items():
        if field not in target or target[field] is None:
            target[field] = deepcopy(value)
        elif value is None or target[field] == value:
            continue
        elif isinstance(value, dict) and isinstance(target[field], dict):
            merge_metadata(target[field], value, conflicts, context + '.' + field)
        elif isinstance(value, list) and isinstance(target[field], list):
            for item in value:
                if item not in target[field]:
                    target[field].append(deepcopy(item))
        else:
            alternatives = target.setdefault('deduplication_alternatives', {}).setdefault(field, [])
            for item in (target[field], value):
                if item not in alternatives:
                    alternatives.append(deepcopy(item))
            conflict = {'context': context, 'field': field,
                        'kept': deepcopy(target[field]), 'alternative': deepcopy(value)}
            if conflict not in conflicts:
                conflicts.append(conflict)


def deduplicate_catalog(base):
    """Consolidate exact normalized names, retaining variants and conflicting specs."""
    result = deepcopy(base)
    brands, changes, conflicts = {}, [], []
    before_models = sum(len(b['modeller']) for b in base['brands'])
    for original in result['brands']:
        brand = deepcopy(original)
        brand['mærke'] = clean(brand['mærke'])
        key = make_key(brand['mærke'])
        if key not in brands:
            brands[key] = brand
        else:
            target = brands[key]
            changes.append({'type': 'make', 'from': brand['mærke'], 'into': target['mærke']})
            target.setdefault('source_names', [])
            for n in [brand['mærke']] + brand.get('source_names', []):
                if n != target['mærke'] and n not in target['source_names']:
                    target['source_names'].append(n)
            incoming = {k: v for k, v in brand.items() if k not in {'mærke', 'modeller', 'source_names'}}
            merge_metadata(target, incoming, conflicts, target['mærke'])
            target['modeller'].extend(brand['modeller'])
    for brand in brands.values():
        models = {}
        for original in brand['modeller']:
            model = deepcopy(original)
            model['model'] = clean(model['model'])
            key = name_key(model['model'])
            if key not in models:
                models[key] = model
            else:
                target = models[key]
                changes.append({'type': 'model', 'make': brand['mærke'],
                                'from': model['model'], 'into': target['model']})
                target.setdefault('source_names', [])
                for n in [model['model']] + model.get('source_names', []):
                    if n != target['model'] and n not in target['source_names']:
                        target['source_names'].append(n)
                merge_metadata(target, {k: v for k, v in model.items()
                                       if k not in {'model', 'source_names'}},
                               conflicts, brand['mærke'] + '/' + target['model'])
        for model in models.values():
            variants = {}
            for original in model.get('variants', []):
                variant = deepcopy(original)
                variant['name'] = clean(variant['name'])
                key = name_key(variant['name'])
                if key not in variants:
                    variants[key] = variant
                else:
                    merge_metadata(variants[key], {k: v for k, v in variant.items() if k != 'name'},
                                   conflicts, brand['mærke'] + '/' + model['model'] + '/' + variant['name'])
            if 'variants' in model:
                model['variants'] = sorted(variants.values(), key=lambda x: name_key(x['name']))
            if 'dmr_profiles' in model:
                profiles = {json.dumps(x, ensure_ascii=False, sort_keys=True): x
                            for x in model['dmr_profiles']}
                model['dmr_profiles'] = [profiles[k] for k in sorted(profiles)]
        brand['modeller'] = sorted(models.values(), key=lambda x: name_key(x['model']))
    result['brands'] = sorted(brands.values(), key=lambda b: name_key(b['mærke']))
    report = {'makes_before': len(base['brands']), 'makes_after': len(result['brands']),
              'models_before': before_models,
              'models_after': sum(len(b['modeller']) for b in result['brands']),
              'merges': changes, 'conflicts': conflicts,
              'requires_review': bool(conflicts),
              'policy': 'Case, whitespace and NFC only; explicit make aliases. Punctuation and accents preserved. No fuzzy matching.'}
    return result, report


def download_latest(destination, ftp_factory=FTP):
    """Retry interrupted transfers with FTP REST; never replace a valid local file."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    name = None
    with tempfile.NamedTemporaryFile('wb', dir=destination.parent, delete=False) as handle:
        temporary = Path(handle.name)
    try:
        for attempt in range(1, 4):
            try:
                print(f'DMR: connection attempt {attempt}/3', file=sys.stderr, flush=True)
                with ftp_factory(FTP_HOST, timeout=180) as ftp:
                    ftp.login(FTP_USER, FTP_PASSWORD)
                    ftp.cwd('ESStatistikListeModtag')
                    if name is None:
                        names = [item.rsplit('/', 1)[-1] for item in ftp.nlst()]
                        names = [item for item in names if re.fullmatch(r'ESStatistikListeModtag-\d{8}-\d{6}\.zip', item)]
                        if not names:
                            raise ValueError('No official DMR archive found; existing file left untouched')
                        name = max(names)
                    offset = temporary.stat().st_size
                    print(f'DMR: {name}; starting at {offset // (1024 * 1024)} MiB', file=sys.stderr, flush=True)
                    with temporary.open('ab') as handle:
                        transferred = offset
                        last_report = offset

                        def write_chunk(chunk):
                            nonlocal transferred, last_report
                            handle.write(chunk)
                            transferred += len(chunk)
                            if transferred - last_report >= 64 * 1024 * 1024:
                                print(f'DMR: downloaded {transferred // (1024 * 1024)} MiB', file=sys.stderr, flush=True)
                                last_report = transferred

                        try:
                            kwargs = {'rest': offset} if offset else {}
                            ftp.retrbinary('RETR ' + name, write_chunk, blocksize=1024 * 1024, **kwargs)
                        except error_perm:
                            if not offset:
                                raise
                            # Some servers reject REST: reconnect and restart on next attempt.
                            handle.close()
                            temporary.write_bytes(b'')
                            raise
                break
            except (OSError, EOFError, error_perm) as exc:
                print(f'DMR: transfer interrupted ({type(exc).__name__}); saved {temporary.stat().st_size // (1024 * 1024)} MiB', file=sys.stderr, flush=True)
                if attempt == 3:
                    raise
        with zipfile.ZipFile(temporary) as archive:
            if not any(info.filename.lower().endswith('.xml') for info in archive.infolist()):
                raise ValueError('Downloaded ZIP contains no XML')
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return name


@contextmanager
def input_xml(path):
    """Read compressed XML directly; never unpack the huge file onto disk."""
    path = Path(path)
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            members = [info for info in archive.infolist() if info.filename.lower().endswith('.xml')]
            if len(members) != 1:
                raise ValueError('Expected exactly one XML member in DMR ZIP')
            with archive.open(members[0]) as stream:
                yield stream
    else:
        with path.open('rb') as stream:
            yield stream


def iter_records(stream):
    """Keep at most one Statistik subtree; discard every record after extraction."""
    stack = []
    for event, element in ET.iterparse(stream, events=('start', 'end')):
        if event == 'start':
            stack.append(element)
            continue
        if element.tag.rsplit('}', 1)[-1] == 'Statistik':
            values = {}
            for child in element.iter():
                tag = child.tag.rsplit('}', 1)[-1]
                if tag in FIELDS and clean(child.text):
                    values.setdefault(tag, set()).add(clean(child.text))
            yield values
            element.clear()
            if len(stack) > 1:
                stack[-2].remove(element)
        stack.pop()


def build_catalog(stream, base, source_date, source_file, limit=None, include_profiles=True):
    """Preserve curated specs; aggregate names/variants, never individual vehicles."""
    date.fromisoformat(source_date)
    result, cleanup = deduplicate_catalog(base)
    brands = {make_key(row['mærke']): row for row in result['brands']}
    indexes = {key: {name_key(model['model']): model for model in brand['modeller']}
               for key, brand in brands.items()}
    variants = {}
    profiles = {}
    records = included = skipped = added_models = added_brands = 0
    for row in iter_records(stream):
        if limit is not None and records >= limit:
            break
        records += 1
        if records % 100000 == 0:
            print(f'DMR: processed {records:,} records', file=sys.stderr, flush=True)
        if not powered_kind(row):
            skipped += 1
            continue
        makes, models = row.get('KoeretoejMaerkeTypeNavn', set()), row.get('KoeretoejModelTypeNavn', set())
        if len(makes) != 1 or len(models) != 1:
            skipped += 1
            continue
        make, model = next(iter(makes)), next(iter(models))
        if len(make) > 100 or len(model) > 200 or model.casefold() in {'uoplyst', 'ukendt', 'unknown', '-'}:
            skipped += 1
            continue
        key = make_key(make)
        if key not in brands:
            brand = {'mærke': make, 'modeller': []}
            result['brands'].append(brand)
            brands[key], indexes[key] = brand, {}
            added_brands += 1
        index, brand = indexes[key], brands[key]
        model_key = name_key(model)
        if model_key not in index:
            entry = {'model': model, 'brændstof': None, 'tank_l': None,
                     'requires_fuel_selection': True, 'source_url': SOURCE,
                     'specification_note': 'Registermodel: vælg drivmiddel, årgang/variant og kontrollér tank/batteri.'}
            index[model_key] = entry
            brand['modeller'].append(entry)
            added_models += 1
        included += 1
        entry = index[model_key]
        if model != entry['model']:
            names = entry.setdefault('source_names', [])
            if model not in names:
                names.append(model)
        entry['fuel_types'] = sorted(set(entry.get('fuel_types', [])) | row.get('DrivkraftTypeNavn', set()))
        entry['model_years'] = sorted(set(entry.get('model_years', [])) | row.get('KoeretoejOplysningModelAar', set()))
        # Only explicitly allowlisted model-level facts leave the record parser.
        entry_key = (key, model_key)
        # Keep each observed combination intact, rather than cross-combining years,
        # engine figures, fuel types or measurement norms across vehicles.
        if include_profiles:
            profile = {field: sorted(row[field]) for field in
                       sorted(TECHNICAL_FIELDS | {'KoeretoejArtNummer', 'KoeretoejArtNavn',
                                                  'DrivkraftTypeNavn', 'KoeretoejVariantTypeNavn'})
                       if row.get(field)}
            signature = json.dumps(profile, ensure_ascii=False, sort_keys=True)
            profiles.setdefault(entry_key, {})[signature] = profile
        for variant in row.get('KoeretoejVariantTypeNavn', set()):
            if len(variant) > 200 or variant.casefold() in {'uoplyst', 'ukendt', '-'}:
                continue
            bucket = variants.setdefault(entry_key, {})
            bucket.setdefault(variant, set()).update(row.get('DrivkraftTypeNavn', set()))
    if not records or not included:
        raise ValueError('No usable DMR records; catalog not replaced')
    for (key, model_key), values in variants.items():
        entry = indexes[key][model_key]
        existing = {variant['name']: variant for variant in entry.get('variants', [])}
        for name, fuels in values.items():
            previous = existing.get(name, {})
            existing[name] = {**previous, 'name': name,
                              'fuel_types': sorted(set(previous.get('fuel_types', [])) | fuels)}
        entry['variants'] = sorted(existing.values(), key=lambda row: row['name'].casefold())
    for (key, model_key), values in profiles.items():
        entry = indexes[key][model_key]
        existing = {json.dumps(p, ensure_ascii=False, sort_keys=True): p
                    for p in entry.get('dmr_profiles', [])}
        existing.update(values)
        entry['dmr_profiles'] = [existing[k] for k in sorted(existing)]
    for brand in result['brands']:
        brand['modeller'].sort(key=lambda row: row['model'].casefold())
    result['brands'].sort(key=lambda row: row['mærke'].casefold())
    report = {'source_url': SOURCE, 'source_date': source_date, 'source_file': Path(source_file).name,
              'processed_records': records, 'included_records': included, 'skipped_records': skipped,
              'added_makes': added_brands, 'added_models': added_models,
              'makes': len(result['brands']), 'models': sum(len(row['modeller']) for row in result['brands']),
              'identifier_fields_exported': False,
              'sample_limit': limit,
              'deduplication': cleanup,
              'technical_profiles_included': include_profiles,
              'technical_values': 'Raw source fields; units not inferred; not used as confirmed tank, battery or consumption specifications.',
              'scope': 'DMR powered kinds 1,2,3,4,7,8,12,16,17,91 plus recognized powered kind names; unknown kinds and unpowered trailers excluded. Historical records included; not every future model or specification.'}
    result, final_cleanup = deduplicate_catalog(result)
    report['deduplication']['variant_conflicts'] = final_cleanup['conflicts']
    report['deduplication']['requires_review'] = bool(cleanup['conflicts'] or final_cleanup['conflicts'])
    report['unique_profiles'] = sum(len(m.get('dmr_profiles', [])) for b in result['brands'] for m in b['modeller'])
    result['dmr_catalog'] = report
    return result, report


def inspect_archive(path, limit=None):
    """Aggregate only allowlisted technical values; never export whole records."""
    kinds, samples = {}, {}
    count = 0
    with input_xml(path) as stream:
        for row in iter_records(stream):
            count += 1
            kind = json.dumps([sorted(row.get('KoeretoejArtNummer', [])),
                               sorted(row.get('KoeretoejArtNavn', []))], ensure_ascii=False)
            kinds[kind] = kinds.get(kind, 0) + 1
            for field in sorted(TECHNICAL_FIELDS | {'DrivkraftTypeNavn'}):
                bucket = samples.setdefault(field, set())
                # Bounded deterministic examples, independent of record count.
                bucket.update(row.get(field, ()))
                if len(bucket) > 20:
                    samples[field] = set(sorted(bucket)[:20])
            if count % 100000 == 0:
                print(f'DMR: inspected {count:,} records', file=sys.stderr, flush=True)
            if limit is not None and count >= limit:
                break
    return {'processed_records': count, 'sample_limit': limit,
            'vehicle_kinds': [{'codes': json.loads(k)[0], 'names': json.loads(k)[1],
                               'records': n} for k, n in sorted(kinds.items())],
            'technical_value_examples': {k: sorted(v) for k, v in sorted(samples.items())},
            'identifier_fields_exported': False,
            'note': 'Raw values only; samples do not establish units or complete coverage.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    download = commands.add_parser('download')
    download.add_argument('--output', type=Path, required=True)
    build = commands.add_parser('build')
    build.add_argument('--input', type=Path, required=True)
    build.add_argument('--source-date', required=True)
    build.add_argument('--source-file', help='Original official archive name')
    build.add_argument('--base', type=Path, default=CATALOG)
    build.add_argument('--output', type=Path, required=True)
    build.add_argument('--report', type=Path, required=True)
    build.add_argument('--limit', type=int, help='First N records only; omit for full catalog')
    build.add_argument('--include-technical-profiles', action='store_true',
                       help='Large research export; omit for a compact UI catalog')
    dedup = commands.add_parser('deduplicate')
    dedup.add_argument('--input', type=Path, required=True)
    dedup.add_argument('--output', type=Path, required=True)
    dedup.add_argument('--report', type=Path, required=True)
    inspect = commands.add_parser('inspect')
    inspect.add_argument('--input', type=Path, required=True)
    inspect.add_argument('--output', type=Path, required=True)
    inspect.add_argument('--limit', type=int)
    args = parser.parse_args()
    if args.command in {'build', 'deduplicate'}:
        protected = {args.input.resolve()}
        if args.command == 'build':
            protected.add(args.base.resolve())
            if args.limit is not None and args.limit < 1:
                parser.error('--limit must be positive')
        if args.output.resolve() in protected or args.report.resolve() in protected or args.report.resolve() == args.output.resolve():
            parser.error('Input, base, output and report must be separate files')
    if args.command == 'download':
        print(download_latest(args.output))
    elif args.command == 'deduplicate':
        base = json.loads(args.input.read_text(encoding='utf-8-sig'))
        catalog, report = deduplicate_catalog(base)
        save_json(args.output, catalog)
        save_json(args.report, report)
        print(json.dumps({k: v for k, v in report.items() if k not in {'merges', 'conflicts'}}, ensure_ascii=False, indent=2))
    elif args.command == 'inspect':
        if args.limit is not None and args.limit < 1:
            parser.error('--limit must be positive')
        if args.output.resolve() == args.input.resolve():
            parser.error('Output must not overwrite the input archive')
        report = inspect_archive(args.input, args.limit)
        save_json(args.output, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        if args.output.resolve() in {args.input.resolve(), args.base.resolve()}:
            parser.error('Write a separate candidate file; review it before replacing the shipped catalog')
        base = json.loads(args.base.read_text(encoding='utf-8'))
        with input_xml(args.input) as stream:
            catalog, report = build_catalog(stream, base, args.source_date, args.source_file or args.input.name, limit=args.limit, include_profiles=args.include_technical_profiles)
        save_json(args.output, catalog)
        save_json(args.report, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
