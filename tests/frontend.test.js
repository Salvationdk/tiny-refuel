const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
class Element {
  constructor() { this.events = {}; }
  addEventListener(name, fn) { this.events[name] = fn; }
  querySelector() { return null; }
  querySelectorAll() { return []; }
}
const registry = new Map();
const timers = new Map();
let timerId = 0;
const window = {
  customElements: { define: (name, type) => registry.set(name, type), get: name => registry.get(name) },
  navigator: { userAgent: 'Desktop' }, location: { href: '' },
};
const context = { window, HTMLElement: Element, customElements: window.customElements,
  document: { createElement: name => new (registry.get(name) || Element)() },
  console, URLSearchParams, Date, Map, Set, Promise,
  setTimeout: fn => { timers.set(++timerId, fn); return timerId; },
  clearTimeout: id => timers.delete(id),
};
const frontendSource = fs.readFileSync('custom_components/tiny_refuel/frontend/tiny-refuel-card-v0.1.js', 'utf8');
vm.runInNewContext(frontendSource, context);
const Card = registry.get('tiny-refuel-card');
assert.ok(Card);
assert.ok(registry.get('tiny-refuel-card-editor'));
assert.equal(window.customCards[0].type, 'tiny-refuel-card');
const editor = new (registry.get('tiny-refuel-card-editor'))();
editor.setConfig({ vis_scrape_knap: false });
assert.ok(editor.innerHTML.includes('data-key="vis_scrape_knap"'));
assert.ok(editor.innerHTML.includes('Vis knappen på kortet'));
assert.ok(editor.innerHTML.includes('data-key="scrape_valgt_bil"'));
const card = new Card();
assert.equal(card._progressText({ phase: 'benzin/diesel', provider: 'Shell' }), 'Henter benzin/diesel fra Shell…');
assert.equal(card._progressText({ phase: 'el', provider: 'Circle K', station: 'Hovedgaden', current: 2, total: 7 }),
  'Henter el fra Circle K · Hovedgaden (2/7)…');
