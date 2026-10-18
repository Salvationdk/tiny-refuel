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
  CustomEvent: class { constructor(type, options) { this.type = type; Object.assign(this, options); } },
  document: { createElement: name => new (registry.get(name) || Element)() },
  console, URLSearchParams, Date, Map, Set, Promise,
  setTimeout: fn => { timers.set(++timerId, fn); return timerId; },
  clearTimeout: id => timers.delete(id),
};
const frontendSource = fs.readFileSync('custom_components/tiny_refuel/frontend/tiny-refuel-card.js', 'utf8');
vm.runInNewContext(frontendSource, context);
// Loading the canonical module through both HA and a legacy resource is harmless.
const beforeReload = new Map(registry);
vm.runInNewContext(frontendSource, context);
assert.deepEqual(registry, beforeReload);
const Card = registry.get('tiny-refuel-card');
assert.ok(Card);
assert.ok(registry.get('tiny-refuel-card-editor'));
assert.equal(window.customCards[0].type, 'tiny-refuel-card');
const editor = new (registry.get('tiny-refuel-card-editor'))();
editor.setConfig({ vis_scrape_knap: false });
assert.ok(editor.innerHTML.includes('data-key="vis_scrape_knap"'));
assert.ok(editor.innerHTML.includes('Vis knappen på kortet'));
assert.ok(editor.innerHTML.includes('data-key="scrape_valgt_bil"'));
assert.ok(editor.innerHTML.includes('class="trfe-brand-grid"'));
assert.ok(editor.innerHTML.includes('src="/tiny_refuel/static/logos/logo-circle-k.svg"'));
assert.ok(editor.innerHTML.includes('src="/tiny_refuel/static/logos/logo-ionity.svg"'));
assert.ok(editor.innerHTML.includes('Stationer og udbydere'));
assert.match(editor.innerHTML, /data-key="vis_benzin" checked>/);
assert.match(editor.innerHTML, /data-key="vis_scrape_knap">/);
assert.match(editor.innerHTML, /data-key="kæde:circle_k" checked><img/);
for (const tag of editor.innerHTML.match(/<input\b[^>]*>/g) || []) {
  assert.ok(!tag.includes('<img') && !tag.includes('<span'), 'input tags must close before logo and label elements');
}
editor.setConfig({ kaeder: { circle_k: false } });
assert.match(editor.innerHTML, /data-key="kæde:circle_k"><img/);
assert.ok(editor.innerHTML.includes('Ingen bil tilføjet endnu'));
assert.ok(editor.innerHTML.includes('manuel hentning tager alle typer'));
editor._katalog = { brands: [], logos: { Volkswagen: '<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0"/></svg>' }, logo_pngs: { Hongqi: 'iVBORw0KGgoAAA==' } };
editor.setConfig({ biler: [{ navn: 'Testbil', mærke: 'Volkswagen', model: 'up!' }] });
assert.ok(editor.innerHTML.includes('data-car-toggle="0"'));
assert.ok(editor.innerHTML.includes('alt="Volkswagen logo"'));
assert.ok(editor.innerHTML.includes('data:image/svg+xml,%3Csvg'));
editor.setConfig({ biler: [{ navn: 'Hongqi-bil', mærke: 'Hongqi' }] });
assert.ok(editor.innerHTML.includes('alt="Hongqi logo"'));
assert.ok(editor.innerHTML.includes('data:image/png;base64,iVBORw0KGgoAAA=='));
editor.setConfig({ biler: [{ navn: 'Anden bil', mærke: 'Mitsubishi' }] });
assert.ok(!editor.innerHTML.includes('alt="Mitsubishi logo"'), 'brands without a packaged logo keep the text label');
assert.ok(editor.innerHTML.includes('title="Vis benzinpriser fra de valgte selskaber."'));
// Exercise every packaged logo through the editor, including real PNG files.
const catalogRoot = 'custom_components/tiny_refuel/frontend/';
const catalogManifest = JSON.parse(fs.readFileSync(catalogRoot + 'bilkatalog.json', 'utf8'));
function readPackagedCatalog() {
  const catalog = JSON.parse(catalogManifest.catalog_parts.map(part => fs.readFileSync(catalogRoot + part, 'utf8')).join(''));
  const defaults = catalog.model_defaults || {};
  delete catalog.model_defaults; delete catalog.catalog_schema;
  for (const brand of catalog.brands) {
    for (const model of brand.modeller) {
      if (!model._no_defaults) for (const [key, value] of Object.entries(defaults)) if (model[key] === undefined) model[key] = value;
      delete model._no_defaults;
    }
    for (const part of brand.detail_files || []) {
      const details = JSON.parse(fs.readFileSync(catalogRoot + part.file, 'utf8'));
      details.forEach((row, index) => Object.assign(brand.modeller[part.start + index], row));
    }
    delete brand.detail_files;
  }
  return catalog;
}
const packagedCatalog = readPackagedCatalog();
editor._katalog = packagedCatalog;
for (const brand of packagedCatalog.brands) {
  editor.setConfig({ biler: [{ mærke: brand.mærke }] });
  const assetMake = packagedCatalog.logo_aliases[brand.mærke] || brand.mærke;
  const png = packagedCatalog.logo_pngs[assetMake];
  const svg = packagedCatalog.logos[assetMake];
  const source = packagedCatalog.logo_urls && packagedCatalog.logo_urls[assetMake];
  if (png) {
    assert.equal(Buffer.from(png, 'base64').subarray(0, 8).toString('hex'), '89504e470d0a1a0a');
    assert.ok(editor.innerHTML.includes('data:image/png;base64,' + png));
    assert.ok(!/\s/.test(png), 'packaged PNG data must contain no whitespace');
  } else if (svg) {
    assert.ok(editor.innerHTML.includes('data:image/svg+xml,' + encodeURIComponent(svg)));
  } else if (source) {
    assert.ok(editor.innerHTML.includes('src="' + source.url + '"'));
  } else {
    assert.ok(!editor.innerHTML.includes('class="trfe-car-logo"'));
  }
}
// A custom catalog must not be able to inject attributes through PNG data.
editor._katalog = { brands: [], logo_pngs: { Test: 'iVBORw0KGgo" onerror="injected' } };
editor.setConfig({ biler: [{ mærke: 'Test' }] });
assert.ok(!editor.innerHTML.includes('onerror='));
assert.ok(!editor.innerHTML.includes('class="trfe-car-logo"'));

