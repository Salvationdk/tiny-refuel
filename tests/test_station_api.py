"""Real authenticated HA view contracts and non-fatal historical storage errors."""
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
from custom_components.tiny_refuel import RefuelStationsView, RefuelHistoryView
from custom_components.tiny_refuel.manager import RefuelManager
from test_integration import FakeHass, payload

class StationApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.hass=FakeHass(self.temp.name)
        self.manager=RefuelManager(self.hass,Path(self.temp.name),collector=lambda _:payload())
        self.hass.data['tiny_refuel']={'manager':self.manager}
    async def test_station_and_history_routes_and_invalid_selections(self):
        self.manager.start_refresh();await self.manager.task
        view=RefuelStationsView(self.hass)
        response=await view.get(None)
        self.assertTrue(view.requires_auth)
        self.assertEqual(response.headers['Cache-Control'],'no-store')
        rows=json.loads(response.text)['stations'];self.assertEqual(len(rows),3)
        self.assertTrue(all('vehicles' not in row for row in rows))
        route=RefuelHistoryView(self.hass);self.assertTrue(route.requires_auth)
        request=SimpleNamespace(query={'field':'kwh','days':'7'})
        result=await route.get(request,rows[0]['id'])
        self.assertEqual(result.status,200);self.assertEqual(len(json.loads(result.text)['points']),1)
        for uid,query in [('..',{}),(rows[0]['id'],{'days':'NaN'}),(rows[0]['id'],{'field':'bad'}),(rows[0]['id'],{'days':'366'})]:
            self.assertEqual((await route.get(SimpleNamespace(query=query),uid)).status,400)
        self.hass.data['tiny_refuel'].pop('manager')
        self.assertEqual((await view.get(None)).status,503)
    async def test_history_failure_does_not_fail_price_collection(self):
        with patch.object(self.manager.history,'record',side_effect=OSError('disk full')):
            with self.assertLogs('custom_components.tiny_refuel.manager',level='ERROR'):
                self.manager.start_refresh();await self.manager.task
        self.assertIsNone(self.manager.last_error)
        self.assertTrue(self.manager.history_error)
        self.assertTrue(self.manager.data['updated'])
        self.assertTrue(self.manager.station_snapshot()['history_error'])