card._config = { vis_benzin: false, vis_diesel: false, vis_el: true, vis_andet: true };
card._render = () => {};
card._data = { updated: '2026-01-01T00:00:00Z', benefits: {
  circle_k: { summary: 'Eksempel på scraped fordel', source_url: 'https://circlek.example/fordele',
    fetched_at: '2026-10-09T10:00:00+00:00', status: 'ok' },
  q8: { summary: 'Q8 kort giver rabat på bilvask.', source_url: 'https://q8.example/kort',
    fetched_at: '2026-10-09T10:00:00+00:00', status: 'ok' },
  f24: { summary: null, source_url: 'https://f24.example/fordele', status: 'source_only' },
}, ev: [
  { brand: 'Q8', name: 'A', address: 'A vej 1', lat: 55.64, lon: 12.08, app_only: true, kind: 'DC' },
  { brand: 'Q8', name: 'B', address: 'B vej 2', lat: 56, lon: 12, kwh: 3.89, kind: 'DC' },
  { brand: 'Q8', name: 'Q8 Lyn', kwh: 3.89 },
  { brand: 'OK', name: 'C', location_id: 'ok1', address: 'C vej 3', lat: 55.65, lon: 12.08, kind: 'Normal', app_only: true },
  { brand: 'OK', name: 'C', location_id: 'ok1', address: 'C vej 3', lat: 55.65, lon: 12.08, kind: 'Lyn', app_only: true },
  { brand: 'Circle K', name: 'Lynlader (listepris)', kwh: 3.99, lu: '2026-10-01' },
  { brand: 'E.ON', name: 'AC (fra)', kwh: 3.25 },
  { brand: 'IONITY', name: 'App/kontaktløs (minimum)', kwh: 3.86,
    tariff_note: 'IONITY oplyser, at den faktiske stationspris kan være højere.' },
  { brand: 'Spirii', name: 'Excluded', kwh: 2 },
] };
card._openFordel = 'ev:circle_k:provider:';
const scrapedBenefit = card._evBenefits({ brand: 'Circle K' }, 'box');
assert.ok(scrapedBenefit.includes('Eksempel på scraped fordel'));
assert.ok(scrapedBenefit.includes('https://circlek.example/fordele'));
assert.ok(scrapedBenefit.includes('Hentet: 2026-10-09'));
assert.equal(card._evBenefits({ brand: 'F24' }, 'button'), '');
assert.equal(card._benefitBox('f24', 'F24', card._data.benefits.f24), '');
const q8ButtonA = card._evBenefits({ brand: 'Q8', address: 'A vej 1', kind: 'DC' }, 'button');
const q8ButtonB = card._evBenefits({ brand: 'Q8', address: 'B vej 2', kind: 'DC' }, 'button');
const q8KeyA = q8ButtonA.match(/data-fordel="([^"]+)"/)[1];
const q8KeyB = q8ButtonB.match(/data-fordel="([^"]+)"/)[1];
assert.notEqual(q8KeyA, q8KeyB);
card._openFordel = q8KeyA;
assert.ok(card._evBenefits({ brand: 'Q8', address: 'A vej 1', kind: 'DC' }, 'box').includes('Q8 kort giver rabat'));
assert.equal(card._evBenefits({ brand: 'Q8', address: 'B vej 2', kind: 'DC' }, 'box'), '');
const html = card._evHtml({ lat: 55.63, lon: 12.08 });
assert.ok(html.includes('<div class="trf-ev-grid">'));
assert.equal((html.match(/logo-q8.svg/g) || []).length, 1);
assert.ok(html.includes('3 ladesteder'));
assert.ok(html.includes('1 med lokal elpris'));
assert.ok(html.includes('3,99'));
assert.ok(html.includes('Pris opdateret'));
assert.ok(html.includes('den faktiske stationspris kan være højere'));
assert.ok(!html.includes('Spirii'));
assert.ok(!html.includes('Find OK-ladesteder'));
card._openEvBrand = 'Q8';
const popup = card._evPopupHtml({ lat: 55.63, lon: 12.08 });
assert.ok(popup.includes('class="trf-ev-list"'));
assert.ok(popup.includes('Tryk på et logo for navigation'));
assert.ok(!popup.includes('Navigér hertil'));
for (const nav of ['waze', 'google']) {
  card._config.navigation = nav;
  const url = card._navHref('55.64,12.08', 'Q8');
  assert.ok(url.includes(nav === 'waze' ? 'll=55.64,12.08' : 'destination=55.64%2C12.08'));
  assert.ok(card._evRow(card._data.ev[0], null, 1, true).includes(url.replace(/&/g, '&amp;')));
}
(async () => {
  const calls = [], apiCalls = [];
  let response = { ...card._data, refreshing: true };
  card._hass = {
    callService: (...args) => { calls.push(args); return Promise.resolve(); },
    callApi: (...args) => { apiCalls.push(args); return Promise.resolve(response); },
  };
  card._scrapeAll(); card._scrapeAll();
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], 'tiny_refuel');
  assert.equal(calls[0][1], 'refresh');
  card._pollScrape(card._scrapeRun);
  await new Promise(setImmediate);
  assert.equal(card._scraping, true);
  response = { ...response, updated: new Date().toISOString(), refreshing: false, errors: [{ error: 'Kilde HTTP 403' }] };
  card._pollScrape(card._scrapeRun);
  await new Promise(setImmediate);
  assert.equal(card._scraping, false);
  assert.ok(card._scrapeMessage.includes('1 fejl'));
  assert.ok(apiCalls.every(args => args[0] === 'GET' && args[1] === 'tiny_refuel/data'));
  const scoped = new Card();
  scoped._config = { biler: [{ navn: 'Min dieselbil', brændstof: 'diesel' }] };
  scoped._hass = { callService: (...args) => { calls.push(args); return Promise.resolve(); } };
  scoped._scrapeAll();
  assert.equal(JSON.stringify(calls[calls.length - 1][2]), JSON.stringify({ fuel_types: ['diesel'] }));
  scoped.disconnectedCallback();
  card._scrapeAll();
  response = { ...response, last_attempt: new Date().toISOString(), last_error: 'Failed source', refreshing: false };
  card._pollScrape(card._scrapeRun);
  await new Promise(setImmediate);
  assert.equal(card._scraping, false);
  assert.ok(card._scrapeMessage.includes('Failed source'));
  card._hass.callApi = () => Promise.reject(new Error('Offline'));
  assert.equal(await card._fetchJson(), null);
  card.disconnectedCallback();
  assert.equal(card._scraping, false);
  console.log('PASS: frontend grouping, counts, navigation, authenticated API and shared refresh');
})().catch(error => { console.error(error); process.exitCode = 1; });

