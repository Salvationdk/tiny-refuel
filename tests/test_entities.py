"""Entity prices, location updates and shared vehicle configuration contracts."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import unittest
import homeassistant
import voluptuous as vol
from custom_components.tiny_refuel.manager import RefuelManager
from custom_components.tiny_refuel import sensor, binary_sensor
from custom_components.tiny_refuel.config_flow import TinyRefuelOptionsFlow
from custom_components.tiny_refuel.entity_data import price_rows, nearest_row
from homeassistant.helpers import selector


class EntityTests(unittest.TestCase):
    def setUp(self):
        self.hass = SimpleNamespace(states={"person.driver": SimpleNamespace(state="home", attributes={"latitude":55.6, "longitude":12.5})})
        self.manager = RefuelManager(self.hass, Path('/tmp/not-written'))
        self.manager.data = {"stations": [
            {"brand":"Q8", "name":"Near", "address":"A", "p95":15, "diesel":14, "lat":55.601, "lon":12.5},
            {"brand":"OK", "name":"Far", "address":"B", "p95":16, "diesel":15, "lat":56.1, "lon":12.5},
            {"brand":"Shell", "p95":1, "stale":True},
            {"brand":"OK", "p95":2, "liste":True},
            {"brand":"Invalid", "p95":True},
            {"brand":"Invalid", "p95":float('nan')}],
            "ev":[{"brand":"OK", "name":"National", "kwh":1},
                  {"brand":"Q8", "name":"Charger", "address":"A", "lat":55.6,"lon":12.5,"kwh":3}],
            "errors":[], "benefit_errors":[], "updated":"2026-10-19T08:00:00Z"}
        self.vehicle = {"id":"stable-id", "navn":"Familiebil", "brændstof":"benzin", "tank_liters":35,"location_entity":"person.driver"}

    def test_global_prices_exclude_stale_list_and_invalid_values(self):
        self.assertEqual(sensor.RefuelSensor(self.manager,"lowest_p95").native_value,15)
        self.assertEqual(sensor.RefuelSensor(self.manager,"average_p95").native_value,15.5)
        self.assertEqual(sensor.RefuelSensor(self.manager,"lowest_kwh").native_value,3)
        self.assertEqual(sensor.RefuelPriceSensor(self.manager,"p95","OK").native_value,16)
        self.assertEqual(sensor.RefuelSensor(self.manager,"lowest_p95").extra_state_attributes['adresse'],'A')
        self.manager.data['stations']=[]
        self.assertIsNone(sensor.RefuelSensor(self.manager,"lowest_p95").native_value)

    def test_vehicle_updates_with_position_and_capacity_is_never_assumed(self):
        values=lambda metric:sensor.RefuelVehicleSensor(self.manager,self.vehicle,"p95",metric).native_value
        self.assertEqual(values('station'),'Near')
        self.assertEqual(values('price'),15)
        self.assertEqual(values('full_cost'),525)
        self.assertLess(values('distance'),1)
        self.hass.states['person.driver'].attributes['latitude']=56.1
        self.assertEqual(values('station'),'Far')
        self.vehicle.pop('tank_liters')
        self.assertIsNone(values('full_cost'))
        self.hass.states['person.driver'].state='unavailable'
        self.assertIsNone(values('station'))

    def test_closest_ev_without_price_is_navigable_but_not_costed(self):
        self.manager.data['ev'].append({'brand':'Clever','name':'Closest','address':'C','lat':55.6,'lon':12.5,'app_only':True})
        self.manager.data['ev'][1]['lat']=55.7
        row,distance=nearest_row(self.manager.data,'kwh',(55.6,12.5))
        self.assertEqual(row['name'],'Closest')
        self.assertEqual(distance,0)
        self.assertIsNone(sensor.RefuelVehicleSensor(self.manager,self.vehicle,'kwh','price').native_value)

    def test_binary_errors_include_benefits_and_manager_failure(self):
        problem=binary_sensor.RefuelBinarySensor(self.manager,'problem')
        self.assertFalse(problem.is_on)
        self.manager.data['benefit_errors']=[{'provider':'Q8','error':'offline'}]
        self.assertTrue(problem.is_on)
        self.assertEqual(sensor.RefuelSensor(self.manager,'errors').native_value,1)
        self.manager.last_error='offline'
        self.assertEqual(sensor.RefuelSensor(self.manager,'errors').native_value,2)

    def test_options_capacity_validation(self):
        schema=TinyRefuelOptionsFlow._vehicle_schema({},selector)
        for value in (0,-1,float('nan'),float('inf')):
            with self.subTest(value=value),self.assertRaises(vol.Invalid):
                schema({'navn':'Car','brændstof':'benzin','tank_liters':value})
        self.assertEqual(schema({'navn':'Car','brændstof':'el','batteri_kwh':2.5})['batteri_kwh'],2.5)


class OptionsTests(unittest.IsolatedAsyncioTestCase):
    async def test_shared_vehicle_add_edit_remove_preserves_stable_identity(self):
        class Flow(TinyRefuelOptionsFlow):
            @property
            def config_entry(self):
                return SimpleNamespace(options=self.saved, data={})
        flow=Flow();flow.saved={"scan_hours":8}
        created=await flow.async_step_vehicle({'navn':' Test ', 'brændstof':'diesel','tank_liters':40})
        flow.saved=created['data'];vehicle=flow.saved['vehicles'][0]
        self.assertEqual(vehicle['navn'],'Test');self.assertTrue(vehicle['vis']['diesel'])
        flow._vehicle_id=vehicle['id']
        changed=await flow.async_step_vehicle({'navn':'Renamed','brændstof':'diesel','tank_liters':45})
        self.assertEqual(changed['data']['vehicles'][0]['id'],vehicle['id'])
        self.assertEqual(changed['data']['scan_hours'],8)
        flow.saved=changed['data']
        removed=await flow.async_step_remove_vehicle({'vehicle_id':vehicle['id']})
        self.assertEqual(removed['data']['vehicles'],[])
