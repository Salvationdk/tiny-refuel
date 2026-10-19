import json
from pathlib import Path
from types import SimpleNamespace
from scripts.verify_vehicle_catalog import compare, run, targets


def catalog(**values):
    return {'brands': [{'mærke': 'MAN', 'modeller': [{'model': 'e-TGE', **values}]}]}


def test_exact_identity_no_brand_or_model_substrings():
    evidence = [{'make': 'MAN', 'model': 'TGE', 'specifications': {'tank_l': 75}, 'source_url': 'https://example.org/spec'}]
    rows, _ = compare(catalog(tank_l=75), evidence)
    assert all(r['status'] == 'no_evidence' for r in rows)


def test_equal_value_still_requires_scope_review():
    evidence = [{'make': 'MAN', 'model': 'e-TGE', 'year': 2020, 'specifications': {'tank_l': 75}, 'source_url': 'https://example.org/spec'}]
    rows, _ = compare(catalog(tank_l=75), evidence)
    assert rows[0]['status'] == 'value_agrees_review_scope'
    assert rows[0]['verified'] is False
    evidence[0]['specifications']['tank_l'] = 60
    assert compare(catalog(tank_l=75), evidence)[0][0]['status'] == 'possible_conflict_review_scope'


def test_battery_basis_unknown_not_comparable():
    evidence = [{'make': 'MAN', 'model': 'e-TGE', 'specifications': {'batteri_kwh': 36}, 'battery_basis': 'gross', 'source_url': 'https://example.org/spec'}]
    rows, _ = compare(catalog(batteri_kwh=36), evidence)
    assert rows[1]['status'] == 'battery_basis_unresolved'


def test_full_catalog_targets_and_flags():
    data = catalog(tank_l=120, batteri_kwh=0, vehicle_types=['motorcykel'])
    assert targets(data)[0]['missing'] == ['tank_l', 'batteri_kwh', 'brændstof']
    _, suspicious = compare(data, [])
    assert len(suspicious[0]['flags']) == 2


def test_local_run_preserves_input_and_writes_zip(tmp_path):
    path = tmp_path / 'catalog.json'
    raw = json.dumps(catalog(tank_l=75)).encode()
    path.write_bytes(raw)
    out = tmp_path / 'out'
    summary = run(SimpleNamespace(input=str(path), output=str(out), skip_online=True, candidates=[]))
    assert path.read_bytes() == raw
    assert summary['models'] == 1
    assert (out / 'kontrol-resultat.zip').is_file()


def test_register_match_does_not_verify_capacity():
    from scripts.verify_vehicle_catalog import compare_register
    rows = compare_register(catalog(tank_l=75), catalog(fuel_types=['El']))
    assert rows[0]['identity_found_in_extract'] is True
    assert rows[0]['registered_fuels'] == ['El']
    assert rows[0]['capacity_verified_by_dmr'] is False
