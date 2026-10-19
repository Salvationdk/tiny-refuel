"""Explicit DMR kind mappings; unknown kinds never acquire a guessed category."""
CODES = {'1': 'personbil', '2': 'bus', '3': 'varebil', '4': 'lastbil',
         '7': 'motorcykel', '8': 'traktor', '16': 'knallert', '17': 'knallert', '91': 'andet'}
NAMES = {'personbil': 'personbil', 'stor personbil': 'bus', 'bus': 'bus',
         'varebil': 'varebil', 'varevogn': 'varebil', 'lastbil': 'lastbil',
         'motorcykel': 'motorcykel', 'traktor': 'traktor', 'knallert': 'knallert',
         'stor knallert': 'knallert', 'lille knallert': 'knallert',
         'motorkøretøj': 'andet', 'atv': 'andet', 'motordrevet blokvogn': 'andet'}


def vehicle_types(codes=(), names=()):
    return sorted({CODES[str(code).strip()] for code in codes if str(code).strip() in CODES}
                  | {NAMES[str(name).strip().casefold()] for name in names if str(name).strip().casefold() in NAMES})
