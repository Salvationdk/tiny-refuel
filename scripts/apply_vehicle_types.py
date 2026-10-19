"""Apply reviewed exact model-family categories without guessing new models."""
from copy import deepcopy
import json
from pathlib import Path

REVIEW = Path(__file__).parent / 'data' / 'vehicle-types.reviewed.json'


def apply_vehicle_types(catalog):
    data = deepcopy(catalog)
    reviewed = json.loads(REVIEW.read_text())['brands']
    for brand in data['brands']:
        entries = {name: types.split(',') for types, names in reviewed.get(brand['mærke'], {}).items() for name in names}
        for model in brand['modeller']:
            if not any(key in model for key in ('vehicle_types', 'vehicle_type', 'koeretoejstype')) and model['model'] in entries:
                model['vehicle_types'] = entries[model['model']]
    return data
