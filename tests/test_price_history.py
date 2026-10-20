"""Station identities and price changes survive restarts without false prices."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from custom_components.tiny_refuel.price_history import PriceHistory, station_id, station_rows

class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'history.sqlite3'
        self.store=PriceHistory(self.path,30)
        self.now=datetime(2026,10,20,tzinfo=timezone.utc)
        self.row={'brand':'Q8','name':'Test','address':'Testvej 1','p95':14.5,'diesel':13.0}
        self.data={'stations':[self.row],'ev':[]}
        self.uid=station_id(self.row,'fuel')
    def test_identity_survives_geocoding_and_label_changes(self):
        self.assertEqual(self.uid,station_id({**self.row,'lat':55.1,'lon':12.1,'name':'Renamed'},'fuel'))
        self.assertNotEqual(self.uid,station_id({**self.row,'brand':'OK'},'fuel'))
        self.assertNotEqual(station_id({'brand':'Q8','location_id':'a','kind':'AC'},'ev'),station_id({'brand':'Q8','location_id':'a','kind':'DC'},'ev'))
    def test_only_changes_are_stored_and_survive_restart(self):
        self.store.record(self.data,self.now-timedelta(days=2))
        self.store.record(self.data,self.now-timedelta(days=1))
        self.row['p95']=14.1;self.store.record(self.data,self.now)
        result=PriceHistory(self.path,30).query(self.uid,'p95',7,self.now)
        self.assertEqual([p['value'] for p in result['points']],[14.5,14.1])
        self.assertEqual(len(self.store.query(self.uid,'diesel',7,self.now)['points']),1)
    def test_stale_list_nonfinite_generic_conflicting_not_recorded(self):
        for changes in [{'stale':True},{'liste':True},{'p95':float('nan'),'diesel':None}]:
            self.store.record({'stations':[{**self.row,**changes}]},self.now)
        self.store.record({'stations':[self.row,{**self.row,'p95':1}]},self.now)
        self.store.record({'ev':[{'brand':'Q8','kwh':2.5}]},self.now)
        self.assertEqual(self.store.query(self.uid,'p95',7,self.now)['points'],[])
        rows=station_rows({'stations':[self.row,{**self.row,'p95':1}]})
        self.assertFalse(rows[0]['current']);self.assertTrue(rows[0]['ambiguous'])
    def test_retention_keeps_one_baseline_without_new_observation(self):
        self.store.record(self.data,self.now-timedelta(days=80))
        self.row['p95']=13;self.store.record(self.data,self.now-timedelta(days=70))
        self.store.record(self.data,self.now)
        points=self.store.query(self.uid,'p95',7,self.now)['points']
        self.assertEqual(len(points),1);self.assertTrue(points[0]['baseline']);self.assertEqual(points[0]['value'],13)
        self.assertEqual(points[0]['observed_at'],(self.now-timedelta(days=70)).isoformat())
    def test_disabled_creates_no_database(self):
        store=PriceHistory(self.path,0);store.record(self.data,self.now)
        self.assertFalse(self.path.exists());self.assertFalse(store.query(self.uid,'p95')['enabled'])
