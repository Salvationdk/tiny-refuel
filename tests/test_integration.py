"""Integration contracts using real HA classes and controlled external collection."""
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock, Mock

import homeassistant  # Initialiserer Home Assistants valideringsbibliotek først.
import voluptuous as vol
from custom_components import tiny_refuel
from custom_components.tiny_refuel import scraper, sensor, button
from custom_components.tiny_refuel.config_flow import TinyRefuelConfigFlow
from custom_components.tiny_refuel.manager import RefuelManager


def payload():
    return {"project": "Tiny Refuel", "scraper_version": "v0.1", "updated": datetime.now(timezone.utc).isoformat(),
            "stations": [], "ev": [{"brand": "Q8", "location_id": "a", "address": "A", "kind": "AC", "kwh": 3.89},
            {"brand": "Q8", "location_id": "a", "address": "A", "kind": "DC", "kwh": 3.89},
            {"brand": "OK", "location_id": "b", "address": "B", "kwh": None},
            {"brand": "OK", "name": "Generel takst", "kwh": 3.49}], "errors": [], "ev_sources": {}}


class FakeHass:
    def __init__(self, directory):
        self.data = {"frontend_extra_module_url": set()}
        self.config = SimpleNamespace(path=lambda *args: str(Path(directory).joinpath(*args)))
        self.views, self.paths, self.services_map = [], [], {}
        self.http = SimpleNamespace(async_register_static_paths=self.register_paths, register_view=self.views.append)
        self.services = SimpleNamespace(async_register=lambda d,n,f:self.services_map.update({(d,n):f}),
                                        async_remove=lambda d,n:self.services_map.pop((d,n),None))
        self.config_entries = SimpleNamespace(async_forward_entry_setups=AsyncMock(), async_unload_platforms=AsyncMock(return_value=True))

    async def register_paths(self, paths):
        self.paths.extend(paths)

    async def async_add_executor_job(self, function, *args):
        return await asyncio.to_thread(function, *args)

    def async_create_background_task(self, coroutine, name):
        return asyncio.create_task(coroutine, name=name)


class ManagerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.hass = FakeHass(self.temp.name)
        self.path = Path(self.temp.name) / '.storage/tiny_refuel'

    async def test_shared_job_and_failure_retains_data(self):
        entered, release = threading.Event(), threading.Event()
        calls = []
        def collect(path):
            calls.append(path); entered.set(); release.wait(3); return payload()
        manager = RefuelManager(self.hass, self.path, collect)
        notifications=[];manager.subscribe(lambda:notifications.append(manager.refreshing))
        manager.start_refresh(); manager.start_refresh()
        await asyncio.to_thread(entered.wait, 2)
        self.assertTrue(manager.refreshing);self.assertEqual(len(calls),1)
        release.set();await manager.task
        self.assertFalse(manager.refreshing);self.assertEqual(manager.counts(),(2,1));self.assertEqual(notifications,[True,False])
        previous=manager.data
        def fail(path):raise RuntimeError('source unavailable')
        manager.collector=fail
        with self.assertLogs('custom_components.tiny_refuel.manager',level='ERROR'):
            manager.start_refresh();await manager.task
        self.assertIs(manager.data,previous);self.assertEqual(manager.last_error,'source unavailable')
        await manager.async_close();manager.start_refresh();self.assertTrue(manager.closed)

    async def test_close_waits_for_writer_before_reload(self):
        entered, release = threading.Event(), threading.Event()
        def collect(path):entered.set();release.wait(3);return payload()
        manager=RefuelManager(self.hass,self.path,collect);manager.start_refresh()
        await asyncio.to_thread(entered.wait,2)
        closing=asyncio.create_task(manager.async_close());await asyncio.sleep(0)
        self.assertFalse(closing.done());manager.start_refresh();release.set();await closing
        self.assertFalse(manager.refreshing)

    async def test_cache_load_and_private_api(self):
        self.path.mkdir(parents=True);scraper.save_json(str(self.path/'priser-og-ladesteder.json'),payload())
        manager=RefuelManager(self.hass,self.path);await manager.async_load();self.assertEqual(manager.counts(),(2,1))
        self.hass.data['tiny_refuel']={'manager':manager}
        view=tiny_refuel.RefuelDataView(self.hass);self.assertTrue(view.requires_auth)
        response=await view.get(None);self.assertEqual(response.status,200);self.assertEqual(response.headers['Cache-Control'],'no-store')
        self.assertEqual(json.loads(response.text)['project'],'Tiny Refuel')
        self.hass.data['tiny_refuel'].pop('manager');self.assertEqual((await view.get(None)).status,503)

    async def test_setup_service_entities_and_unload(self):
        entry=SimpleNamespace(data={'scan_hours':6},async_on_unload=Mock())
        with patch.object(tiny_refuel,'add_extra_js_url') as add_js, patch.object(tiny_refuel,'async_track_time_interval',return_value=lambda:None) as interval:
            with patch.object(scraper,'collect',return_value=payload()):
                self.assertTrue(await tiny_refuel.async_setup(self.hass,{}));self.assertTrue(await tiny_refuel.async_setup(self.hass,{}))
                self.assertEqual(len(self.hass.paths),1);add_js.assert_called_once()
                self.assertTrue(await tiny_refuel.async_setup_entry(self.hass,entry));await entry.runtime_data.task
                self.assertEqual(interval.call_args.args[2].total_seconds(),21600)
                self.assertIn(('tiny_refuel','refresh'),self.hass.services_map)
                entities=[];await sensor.async_setup_entry(self.hass,entry,entities.extend)
                self.assertEqual([e.native_value for e in entities[:2]],[2,1]);self.assertIsNotNone(entities[2].native_value)
                buttons=[];await button.async_setup_entry(self.hass,entry,buttons.extend)
                await buttons[0].async_press();await entry.runtime_data.task
                await self.hass.services_map[('tiny_refuel','refresh')](None);await entry.runtime_data.task
                self.assertTrue(await tiny_refuel.async_unload_entry(self.hass,entry));self.assertNotIn('manager',self.hass.data['tiny_refuel'])
                self.assertNotIn(('tiny_refuel','refresh'),self.hass.services_map)

    async def test_config_flow_interval_and_no_credentials(self):
        flow=TinyRefuelConfigFlow();flow.async_set_unique_id=AsyncMock();flow._abort_if_unique_id_configured=Mock()
        form=await flow.async_step_user();schema=form['data_schema'];self.assertEqual(schema({}),{'scan_hours':6})
        with self.assertRaises(vol.Invalid):schema({'scan_hours':0})
        result=await flow.async_step_user({'scan_hours':12});self.assertEqual(result['data'],{'scan_hours':12})
        flow._abort_if_unique_id_configured.assert_called()