// Committing a text field while clicking Save must not rebuild the editor,
// including when HA echoes the config with a different object-key order.
const StableEditor = registry.get('tiny-refuel-card-editor');
const stable = new StableEditor();
stable._katalog = packagedCatalog;
stable.setConfig({ type: 'custom:tiny-refuel-card', biler: [{ mærke: 'Volkswagen', navn: 'Bil 1' }] });
const stableRender = stable._render.bind(stable);
let editorRenders = 0;
stable._render = (...args) => { editorRenders++; stableRender(...args); };
stable.dispatchEvent = event => {
  assert.equal(event.type, 'config-changed');
  assert.equal(event.bubbles, true);
  assert.equal(event.composed, true);
  const echoed = JSON.parse(JSON.stringify(event.detail.config));
  stable.setConfig(Object.fromEntries(Object.entries(echoed).reverse()));
};
const change = (key, value) => stable.events.change({ target: { dataset: { key }, value } });
change('bil:0:navn', 'Min bil');
change('bil:0:model', 'up!');
change('bil:0:location_entity', 'device_tracker.telefon');
change('bil:0:tank_liters', '36');
assert.equal(editorRenders, 0, 'blur and config echoes must preserve the live form');
assert.equal(stable._config.biler[0].navn, 'Min bil');
assert.equal(stable._config.biler[0].model, 'up!');
assert.equal(stable._config.biler[0].brændstof, 'benzin');
assert.equal(stable._config.biler[0].tank_liters, 36);
assert.equal(stable._config.biler[0].location_entity, 'device_tracker.telefon');
stable.style = { values: {}, setProperty(key, value) { this.values[key] = value; } };
stable.hass = { states: { 'device_tracker.telefon': {} }, themes: { darkMode: false } };
const trackerRenderCount = editorRenders;
stable.hass = { states: { 'device_tracker.telefon': { state: 'away' } }, themes: { darkMode: true } };
assert.equal(editorRenders, trackerRenderCount, 'GPS and theme updates must not rebuild editor fields');
assert.equal(stable.style.values['--trf-vehicle-logo-filter'], 'invert(1)');
assert.equal(stable.style.values['--trf-vehicle-logo-blend'], 'screen');
assert.equal(stable.style.values['--trf-white-logo-filter'], 'none');
stable.hass = { states: { 'device_tracker.telefon': {} }, themes: { darkMode: false } };
assert.equal(stable.style.values['--trf-vehicle-logo-filter'], 'none');

