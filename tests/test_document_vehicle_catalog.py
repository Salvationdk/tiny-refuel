from copy import deepcopy
from scripts.document_vehicle_catalog import attach, allowed, Title


def test_preserve_values_scoped_evidence_and_existing_documentation():
    original = {'brands': [{'mærke': 'MAN', 'modeller': [{'model': 'e-TGE', 'tank_l': 75, 'documentation': {'note': 'existing'}}]}]}
    before = deepcopy(original)
    row = {'make': 'MAN', 'model': 'e-TGE', 'year': 2020, 'variant': 'EV',
           'specifications': {'tank_l': 0, 'batteri_kwh': 36}, 'source_url': 'https://example.org/spec'}
    documented = attach(original, [row])
    assert original == before
    model = documented['brands'][0]['modeller'][0]
    assert model['tank_l'] == 75
    assert model['documentation'] == {'note': 'existing'}
    assert model['source_review']['batteri_kwh']['verified'] is False
    assert len(documented['source_review_data']['records']) == 1
    again = attach(documented, [row])
    assert again == documented


def test_no_substring_match_and_wikipedia_excluded():
    catalog = {'brands': [{'mærke': 'AME', 'modeller': [{'model': '4'}]}]}
    out = attach(catalog, [{'make': 'SAME', 'model': '4', 'specifications': {'tank_l': 120}, 'source_url': 'https://example.org/spec'}])
    assert 'source_review' not in out['brands'][0]['modeller'][0]
    assert not allowed('https://en.wikipedia.org/wiki/Car')
    assert not allowed('file:///tmp/spec')
    assert allowed('https://manufacturer.example/spec')


def test_new_batch_keeps_original_evidence():
    catalog = {'brands': [{'mærke': 'MAN', 'modeller': [{'model': 'e-TGE'}]}]}
    first = {'make': 'MAN', 'model': 'e-TGE', 'specifications': {'batteri_kwh': 36}, 'source_url': 'https://example.org/one'}
    second = dict(first, source_url='https://example.org/two')
    out = attach(attach(catalog, [first]), [second])
    assert len(out['source_review_data']['records']) == 2
    assert len(out['brands'][0]['modeller'][0]['source_review']['batteri_kwh']['record_ids']) == 2


def test_page_title():
    parser = Title(); parser.feed('<html><title>Vehicle &amp; specifications</title></html>')
    assert ''.join(parser.parts) == 'Vehicle & specifications'


def test_online_extract_and_resume_without_new_request(tmp_path):
    import scripts.document_vehicle_catalog as module
    calls = []
    class FakeFetcher:
        def __init__(self, *args, **kwargs): pass
        def get(self, url):
            calls.append(url)
            return '<title>Specifications</title><script type="application/ld+json">{"@type":"Car","brand":"MAN","model":"e-TGE","fuelCapacity":{"value":75,"unitCode":"LTR"}}</script>'
    original = module.PoliteFetcher
    module.PoliteFetcher = FakeFetcher
    try:
        catalog = {'brands': [{'mærke': 'MAN', 'modeller': [{'model': 'e-TGE', 'tank_l': 75}]}]}
        row = {'make': 'MAN', 'model': 'e-TGE', 'specifications': {'tank_l': 75}, 'source_url': 'https://example.org/spec'}
        documented = attach(catalog, [row])
        found = module.check_pages(documented, tmp_path)
        assert found[0]['specifications']['tank_l'] == 75
        assert len(module.check_pages(attach(catalog, [row]), tmp_path)) == 1
        assert len(calls) == 1
        assert next(iter(documented['source_review_data']['sources'].values()))['primary_source_verified'] is False
    finally:
        module.PoliteFetcher = original
