"""DMR import tests use synthetic public-field shapes, never real vehicle records."""
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock
import xml.etree.ElementTree as ET
import zipfile

from scripts import dmr_catalog as dmr


def record(make='VW', model='GOLF', kind='1', variant='1.6 TDI', fuel='Diesel'):
    # Identifier tags deliberately exercise the export allowlist.
    return f'''<ns:Statistik><ns:KoeretoejIdent>PRIVATE_ID</ns:KoeretoejIdent>
      <ns:RegistreringNummerNummer>PRIVATE_PLATE</ns:RegistreringNummerNummer>
      <ns:KoeretoejOplysningStelNummer>PRIVATE_VIN</ns:KoeretoejOplysningStelNummer>
      <ns:KoeretoejArtNummer>{kind}</ns:KoeretoejArtNummer>
      <ns:KoeretoejOplysningGrundStruktur><ns:KoeretoejBetegnelseStruktur>
      <ns:KoeretoejMaerkeTypeNavn>{make}</ns:KoeretoejMaerkeTypeNavn>
      <ns:Model><ns:KoeretoejModelTypeNavn>{model}</ns:KoeretoejModelTypeNavn></ns:Model>
      <ns:Variant><ns:KoeretoejVariantTypeNavn>{variant}</ns:KoeretoejVariantTypeNavn></ns:Variant>
      </ns:KoeretoejBetegnelseStruktur></ns:KoeretoejOplysningGrundStruktur>
      <ns:DrivkraftTypeNavn>{fuel}</ns:DrivkraftTypeNavn></ns:Statistik>'''


def xml(*records):
    return ('<ns:ESStatistikListeModtag xmlns:ns="http://skat.dk/dmr/2007/05/31/">' + ''.join(records) + '</ns:ESStatistikListeModtag>').encode()


def base():
    return {'brands': [{'mærke': 'Volkswagen', 'modeller': [{'model': 'Golf', 'brændstof': 'diesel', 'tank_l': 50}]}],
            'logos': {'Volkswagen': 'SVG'}, 'custom_metadata': {'keep': True}}