// A late catalog render preserves open sections and an uncommitted text draft.
const focusedEditor = new StableEditor();
focusedEditor.setConfig({ biler: [{ navn: 'Bil 1' }] });
const oldFocus = { dataset: { key: 'bil:0:navn' }, value: 'I gang med navn', selectionStart: 5, selectionEnd: 8 };
const newFocus = { value: '', focus(options) { this.focusOptions = options; }, setSelectionRange(start, end) { this.selection = [start, end]; } };
const section = open => ({ open, getAttribute(name) { return name === 'data-editor-section' ? 'providers' : null; } });
const oldSection = section(true), newSection = section(false);
let replaced = false;
Object.defineProperty(focusedEditor, 'innerHTML', { configurable: true, set() { replaced = true; } });
focusedEditor.getRootNode = () => ({ activeElement: oldFocus });
focusedEditor.contains = node => node === oldFocus;
focusedEditor.querySelectorAll = () => [replaced ? newSection : oldSection];
focusedEditor.querySelector = selector => selector === '[data-key="bil:0:navn"]' ? newFocus : null;
focusedEditor._render();
assert.equal(newSection.open, true);
assert.equal(newFocus.value, oldFocus.value);
assert.deepEqual(newFocus.selection, [5, 8]);
assert.equal(newFocus.focusOptions.preventScroll, true);

const logoPanel = new Card();
logoPanel._katalog = packagedCatalog;
logoPanel.setConfig({ biler: [{ mærke: 'Citroën', model: 'C3', navn: 'Min C3', brændstof: 'benzin' }] });
assert.ok(logoPanel.innerHTML.includes('class="trf-car-logo"'));
assert.ok(logoPanel.innerHTML.includes('class="trf-model-logo"'));
assert.ok(logoPanel.innerHTML.includes('Min C3'));
for (const [make, models] of Object.entries(packagedCatalog.model_logos)) {
  for (const [model, entry] of Object.entries(models)) {
    const panel = new Card();
    panel._katalog = packagedCatalog;
    panel.setConfig({ biler: [{ mærke: make, model }] });
    const src = entry.svg ? 'data:image/svg+xml,' + encodeURIComponent(entry.svg) : entry.url;
    assert.ok(panel.innerHTML.includes('src="' + src + '"'), 'model logo must appear in controls: ' + make + ' ' + model);
    assert.ok(entry.source_url, 'every model logo must record its source');
  }
}
const modelUrl = packagedCatalog.model_logos['Citroën'].C3.url;
const failedImage = { dataset: { vehicleLogo: 'true' }, getAttribute: () => modelUrl };
logoPanel.events.error({ target: failedImage });
assert.equal(failedImage.hidden, true);
logoPanel._render();
assert.ok(!logoPanel.innerHTML.includes('class="trf-model-logo"'));
assert.ok(logoPanel.innerHTML.includes('Min C3'), 'failed model images retain the usable vehicle label');
assert.ok(logoPanel.innerHTML.includes('data-model-fallback title='), 'failed model images reveal a model-name fallback');
const customCatalogPanel = new Card();
customCatalogPanel._katalog = { brands: [{ mærke: 'Eget mærke', modeller: [{ model: 'Egen model' }] }] };
customCatalogPanel.setConfig({ biler: [{ mærke: 'Eget mærke', model: 'Egen model', navn: 'Min bil' }] });
assert.ok(customCatalogPanel.innerHTML.includes('data-make-fallback>Eget mærke</span>'));
assert.ok(customCatalogPanel.innerHTML.includes('>Egen model</span>'));
assert.ok(customCatalogPanel.innerHTML.includes('>Min bil</span>'));
const unsourcedPanel = new Card();
unsourcedPanel._katalog = packagedCatalog;
unsourcedPanel.setConfig({ biler: [{ mærke: 'Volkswagen', model: 'up!' }] });
assert.ok(unsourcedPanel.innerHTML.includes('data-model-fallback title='));
assert.ok(unsourcedPanel.innerHTML.includes('>up!</span>'));
assert.ok(unsourcedPanel.innerHTML.includes('aria-label="Volkswagen up!"'));
for (const model of ['Macan Electric', 'Cayenne E-Hybrid']) {
  const variantPanel = new Card();
  variantPanel._katalog = packagedCatalog;
  variantPanel.setConfig({ biler: [{ mærke: 'Porsche', model }] });
  assert.ok(variantPanel.innerHTML.includes('<span>Porsche ' + model + '</span>'), 'family emblems must preserve the visible variant name');
}

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
  { brand: 'Q8', name: 'Q8 Lyn (150 kW)', kwh: 3.89 },
  { brand: 'OK', name: 'Normallader', kwh: 3.49 },
  { brand: 'OK', name: 'Hurtiglader', kwh: 3.69 },
  { brand: 'OK', name: 'Lynlader', kwh: 3.89 },
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
assert.equal(card._evPublicTariff(card._data.ev[0]).kwh, 3.89);
assert.equal(card._evPublicTariff(card._data.ev[0]).label, 'indicative');
assert.equal(card._evPublicTariff(card._data.ev[6]).kwh, 3.49);
assert.equal(card._evPublicTariff(card._data.ev[6]).label, 'indicative');
assert.ok(card._evRow(card._data.ev[0], null, 1, true).includes('3,89*'));
assert.ok(card._evRow(card._data.ev[6], null, 1, true).includes('3,49*'));
assert.ok(card._evRow(card._data.ev[0], null, 1, true).includes('lokale pris kan afvige'));
const noPublicPrice = card._evRow({ brand: 'Shell', name: 'Shell Recharge', address: 'Testvej 1', kind: 'DC' }, null, 1, true);
assert.ok(noPublicPrice.includes('Se pris'));
card._data.ev.push({ brand: 'Circle K', name: 'Lynlader (listepris)', kwh: 3.99 });
assert.equal(card._evPublicTariff({ brand: 'Circle K', kind: 'DC', power_kw: 150 }).kwh, 3.99);
assert.equal(card._evPublicTariff({ brand: 'Circle K', kind: 'DC', power_kw: 150 }).label, 'list');
card._data.ev.pop();
card._openFordel = q8KeyA;
assert.ok(card._evBenefits({ brand: 'Q8', address: 'A vej 1', kind: 'DC' }, 'box').includes('Q8 kort giver rabat'));
assert.equal(card._evBenefits({ brand: 'Q8', address: 'B vej 2', kind: 'DC' }, 'box'), '');
const html = card._evHtml({ lat: 55.63, lon: 12.08 });
assert.ok(html.includes('<div class="trf-ev-grid">'));
assert.equal((html.match(/logo-q8.svg/g) || []).length, 1);
const evSummary = card._evDataSummary(card._evEntries());
assert.ok(evSummary.includes('3 ladesteder'));
assert.ok(evSummary.includes('1 med lokal elpris'));
assert.ok(evSummary.includes('class="trf-info-section"'));
assert.ok(!evSummary.includes('<details class="trf-data-counts"'));
assert.ok(frontendSource.includes('Information og datagrundlag'));
assert.ok(frontendSource.includes('.trf-info-panel {'));
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
  const retainedData = card._data;
  card._hass.callApi = () => Promise.reject({ status_code: 500 });
  assert.equal(await card._fetchJson(), null);
  assert.equal(card._data, retainedData, 'data-API errors must retain cached prices');
  assert.equal(card._dataApiError, 'HTTP 500');
  assert.ok(decodeURIComponent(card._issueUrl().replace(/\+/g, ' ')).includes('Home Assistant data-API: HTTP 500'));
  card._hass.callApi = () => Promise.resolve(retainedData);
  await card._fetchJson();
  assert.equal(card._dataApiError, null, 'successful recovery clears the API error');
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
  const summary = status._fuelDataSummary() + status._coordinateSummary();
  assert.ok(summary.includes('Circle K og Ingo'));
  assert.ok(summary.includes('Gemte data · nyt forsøg fejlede'));
  assert.ok(summary.includes('2 stationer mangler koordinater'));
  assert.ok(summary.includes('Offline'));
}

