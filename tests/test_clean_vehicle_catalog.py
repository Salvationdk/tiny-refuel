import copy
import unittest
from scripts.clean_vehicle_catalog import clean

class CleanVehicleCatalogTests(unittest.TestCase):
    def test_quarantine_aliases_and_variants_preserve_data(self):
        data={'brands':[
            {'mærke':'CHERVOLET','modeller':[{'model':'A','tank_l':40,'variants':[{'name':'Turbo','fuel_types':['Benzin']}]}]},
            {'mærke':'Chevrolet','modeller':[{'model':'a','battery_kwh':20,'variants':[{'name':' turbo ','fuel_types':['El']}]}]},
            {'mærke':'10279','modeller':[{'model':'Do not lose this'}]},
            {'mærke':'TESTKØRSEL','modeller':[{'model':'A'}]},
            {'mærke':'AC','modeller':[{'model':'123'},{'model':'A-B'},{'model':'AB'}]}],
            'logos':{'Chevrolet':'SVG'},'custom':{'preserve':True}}
        original=copy.deepcopy(data)
        result,report,excluded=clean(data)
        self.assertEqual(data,original)
        self.assertEqual(len(excluded),2)
        self.assertEqual(excluded[0]['entry']['modeller'][0]['model'],'Do not lose this')
        self.assertEqual(result['logos'],data['logos'])
        self.assertEqual(result['custom'],data['custom'])
        chevy=next(b for b in result['brands'] if b['mærke']=='Chevrolet')
        self.assertEqual(len(chevy['modeller']),1)
        model=chevy['modeller'][0]
        self.assertEqual(model['tank_l'],40)
        self.assertEqual(model['battery_kwh'],20)
        self.assertEqual(set(model['variants'][0]['fuel_types']),{'Benzin','El'})
        self.assertEqual(len(next(b for b in result['brands']if b['mærke']=='AC')['modeller']),3)
        self.assertFalse(report['requires_review'])
        self.assertEqual(report['logo_coverage']['register_makes'],2)

    def test_conflicting_values_preserved(self):
        data={'brands':[{'mærke':'A','modeller':[{'model':'123','tank_l':40},{'model':'123','tank_l':50}]}]}
        result,report,_=clean(data)
        model=result['brands'][0]['modeller'][0]
        self.assertEqual(model['tank_l'],40)
        self.assertEqual(model['cleanup_alternatives']['tank_l'],[50])
        self.assertTrue(report['requires_review'])

    def test_composite_names_do_not_inherit_base_make_logo(self):
        data={'brands':[{'mærke':'Fiat / Hobby','modeller':[{'model':'A'}]},
                        {'mærke':'Fiat/Hobby','modeller':[{'model':'a'}]}],
              'logos':{'Fiat':'SVG'}}
        result,report,_=clean(data)
        self.assertEqual(len(result['brands']),1)
        self.assertEqual(result['brands'][0]['mærke'],'Fiat/Hobby')
        self.assertEqual(report['logo_coverage']['covered'],0)
        self.assertEqual(report['logo_coverage']['pending_combined'],1)
        self.assertEqual(len(result['brands'][0]['modeller']),1)
