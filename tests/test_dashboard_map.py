"""Opt-in map filtering, stable entity updates and small dashboard contracts."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock
from custom_components.tiny_refuel.geo_location import map_selection, StationMapEntity, async_setup_entry
from custom_components.tiny_refuel.dashboard_data import dashboard_snapshot, general_tariffs
from custom_components.tiny_refuel import RefuelDashboardView
from custom_components.tiny_refuel.manager import RefuelManager
from custom_components.tiny_refuel.config_flow import TinyRefuelOptionsFlow
from test_integration import FakeHass

ROW={'id':'a'*24,'brand':'Q8','name':'Local','kind':'fuel','lat':55,'lon':12,'address':'A','current':True,'prices':{'p95':15},'updated':'2026-10-20T12:00:00Z'}

class MapSelectionTests(unittest.TestCase):
    def setUp(self):
        self.hass=SimpleNamespace(config=SimpleNamespace(latitude=55,longitude=12),states={})
        self.rows=[ROW,{**ROW,'id':'b'*24,'brand':'OK','lat':56},{**ROW,'id':'c'*24,'lat':None}]
        self.manager=SimpleNamespace(station_snapshot=lambda:{'stations':self.rows})
    def test_disabled_is_empty_and_radius_limit_brands_and_selection_are_enforced(self):
        self.assertEqual(map_selection(self.hass,self.manager,{})[0],[])
        options={'map_enabled':True,'map_radius_km':200,'map_limit':1}
        rows,status=map_selection(self.hass,self.manager,options)
        self.assertEqual([r['id'] for r in rows],['a'*24]);self.assertEqual(status['matched'],2)
        self.assertEqual(map_selection(self.hass,self.manager,{**options,'map_brands':['ok']})[0][0]['brand'],'OK')
        self.assertEqual(map_selection(self.hass,self.manager,{**options,'map_selected_only':True,'map_station_ids':[]})[0],[])
        self.assertEqual(len(map_selection(self.hass,self.manager,{**options,'map_radius_km':10})[0]),1)
    def test_explicit_unavailable_position_never_falls_back_to_home(self):
        rows,status=map_selection(self.hass,self.manager,{'map_enabled':True,'map_location_entity':'person.missing'})
        self.assertEqual(rows,[]);self.assertFalse(status['origin_available'])
    def test_entity_has_native_map_coordinates_and_distinguishes_cached_prices(self):
        entity=StationMapEntity({**ROW,'distance':1.25,'current':False})
        self.assertEqual(entity.source,'tiny_refuel');self.assertEqual(entity.latitude,55)
        self.assertEqual(entity.distance,1.25);self.assertFalse(entity.extra_state_attributes['aktuelle_priser'])
        self.assertEqual(entity.extra_state_attributes['benzin_95_kr_l'],15)
        self.assertEqual(entity.unique_id,'tiny_refuel_map_'+'a'*24)

class MapLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_refresh_reuses_entity_then_removes_out_of_scope_station(self):
        with tempfile.TemporaryDirectory() as temp:
            hass=FakeHass(temp);hass.states={};hass.config.latitude=55;hass.config.longitude=12;hass.data['tiny_refuel']={}
            rows=[ROW];listeners=[];unsub=Mock();tasks=[]
            manager=SimpleNamespace(station_snapshot=lambda:{'stations':rows},subscribe=lambda callback:(listeners.append(callback) or unsub))
            def create(coro,name):
                task=asyncio.create_task(coro);tasks.append(task);return task
            hass.async_create_background_task=create
            stops=[];entry=SimpleNamespace(runtime_data=manager,options={'map_enabled':True},async_on_unload=stops.append)
            added=[];await async_setup_entry(hass,entry,added.extend);await tasks[-1]
            self.assertEqual(len(added),1);entity=added[0];entity.hass=hass;entity.async_write_ha_state=Mock();entity.async_remove=AsyncMock()
            rows[0]={**ROW,'prices':{'p95':16}};listeners[0]();await tasks[-1]
            self.assertEqual(len(added),1);self.assertEqual(entity.extra_state_attributes['benzin_95_kr_l'],16)
            rows.clear();listeners[0]();await tasks[-1];entity.async_remove.assert_awaited_once()
            for stop in stops:stop()
            unsub.assert_called_once()

class DashboardTests(unittest.IsolatedAsyncioTestCase):
    async def test_summary_api_is_authenticated_and_omits_notification_and_catalog_contents(self):
        with tempfile.TemporaryDirectory() as temp:
            hass=FakeHass(temp);manager=RefuelManager(hass,Path(temp),vehicles=[{'id':'v','navn':'Test','tank_liters':35,'notify_service':'private'}])
            manager.data={'updated':'2026-10-20T12:00:00Z','fuel_sources':{'f24.dk':{'status':'ok','last_success':'now'}}}
            hass.data['tiny_refuel']={'manager':manager}
            view=RefuelDashboardView(hass);response=await view.get(None);data=json.loads(response.text)
            self.assertTrue(view.requires_auth);self.assertEqual(response.headers['Cache-Control'],'no-store')
            self.assertNotIn('notify_service',data['vehicles'][0]);self.assertEqual(data['sources'][0]['name'],'Q8 og F24 brændstof')
            self.assertNotIn('stations',data)
    async def test_generic_tariffs_never_become_local_station_prices(self):
        data={'ev':[{'brand':'OK','name':'Normal','kwh':3.49},{'brand':'OK','address':'Local','kwh':2}]}
        self.assertEqual(len(general_tariffs(data)),1);self.assertEqual(general_tariffs(data)[0]['kwh'],3.49)
        self.assertFalse(general_tariffs(data,True)[0]['current'])
    async def test_changed_catalog_capacity_loses_supported_status_but_keeps_evidence_link(self):
        class Flow(TinyRefuelOptionsFlow):
            @property
            def config_entry(self):return SimpleNamespace(options={})
        flow=Flow();flow._catalog_defaults={'navn':'Test','tank_liters':35,'brændstof':'benzin'}
        flow._catalog_evidence={'capacity_status':'source_supported','capacity_source_urls':['https://example.com/spec']}
        result=await flow.async_step_vehicle({'navn':'Test','tank_liters':40,'brændstof':'benzin'})
        car=result['data']['vehicles'][0]
        self.assertEqual(car['capacity_status'],'needs_review');self.assertTrue(car['capacity_source_urls'])
    async def test_map_options_selection_serializes_and_preserves_other_settings(self):
        from homeassistant.helpers.data_entry_flow import _BaseFlowManagerView
        class Flow(TinyRefuelOptionsFlow):
            @property
            def config_entry(self):return SimpleNamespace(options={'history_days':90})
        flow=Flow();flow.hass=SimpleNamespace(data={'tiny_refuel':{'manager':SimpleNamespace(station_snapshot=lambda:{'stations':[ROW]})}},states={},config=SimpleNamespace(latitude=55,longitude=12))
        form=await flow.async_step_map({'map_enabled':True,'map_selected_only':True,'map_radius_km':25,'map_limit':10,'map_brands':[]})
        self.assertEqual(form['step_id'],'map_stations')
        serialized=_BaseFlowManagerView(None)._prepare_result_json(form)
        self.assertTrue(serialized['data_schema'])
        result=await flow.async_step_map_stations({'map_station_ids':[ROW['id']]})
        self.assertEqual(result['data']['history_days'],90)
        self.assertEqual(result['data']['map_station_ids'],[ROW['id']])