assert.ok(!/tesla/i.test(frontendSource), 'Tesla should be removed from the card UI');

// The preview card and editor share one catalog fetch. A response for an old
// custom catalog must not replace the newly selected catalog.
(async () => {
  const localRegistry = new Map();
  const localWindow = { ...window, customElements: {
    define: (name, type) => localRegistry.set(name, type), get: name => localRegistry.get(name),
  } };
  const pending = {};
  const requests = [];
  const localContext = { ...context, window: localWindow, customElements: localWindow.customElements,
    fetch: url => {
      requests.push(url);
      if (url === '/tiny_refuel/static/bilkatalog.json') return Promise.resolve({ ok: true, json: () => Promise.resolve(catalogManifest) });
      if (url.startsWith('/tiny_refuel/static/catalog-parts/')) return Promise.resolve({ ok: true, text: () => Promise.resolve(fs.readFileSync(catalogRoot + url.replace('/tiny_refuel/static/', ''), 'utf8')) });
      return new Promise(resolve => { pending[url] = resolve; });
    },
  };
  vm.runInNewContext(frontendSource, localContext);
  const Preview = localRegistry.get('tiny-refuel-card');
  const Editor = localRegistry.get('tiny-refuel-card-editor');
  const first = new Preview(), second = new Preview(), form = new Editor();
  first.setConfig({ biler: [{ mærke: 'Volkswagen', model: 'up!' }] });
  second.setConfig({ biler: [{ mærke: 'Citroën', model: 'C3' }] });
  form.setConfig({ biler: [] });
  await new Promise(setImmediate);
  assert.equal(requests.length, 1 + catalogManifest.catalog_parts.length);
  assert.equal(first._katalog.brands.length, packagedCatalog.brands.length);
  assert.equal(JSON.stringify(first._katalog.logos), JSON.stringify(packagedCatalog.logos));
  assert.ok(!first._katalog.brands.some(b => b.modeller.some(m => m.variants)), 'initial catalog must not contain variant lists');
  assert.equal(second._katalog, first._katalog);
  assert.equal(form._katalog, first._katalog);
  form.setConfig({ biler: [{ mærke: 'Volkswagen', model: 'up!' }] });
  const entry = form._katalogFind('Volkswagen', 'up!');
  assert.ok(entry && !entry.variants);
  const detailUrl = requests.find(url => url.includes('/catalog-details/'));
  assert.ok(detailUrl, 'selecting a model starts its details request');
  assert.equal(requests.filter(url => url === detailUrl).length, 1);
  let renders = 0, changes = 0;
  const variantInput = { value: 'min ufærdige variant', selectionStart: 4 };
  const options = {}, years = {}, note = {};
  form.querySelector = selector => selector === '[data-key="bil:0:variant"]' ? variantInput : selector === '[data-variant-options="0"]' ? options : selector === '[data-year-options="0"]' ? years : selector === '[data-model-note="0"]' ? note : null;
  const render = form._render;
  form._render = () => { renders++; };
  form.dispatchEvent = () => { changes++; };
  const beforeDetails = JSON.stringify(form._config);
  const detailRows = JSON.parse(fs.readFileSync(catalogRoot + detailUrl.replace('/tiny_refuel/static/', ''), 'utf8'));
  pending[detailUrl]({ ok: true, json: () => Promise.resolve(detailRows) });
  await new Promise(setImmediate);
  assert.ok(entry.variants.length > 0);
  assert.equal(form._config.biler[0].model, 'up!');
  assert.equal(JSON.stringify(form._config), beforeDetails);
  assert.equal(variantInput.value, 'min ufærdige variant');
  assert.equal(variantInput.selectionStart, 4);
  assert.equal(renders, 0); assert.equal(changes, 0);
  form._render = render;
  form.querySelector = () => null;

  form.setConfig({ katalog_url: '/local/old.json' });
  form.setConfig({ katalog_url: '/local/new.json' });
  const newer = { brands: [{ mærke: 'Nyt mærke', modeller: [] }] };
  pending['/local/new.json']({ ok: true, json: () => Promise.resolve(newer) });
  await new Promise(setImmediate);
  pending['/local/old.json']({ ok: true, json: () => Promise.resolve({ brands: [] }) });
  await new Promise(setImmediate);
  assert.equal(form._katalog, newer);
  form.setConfig({ katalog_url: '/local/lazy.json', biler: [] });
  pending['/local/lazy.json']({ ok: true, json: () => Promise.resolve({ catalog_schema: 2, model_defaults: {}, brands: [{ mærke: 'Test', modeller: [{ model: 'X' }], detail_files: [{ start: 0, file: 'catalog-details/aa.json' }] }] }) });
  await new Promise(setImmediate);
  form.setConfig({ katalog_url: '/local/lazy.json', biler: [{ mærke: 'Test', model: 'X' }] });
  assert.ok(form._katalogFind('Test', 'X'));
  const failureNote = {};
  form.querySelector = selector => selector === '[data-model-note="0"]' ? failureNote : null;
  pending['/local/catalog-details/aa.json']({ ok: false, status: 503 });
  await new Promise(setImmediate);
  assert.ok(form._katalogFind('Test', 'X'), 'failed details must retain model selection');
  assert.ok(failureNote.textContent.includes('Årgang og varianter kunne ikke hentes'));
  form.querySelector = () => null;
  form.setConfig({ katalog_url: '/local/stale-details.json', biler: [{ mærke: 'Test', model: 'X' }] });
  pending['/local/stale-details.json']({ ok: true, json: () => Promise.resolve({ catalog_schema: 2, model_defaults: {}, brands: [{ mærke: 'Test', modeller: [{ model: 'X' }], detail_files: [{ start: 0, file: 'catalog-details/bb.json' }] }] }) });
  await new Promise(setImmediate);
  const staleDetails = pending['/local/catalog-details/bb.json'];
  assert.equal(typeof staleDetails, 'function');
  form.setConfig({ katalog_url: '/local/new.json', biler: [] });
  await new Promise(setImmediate);
  const afterSwitch = JSON.stringify(form._config);
  let staleRefreshes = 0;
  const refreshDetails = form._refreshModelDetailFields;
  form._refreshModelDetailFields = () => { staleRefreshes++; };
  staleDetails({ ok: true, json: () => Promise.resolve([{ variants: [{ name: 'Old result' }] }]) });
  await new Promise(setImmediate);
  assert.equal(form._katalog, newer);
  assert.equal(JSON.stringify(form._config), afterSwitch);
  assert.equal(staleRefreshes, 0, 'old detail responses must not change the current form');
  form._refreshModelDetailFields = refreshDetails;
  form.setConfig({ katalog_url: '/local/broken.json' });
  pending['/local/broken.json']({ ok: true, json: () => Promise.resolve({ catalog_parts: ['../outside.txt'] }) });
  await new Promise(setImmediate);
  assert.equal(form._katalogFailed, true);
  assert.equal(form._katalog, null, 'an incomplete catalog must never be displayed');
  assert.ok(!requests.some(url => url.includes('outside.txt')));
  console.log('PASS: stable editor, shared vehicle catalogs, logo fallbacks and theme switching');
})().catch(error => { console.error(error); process.exitCode = 1; });

