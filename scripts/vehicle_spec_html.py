"""Extract explicitly reviewed manufacturer HTML rules; no fuzzy identity matching."""
from html.parser import HTMLParser
import math
import re
from urllib.parse import urlsplit


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript'):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript'):
            self.skip = max(0, self.skip - 1)

    def handle_data(self, value):
        if not self.skip:
            self.parts.append(value)


def visible_text(page):
    parser = VisibleText()
    parser.feed(page)
    return ' '.join(' '.join(parser.parts).split())


def extract_reviewed_html(page, source):
    """Source rules pin a URL, identity marker and contextual numeric field pattern.

    All results remain review candidates. Source year/variant must also have an
    explicit evidence marker; configuration alone is never proof of applicability.
    """
    if source.get('parser') != 'reviewed_html' or source.get('mapping_reviewed') is not True:
        return [], ['unreviewed_html_mapping']
    if urlsplit(source['url']).hostname != source.get('allowed_host'):
        return [], ['unreviewed_source_host']
    text = visible_text(page)
    marker = source.get('identity_marker', '')
    if not marker or marker.casefold() not in text.casefold():
        return [], ['vehicle_identity_marker_missing']
    for field in ('year', 'variant'):
        if source.get(field) is not None:
            evidence = source.get(field + '_evidence')
            if not evidence or str(evidence).casefold() not in text.casefold():
                return [], [field + '_evidence_missing']
    specifications, evidence, warnings = {}, {}, []
    for rule in source.get('html_rules', []):
        field = rule.get('field')
        if field not in ('tank_l', 'batteri_kwh'):
            raise ValueError('Unsupported HTML capacity field')
        pattern = re.compile(rule['pattern'], re.IGNORECASE)
        matches = list(pattern.finditer(text))
        values = set()
        for match in matches:
            raw = match.group('value')
            unit = match.group('unit').casefold()
            number = float(raw.replace(',', '.'))
            units = {'tank_l': {'l': 1, 'litres': 1, 'liters': 1},
                     'batteri_kwh': {'kwh': 1, 'wh': 0.001}}[field]
            if unit in units and math.isfinite(number) and number > 0:
                values.add(round(number * units[unit], 6))
        if len(values) > 1:
            warnings.append('conflicting_' + field)
        elif len(values) == 1:
            specifications[field] = values.pop()
            evidence[field] = ' '.join(matches[0].group(0).split()[:18])
    if not specifications:
        return [], warnings or ['capacity_pattern_missing']
    item = {'make': source['make'], 'model': source['model'],
            'year': source.get('year'), 'variant': source.get('variant'),
            'specifications': specifications, 'battery_basis': source.get('battery_basis', 'unspecified'),
            'source_url': source['url'], 'source_vehicle': marker,
            'evidence': evidence, 'parser': 'reviewed_html', 'review_required': True,
            'scope_note': source.get('scope_note', 'Manufacturer page; model years and all variants not established.')}
    return [item], warnings
