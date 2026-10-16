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
KINDS = {'1', '2', '3', '4'}  # DMR personbiler/busser, varebiler and lastbiler.
KIND_NAMES = {'personbil', 'bus', 'varebil', 'lastbil', 'stor personbil'}
ALIASES = {'vw': 'Volkswagen', 'volkswagen': 'Volkswagen', 'mercedesbenz': 'Mercedes',
           'mercedes': 'Mercedes', 'ds': 'DS Automobiles', 'kgmobility': 'KGM'}


def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value).casefold() if c.isalnum())


def clean(value):
    return re.sub(r'\s+', ' ', value or '').strip()


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
    fields = {'KoeretoejMaerkeTypeNavn', 'KoeretoejModelTypeNavn', 'KoeretoejVariantTypeNavn',
              'KoeretoejArtNummer', 'KoeretoejArtNavn', 'DrivkraftTypeNavn'}
    stack = []
    for event, element in ET.iterparse(stream, events=('start', 'end')):
        if event == 'start':
            stack.append(element)
            continue
        if element.tag.rsplit('}', 1)[-1] == 'Statistik':
            values = {}
            for child in element.iter():
                tag = child.tag.rsplit('}', 1)[-1]
                if tag in fields and clean(child.text):
                    values.setdefault(tag, set()).add(clean(child.text))
            yield values
            element.clear()
            if len(stack) > 1:
                stack[-2].remove(element)
        stack.pop()


def build_catalog(stream, base, source_date, source_file):
    """Preserve curated specs; aggregate names/variants, never individual vehicles."""
    date.fromisoformat(source_date)
    result = deepcopy(base)
    brands = {normalized(row['mærke']): row for row in result['brands']}
    aliases = {key: normalized(value) for key, value in ALIASES.items()}
    indexes = {key: {normalized(model['model']): model for model in brand['modeller']}
               for key, brand in brands.items()}
    variants = {}
    records = included = skipped = added_models = added_brands = 0
    for row in iter_records(stream):
        records += 1
        kind = row.get('KoeretoejArtNummer', set())
        kind_name = {name.casefold() for name in row.get('KoeretoejArtNavn', set())}
        if not (kind & KINDS or kind_name & KIND_NAMES):
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
        key = aliases.get(normalized(make), normalized(make))
        if key not in brands:
            brand = {'mærke': make, 'modeller': []}
            result['brands'].append(brand)
            brands[key], indexes[key] = brand, {}
            added_brands += 1
        index, brand = indexes[key], brands[key]
        model_key = normalized(model)
        if model_key not in index:
            entry = {'model': model, 'brændstof': None, 'tank_l': None,
                     'requires_fuel_selection': True, 'source_url': SOURCE,
                     'specification_note': 'Registermodel: vælg drivmiddel, årgang/variant og kontrollér tank/batteri.'}
            index[model_key] = entry
            brand['modeller'].append(entry)
            added_models += 1
        included += 1
        # Only explicitly allowlisted model-level facts leave the record parser.
        entry_key = (key, model_key)
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
    for brand in result['brands']:
        brand['modeller'].sort(key=lambda row: row['model'].casefold())
    result['brands'].sort(key=lambda row: row['mærke'].casefold())
    report = {'source_url': SOURCE, 'source_date': source_date, 'source_file': Path(source_file).name,
              'processed_records': records, 'included_records': included, 'skipped_records': skipped,
              'added_makes': added_brands, 'added_models': added_models,
              'makes': len(result['brands']), 'models': sum(len(row['modeller']) for row in result['brands']),
              'identifier_fields_exported': False,
              'scope': 'DMR vehicle kinds 1-4; records present in the supplied extract, including historic records; not every future model or specification.'}
    result['dmr_catalog'] = report
    return result, report


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
    args = parser.parse_args()
    if args.command == 'download':
        print(download_latest(args.output))
    else:
        if args.output.resolve() in {args.input.resolve(), args.base.resolve()}:
            parser.error('Write a separate candidate file; review it before replacing the shipped catalog')
        base = json.loads(args.base.read_text(encoding='utf-8'))
        with input_xml(args.input) as stream:
            catalog, report = build_catalog(stream, base, args.source_date, args.source_file or args.input.name)
        save_json(args.output, catalog)
        save_json(args.report, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