// Data refreshes must retain the user's expanded panel and popup state.
{
  const persistent = new Card();
  persistent._config = { vis_benzin: true, vis_el: true };
  persistent._data = { stations: [], ev: [], errors: [{ source: 'clever.dk', error: 'HTTP Error 500' }] };
  let panels = [
    { open: true, getAttribute: () => 'information' },
    { open: false, getAttribute: () => 'errors' },
  ];
  persistent.querySelectorAll = selector => selector === 'details[data-card-panel]' ? panels : [];
  let html;
  Object.defineProperty(persistent, 'innerHTML', {
    get: () => html,
    set: value => { html = value; panels = panels.map(panel => ({ ...panel, open: false })); },
  });
  persistent._openEvBrand = 'Q8';
  persistent._openFordel = 'chosen-benefit';
  persistent._render();
  assert.equal(panels[0].open, true);
  assert.equal(panels[1].open, false);
  assert.equal(persistent._openEvBrand, 'Q8');
  assert.equal(persistent._openFordel, 'chosen-benefit');
  persistent._data.updated = '2026-10-16T18:00:00Z';
  persistent._render();
  assert.equal(panels[0].open, true);
  // Opening another panel explicitly collapses the previous panel.
  const summary = { parentElement: panels[1] };
  persistent.events.click({ target: { closest: selector => selector === 'details[data-card-panel] > summary' ? summary : null } });
  assert.equal(panels[0].open, false);
  let prevented = false;
  persistent.events.cancel({ target: { classList: { contains: () => true } }, preventDefault: () => { prevented = true; } });
  assert.equal(prevented, true);
  assert.equal(persistent._openEvBrand, 'Q8');
}
// A public issue draft contains useful error categories, never raw snapshots.
{
  const report = new Card();
  report._data = { version: '0.2.1', stations: [{ address: 'PRIVATE ADDRESS' }],
    errors: [{ source: 'clever.dk', error: 'HTTP Error 500: https://secret.invalid/?token=PRIVATE_TOKEN' },
      { source: 'PRIVATE_SOURCE', error: 'PRIVATE_MESSAGE' }],
    benefit_errors: [{ provider: 'OK', error: 'HTTP Error 503' }] };
  const url = new URL(report._issueUrl());
  const body = url.searchParams.get('body');
  assert.equal(url.origin, 'https://github.com');
  assert.ok(body.includes('clever.dk: HTTP 500'));
  assert.ok(body.includes('Fordele · OK: HTTP 503'));
  assert.ok(!body.includes('PRIVATE'));
  assert.ok(!body.includes('secret.invalid'));
  const html = report._dataErrorsHtml();
  assert.ok(html.includes('3 fejl'));
  assert.ok(html.includes('Rapportér på GitHub'));
  assert.ok(html.includes('target="_blank" rel="noopener noreferrer"'));
  assert.ok(html.includes('Fordele · OK'));
}
console.log('PASS: persistent panels and redacted GitHub issue drafts');
{
  const queue = new Card();
  queue._config = { vis_benzin: true };
  queue._data = { fuel_sources: { 'f24.dk': { status: 'ok' } }, geocoding: {
    queued: 4, not_found: 2, missing_address: 1, limit: 30,
    run: { checked_at: '2026-10-16T17:00:00Z', attempted: 3, found: 1, not_found: 1, failed: 1, error: 'Offline' },
    pending_addresses: [{ brand: 'Q8', name: 'Teststed', address: 'Testvej 1', status: 'not_found', retry_after: '2026-10-23T17:00:00Z' }],
  } };
  const html = queue._coordinateSummary();
  assert.ok(html.includes('4 unikke adresser klar til opslag'));
  assert.ok(html.includes('2 forsøgt uden resultat'));
  assert.ok(html.includes('3 opslag forsøgt: 1 fundet, 1 uden resultat, 1 fejl'));
  assert.ok(html.includes('Testvej 1'));
  assert.ok(html.includes('Tidligste genforsøg'));
  assert.ok(html.includes('Opslagene blev stoppet af en fejl'));
  assert.ok(!html.includes('behandles gradvist'));
}

