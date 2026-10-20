"""Catalog integrity, per-type requests and offline recovery without live requests."""
import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('type_store',ROOT/'custom_components/tiny_refuel/catalog_store.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class CatalogTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)
        self.catalog={'vehicle_type':'personbil','brands':[{'mærke':'VW','modeller':[{'model':'up!','tank_l':35,'vehicle_types':['personbil']}]}]}
        self.raw=json.dumps(self.catalog).encode()
        self.index={'schema_version':1,'version':'1','catalogs':{'personbil':{'file':'car.json','size_bytes':len(self.raw),'sha256':hashlib.sha256(self.raw).hexdigest()}}}
        self.calls=[]
        self.bundled=self.folder/'bundled.json';self.bundled.write_text(json.dumps(self.catalog))
    async def fetch(self,url,limit):
        self.calls.append(url)
        await asyncio.sleep(0)
        return json.dumps(self.index).encode() if url.endswith('index.json') else self.raw
    def store(self,fetch=None):return mod.CatalogStore(self.folder/'cache',fetch or self.fetch,self.bundled)
    async def test_only_selected_catalog_and_coalesced_requests(self):
        store=self.store();rows=await asyncio.gather(store.get('personbil'),store.get('personbil'))
        self.assertEqual(rows[0]['brands'],self.catalog['brands'])
        self.assertEqual(len(self.calls),2)
        self.assertTrue(self.calls[-1].endswith('/car.json'))
        self.assertTrue((self.folder/'cache/car.json').exists())
    async def test_restart_offline_uses_persistent_cache(self):
        await self.store().get('personbil')
        async def offline(*args):raise OSError('offline')
        result=await self.store(offline).get('personbil')
        self.assertEqual(result['brands'],self.catalog['brands']);self.assertTrue(result['_download']['stale'])
    async def test_bad_download_cannot_replace_good_cache(self):
        await self.store().get('personbil')
        before=(self.folder/'cache/car.json').read_bytes()
        self.index['catalogs']['personbil']['sha256']='0'*64
        self.raw=b'{"brands":[]}'
        result=await self.store().get('personbil')
        self.assertEqual(result['brands'],self.catalog['brands'])
        self.assertEqual((self.folder/'cache/car.json').read_bytes(),before)
    async def test_unknown_type_rejected_before_request(self):
        with self.assertRaises(ValueError):await self.store().get('../car')
        self.assertFalse(self.calls)
    async def test_manifest_cannot_choose_external_or_parent_path(self):
        self.index['catalogs']['personbil']['file']='../other.json'
        result=await self.store().get('personbil')
        self.assertEqual(result['_download']['source'],'bundled');self.assertEqual(len(self.calls),1)
    async def test_no_network_has_type_filtered_bundled_fallback(self):
        async def offline(*args):raise OSError('offline')
        store=self.store(offline)
        result=await store.get('personbil');self.assertEqual(len(result['brands']),1)
        result=await store.get('lastbil');self.assertEqual(result['brands'],[])
    async def test_all_generated_catalog_hashes_and_schema(self):
        folder=ROOT/'catalogs/v1';manifest=json.loads((folder/'index.json').read_text())
        for type_,entry in manifest['catalogs'].items():
            raw=(folder/entry['file']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),entry['sha256'])
            self.assertEqual(len(raw),entry['size_bytes'])
            data=mod.validate_catalog(json.loads(raw));self.assertEqual(data['vehicle_type'],type_)
            for brand in data['brands']:
                self.assertFalse(brand['mærke'].isdigit())
                for model in brand['modeller']:
                    self.assertIn(type_,model['vehicle_types'] or ['andet']) if type_!='andet' else None
                    self.assertNotIn('source_review',model)
    async def test_bad_capacity_rejected(self):
        self.catalog['brands'][0]['modeller'][0]['tank_l']=-1
        with self.assertRaises(ValueError):mod.validate_catalog(self.catalog)

if __name__=='__main__':unittest.main()
