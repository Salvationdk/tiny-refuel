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
                      record('TRAILER', 'DROP', '5'), record('MOTORBIKE', 'DROP', '7'))
        result, report = dmr.build_catalog(BytesIO(payload), original, '2026-10-16', 'ESStatistikListeModtag-20261016-000000.zip')
        self.assertEqual(report['processed_records'], 7)
        self.assertEqual(report['included_records'], 5)
        self.assertEqual(report['added_models'], 3)
        self.assertEqual(report['added_makes'], 2)
        self.assertEqual(len(result['brands']), 3)
        vw = next(b for b in result['brands'] if b['mærke'] == 'Volkswagen')
        golf = next(m for m in vw['modeller'] if m['model'] == 'Golf')
        self.assertEqual(golf['tank_l'], 50)
        self.assertEqual(golf['variants'], [{'name': '1.6 TDI', 'fuel_types': ['Diesel']}])
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
        for payload in (b'<root/>', xml(record(kind='7')), b'<root><Statistik>'):
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