queueCoverage();
function queueCoverage() {
  const onlyElectric = new Card();
  onlyElectric._data = { geocoding: { queued: 1, not_found: 0, missing_address: 0, pending_addresses: [] } };
  onlyElectric.setConfig({ vis_benzin: false, vis_diesel: false, vis_el: true });
  assert.ok(onlyElectric.innerHTML.includes('1 unikke adresser klar til opslag'));
}
// A model-name-only addition must never carry over the preceding car's fuel/specs.
{
  const form = new StableEditor();
  form._katalog = packagedCatalog;
  form.dispatchEvent = () => {};
  form.setConfig({ biler: [{ mærke: 'Toyota', model: 'Prius', brændstof: 'hybrid', tank_liters: 45, batteri_kwh: 8, vis: { benzin: true } }] });
  form.events.change({ target: { dataset: { key: 'bil:0:model' }, value: 'Aygo' } });
  const car = form._config.biler[0];
  assert.equal(car.model, 'Aygo');
  assert.equal(car.brændstof, undefined);
  assert.equal(car.tank_liters, undefined);
  assert.equal(car.batteri_kwh, undefined);
  assert.equal(car.vis, undefined);
  form._render();
  assert.ok(form.innerHTML.includes('Aygo · vælg drivmiddel'));
  assert.ok(form.innerHTML.includes('Vælg drivmiddel og kontrollér tank/batteri'));
  assert.ok(!form.innerHTML.includes('Aygo · null'));
  assert.ok(form.innerHTML.includes(packagedCatalog.brands.length + ' mærker · ' + packagedCatalog.brands.reduce((n, b) => n + b.modeller.length, 0) + ' modeller'));
  form.events.change({ target: { dataset: { key: 'bil:0:brændstof' }, value: 'benzin' } });
  assert.equal(form._config.biler[0].brændstof, 'benzin');
  assert.equal(form._config.biler[0].vis.benzin, true);
}
// Large bundled catalogs filter locally without replacing the input or emitting config.
{
  const form = new StableEditor();
  form._katalog = { brands: [{ mærke: 'Test', modeller: Array.from({ length: 5000 }, (_, i) => ({ model: 'Model ' + i })) }] };
  form.setConfig({ biler: [{ mærke: 'Test', model: '', navn: 'Min bil' }] });
  assert.equal((form._modelSuggestions('Test', '').html.match(/<option /g) || []).length, 60);
  assert.equal(form._modelSuggestions('Test', '4999').total, 1);
  assert.ok(form._modelSuggestions('Test', '4999').html.includes('Model 4999'));
  const list = {}, count = {};
  form.querySelector = selector => selector === '[data-model-options="0"]' ? list : selector === '[data-model-count="0"]' ? count : null;
  let renders = 0, events = 0;
  form._render = () => { renders++; };
  form.dispatchEvent = () => { events++; };
  const input = { dataset: { key: 'bil:0:model' }, value: '4999', selectionStart: 4 };
  form.events.input({ target: input });
  assert.ok(list.innerHTML.includes('Model 4999'));
  assert.equal(count.textContent, '1 modeller matcher. Du kan også skrive din egen model.');
  assert.equal(form._config.biler[0].model, '');
  assert.equal(input.selectionStart, 4);
  assert.equal(renders, 0);
  assert.equal(events, 0);
  assert.ok(form._modelSuggestions('Missing', 'Custom').message.includes('skrive din egen model'));
  form._katalog.brands[0].modeller.push({ model: 'Ældre årgang', variants: [{ name: '1.6 TDI', fuel_types: ['Diesel'] }] });
  assert.equal(form._modelSuggestions('Test', 'aeldre').total, 1);
  assert.ok(form._variantOptions('Test', 'Ældre årgang').includes('1.6 TDI'));
}