class SourceTests(unittest.TestCase):
    def test_failed_source_preserves_only_its_own_previous_records(self):
        old=[{'brand':'Shell','source':'shell-charging','address':'A','source_updated':'2026-01-01T00:00:00Z'}, {'brand':'OK','source':'different','address':'B'}]
        def fail():raise ValueError('offline')
        errors=[];rows,status=scraper.fetch_public_ev_locations('',lambda x:x,'shell-charging',old,errors,payload_loader=fail)
        self.assertEqual(len(rows),1);self.assertTrue(rows[0]['stale']);self.assertEqual(rows[0]['source_updated'],old[0]['source_updated']);self.assertEqual(status['status'],'stale');self.assertNotIn('stale',old[0])

    def test_non_danish_shell_and_incomplete_circlek_are_rejected(self):
        with patch.object(scraper,'get_text',return_value=json.dumps({'evsePools':[],'clusters':[{}]})):
            with self.assertRaises(ValueError):scraper.load_circlek_charging()
        with patch.object(scraper,'get_text',return_value=json.dumps({'locations':[{'id':'x','country_code':'SE'}]})):
            with self.assertRaises(ValueError):scraper.load_shell_charging()

    def test_storage_is_created_without_legacy_history(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'.storage/tiny_refuel'
            fuel={'brand':'OK','name':'Test','address':'A','lat':55,'lon':12,'p95':17,'source':'mobility-prices.ok.dk'}
            with patch.multiple(scraper,fetch_ck_ingo=lambda e:([],True),fetch_f24q8=lambda e:([],True),fetch_goon=lambda e:([],True),fetch_shell=lambda e:([],True),fetch_oil=lambda e:([],True),fetch_oil_fuel=lambda e:([],True),fetch_unox=lambda e:(([],[]),True),fetch_ok=lambda e:([],[],True),fetch_q8_el=lambda e:[],geocode_new=lambda addresses, errors, brands=None:{},fetch_ok_fuel=lambda e:([fuel],True),fetch_public_ev_locations=lambda *a,**k:([],{'status':'error','records':0})):
                data=scraper.collect(path)
            self.assertTrue((path/'priser-og-ladesteder.json').exists());self.assertEqual(data['scraper_version'],'v0.1');self.assertEqual(len(data['stations'][0]['h95']),1)


class TeslaCountTests(unittest.TestCase):
    def test_two_tesla_tariffs_count_as_one_priced_location(self):
        row = {'brand': 'Tesla', 'location_id': 't1', 'kwh': None, 'app_only': False,
               'tesla_prices': {'member': [{'price': 2.6}], 'non_member': [{'price': 3.6}]}}
        manager = SimpleNamespace(data={'ev': [row, dict(row)]})
        self.assertEqual(RefuelManager.counts(manager), (1, 1))
        row['tesla_prices'] = {'member': [], 'non_member': []}
        manager.data = {'ev': [row]}
        self.assertEqual(RefuelManager.counts(manager), (1, 0))


if __name__=='__main__':unittest.main()
