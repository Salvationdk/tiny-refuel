"""Shared catalog choices preserve scoped capacities and stable vehicle settings."""
from types import SimpleNamespace
from unittest.mock import AsyncMock
import unittest
from custom_components.tiny_refuel.config_flow import TinyRefuelOptionsFlow
from custom_components.tiny_refuel.sensor import RefuelCatalogStatusSensor


class Flow(TinyRefuelOptionsFlow):
    @property
    def config_entry(self):
        return SimpleNamespace(options={"scan_hours":8}, data={})


class CatalogOptionsTests(unittest.IsolatedAsyncioTestCase):
    async def test_catalog_flow_prefills_capacity_without_overwriting_user_choice(self):
        model={"model":"Test","brændstof":"benzin","tank_l":35}
        store=SimpleNamespace(get=AsyncMock(return_value={"brands":[{"mærke":"Make","modeller":[model]}]}))
        flow=Flow();flow.hass=SimpleNamespace(data={"tiny_refuel":{"catalogs":store}})
        self.assertEqual((await flow.async_step_catalog_vehicle({"koeretoejstype":"personbil"}))["step_id"],"catalog_make")
        await flow.async_step_catalog_make({"mærke":"Make"})
        form=await flow.async_step_catalog_model({"model":"Test"})
        values=form['data_schema']({"brændstof":"benzin"})
        self.assertEqual(values['tank_liters'],35)
        values['tank_liters']=40
        result=await flow.async_step_vehicle(values)
        self.assertEqual(result['data']['vehicles'][0]['tank_liters'],40)
        self.assertEqual(result['data']['vehicles'][0]['koeretoejstype'],'personbil')
        self.assertEqual(result['data']['scan_hours'],8)
        store.get.assert_awaited_once_with('personbil')

    async def test_variant_does_not_inherit_other_variants_capacity_or_fuel(self):
        flow=Flow();flow._catalog_type='personbil';flow._catalog_make={'mærke':'Make'}
        flow._catalog_model={'model':'Test','brændstof':'benzin','tank_l':80,
            'variants':[{'name':'Electric','brændstof':'el','batteri_kwh':45}]}
        form=await flow.async_step_catalog_variant({'variant_choice':'0'})
        values=form['data_schema']({})
        self.assertNotIn('tank_liters',values)
        self.assertEqual(values['batteri_kwh'],45)
        self.assertEqual(values['brændstof'],'el')
        self.assertEqual(values['variant'],'Electric')
        await flow.async_step_catalog_variant({'variant_choice':'manual'})
        self.assertNotIn('tank_liters',flow._catalog_defaults)
        self.assertNotIn('batteri_kwh',flow._catalog_defaults)

    async def test_catalog_status_distinguishes_cache_from_capacity_verification(self):
        snapshot={'loaded_types':[], 'stale_types':[]}
        entity=RefuelCatalogStatusSensor(SimpleNamespace(snapshot=lambda:snapshot))
        self.assertEqual(entity.native_value,'not_loaded')
        snapshot.update(loaded_types=['personbil'])
        self.assertEqual(entity.native_value,'ready')
        snapshot.update(stale_types=['personbil'])
        self.assertEqual(entity.native_value,'cached')