{
  const form = new StableEditor();
  form._katalog = { brands: [{ mærke: 'Test', modeller: [{ model: 'Van', variants: Array.from({ length: 2000 }, (_, i) => ({ name: 'Variant ' + i, fuel_types: ['Diesel'] })) }] }] };
  assert.equal((form._variantOptions('Test', 'Van').match(/<option /g) || []).length, 100);
  assert.ok(form._variantOptions('Test', 'Van', '1999').includes('Variant 1999'));
}

{
  const form = new StableEditor();
  form._katalog = packagedCatalog;
  form.dispatchEvent = () => {};
  form.setConfig({ biler: [{ mærke: 'Volkswagen', model: 'Golf', brændstof: 'diesel', tank_liters: 50 }] });
  form.events.change({ target: { dataset: { key: 'bil:0:variant' }, value: '2018 · 1.4 benzin' } });
  assert.equal(form._config.biler[0].variant, '2018 · 1.4 benzin');
  assert.equal(form._config.biler[0].brændstof, undefined);
  assert.equal(form._config.biler[0].tank_liters, undefined);
  form.events.change({ target: { dataset: { key: 'bil:0:brændstof' }, value: 'benzin' } });
  form.events.change({ target: { dataset: { key: 'bil:0:tank_liters' }, value: '45' } });
  form.events.change({ target: { dataset: { key: 'bil:0:variant' }, value: '2018 · 1.4 benzin' } });
  assert.equal(form._config.biler[0].brændstof, 'benzin');
  assert.equal(form._config.biler[0].tank_liters, 45, 'unchanged variant preserves confirmed manual specifications');
}

