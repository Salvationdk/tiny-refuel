"""Public data actions and station entities share validated integration data."""
import asyncio
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

import homeassistant
import voluptuous as vol
from homeassistant.core import SupportsResponse
from homeassistant.exceptions import HomeAssistantError, Unauthorized
from custom_components.tiny_refuel.const import DOMAIN
from custom_components.tiny_refuel.manager import RefuelManager
from custom_components.tiny_refuel import data_services as api, sensor
from custom_components.tiny_refuel.station_entities import RefuelStationPriceSensor, refresh_station_index
from custom_components.tiny_refuel.config_flow import TinyRefuelOptionsFlow


class PublicDataTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        async def executor(function, *args):
            return await asyncio.to_thread(function, *args)
        self.hass = SimpleNamespace(data={DOMAIN:{}}, async_add_executor_job=executor,
            async_create_background_task=lambda coroutine,name:asyncio.create_task(coroutine,name=name),
            states={"person.driver": SimpleNamespace(state="home", attributes={"latitude":55,"longitude":12})})
        self.car = {"id":"car", "navn":"Bil", "mærke":"VW", "brændstof":"benzin", "tank_liters":35,
                    "location_entity":"person.driver", "capacity_status":"needs_review"}
        self.manager = RefuelManager(self.hass, Path(self.temp.name), vehicles=[self.car])
        self.manager.data = {"project":"Tiny Refuel", "updated":"2026-10-20T10:00:00Z",
            "stations":[
                {"brand":"Q8", "name":"Near", "address":"A", "lat":55,"lon":12,"p95":15},
                {"brand":"OK", "name":"Cheap", "address":"B", "lat":56,"lon":12,"p95":14},
                {"brand":"OK", "name":"Old", "address":"C", "p95":1, "stale":True}],
            "ev":[{"brand":"Q8", "name":"General", "kwh":2.99},
                  {"brand":"Q8", "name":"Local", "address":"D", "lat":55,"lon":12,"kwh":3.5}],
            "benefits":{"Q8":{"text":"Example", "url":"https://example.com"}},
            "fuel_sources":{"example":{"status":"ok","records":3}}, "errors":[]}

    async def query(self, service, user=None, **data):
        call = SimpleNamespace(service=service, data=api.SCHEMAS[service](data),
                               context=SimpleNamespace(user_id=user))
        return await api.async_query(self.hass, self.manager, call)

    async def test_every_collected_field_is_reachable_and_paged(self):
        metadata = await self.query("get_data")
        for section, original in self.manager.snapshot().items():
            self.assertIn(section, metadata["sections"])
            response = await self.query("get_data", section=section, limit=1)
            if isinstance(original, list):
                collected=[]
                while True:
                    collected.extend(response["items"])
                    if response["next_offset"] is None: break
                    response=await self.query("get_data",section=section,limit=1,offset=response["next_offset"])
                self.assertEqual(collected, original)
            elif isinstance(original, dict):
                collected={}
                while True:
                    collected.update({row["key"]:row["value"] for row in response["items"]})
                    if response["next_offset"] is None: break
                    response=await self.query("get_data",section=section,limit=1,offset=response["next_offset"])
                self.assertEqual(collected, original)
            else:
                self.assertEqual(response["value"],original)
        benefits=await self.query("get_data",section="benefits")
        benefits["items"][0]["value"]["text"]="Changed"
        self.assertEqual(self.manager.data["benefits"]["Q8"]["text"],"Example")
        with self.assertRaises(HomeAssistantError):
            await self.query("get_data",section="not_a_section")

    async def test_prices_distance_filters_and_pagination(self):
        cheapest=await self.query("get_stations",fuel="p95",sort="price",limit=1)
        self.assertEqual(cheapest["items"][0]["prices"]["p95"],14)
        self.assertEqual(cheapest["total"],2)
        self.assertEqual(cheapest["next_offset"],1)
        near=await self.query("get_stations",fuel="p95",location_entity="person.driver",sort="distance",radius_km=2)
        self.assertEqual(near["total"],1)
        self.assertEqual(near["items"][0]["distance_km"],0)
        self.assertIn("google",near["items"][0]["navigation"])
        self.assertEqual((await self.query("get_stations",brands=["q8"],search="near"))["total"],1)
        uid=near["items"][0]["id"]
        self.assertEqual((await self.query("get_stations",station_ids=[uid]))["total"],1)
        self.assertEqual((await self.query("get_stations",fuel="kwh"))["total"],1)
        with self.assertRaises(HomeAssistantError): await self.query("get_stations",sort="price")
        with self.assertRaises(HomeAssistantError): await self.query("get_stations",sort="distance")

    async def test_failure_keeps_raw_evidence_but_never_current_prices(self):
        self.manager.last_error="Offline"
        self.assertEqual((await self.query("get_stations"))["total"],0)
        saved=await self.query("get_stations",current_only=False,fuel="p95")
        self.assertEqual(saved["total"],3)
        self.assertTrue(all(not row["current"] for row in saved["items"]))
        self.assertEqual((await self.query("get_data",section="stations"))["items"][0]["p95"],15)

    async def test_vehicle_capacities_calculations_and_supplied_card_vehicle(self):
        result=await self.query("get_vehicles")
        car=result["items"][0]
        self.assertEqual(car["capacity_status"],"needs_review")
        self.assertEqual(car["calculations"]["p95"]["full_cost"],525)
        self.assertEqual(car["calculations"]["p95"]["price"],15)
        own={**self.car,"id":"own","tank_liters":10}
        self.assertEqual((await self.query("get_vehicles",vehicle=own))["items"][0]["calculations"]["p95"]["full_cost"],150)
        self.assertEqual((await self.query("get_vehicles",vehicle_id="missing"))["total"],0)
        self.car.pop("tank_liters")
        self.assertIsNone((await self.query("get_vehicles"))["items"][0]["calculations"]["p95"]["full_cost"])
        self.hass.states["person.driver"].state="unavailable"
        self.assertIsNone((await self.query("get_vehicles"))["items"][0]["calculations"]["p95"]["price"])

    async def test_private_position_permissions_apply_to_queries_and_raw_vehicles(self):
        denied=SimpleNamespace(is_active=True,is_admin=False,permissions=SimpleNamespace(check_entity=Mock(return_value=False)))
        self.hass.auth=SimpleNamespace(async_get_user=AsyncMock(return_value=denied))
        with self.assertRaises(Unauthorized):
            await self.query("get_stations",user="restricted",location_entity="person.driver")
        self.assertEqual((await self.query("get_vehicles",user="restricted"))["total"],0)
        self.assertEqual((await self.query("get_data",user="restricted",section="vehicles"))["items"],[])
        self.assertNotIn("vehicles",await self.query("get_status",user="restricted"))
        denied.permissions.check_entity.return_value=True
        self.assertEqual((await self.query("get_vehicles",user="restricted"))["total"],1)

    async def test_history_and_catalog_preserve_evidence(self):
        await self.hass.async_add_executor_job(self.manager.history.record,self.manager.data)
        uid=self.manager.station_snapshot()["stations"][0]["id"]
        result=await self.query("get_history",station_id=uid,fuel="p95",days=7)
        self.assertEqual(result["points"][0]["value"],15)
        catalog={"vehicle_type":"personbil","brands":[{"mærke":"VW","logo":"vw.svg","modeller":[
            {"model":"up!","tank_l":35,"capacity_status":"needs_review","variants":[{"name":"Test","tank_l":35}]},
            {"model":"Golf","tank_l":50}]}],"_download":{"source":"bundled","stale":True}}
        store=SimpleNamespace(get=AsyncMock(return_value=catalog))
        self.hass.data[DOMAIN]["catalogs"]=store
        result=await self.query("get_catalog",vehicle_type="personbil",make="vw",search="up",limit=1)
        self.assertEqual(result["total"],1)
        self.assertEqual(result["items"][0]["make"]["logo"],"vw.svg")
        self.assertEqual(result["items"][0]["model"]["variants"][0]["tank_l"],35)
        self.assertTrue(result["metadata"]["_download"]["stale"])
        self.assertEqual((await self.query("get_catalog",vehicle_type="personbil",offset=100))["items"],[])

    async def test_service_lifecycle_and_schema_rejections(self):
        registry={}
        self.hass.services=SimpleNamespace(
            async_register=lambda domain,name,handler,**kwargs:registry.update({name:(handler,kwargs)}),
            async_remove=lambda domain,name:registry.pop(name,None))
        api.async_register_services(self.hass,self.manager)
        self.assertEqual(set(registry),set(api.SERVICE_NAMES))
        for _, options in registry.values():self.assertEqual(options["supports_response"],SupportsResponse.ONLY)
        result=await registry["get_status"][0](SimpleNamespace(service="get_status",data={},context=SimpleNamespace(user_id=None)))
        self.assertEqual(result["schema_version"],1)
        api.async_remove_services(self.hass);self.assertEqual(registry,{})
        for name,data in [("get_data",{"offset":-1}),("get_data",{"limit":501}),("get_history",{"station_id":"bad"}),
                          ("get_catalog",{"vehicle_type":"../secret"}),("get_stations",{"fuel":"unknown"})]:
            with self.subTest(name=name,data=data),self.assertRaises(vol.Invalid):api.SCHEMAS[name](data)
        self.assertEqual(api.clean({"bad":float("nan")}),{"bad":None})
        json.dumps(api.clean({"bad":float("inf")}),allow_nan=False)

    async def test_station_sensor_and_vehicle_metadata(self):
        uid=self.manager.station_snapshot()["stations"][0]["id"]
        await self.hass.async_add_executor_job(refresh_station_index,self.manager)
        station=RefuelStationPriceSensor(self.manager,uid,"p95")
        self.assertEqual(station.native_value,15)
        self.assertEqual(station.extra_state_attributes["station"]["address"],"A")
        self.assertIsNone(RefuelStationPriceSensor(self.manager,uid,"kwh").native_value)
        self.manager.last_error="Offline";self.assertIsNone(station.native_value)
        self.assertFalse(station.extra_state_attributes["current"])
        self.manager.last_error=None
        self.manager.data={**self.manager.data,"stations":[]}
        self.assertIsNone(station.native_value)
        info=sensor.RefuelVehicleInfoSensor(self.manager,self.car)
        self.assertEqual(info.native_value,"Bil")
        self.assertEqual(info.extra_state_attributes["capacity_status"],"needs_review")
        self.assertEqual(sensor.RefuelVehicleInfoSensor(self.manager,self.car,"tank_liters").native_value,35)
        self.assertIsNone(sensor.RefuelVehicleInfoSensor(self.manager,self.car,"batteri_kwh").native_value)

    async def test_station_selection_preserves_other_options(self):
        class Flow(TinyRefuelOptionsFlow):
            @property
            def config_entry(self):
                return SimpleNamespace(options={"vehicles":[self_car],"scan_hours":8})
        self_car=self.car
        flow=Flow()
        uid=self.manager.station_snapshot()["stations"][0]["id"]
        result=await flow.async_step_station_sensors({"station_sensor_ids":[uid,uid]})
        self.assertEqual(result["data"]["station_sensor_ids"],[uid])
        self.assertEqual(result["data"]["scan_hours"],8)
        self.assertEqual(result["data"]["vehicles"],[self.car])
        cleared=await flow.async_step_station_sensors({"station_sensor_ids":[]})
        self.assertEqual(cleared["data"]["station_sensor_ids"],[])

    async def test_station_prices_follow_the_real_refresh_and_failure_cycle(self):
        await self.hass.async_add_executor_job(refresh_station_index,self.manager)
        uid=self.manager.station_snapshot()["stations"][0]["id"]
        entity=RefuelStationPriceSensor(self.manager,uid,"p95")
        self.manager._station_entities_enabled=True
        updated={**self.manager.data,"stations":[{**self.manager.data["stations"][0],"p95":18}]}
        self.manager.collector=lambda path:updated
        self.manager._collector_supports_progress=False
        self.manager.start_refresh()
        await self.manager.task
        self.assertEqual(entity.native_value,18)
        def fail(path):raise OSError("offline")
        self.manager.collector=fail
        with self.assertLogs("custom_components.tiny_refuel.manager",level="ERROR"):
            self.manager.start_refresh()
            await self.manager.task
        self.assertIsNone(entity.native_value)
        self.assertFalse(entity.extra_state_attributes["current"])
        await self.manager.async_close()