class DmrCatalogTests(unittest.TestCase):
    def test_names_aliases_variants_and_all_road_car_kinds_without_identifiers(self):
        original = base()
        payload = xml(record(), record(), record('MERCEDES-BENZ', 'SPRINTER', '3'),
                      record('IVECO', 'DAILY', '4'), record('VOLKSWAGEN', 'CRAFTER', '2'),
                      record('TRAILER', 'DROP', '5'), record('UNKNOWN', 'DROP', '999'))
        result, report = dmr.build_catalog(BytesIO(payload), original, '2026-10-16', 'ESStatistikListeModtag-20261016-000000.zip')
        self.assertEqual(report['processed_records'], 7)
        self.assertEqual(report['included_records'], 5)
        self.assertEqual(report['added_models'], 3)
        self.assertEqual(report['added_makes'], 2)
        self.assertEqual(len(result['brands']), 3)
        vw = next(b for b in result['brands'] if b['mærke'] == 'Volkswagen')
        golf = next(m for m in vw['modeller'] if m['model'] == 'Golf')
        self.assertEqual(golf['tank_l'], 50)
        self.assertEqual(golf['variants'], [{'name': '1.6 TDI', 'fuel_types': ['Diesel'], 'model_years': []}])
        self.assertEqual(result['logos'], original['logos'])
        self.assertEqual(len(original['brands']), 1)
        self.assertNotIn('PRIVATE', json.dumps(result))
        self.assertNotIn('RegistreringNummer', json.dumps(result))
        self.assertFalse(report['identifier_fields_exported'])
        new = next(b for b in result['brands'] if b['mærke'] == 'IVECO')['modeller'][0]
        self.assertIsNone(new['brændstof'])
        self.assertIsNone(new['tank_l'])
        self.assertTrue(new['requires_fuel_selection'])

    def test_truncated_or_empty_xml_and_unknown_layout_fail_before_replacing_catalog(self):
        for payload in (b'<root/>', xml(record(kind='999')), b'<root><Statistik>'):
            with self.assertRaises((ValueError, ET.ParseError)):
                dmr.build_catalog(BytesIO(payload), base(), '2026-10-16', 'input.xml')

    def test_zip_is_streamed_without_extracting_and_duplicates_are_not_repeated(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'extract.zip'
            with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('ESStatistikListeModtag.xml', xml(record(), record()))
            with dmr.input_xml(path) as stream:
                result, _ = dmr.build_catalog(stream, base(), '2026-10-16', path.name)
            self.assertEqual(list(Path(folder).iterdir()), [path])
            self.assertEqual(sum(len(b['modeller']) for b in result['brands']), 1)

    def test_powered_types_profiles_and_inspection_are_bounded_and_identifier_free(self):
        motorcycle = record('HONDA', 'CB500', '999').replace(
            '</ns:Statistik>', '<ns:KoeretoejArtNavn>Motorcykel</ns:KoeretoejArtNavn>'
            '<ns:KoeretoejOplysningModelAar>2020</ns:KoeretoejOplysningModelAar>'
            '<ns:KoeretoejMotorKmPerLiter>25.0</ns:KoeretoejMotorKmPerLiter></ns:Statistik>')
        later = motorcycle.replace('2020', '2022').replace('25.0', '27.0')
        trailer = record('TRAILER', 'DROP', '999').replace('</ns:Statistik>',
            '<ns:KoeretoejArtNavn>Påhængsvogn</ns:KoeretoejArtNavn></ns:Statistik>')
        result, report = dmr.build_catalog(BytesIO(xml(motorcycle, later, motorcycle, trailer)),
                                           base(), '2026-10-07', 'input.zip')
        self.assertEqual(report['included_records'], 3)
        model = next(b for b in result['brands'] if b['mærke'] == 'HONDA')['modeller'][0]
        profiles = model['dmr_profiles']
        self.assertEqual(len(profiles), 2)
        self.assertEqual({(p['KoeretoejOplysningModelAar'][0], p['KoeretoejMotorKmPerLiter'][0])
                          for p in profiles}, {('2020', '25.0'), ('2022', '27.0')})
        self.assertNotIn('PRIVATE', json.dumps(result))
        self.assertIsNone(model['tank_l'])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'source.zip'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('source.xml', xml(motorcycle, later, trailer))
            inspection = dmr.inspect_archive(path, limit=2)
            self.assertEqual(inspection['processed_records'], 2)
            self.assertEqual(inspection['vehicle_kinds'][0]['records'], 2)
            self.assertNotIn('PRIVATE', json.dumps(inspection))

    def test_full_extract_kind_codes_include_all_observed_powered_types(self):
        for code in ('1', '2', '3', '4', '7', '8', '16', '17', '91'):
            self.assertTrue(dmr.powered_kind({'KoeretoejArtNummer': {code}}))
        for code in ('5', '6', '9', '10', '11', '96', '999', '12'):
            self.assertFalse(dmr.powered_kind({'KoeretoejArtNummer': {code},
                                              'DrivkraftTypeNavn': {'Diesel'}}))

    def test_deduplication_preserves_punctuation_variants_specs_and_custom_metadata(self):
        original = base()
        original['brands'][0]['modeller'].extend([
            {'model': ' GOLF ', 'tank_l': 55, 'variants': [{'name': ' 1.6 TDI ', 'fuel_types': ['Diesel']}]},
            {'model': 'G-O-L-F', 'tank_l': 40},
            {'model': 'C4', 'tank_l': 50},
            {'model': 'C 4', 'tank_l': 60},
        ])
        original['brands'].append({'mærke': 'VW', 'modeller': [
            {'model': 'golf', 'battery_kwh': 12, 'variants': [{'name': '1.6 tdi', 'fuel_types': ['Benzin']}]}]})
        result, report = dmr.deduplicate_catalog(original)
        self.assertEqual(len(result['brands']), 1)
        models = result['brands'][0]['modeller']
        self.assertEqual(len(models), 4)
        golf = next(m for m in models if m['model'] == 'Golf')
        self.assertEqual(golf['tank_l'], 50)
        self.assertEqual(golf['deduplication_alternatives']['tank_l'], [50, 55])
        self.assertEqual(golf['battery_kwh'], 12)
        self.assertEqual(len(golf['variants']), 1)
        self.assertEqual(set(golf['variants'][0]['fuel_types']), {'Diesel', 'Benzin'})
        self.assertTrue(report['requires_review'])
        self.assertEqual(result['logos'], original['logos'])
        self.assertEqual(result['custom_metadata'], {'keep': True})
        again, _ = dmr.deduplicate_catalog(result)
        self.assertEqual(result, again)
        self.assertEqual(len(original['brands']), 2)

    def test_limited_build_keeps_distinct_technical_combinations_without_fuzzy_model_merge(self):
        a = record(model='Golf').replace('</ns:Statistik>',
              '<ns:KoeretoejOplysningModelAar>2020</ns:KoeretoejOplysningModelAar></ns:Statistik>')
        b = a.replace('2020', '2021').replace('Diesel', 'Benzin')
        result, report = dmr.build_catalog(BytesIO(xml(a, b, record(model='G-OLF'))),
                                          base(), '2026-10-07', 'input.zip', limit=2)
        self.assertEqual(report['processed_records'], 2)
        self.assertEqual(report['sample_limit'], 2)
        self.assertEqual(report['unique_profiles'], 2)
        golf = result['brands'][0]['modeller'][0]
        self.assertEqual(golf['model_years'], ['2020', '2021'])
        self.assertEqual(golf['fuel_types'], ['Benzin', 'Diesel'])
        self.assertEqual(golf['tank_l'], 50)
        self.assertEqual(len(golf['dmr_profiles']), 2)

    def test_compact_build_omits_profiles_but_retains_variant_fuel_and_year(self):
        payload = record().replace('</ns:Statistik>',
            '<ns:KoeretoejOplysningModelAar>2021</ns:KoeretoejOplysningModelAar></ns:Statistik>')
        result, report = dmr.build_catalog(BytesIO(xml(payload)), base(),
            '2026-10-07', 'input.zip', include_profiles=False)
        model = result['brands'][0]['modeller'][0]
        self.assertNotIn('dmr_profiles', model)
        self.assertEqual(model['model_years'], ['2021'])
        self.assertEqual(model['fuel_types'], ['Diesel'])
        self.assertEqual(model['variants'], [{'name': '1.6 TDI', 'fuel_types': ['Diesel'], 'model_years': ['2021']}])
        self.assertFalse(report['technical_profiles_included'])
        self.assertEqual(model['vehicle_types'], ['personbil'])
        self.assertEqual(report['unique_models_by_type']['personbil'], 1)

    def test_unique_categories_are_model_counts_not_record_counts(self):
        payload = xml(record(model='One', kind='1'), record(model='One', kind='1'),
                      record(model='One', kind='3'), record(model='Truck', kind='4'),
                      record(model='Bike', kind='7'), record(model='Moped', kind='16'),
                      record(model='Moped', kind='17'), record(model='Tractor', kind='8'),
                      record(model='Bus', kind='2'), record(model='Heavy', kind='91'))
        result, report = dmr.build_catalog(BytesIO(payload), {'brands': []},
                                          '2026-10-07', 'test.zip', include_profiles=False)
        self.assertEqual(report['unique_models_by_type'], dict.fromkeys(
            ['personbil', 'varebil', 'lastbil', 'bus', 'motorcykel', 'knallert', 'traktor', 'andet'], 1))
        self.assertEqual(report['models'], 7)
        self.assertEqual(report['processed_records'], 10)
        self.assertTrue(all('dmr_profiles' not in m for b in result['brands'] for m in b['modeller']))

    def test_download_uses_latest_archive_and_keeps_old_file_on_interrupted_download(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'dmr.zip'
            path.write_bytes(b'old file')
            factory = MagicMock()
            ftp = factory.return_value.__enter__.return_value
            ftp.nlst.return_value = ['ESStatistikListeModtag-20261001-000000.zip', 'ESStatistikListeModtag-20261015-010000.zip', 'bad.zip']
            ftp.retrbinary.side_effect = OSError('connection lost')
            with self.assertRaises(OSError):
                dmr.download_latest(path, factory)
            self.assertEqual(path.read_bytes(), b'old file')
            self.assertEqual(list(Path(folder).iterdir()), [path])
            self.assertEqual(ftp.retrbinary.call_args.args[0], 'RETR ESStatistikListeModtag-20261015-010000.zip')

    def test_timeout_resumes_partial_zip_on_fresh_connection(self):
        payload = BytesIO()
        with zipfile.ZipFile(payload, 'w') as archive:
            archive.writestr('data.xml', xml(record()))
        data = payload.getvalue()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'dmr.zip'
            path.write_bytes(b'previous catalog download')
            factory = MagicMock()
            first, second = MagicMock(), MagicMock()
            factory.side_effect = [first, second]
            a, b = first.__enter__.return_value, second.__enter__.return_value
            a.nlst.return_value = ['ESStatistikListeModtag-20261015-010000.zip']

            def interrupted(command, callback, **kwargs):
                callback(data[:80])
                raise TimeoutError('idle socket')

            def resumed(command, callback, **kwargs):
                self.assertEqual(kwargs['rest'], 80)
                callback(data[80:])

            a.retrbinary.side_effect = interrupted
            b.retrbinary.side_effect = resumed
            name = dmr.download_latest(path, factory)
            self.assertEqual(name, 'ESStatistikListeModtag-20261015-010000.zip')
            self.assertEqual(path.read_bytes(), data)
            b.nlst.assert_not_called()
            self.assertEqual(factory.call_args.kwargs['timeout'], 180)
            self.assertEqual(list(Path(folder).iterdir()), [path])