// Prepared vehicle makes work in both editor and dashboard before model import.
for (const make of Object.keys(packagedCatalog.logo_assets)) {
  for (const name of [make, ...Object.keys(packagedCatalog.logo_aliases).filter(k => packagedCatalog.logo_aliases[k] === make)]) {
    const src = 'data:image/svg+xml,' + encodeURIComponent(packagedCatalog.logos[make]);
    editor._katalog = packagedCatalog;
    editor.setConfig({biler:[{mærke:name, model:'Egen model'}]});
    assert.ok(editor.innerHTML.includes(src), 'embedded editor logo: ' + name);
    const panel = new Card(); panel._katalog = packagedCatalog;
    panel.setConfig({biler:[{mærke:name, model:'Egen model'}]});
    assert.ok(panel.innerHTML.includes(src), 'embedded dashboard logo: ' + name);
    assert.ok(panel.innerHTML.includes('Egen model'));
  }
}

// New raster fallbacks also work for makes not yet in the shipped model list.
for (const [make, png] of Object.entries(packagedCatalog.logo_pngs)) {
  assert.equal(Buffer.from(png, 'base64').subarray(0, 8).toString('hex'), '89504e470d0a1a0a');
  editor._katalog = packagedCatalog;
  editor.setConfig({biler:[{mærke:make, model:'Egen model'}]});
  assert.ok(editor.innerHTML.includes('data:image/png;base64,' + png));
  const panel = new Card(); panel._katalog = packagedCatalog;
  panel.setConfig({biler:[{mærke:make, model:'Egen model'}]});
  assert.ok(panel.innerHTML.includes('data:image/png;base64,' + png));
  assert.ok(panel.innerHTML.includes('Egen model'));
}

// Full DMR catalog uses bounded make/model suggestions and preserves manual vehicles.
{
  const form = new StableEditor();
  form._katalog = packagedCatalog;
  form.dispatchEvent = () => {};
  form.setConfig({ biler: [{ mærke: 'Honda', model: 'CB 500', brændstof: 'benzin', tank_liters: 17 }] });
  assert.ok(form._makeSuggestions('').total > 1800);
  assert.ok((form._makeSuggestions('').html.match(/<option/g) || []).length <= 60);
  assert.ok(form.innerHTML.includes('bil:0:koeretoejstype'));
  assert.ok(form.innerHTML.includes('bil:0:aargang'));
  const renderBefore = form.innerHTML;
  form.events.input({ target: { dataset: { key: 'bil:0:mærke' }, value: 'Honda' } });
  assert.equal(form.innerHTML, renderBefore, 'typing in make search must preserve input and form');
  form.events.change({ target: { dataset: { key: 'bil:0:koeretoejstype' }, value: 'motorcykel' } });
  assert.equal(form._config.biler[0].tank_liters, 17);
  assert.equal(form._config.biler[0].brændstof, 'benzin');
  form.events.change({ target: { dataset: { key: 'bil:0:mærke' }, value: 'Eget mærke' } });
  assert.equal(form._config.biler[0].tank_liters, undefined);
  assert.equal(form._config.biler[0].brændstof, undefined);
  assert.ok(!form.innerHTML.match(/data-key="bil:0:model"[^>]*disabled/));
  form.events.change({ target: { dataset: { key: 'bil:0:model' }, value: 'Egen model' } });
  assert.equal(form._config.biler[0].model, 'Egen model');
}
console.log('PASS: full vehicle catalog, bounded make search, manual types and model years');

// Previous make labels still resolve after deduplication, without duplicate choices.
{
  const form = new (registry.get('tiny-refuel-card-editor'))();
  form._katalog = packagedCatalog;
  assert.equal(form._katalogModels('CITROEN'), form._katalogModels('Citroën'));
  assert.equal(form._katalogModels('CF MOTO'), form._katalogModels('CFMOTO'));
  assert.ok(form._makeSuggestions('CITROEN').html.includes('value="Citroën"'));
  assert.ok(!form._makeSuggestions('CITROEN').html.includes('value="CITROEN"'));
  assert.ok(!packagedCatalog.brands.some(b => b.mærke.toLowerCase() === 'selvbyg'));
}