// Keep fuel rows visible while coordinate lookup is incomplete.
{
  const fuel = new Card();
  fuel._config = { vis_benzin: true, vis_diesel: true, vis_el: false };
  fuel._data = { stations: [
    { brand: "Go'on", name: 'Go on A', address: 'A vej 1', p95: 14.5, lat: null, lon: null },
    { brand: 'Shell', name: 'Shell A', address: 'B vej 2', p95: 15, diesel: 13.9, lat: null, lon: null },
  ] };
  for (const loc of [null, { lat: 55.6, lon: 12.1 }]) {
    const rows = fuel._buildRows(loc).filter(r => ['goon', 'shell'].includes(r.b.key));
    assert.equal(rows.length, 2);
    for (const row of rows) {
      assert.ok(row.v95 > 0);
      assert.ok(row.stAddr);
      assert.equal(row.km, null);
      assert.equal(Boolean(row.locationNote), Boolean(loc));
    }
  }
  fuel._data.stations[0].stale = true;
  fuel._data.version = '0.2.0';
  fuel._render();
  assert.ok(fuel.innerHTML.includes('class="trf-fuel-grid"'));
  assert.equal((fuel.innerHTML.match(/class="trf-fuel-col"/g) || []).length, 0);
  assert.ok(fuel.innerHTML.includes('data-label="95"'));
  assert.ok(fuel.innerHTML.includes('data-label="Diesel"'));
  assert.ok(fuel.innerHTML.includes('13,90'));
  assert.ok(fuel.innerHTML.includes('Tiny Refuel v0.2.0'));
  assert.ok(fuel.innerHTML.includes('trf-stale-tag">Gemt'));
  fuel._data.stations.push({ brand: 'Shell', name: 'Shell B', address: 'C vej 3', p95: 16, lat: 55.61, lon: 12.11 });
  const row = fuel._buildRows({ lat: 55.6, lon: 12.1 }).find(r => r.b.key === 'shell');
  assert.equal(row.stAddr, 'C vej 3');
  assert.ok(row.km > 0);
  assert.ok(row.locationNote.includes('kendte koordinater'));
  fuel._data.stations = [];
  assert.equal(fuel._buildRows({ lat: 55.6, lon: 12.1 }).find(r => r.b.key === 'shell').v95, null);
}

// Both screen orientations use the same list layout.
assert.ok(!frontendSource.includes('@media (orientation:'));
assert.ok(!frontendSource.includes('grid-template-columns: repeat(5, minmax(0, 1fr))'));
assert.ok(frontendSource.includes('.trf-fuel-grid, .trf-ev-grid { display: contents; }'));
assert.ok(frontendSource.includes('fuelHtmlRows.join'));
assert.ok(frontendSource.includes('evHtmlRows.join'));
assert.ok(!frontendSource.includes('grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) !important'));

// Fuel source health and geocoding backlog remain visible from the data file.
{
  const status = new Card();
  status._config = { vis_benzin: true, vis_diesel: true };
  status._data = { geocode_pending: 2, fuel_sources: {
    'api.circlek.com': { status: 'stale', records: 8, priced: 7, missing_coordinates: 2, last_attempt: '2026-10-10T10:00:00Z', error: 'Offline' },
    'goon.nu': { status: 'ok', records: 4, priced: 4, missing_coordinates: 0, last_success: '2026-10-10T10:00:00Z' },
  } };
  const summary = status._fuelDataSummary();
  assert.ok(summary.includes('Circle K og Ingo'));
  assert.ok(summary.includes('Gemte data · nyt forsøg fejlede'));
  assert.ok(summary.includes('2 adresser afventer koordinater'));
  assert.ok(summary.includes('Offline'));
}

assert.ok(!/tesla/i.test(frontendSource), 'Tesla should be removed from the card UI');
