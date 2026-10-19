!function (window) {
  "use strict";
  if (window.customElements.get("tiny-refuel-card")) return;

  var CSS = `
  .trf { container-type: inline-size; container-name: tiny-refuel; font-family: var(--paper-font-body1_-_font-family, inherit); padding: 14px 16px; color: var(--primary-text-color); }
  .trf.trf-compact { padding: 8px 10px; }
  .trf-compact .trf-title { font-size: 13px; }
  .trf-compact .trf-row, .trf-compact .trf-evrow { padding-top: 6px; padding-bottom: 6px; }
  .trf-compact .trf-chg { display: none; }
  .trf-list-actions { display: flex; align-items: center; gap: 8px; margin: 6px 0; }
  .trf-titlebar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 2px; }
  .trf-title { font-weight: 600; font-size: 15px; text-transform: uppercase; letter-spacing: .6px; text-shadow: 0 0 12px rgba(0,229,255,.35); }
  .trf-rule { height: 2px; border-radius: 2px; margin: 6px 0 4px; background: linear-gradient(90deg, var(--primary-color, #00e5ff), var(--accent-color, #b967ff)); opacity: .55; box-shadow: 0 0 8px rgba(0,229,255,.35); }
  .trf-pos { font-size: 11px; color: var(--secondary-text-color); margin-bottom: 8px; opacity: .85; }
  .trf-cars { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px; }
  .trf-car { border: 1px solid rgba(0,229,255,.45); background: linear-gradient(180deg, rgba(0,229,255,.08), rgba(185,103,255,.08)); color: var(--primary-text-color); border-radius: 20px; padding: 4px 10px; font-size: 11px; font-weight: 600; letter-spacing: .5px; text-transform: uppercase; cursor: pointer; box-shadow: 0 0 8px rgba(0,229,255,.25); }
  .trf-car:active { transform: scale(.95); }
  .trf-car { display: inline-flex; align-items: center; gap: 6px; }
  .trf-make-mark { display: inline-flex; align-items: center; min-height: 22px; }
  .trf-car-logo { width: 22px; height: 22px; object-fit: contain; }
  .trf-model-logo { width: 38px; height: 18px; object-fit: contain; }
  .trf-model-mark { display: inline-flex; align-items: center; }
  .trf-model-logo-text { font-size: 11px; font-weight: 700; color: var(--primary-text-color); }
  .trf-car-logo, .trf-model-logo { filter: var(--trf-vehicle-logo-filter, none); mix-blend-mode: var(--trf-vehicle-logo-blend, multiply); background: transparent; }
  .trf-logo-color { filter: none; mix-blend-mode: normal; }
  .trf-logo-white { filter: var(--trf-white-logo-filter, invert(1)); }
  .trf-car.trf-on { background: linear-gradient(90deg, rgba(0,229,255,.28), rgba(185,103,255,.28)); border-color: var(--primary-color, #00e5ff); font-weight: 700; box-shadow: 0 0 14px rgba(0,229,255,.5); text-shadow: 0 0 8px rgba(0,229,255,.8); }
  .trf-refresh { border: 1px solid rgba(0,229,255,.4); background: rgba(0,229,255,.06); color: var(--primary-text-color); border-radius: 50%; width: 34px; height: 34px; font-size: 17px; line-height: 1; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; box-shadow: 0 0 10px rgba(0,229,255,.25); }
  .trf-refresh:active { transform: scale(.93); }
  .trf-refresh.trf-spin { animation: trf-rot 1s linear infinite; opacity: .8; }
  @keyframes trf-rot { to { transform: rotate(360deg); } }
  .trf-best { display: flex; flex-wrap: wrap; gap: 4px 16px; font-size: 13px; margin-bottom: 8px; color: var(--secondary-text-color); }
  .trf-best b { font-weight: 700; }
  .trf-b95 { color: var(--primary-color, #00e5ff); text-shadow: 0 0 10px rgba(0,229,255,.7); }
  .trf-b100 { color: var(--accent-color, #b967ff); text-shadow: 0 0 10px rgba(185,103,255,.7); }
  .trf-inline { height: 14px; vertical-align: middle; margin-left: 6px; border-radius: 3px; }
  .trf-head, .trf-row, .trf-evrow { display: grid; align-items: center; gap: 6px; padding: 4px 8px; }
  .trf-fuel-grid, .trf-ev-grid { display: contents; }
  .trf-fuel-head-duplicate { display: none; }
  .trf-head { font-size: 11px; letter-spacing: .8px; text-transform: uppercase; color: var(--secondary-text-color); opacity: .8; border-bottom: 1px solid rgba(255,255,255,.06); }
  .trf-head .trf-p { text-align: right; }
  .trf-head .trf-km { text-align: right; }
  .trf-row, .trf-evrow { border-radius: 10px; margin: 3px 6px; border: 1px solid rgba(0,229,255,.28); background: rgba(0,229,255,.06); box-shadow: 0 0 10px rgba(0,229,255,.08); }
  .trf-logo { height: 22px; display: flex; align-items: center; }
  .trf-logo img { height: 22px; max-width: 96px; object-fit: contain; filter: drop-shadow(0 0 4px rgba(255,255,255,.08)); }
  .trf-navlink { display: inline-flex; }
  .trf-navlink img { cursor: pointer; transition: opacity .15s; }
  .trf-navlink:hover img { opacity: .85; }
  .trf-navlink:hover::after { content: "→"; margin-left: 6px; font-size: 12px; color: var(--accent-color, #00e58d); }
  .trf-row.trf-flash, .trf-evrow.trf-flash { transform: scale(.98); opacity: .65; transition: transform .12s, opacity .12s; }
  .trf-price { text-align: right; font-size: 14px; font-weight: 700; font-variant-numeric: tabular-nums; color: var(--primary-text-color); }
  .trf-price.trf-g95 { color: var(--primary-color, #00e5ff); text-shadow: 0 0 10px rgba(0,229,255,.75); }
  .trf-price.trf-g100 { color: var(--accent-color, #b967ff); text-shadow: 0 0 10px rgba(185,103,255,.75); }
  .trf-price.trf-na { color: var(--secondary-text-color); opacity: .55; }
  .trf-km { text-align: right; font-size: 12px; font-weight: 600; font-variant-numeric: tabular-nums; color: var(--secondary-text-color); }
  .trf-km.trf-far { color: #ff6a6a; }
  .trf-age { display: block; font-size: 10px; font-weight: 400; opacity: .65; }
  .trf-pcol { text-align: right; }
  .trf-chg { display: block; font-size: 10px; font-weight: 600; font-variant-numeric: tabular-nums; }
  .trf-chg.dn { color: #00e58d; }
  .trf-chg.up { color: #ff6a6a; }
  .trf-chg.flat { color: var(--secondary-text-color); opacity: .6; }
  .trf-station { grid-column: 1 / -1; font-size: 10px; color: var(--secondary-text-color); opacity: .85; padding-top: 1px; display: flex; gap: 8px; align-items: flex-start; }
  .trf-subtxt { flex: 1; min-width: 0; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  .trf-fordel-btn { color: var(--primary-color, #00e5ff); text-decoration: none; font-weight: 700; white-space: nowrap; }
  .trf-fordel-box { grid-column: 1 / -1; font-size: 11px; line-height: 1.5; margin-top: 4px; padding: 6px 10px; border-radius: 8px; border: 1px dashed rgba(0,229,255,.4); background: rgba(0,229,255,.05); color: var(--primary-text-color); }
  .trf-pill { display: inline-block; font-size: 10px; font-weight: 700; letter-spacing: .4px; text-transform: uppercase; border: 1px solid rgba(255,179,64,.5); color: #ffb340; border-radius: 20px; padding: 1px 8px; margin-top: 3px; }
  .trf-srctag { display: inline-block; font-size: 10px; opacity: .6; border: 1px solid rgba(255,255,255,.18); border-radius: 20px; padding: 1px 8px; margin-top: 3px; }
  .trf-stale-tag { display: inline-block; margin-left: 4px; color: #ffb340; font-size: 9px; font-weight: 600; vertical-align: middle; }
  .trf-brand { font-weight: 700; font-size: 13px; margin: 12px 6px 4px; }
  .trf-evrow .trf-price { color: var(--primary-color, #00e5ff); text-shadow: 0 0 10px rgba(0,229,255,.75); }
  .trf-evrow .trf-meta { color: var(--secondary-text-color); font-size: 10px; }
  .trf-tariffs { grid-column: 1 / -1; min-width: 0; font-size: clamp(8px, 2.4vw, 10px); line-height: 1.5; }
  .trf-tariff-line { display: block; white-space: normal; overflow-wrap: anywhere; font-weight: 600; }
  .trf-tariff-note { color: var(--secondary-text-color); font-size: 10px; }
  .trf-data-tools { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 8px 0; font-size: 11px; }
  .trf-data-tools button:disabled { cursor: wait; opacity: .65; }
  .trf-data-counts { margin: 8px 6px; font-size: 11px; color: var(--secondary-text-color); }
  .trf-data-counts summary { cursor: pointer; }
  .trf-data-counts table { width: 100%; margin-top: 5px; border-collapse: collapse; font-size: 10px; }
  .trf-data-counts th, .trf-data-counts td { padding: 3px 5px; text-align: left; }
  .trf-data-counts th { font-weight: 600; }
  .trf-info-panel { margin: 10px 0 2px; border: 1px solid rgba(255,193,7,.42); border-radius: 14px; background: rgba(255,193,7,.07); color: var(--primary-text-color); overflow: hidden; }
  .trf-info-panel > summary { display: flex; align-items: center; gap: 8px; cursor: pointer; list-style: none; padding: 10px 12px; font-size: 12px; font-weight: 700; }
  .trf-info-panel > summary::-webkit-details-marker { display: none; }
  .trf-info-panel > summary::before { content: "i"; display: inline-grid; place-items: center; width: 19px; height: 19px; border: 1px solid rgba(255,193,7,.75); border-radius: 50%; color: var(--primary-text-color); font: 700 12px/1 sans-serif; }
  .trf-info-panel > summary::after { content: "⌄"; margin-left: auto; font-size: 16px; transition: transform .15s ease; }
  .trf-info-panel[open] > summary::after { transform: rotate(180deg); }
  .trf-info-panel > summary:focus-visible { outline: 2px solid rgba(255,193,7,.8); outline-offset: -2px; }
  .trf-info-content { padding: 0 12px 10px; border-top: 1px solid rgba(255,193,7,.25); }
  .trf-info-section { margin-top: 8px; font-size: 10px; line-height: 1.5; }
  .trf-info-count { margin-bottom: 4px; font-weight: 700; font-size: 11px; color: var(--primary-text-color); }
  .trf-info-table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; }
  .trf-info-panel .trf-data-counts { margin: 6px 0; }
  .trf-info-panel .trf-legend { padding: 4px 0; }
  .trf-info-panel .trf-tank { padding: 5px 0 0; }
  .trf-info-panel .trf-foot { padding: 7px 0 0; }
  .trf-tank { font-size: 11px; color: var(--secondary-text-color); padding: 6px 12px 0; opacity: .9; }
  .trf-tank b { color: var(--primary-text-color); }
  .trf-legend { font-size: 10px; color: var(--secondary-text-color); opacity: .75; padding: 6px 12px 2px; line-height: 1.5; }
  .trf-legend b { color: var(--primary-text-color); }
  .trf-em { font-size: 12px; color: var(--secondary-text-color); opacity: .8; padding: 4px 6px; }
  .trf-foot { display: flex; justify-content: space-between; gap: 8px; font-size: 11px; color: var(--secondary-text-color); padding: 8px 12px 2px; opacity: .9; }
  .trf-foot a { color: var(--secondary-text-color); text-decoration: none; }
  .trf-ev-actions { grid-column: 1 / -1; display: flex; flex-wrap: wrap; align-items: center; gap: 12px; }
  .trf-ev-actions .trf-fordel-box { flex-basis: 100%; }
  .trf-ev-link { cursor: pointer; font: inherit; border: 0; padding: 0; background: transparent; }
  .trf-ev-button { cursor: pointer; font: inherit; font-size: 11px; border: 1px solid rgba(0,229,255,.4); border-radius: 14px; padding: 4px 10px; background: rgba(0,229,255,.08); color: var(--primary-color, #00b8d4); }
  .trf-ev-button:focus-visible { outline: 2px solid var(--primary-color, #00b8d4); outline-offset: 2px; }
  .trf-ev-dialog { width: min(680px, calc(100vw - 32px)); max-height: 85vh; box-sizing: border-box; padding: 16px; border: 1px solid rgba(0,229,255,.5); border-radius: 14px; background: var(--ha-card-background, var(--card-background-color, #fafafa)); color: var(--primary-text-color, #17252b); box-shadow: 0 0 24px rgba(0,229,255,.18); font-family: inherit; }
  .trf-ev-dialog::backdrop { background: rgba(0,0,0,.5); }
  .trf-ev-dialog-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
  .trf-ev-dialog h3 { font-size: 16px; margin: 0; }
  .trf-ev-filters { display: flex; gap: 8px; margin: 10px 6px; }
  .trf-ev-filters .trf-on { background: rgba(0,229,255,.2); border-color: var(--primary-color, #00b8d4); }
  .trf-ev-list { max-height: 58vh; overflow-y: auto; overscroll-behavior: contain; }
  .trf-ev-dialog .trf-subtxt { display: block; overflow: visible; }
  @media (max-width: 480px) {
    .trf-head, .trf-row, .trf-evrow { gap: 5px; padding: 3px 6px; }
    .trf-logo { height: 22px; }
    .trf-logo img { height: 22px; max-width: 80px; }
    .trf-price { font-size: 13px; }
    .trf-km { font-size: 11px; }
  }
  @container tiny-refuel (max-width: 390px) {
    .trf { padding: 10px 8px; }
    .trf-head[data-price-cols], .trf-row[data-price-cols] { grid-template-columns: minmax(52px,.9fr) repeat(var(--trf-price-cols), minmax(38px,1fr)) 34px !important; gap: 3px; padding: 3px 4px; }
    .trf-logo img { max-width: 66px; }
    .trf-price { font-size: 12px; }
    .trf-km { font-size: 10px; }
    .trf-data-tools { gap: 5px; }
    .trf-evrow { grid-template-columns: minmax(52px,100px) minmax(40px,1fr) 34px !important; gap: 4px; padding: 3px 4px; }
  }
  `;

  var ECSS = `
  .trfe { font-family: var(--paper-font-body1_-_font-family, inherit); padding: 8px 4px; color: var(--primary-text-color); font-size: 13px; }
  .trfe h4 { margin: 14px 0 6px; font-size: 13px; text-transform: uppercase; letter-spacing: .5px; color: var(--secondary-text-color); }
  .trfe h4:first-child { margin-top: 0; }
  .trfe label { display: flex; align-items: center; gap: 8px; padding: 4px 0; cursor: pointer; }
  .trfe input[type=checkbox] { width: 16px; height: 16px; accent-color: var(--primary-color, #03a9f4); }
  .trfe input[type=number], .trfe input[type=text], .trfe select, .trfe textarea { background: var(--mdc-text-field-fill-color, rgba(255,255,255,.06)); color: var(--primary-text-color); border: 1px solid var(--divider-color, rgba(255,255,255,.12)); border-radius: 4px; padding: 6px 8px; font-size: 13px; width: 100%; box-sizing: border-box; }
  .trfe textarea { display: block; margin-top: 8px; min-height: 180px; font-family: monospace; font-size: 11px; white-space: pre; }
  .trfe .trfe-row { display: flex; gap: 8px; align-items: center; }
  .trfe .trfe-hint { font-size: 11px; color: var(--secondary-text-color); opacity: .8; margin-top: 2px; }
  .trfe details { margin-top: 10px; }
  .trfe summary { cursor: pointer; color: var(--secondary-text-color); font-size: 12px; }
  .trfe .trfe-section { margin: 12px 0; border: 1px solid var(--divider-color, rgba(255,255,255,.14)); border-radius: 12px; background: var(--card-background-color, rgba(127,127,127,.035)); overflow: hidden; }
  .trfe .trfe-section > summary { display: flex; align-items: center; gap: 8px; padding: 11px 12px; color: var(--primary-text-color); font-weight: 600; font-size: 13px; list-style: none; }
  .trfe .trfe-section > summary::-webkit-details-marker, .trfe .trfe-car > summary::-webkit-details-marker { display: none; }
  .trfe .trfe-section > summary::after, .trfe .trfe-car > summary::after { content: "⌄"; margin-left: auto; color: var(--secondary-text-color); transition: transform .15s ease; }
  .trfe .trfe-section[open] > summary::after, .trfe .trfe-car[open] > summary::after { transform: rotate(180deg); }
  .trfe .trfe-section > summary:focus-visible, .trfe .trfe-car > summary:focus-visible { outline: 2px solid var(--primary-color, #03a9f4); outline-offset: -2px; }
  .trfe .trfe-section-body { padding: 0 12px 12px; border-top: 1px solid var(--divider-color, rgba(127,127,127,.14)); }
  .trfe .trfe-summary-meta { color: var(--secondary-text-color); font-size: 11px; font-weight: 400; margin-left: auto; }
  .trfe .trf-make-mark { display: inline-flex; align-items: center; min-height: 28px; }
  .trfe .trfe-car-logo { width: 28px; height: 28px; flex: 0 0 28px; object-fit: contain; background: transparent; filter: var(--trf-vehicle-logo-filter, none); mix-blend-mode: var(--trf-vehicle-logo-blend, multiply); }
  .trfe .trfe-model-logo { width: 46px; height: 24px; object-fit: contain; background: transparent; filter: var(--trf-vehicle-logo-filter, none); mix-blend-mode: var(--trf-vehicle-logo-blend, multiply); }
  .trfe .trf-logo-color { filter: none; mix-blend-mode: normal; }
  .trfe .trf-logo-white { filter: var(--trf-white-logo-filter, invert(1)); }
  .trfe .trfe-car-title { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; font-weight: 600; }
  .trfe .trfe-brand-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(145px, 1fr)); gap: 6px; margin-top: 8px; }
  .trfe .trfe-brand-grid label { display: grid; grid-template-columns: 16px 42px minmax(0,1fr); box-sizing: border-box; min-width: 0; margin: 0; padding: 7px 9px; border: 1px solid var(--divider-color, rgba(127,127,127,.14)); border-radius: 9px; background: rgba(127,127,127,.035); font-size: 12px; }
  .trfe .trfe-brand-grid label:hover { background: rgba(127,127,127,.09); }
  .trfe .trfe-brand-logo { display: block; width: 42px; height: 24px; object-fit: contain; }
  .trfe .trfe-car { border: 1px solid var(--divider-color, rgba(127,127,127,.18)); border-radius: 10px; margin: 8px 0; overflow: hidden; }
  .trfe .trfe-car > summary { display: flex; align-items: center; gap: 8px; padding: 10px 11px; cursor: pointer; list-style: none; }
  .trfe .trfe-car > summary span:first-child { font-weight: 600; font-size: 13px; }
  .trfe .trfe-car-fields { padding: 0 11px 11px; border-top: 1px solid var(--divider-color, rgba(127,127,127,.14)); }
  .trfe .trfe-row { flex-wrap: wrap; }
  .trfe .trfe-row label { width: auto; margin-right: 7px; font-size: 12px; }
  .trfe .trfe-empty-car { padding: 10px 11px; margin: 8px 0; border-radius: 10px; background: rgba(127,127,127,.06); font-size: 12px; line-height: 1.5; }
  .trfe .trfe-empty-car strong { display: block; margin-bottom: 3px; }
  .trfe .trfe-tip { display: inline-grid; place-items: center; width: 16px; height: 16px; margin-left: 4px; border: 1px solid var(--secondary-text-color); border-radius: 50%; color: var(--secondary-text-color); font-size: 10px; cursor: help; vertical-align: middle; }
  .trfe .trfe-tip:focus-visible { outline: 2px solid var(--primary-color, #03a9f4); outline-offset: 2px; }
  .trfe a { color: var(--primary-color, #03a9f4); }`;

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (m) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m];
    });
  }

  var VEHICLE_CATALOG_REQUESTS = {};
  var VEHICLE_CATALOG_INDEXES = new WeakMap();
  function catalogKey(value) { return String(value || "").normalize("NFC").trim().replace(/\s+/g, " ").toLowerCase(); }
  function catalogIndex(catalog) {
    if (!catalog) return null;
    if (!VEHICLE_CATALOG_INDEXES.has(catalog)) {
      var makes = new Map(), models = new Map();
      (catalog.brands || []).forEach(function (brand) {
        makes.set(catalogKey(brand.mærke), brand);
        (brand.source_names || []).forEach(function (name) { makes.set(catalogKey(name), brand); });
      });
      VEHICLE_CATALOG_INDEXES.set(catalog, { makes: makes, models: models });
    }
    return VEHICLE_CATALOG_INDEXES.get(catalog);
  }
  var FAILED_VEHICLE_LOGOS = {};

  function vehicleCatalogUrl(config) {
    var url = config && config.katalog_url && String(config.katalog_url).trim();
    return url && ["/tiny_refuel/static/bilkatalog.json", "/local/fuelprices/bilkatalog.json", "/local/tiny-gas/data/bilkatalog.json", "/local/tiny-refuel/data/bilkatalog.json"].indexOf(url.split("?")[0]) === -1 ? url : "/tiny_refuel/static/katalog.json";
  }

  var VEHICLE_MODEL_REFERENCES = new WeakMap();
  var VEHICLE_DETAIL_REQUESTS = {};
  function validateVehicleCatalog(catalog) {
    if (!catalog || !Array.isArray(catalog.brands)) throw new Error("Expected brands in Tiny Refuel catalog");
    catalog.brands.forEach(function (brand) {
      if (!brand || typeof brand.mærke !== "string" || !brand.mærke.trim() || !Array.isArray(brand.modeller)) throw new Error("Invalid catalog make");
      brand.modeller.forEach(function (model) {
        if (!model || typeof model.model !== "string" || !model.model.trim()) throw new Error("Invalid catalog model");
        ["tank_l", "batteri_kwh"].forEach(function (field) {
          var value = model[field];
          if (value !== undefined && value !== null && (typeof value !== "number" || !isFinite(value) || value <= 0)) throw new Error("Invalid catalog capacity");
        });
      });
    });
  }

  function prepareVehicleCatalog(catalog, url) {
    validateVehicleCatalog(catalog);
    if (catalog.catalog_schema !== 2) return catalog;
    var defaults = catalog.model_defaults || {};
    delete catalog.catalog_schema;
    delete catalog.model_defaults;
    (catalog.brands || []).forEach(function (brand) {
      var files = brand.detail_files || [];
      delete brand.detail_files;
      (brand.modeller || []).forEach(function (model) {
        if (!model._no_defaults) Object.keys(defaults).forEach(function (key) {
          if (model[key] === undefined) model[key] = defaults[key];
        });
        delete model._no_defaults;
      });
      files.forEach(function (part, index) {
        var end = index + 1 < files.length ? files[index + 1].start : brand.modeller.length;
        if (!Number.isInteger(part.start) || part.start < 0 || end <= part.start || end > brand.modeller.length ||
            (index === 0 && part.start !== 0) || !/^catalog-details\/[a-f0-9]+\.json$/.test(part.file)) throw new Error("Invalid model detail reference");
        for (var i = part.start; i < end; i++) VEHICLE_MODEL_REFERENCES.set(brand.modeller[i], {
          catalog: catalog, url: url.slice(0, url.lastIndexOf("/") + 1) + part.file,
          index: i - part.start, count: end - part.start,
        });
      });
      if (brand.modeller.length && !files.length) throw new Error("Missing model detail references");
    });
    return catalog;
  }

  function loadVehicleModelDetails(owner, entry) {
    var ref = entry && VEHICLE_MODEL_REFERENCES.get(entry);
    if (!ref || ref.loaded || ref.failed || typeof fetch !== "function") return;
    if (!VEHICLE_DETAIL_REQUESTS[ref.url]) VEHICLE_DETAIL_REQUESTS[ref.url] = fetch(ref.url, { cache: "force-cache" }).then(function (response) {
      if (!response.ok) throw new Error("http " + response.status);
      return response.json();
    });
    if (ref.listeners && ref.listeners.has(owner)) return;
    if (!ref.listeners) ref.listeners = new WeakSet();
    ref.listeners.add(owner);
    VEHICLE_DETAIL_REQUESTS[ref.url].then(function (rows) {
      if (!Array.isArray(rows) || rows.length !== ref.count || !rows.every(function (row) { return row && typeof row === "object" && !Array.isArray(row); })) throw new Error("Invalid model details");
      Object.assign(entry, rows[ref.index]);
      ref.loaded = true;
      if (owner._katalog === ref.catalog) owner._refreshModelDetailFields(entry);
    }).catch(function () {
      ref.failed = true;
      if (owner._katalog === ref.catalog) owner._refreshModelDetailFields(entry);
    });
  }

  function vehicleModelNote(entry, variant) {
    var ref = entry && VEHICLE_MODEL_REFERENCES.get(entry);
    if (ref && ref.failed) return "Årgang og varianter kunne ikke hentes. Du kan stadig skrive oplysningerne manuelt.";
    return entry && entry.specification_note || (variant ? "Variant valgt: vælg drivmiddel og kontrollér tank/batteri for denne variant." : "");
  }

  function loadVehicleCatalog(owner) {
    if (typeof fetch !== "function") return;
    var url = vehicleCatalogUrl(owner._config);
    if (owner._katalogUrlUsed === url && (owner._katalog || owner._katalogLoading || owner._katalogFailed)) return;
    owner._katalogUrlUsed = url;
    owner._katalog = null;
    owner._katalogLoading = true;
    owner._katalogFailed = false;
    if (!VEHICLE_CATALOG_REQUESTS[url]) {
      VEHICLE_CATALOG_REQUESTS[url] = fetch(url, { cache: "no-store" }).then(function (response) {
        if (!response.ok) throw new Error("http " + response.status);
        return response.json();
      }).then(async function (catalog) {
        if (!Array.isArray(catalog.catalog_parts)) return catalog;
        if (!catalog.catalog_parts.length || catalog.catalog_parts.length > 256) throw new Error("Invalid catalog parts");
        var chunks = new Array(catalog.catalog_parts.length), next = 0;
        async function worker() {
          while (next < chunks.length) {
            var index = next++, part = catalog.catalog_parts[index];
            if (typeof part !== "string" || !/^catalog-parts\/[a-f0-9]+\.txt$/.test(part)) throw new Error("Invalid catalog part path");
            var partUrl = url.slice(0, url.lastIndexOf("/") + 1) + part;
            var response = await fetch(partUrl, { cache: "force-cache" });
            if (!response.ok) throw new Error("http " + response.status);
            chunks[index] = await response.text();
          }
        }
        await Promise.all(Array.from({ length: Math.min(4, chunks.length) }, worker));
        return JSON.parse(chunks.join(""));
      }).then(function (catalog) { return prepareVehicleCatalog(catalog, url); });
    }
    VEHICLE_CATALOG_REQUESTS[url].then(function (catalog) {
      if (owner._katalogUrlUsed !== url) return;
      owner._katalog = catalog;
      owner._katalogLoading = false;
      owner._render();
    }).catch(function () {
      if (owner._katalogUrlUsed !== url) return;
      owner._katalogLoading = false;
      owner._katalogFailed = true;
      if (typeof owner._render === "function") owner._render();
    });
  }

  function vehicleLogoTheme(owner, hass) {
    if (!owner.style || !owner.style.setProperty) return;
    var dark = hass && hass.themes && hass.themes.darkMode;
    if (dark === undefined) dark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    owner.style.setProperty("--trf-vehicle-logo-filter", dark ? "brightness(0) invert(1)" : "brightness(0)");
    owner.style.setProperty("--trf-vehicle-logo-blend", "normal");
    owner.style.setProperty("--trf-white-logo-filter", dark ? "brightness(0) invert(1)" : "brightness(0)");
  }

  function vehicleLogoFailure(owner) {
    owner.addEventListener("error", function (ev) {
      var image = ev.target;
      if (!image || !image.dataset || !image.dataset.vehicleLogo) return;
      FAILED_VEHICLE_LOGOS[image.getAttribute("src")] = true;
      image.hidden = true;
      var fallback = image.nextElementSibling;
      if (fallback && (fallback.hasAttribute("data-model-fallback") || fallback.hasAttribute("data-make-fallback"))) fallback.hidden = false;
    }, true);
  }

  function vehicleLogoHtml(catalog, car, className, model) {
    if (!catalog || !car || !car.mærke) return "";
    var svg, png, url, label, color = false, white = false;
    if (model) {
      var entry = catalog.model_logos && catalog.model_logos[car.mærke] && catalog.model_logos[car.mærke][car.model];
      if (!entry) return "";
      svg = entry.svg; png = entry.png; url = entry.url;
      label = car.model + " logo" + (entry.generation ? " (" + entry.generation + ")" : "");
      color = entry.monochrome === false;
    } else {
      var makeKey = catalog.logo_aliases && catalog.logo_aliases[car.mærke] || car.mærke;
      svg = catalog.logos && catalog.logos[makeKey];
      png = catalog.logo_pngs && catalog.logo_pngs[makeKey];
      label = car.mærke + " logo";
      color = catalog.logo_colors && catalog.logo_colors[makeKey] === true;
      var source = catalog.logo_urls && catalog.logo_urls[makeKey];
      if (source) { url = source.url; white = source.white === true; color = source.monochrome === false; }
    }
    var data = typeof png === "string" ? png.replace(/\s+/g, "") : "";
    var src = /^iVBORw0KGgo[A-Za-z0-9+/]*={0,2}$/.test(data) ? "data:image/png;base64," + data :
      (typeof svg === "string" && /<svg(?:\s|>)/.test(svg) ? "data:image/svg+xml," + encodeURIComponent(svg) : "");
    if (!src && typeof url === "string" && (/^https:\/\//.test(url) || /^\/(?!\/)/.test(url))) src = url;
    if (!src || FAILED_VEHICLE_LOGOS[src]) return "";
    return '<img class="' + className + (color ? " trf-logo-color" : "") + (white ? " trf-logo-white" : "") + '" src="' + esc(src) + '" data-vehicle-logo="true" alt="' + esc(label) + '" title="' + esc(label) + '" referrerpolicy="no-referrer">';
  }

  function vehicleMakeHtml(catalog, car, className) {
    if (!car || !car.mærke) return "";
    var image = vehicleLogoHtml(catalog, car, className, false);
    return '<span class="trf-make-mark">' + image + '<span class="' + className + '-text" data-make-fallback' +
      (image ? " hidden" : "") + '>' + esc(car.mærke) + '</span></span>';
  }

  function vehicleModelHtml(catalog, car) {
    if (!car || !car.model) return "";
    var image = vehicleLogoHtml(catalog, car, "trf-model-logo", true);
    return '<span class="trf-model-mark">' + image + '<span class="trf-model-logo-text" data-model-fallback' +
      (image ? " hidden" : "") + ' title="Modelnavn som tekst; officielt navnelogo vises, når en passende fil er tilføjet">' +
      esc(car.model) + '</span></span>';
  }

  var LOGO_SIZE = 22;
  var BRANDS = [
    { key: "circle_k", brand: "Circle K", img: "logo-circle-k.svg", has100: false },
    { key: "ingo", brand: "Ingo", img: "logo-ingo.svg", has100: false },
    { key: "f24", brand: "F24", img: "logo-f24.svg", has100: false },
    { key: "q8", brand: "Q8", img: "logo-q8.svg", has100: false },
    { key: "goon", brand: "Go'on", img: "logo-goon.svg", has100: false },
    { key: "shell", brand: "Shell", img: "logo-shell.svg", has100: true },
    { key: "uno_x", brand: "Uno-X", img: "logo-uno-x.svg", has100: true },
    { key: "ok", brand: "OK", img: "logo-ok.svg", has100: true },
    { key: "oil", brand: "OIL", img: "logo-oil.svg", has100: false },
    { key: "clever", brand: "Clever", img: "logo-clever.svg", has100: false, electricOnly: true },
    { key: "eon", brand: "E.ON", img: "logo-eon.svg", has100: false, electricOnly: true },
    { key: "ionity", brand: "Ionity", img: "logo-ionity.svg", has100: false, electricOnly: true },
  ];

  var FORDELE = {};

  function cfgGet(cfg, key, def) {
    if (cfg && cfg[key] !== undefined && cfg[key] !== null) return cfg[key];
    return def;
  }

  function showBrand(cfg, key) {
    if (cfg && cfg.kaeder && cfg.kaeder[key] !== undefined) return !!cfg.kaeder[key];
    return true;
  }

  class TinyRefuelCard extends HTMLElement {
    constructor() {
      super();
      vehicleLogoFailure(this);
      this._hass = null;
      this._data = null;
      this._dataFetchedAt = 0;
      this._dataFetchFailedAt = 0;
      this._dataLoading = false;
      this._locRefreshing = false;
      this._locRefreshT = 0;
      var self = this;
      this.addEventListener("cancel", function (ev) {
        if (ev.target && ev.target.classList.contains("trf-ev-dialog")) {
          ev.preventDefault();
          // Keep the dialog open until an explicit close or another dialog.
        }
      }, true);
      this.addEventListener("click", function (ev) {
        var summary = ev.target && ev.target.closest ? ev.target.closest("details[data-card-panel] > summary") : null;
        if (summary && !summary.parentElement.open) {
          self.querySelectorAll("details[data-card-panel]").forEach(function (panel) {
            if (panel !== summary.parentElement) panel.open = false;
          });
        }
        var openEv = ev.target && ev.target.closest ? ev.target.closest("[data-open-ev]") : null;
        if (openEv) {
          ev.preventDefault();
          self._openFordel = null;
          self._openEvBrand = openEv.getAttribute("data-open-ev");
          self._evPopupLimit = 10;
          self._evPopupKind = "all";
          self._render();
          return;
        }
        var closeEv = ev.target && ev.target.closest ? ev.target.closest("[data-close-ev]") : null;
        if (closeEv) {
          ev.preventDefault();
          self._closeEvPopup();
          return;
        }
        var kindEv = ev.target && ev.target.closest ? ev.target.closest("[data-ev-kind]") : null;
        if (kindEv) {
          self._evPopupKind = kindEv.getAttribute("data-ev-kind");
          self._evPopupLimit = 10;
          var evList = self.querySelector(".trf-ev-list");
          if (evList) evList.scrollTop = 0;
          self._render();
          return;
        }
        var moreStations = ev.target && ev.target.closest ? ev.target.closest("[data-more-stations]") : null;
        if (moreStations) {
          ev.preventDefault();
          var section = moreStations.getAttribute("data-more-stations");
          if (section === "fuel" || section === "ev") {
            self._extraStationRows = self._extraStationRows || {};
            self._extraStationRows[section] = (self._extraStationRows[section] || 0) + 10;
            self._render();
          }
          return;
        }
        var fewerStations = ev.target && ev.target.closest ? ev.target.closest("[data-fewer-stations]") : null;
        if (fewerStations) {
          ev.preventDefault();
          var foldSection = fewerStations.getAttribute("data-fewer-stations");
          if (foldSection === "fuel" || foldSection === "ev") {
            self._extraStationRows = self._extraStationRows || {};
            self._extraStationRows[foldSection] = 0;
            self._render();
          }
          return;
        }
        var moreEv = ev.target && ev.target.closest ? ev.target.closest("[data-more-ev]") : null;
        if (moreEv) {
          self._evPopupLimit = (self._evPopupLimit || 10) + 10;
          self._render();
          return;
        }
        var fewerEv = ev.target && ev.target.closest ? ev.target.closest("[data-fewer-ev]") : null;
        if (fewerEv) { ev.preventDefault(); self._evPopupLimit = 10; self._render(); return; }
        var scrape = ev.target && ev.target.closest ? ev.target.closest("[data-scrape]") : null;
        if (scrape) {
          ev.preventDefault();
          self._scrapeAll();
          return;
        }
        var rb = ev.target && ev.target.closest ? ev.target.closest("[data-refresh]") : null;
        if (rb) {
          ev.preventDefault();
          self._refreshLocation();
          return;
        }
        var chip = ev.target && ev.target.closest ? ev.target.closest("[data-car]") : null;
        if (chip) {
          ev.preventDefault();
          self._selectCar(parseInt(chip.getAttribute("data-car"), 10));
          return;
        }
        var fb = ev.target && ev.target.closest ? ev.target.closest("[data-fordel]") : null;
        if (fb) {
          ev.preventDefault();
          var bk = fb.getAttribute("data-fordel");
          self._openFordel = (self._openFordel === bk) ? null : bk;
          self._render();
          return;
        }
        var a = ev.target && ev.target.closest ? ev.target.closest("a[data-waze]") : null;
        if (!a) return;
        ev.preventDefault();
        var fb = a.href;
        var ua = (window.navigator && window.navigator.userAgent) || "";
        var url = fb;
        if (/Android/i.test(ua) && fb.indexOf("waze.com") >= 0) {
          url = "intent://?" + fb.split("?")[1] + "#Intent;scheme=waze;package=com.waze;S.browser_fallback_url=" + encodeURIComponent(fb) + ";end";
        }
        var row = a.closest(".trf-row, .trf-evrow");
        if (row) row.classList.add("trf-flash");
        setTimeout(function () {
          if (row) row.classList.remove("trf-flash");
          window.location.href = url;
        }, 120);
      });
    }

    setConfig(config) {
      var previous = this._config || {}, next = config || {};
      if (previous.kompakt !== next.kompakt || previous.antal_stationer !== next.antal_stationer) this._extraStationRows = {};
      this._config = next;
      this._render();
    }

    getCardSize() { return this._config && this._config.kompakt ? 3 : 6; }

    _stationRowLimit(section, total) {
      var configured = this._config && this._config.antal_stationer;
      var valid = configured !== null && configured !== '' && typeof configured !== 'boolean' && Number.isInteger(Number(configured)) && Number(configured) >= 0 && Number(configured) <= 50;
      var limit = valid && configured !== undefined ? Number(configured) : (this._config && this._config.kompakt ? 3 : 0);
      return limit === 0 ? total : Math.min(total, limit + (this._extraStationRows && this._extraStationRows[section] || 0));
    }

    _stationRowActions(section, visible, total) {
      var expanded = this._extraStationRows && this._extraStationRows[section] > 0;
      if (visible >= total && !expanded) return '';
      return '<div class="trf-list-actions">' +
        (visible < total ? '<button type="button" class="trf-ev-button" data-more-stations="' + section + '">Vis 10 mere</button>' : '') +
        (expanded ? '<button type="button" class="trf-ev-button" data-fewer-stations="' + section + '">Vis færre</button>' : '') +
        '<span class="trf-em">Viser ' + visible + ' af ' + total + ' rækker</span></div>';
    }

    static getStubConfig() {
      return { vis_benzin: true, vis_el: true, vis_andet: true };
    }

    static getConfigElement() {
      return document.createElement("tiny-refuel-card-editor");
    }

    set hass(hass) {
      var prev = this._hass && this._trackerState();
      this._hass = hass;
      vehicleLogoTheme(this, hass);
      var cur = this._trackerState();
      if (this._locRefreshing && prev && cur && cur.last_updated !== prev.last_updated) {
        this._locRefreshing = false;
      }
      if (this._locRefreshing && Date.now() - this._locRefreshT > 30000) {
        this._locRefreshing = false;
      }
      this._render();
      this._maybeLoad();
    }

    _state(entity) {
      if (!this._hass || !entity) return null;
      return this._hass.states[entity] || null;
    }

    _trackerEntity() {
      var car = this._car();
      if (car && car.location_entity) return car.location_entity;
      return cfgGet(this._config, "location_entity", "");
    }

    _trackerState() {
      return this._state(this._trackerEntity());
    }

    _location() {
      var st = this._trackerState();
      if (!st) return null;
      var la = parseFloat(st.attributes && st.attributes.latitude);
      var lo = parseFloat(st.attributes && st.attributes.longitude);
      if (!isFinite(la) || !isFinite(lo) || (la === 0 && lo === 0)) return null;
      return { lat: la, lon: lo };
    }

    _haversineKm(lat1, lon1, lat2, lon2) {
      var R = 6371;
      function rad(d) { return d * Math.PI / 180; }
      var dLat = rad(lat2 - lat1), dLon = rad(lon2 - lon1);
      var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos(rad(lat1)) * Math.cos(rad(lat2)) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
      return 2 * R * Math.asin(Math.min(1, Math.sqrt(a)));
    }

    _fmt(v) {
      if (v === null || v === undefined) return "–";
      return v.toFixed(2).replace(".", ",");
    }

    _navHref(ll, brand) {
      var nav = cfgGet(this._config, "navigation", "waze");
      if (nav === "google") {
        return "https://www.google.com/maps/dir/?api=1&destination=" + encodeURIComponent(ll || brand);
      }
      if (ll) return "https://waze.com/ul?ll=" + ll + "&navigate=yes&z=14";
      return "https://waze.com/ul?q=" + encodeURIComponent(brand) + "&navigate=yes&z=14";
    }

    _fmtKm(km) {
      if (km === null) return "–";
      if (km < 10) return km.toFixed(1).replace(".", ",");
      return String(Math.round(km));
    }

    _fmtAge(lu, plain) {
      if (!lu) return null;
      var t = new Date(lu).getTime();
      if (!isFinite(t)) return null;
      var pre = plain ? "" : "opd. ";
      var mins = Math.round((Date.now() - t) / 60000);
      if (mins < 0) return null;
      if (mins < 60) return pre + mins + "m";
      var h = Math.floor(mins / 60);
      if (h < 48) return pre + h + "t";
      return pre + Math.floor(h / 24) + "d";
    }

    _fmtStamp(value) {
      if (!value) return "–";
      var date = new Date(value);
      return isNaN(date.getTime()) ? "–" : date.toLocaleString("da-DK", { dateStyle: "short", timeStyle: "short" });
    }

    _tankLiters() {
      var car = this._car();
      var cfgL = parseFloat(car && car.tank_liters !== undefined && car.tank_liters !== null && car.tank_liters !== ""
        ? car.tank_liters : (this._config && this._config.tank_liters));
      if (isFinite(cfgL) && cfgL > 0) return cfgL;
      var tankEnt = (car && car.tank_entity) || (this._config && this._config.tank_entity) || "input_number.tankstorrelse";
      var st = this._state(tankEnt);
      var v = st ? parseFloat(st.state) : NaN;
      return isFinite(v) && v > 0 ? v : null;
    }

    _notifyService() {
      var car = this._car();
      if (car && car.notify_service) return car.notify_service;
      return cfgGet(this._config, "notify_service", "");
    }

    _cars() {
      var cfg = this._config || {};
      var configuredCars = Array.isArray(cfg.biler) && cfg.biler.length ? cfg.biler :
        (cfg.brug_faelles_koeretoejer !== false && this._data && Array.isArray(this._data.vehicles) ? this._data.vehicles : []);
      if (configuredCars.length) {
        return configuredCars.map(function (b, i) {
          return {
            navn: (b && b.navn) || (b && [b.mærke, b.model].filter(Boolean).join(" ")) || ("Køretøj " + (i + 1)),
            mærke: b ? b.mærke : null,
            model: b ? b.model : null,
            brændstof: b ? b.brændstof : null,
            batteri_kwh: b ? b.batteri_kwh : null,
            vis: b && b.vis && typeof b.vis === "object" ? b.vis : null,
            tank_liters: b ? b.tank_liters : null,
            tank_entity: b ? b.tank_entity : null,
            location_entity: b ? b.location_entity : null,
            notify_service: b ? b.notify_service : null,
          };
        });
      }
      return [{
        navn: null,
        tank_liters: cfg.tank_liters,
        tank_entity: cfg.tank_entity,
        location_entity: cfg.location_entity,
        notify_service: cfg.notify_service,
      }];
    }

    _carIdx() {
      var cars = this._cars();
      var idx = 0;
      try {
        var saved = parseInt(window.localStorage.getItem("tiny-refuel-bil"), 10);
        if (isFinite(saved) && saved >= 0 && saved < cars.length) idx = saved;
      } catch (e) {}
      if (this._carSel !== undefined && this._carSel >= 0 && this._carSel < cars.length) idx = this._carSel;
      return idx;
    }

    _car() {
      var cars = this._cars();
      return cars[this._carIdx()] || cars[0];
    }

    _selectCar(i) {
      var cars = this._cars();
      if (i < 0 || i >= cars.length) return;
      this._carSel = i;
      try { window.localStorage.setItem("tiny-refuel-bil", String(i)); } catch (e) {}
      this._locRefreshing = false;
      this._render();
    }

    _refreshLocation() {
      if (!this._hass || typeof this._hass.callService !== "function") return;
      var parts = this._notifyService().split(".", 2);
      if (parts.length !== 2) return;
      try {
        this._hass.callService(parts[0], parts[1], { message: "request_location_updates" });
      } catch (e) { return; }
      this._locRefreshing = true;
      this._locRefreshT = Date.now();
      this._render();
    }

    _finishScrape(message) {
      this._scraping = false;
      clearTimeout(this._scrapeTimer);
      this._scrapeMessage = message;
      this._render();
    }

    _progressText(progress) {
      if (!progress) return "";
      if (progress.phase === "starting") return "Starter hentning…";
      var place = progress.station ? " · " + progress.station : "";
      var count = progress.current && progress.total ? " (" + progress.current + "/" + progress.total + ")" : "";
      return "Henter " + (progress.phase || "data") + " fra " + (progress.provider || "udbyder") + place + count + "…";
    }

    _scrapeAll() {
      if (this._scraping) return;
      if (!this._hass || typeof this._hass.callService !== "function") {
        this._scrapeMessage = "Tilføj Tiny Refuel under Enheder og tjenester.";
        this._render();
        return;
      }
      this._scraping = true;
      var fuelTypes = null;
      var selectedCar = this._car();
      if (cfgGet(this._config, "scrape_valgt_bil", true) && selectedCar && selectedCar.brændstof) {
        var fuelMap = {
          benzin: ["benzin"], diesel: ["diesel"], el: ["el"],
          hybrid: ["benzin"], plug_in_hybrid: ["benzin", "el"]
        };
        fuelTypes = fuelMap[selectedCar.brændstof] || null;
      }
      var scopeText = fuelTypes ? fuelTypes.join(" og ") : "benzin, diesel og el";
      this._scrapeMessage = "Starter hentning af " + scopeText + "…";
      this._scrapeBaseline = this._data && this._data.updated;
      this._scrapeStarted = Date.now();
      this._scrapeRun = (this._scrapeRun || 0) + 1;
      var self = this, run = this._scrapeRun;
      this._render();
      try {
        var serviceData = fuelTypes ? { fuel_types: fuelTypes } : {};
        Promise.resolve(this._hass.callService("tiny_refuel", "refresh", serviceData)).catch(function (err) {
          if (self._scraping && self._scrapeRun === run) self._finishScrape("Opdateringskaldet fejlede: " + String(err && err.message || err));
        });
        this._scrapeTimer = setTimeout(function () { self._pollScrape(run); }, 5000);
      } catch (err) {
        this._finishScrape("Opdateringskaldet fejlede: " + String(err && err.message || err));
      }
    }

    _pollScrape(run) {
      if (!this._scraping || this._scrapeRun !== run) return;
      var self = this;
      this._fetchJson().then(function (data) {
        if (!self._scraping || self._scrapeRun !== run) return;
        var attempt = data && Date.parse(data.last_attempt);
        if (data && !data.refreshing && data.last_error && isFinite(attempt) && attempt >= self._scrapeStarted - 1000) {
          self._finishScrape("Hentningen fejlede: " + data.last_error);
          return;
        }
        if (data && data.refreshing && data.progress) {
          self._scrapeMessage = self._progressText(data.progress);
          self._render();
        }
        var stamp = data && Date.parse(data.updated);
        if (data && data.updated !== self._scrapeBaseline && isFinite(stamp) && stamp >= self._scrapeStarted - 1000) {
          var errors = self._errorGroups().length;
          self._finishScrape(errors ? "Nye data indlæst · " + errors + " fejl i hentningen. Se datastatus nedenfor." : "Nye data indlæst · hentningen er afsluttet uden registrerede fejl.");
        } else if (Date.now() - self._scrapeStarted > 12 * 60000) {
          self._finishScrape("Ingen ny datafil efter 12 minutter. Kontrollér Tiny Refuels fejl i Home Assistant-loggen.");
        } else {
          self._scrapeTimer = setTimeout(function () { self._pollScrape(run); }, 5000);
        }
      });
    }

    disconnectedCallback() {
      clearTimeout(this._scrapeTimer);
      clearTimeout(this._dataTimer);
      this._scraping = false;
      this._scrapeRun = (this._scrapeRun || 0) + 1;
    }

    _posAge() {
      var st = this._trackerState();
      if (!st || !st.last_updated) return null;
      var t = new Date(st.last_updated).getTime();
      if (!isFinite(t)) return null;
      var mins = Math.round((Date.now() - t) / 60000);
      if (mins < 1) return "lige nu";
      if (mins < 60) return "for " + mins + " min siden";
      var h = Math.floor(mins / 60);
      if (h < 24) return "for " + h + " t siden";
      return "for " + Math.floor(h / 24) + " d siden";
    }


    _fetchJson() {
      var self = this;
      if (!this._hass || typeof this._hass.callApi !== "function") return Promise.resolve(null);
      return this._hass.callApi("GET", "tiny_refuel/data").then(function (data) {
        self._dataApiError = null;
        self._data = data;
        self._dataFetchedAt = Date.now();
        self._dataLoading = false;
        self._render();
        clearTimeout(self._dataTimer);
        self._dataTimer = setTimeout(function () { self._maybeLoad(); }, data.refreshing || !data.updated ? 5000 : 60000);
        return data;
      }).catch(function (error) {
        var code = error && (error.status_code || error.status);
        self._dataApiError = code ? "HTTP " + code : "Data-API kunne ikke kontaktes";
        self._dataLoading = false;
        self._dataFetchFailedAt = Date.now();
        self._render();
        clearTimeout(self._dataTimer);
        self._dataTimer = setTimeout(function () { self._maybeLoad(); }, 30000);
        return null;
      });
    }

    _maybeLoad() {
      if (!this._hass || !this._hass.callApi || this._dataLoading) return;
      var delay = this._data && (this._data.refreshing || !this._data.updated) ? 4000 : 55000;
      if (this._data && Date.now() - this._dataFetchedAt < delay) return;
      if (!this._data && this._dataFetchFailedAt && Date.now() - this._dataFetchFailedAt < 25000) return;
      this._dataLoading = true;
      this._fetchJson();
    }

    _dataStations() {
      if (this._data && Array.isArray(this._data.stations)) return this._data.stations;
      return [];
    }

    _nearestIn(list, loc) {
      if (!list || !list.length || !loc) return null;
      var best = null;
      for (var i = 0; i < list.length; i++) {
        var coords = this._evCoords(list[i]);
        if (!coords) continue;
        var km = this._haversineKm(loc.lat, loc.lon, coords.lat, coords.lon);
        if (!best || km < best.km) best = { st: list[i], km: km };
      }
      return best;
    }

    _chgBadge(p95, prev95, title) {
      if (!isFinite(p95) || !isFinite(prev95)) return "";
      var c = Math.round((p95 - prev95) * 100) / 100;
      var cls = c < -0.005 ? "dn" : (c > 0.005 ? "up" : "flat");
      var arrow = cls === "dn" ? "▼" : (cls === "up" ? "▲" : "=");
      return '<span class="trf-chg ' + cls + '" title="' + esc(title || "") + '">' +
        arrow + Math.abs(c).toFixed(2).replace(".", ",") + "</span>";
    }

    _buildRows(loc) {
      var selfList = this._dataStations();
      var rows = [];
      for (var bi = 0; bi < BRANDS.length; bi++) {
        var b = BRANDS[bi];
        if (b.electricOnly || !showBrand(this._config, b.key)) continue;
        var row = { b: b, v95: null, v100: null, diesel: null, km: null, ll: null,
                    stName: null, stAddr: null, stAge: null, chg: "", liste: false, alt: null };
        if (b.liste || ((b.key === 'ok' || b.key === 'oil') && !selfList.some(function (s) { return s.brand === b.brand && !s.liste; }))) {
          var lr = null;
          for (var li = 0; li < selfList.length; li++) {
            if (selfList[li].brand === b.brand && selfList[li].liste) { lr = selfList[li]; break; }
          }
          if (lr) {
            row.v95 = typeof lr.p95 === 'number' && lr.p95 > 0 ? lr.p95 : null;
            row.diesel = typeof lr.diesel === 'number' && lr.diesel > 0 ? lr.diesel : null;
            row.stName = lr.name;
            row.liste = true;
          }
          rows.push(row);
          continue;
        }
        var picked = null;
        var cands = [];
        for (var si = 0; si < selfList.length; si++) {
          var cs = selfList[si], selection = this._effVis();
          if (cs.brand === b.brand && !cs.liste &&
              ((selection.benzin && typeof cs.p95 === 'number' && cs.p95 > 0) ||
               (selection.diesel && typeof cs.diesel === 'number' && cs.diesel > 0))) cands.push(cs);
        }
        var near = this._nearestIn(cands, loc);
        if (near) {
          picked = { st: near.st, km: near.km };
        } else if (cands.length) {
          picked = { st: cands[0], km: null };
        }
        if (picked) {
          if (loc && !near) {
            row.locationNote = 'Koordinater mangler · nærmeste station kan ikke bestemmes';
          } else if (loc && cands.some(function (station) { return !this._evCoords(station); }, this)) {
            row.locationNote = 'Nærmeste blandt stationer med kendte koordinater';
          }
          var pst = picked.st;
          row.v95 = typeof pst.p95 === 'number' && pst.p95 > 0 ? pst.p95 : null;
          row.v100 = b.has100 && typeof pst.p100 === 'number' && pst.p100 > 0 ? pst.p100 : null;
          row.km = picked.km;
          row.ll = this._evCoords(pst) ? pst.lat + "," + pst.lon : null;
          row.stName = (pst.name || pst.brand) + (pst.stale ? ' · gemte data: seneste hentning fejlede' : '');
          row.stAddr = pst.address;
          row.stale = !!pst.stale;
          row.stAge = this._fmtAge(pst.lu);
          row.stAgeRaw = pst.lu;
          row.alt = pst.alt || null;
          if (isFinite(pst.prev95)) {
            row.chg = this._chgBadge(row.v95, pst.prev95, "Ændring siden sidste udtræk");
          }
          if (typeof pst.diesel === 'number' && pst.diesel > 0) {
            row.diesel = pst.diesel;
          }
        }
        rows.push(row);
      }
      return rows;
    }

    _effVis() {
      var cfg = this._config || {}, car = null;
      try { car = this._car(); } catch (e) {}
      var knownFuel = car && ["benzin", "diesel", "el", "hybrid", "plug_in_hybrid"].indexOf(car.brændstof) !== -1;
      var defaults = knownFuel ? visForFuel(car.brændstof) : { benzin: true, diesel: false, el: true, andet: true };
      var own = car && car.vis && typeof car.vis === "object" ? car.vis : {};
      function visible(key) {
        return own[key] !== undefined ? !!own[key] : cfgGet(cfg, "vis_" + key, defaults[key]);
      }
      return { benzin: visible("benzin"), diesel: visible("diesel"),
        el: (!car || car.brændstof !== "hybrid") && visible("el"), andet: visible("andet") };
    }

    _render() {
      if (!this._config) return;
      if (this._cars().some(function (car) { return !!car.mærke; })) loadVehicleCatalog(this);
      var openPanels = {};
      this.querySelectorAll("details[data-card-panel]").forEach(function (node) {
        openPanels[node.getAttribute("data-card-panel")] = node.open;
      });
      var previousList = this.querySelector && this.querySelector(".trf-ev-list");
      var popupScroll = previousList ? previousList.scrollTop : 0;
      var cfg = this._config;
      var compact = !!cfg.kompakt;
      var loc = this._location();
      var _v = this._effVis();
      var visBenzin = _v.benzin;
      var visDiesel = _v.diesel;
      var visEl = _v.el;
      var visAndet = _v.andet;

      var cols = ["minmax(70px,130px)"];
      if (visBenzin) cols.push("minmax(60px,1fr)", "minmax(60px,1fr)");
      if (visDiesel) cols.push("minmax(60px,1fr)");
      cols.push("52px");
      var grid = cols.join(" ");
      var priceColumnCount = (visBenzin ? 2 : 0) + (visDiesel ? 1 : 0);

      var infoMetrics = "";
      var body = "";
      var rows = this._buildRows(loc);
      if (compact && loc) rows.sort(function (a, b) {
        return (a.liste || a.km === null ? Infinity : a.km) - (b.liste || b.km === null ? Infinity : b.km);
      });
      var hasData = !!this._data;
      if (!visBenzin && !visDiesel) rows = [];

      if (!hasData) {
        body = '<div class="trf-em">Henter priser…</div>';
      } else if (!rows.length && (visBenzin || visDiesel)) {
        body = '<div class="trf-em">Ingen kæder valgt — åbn kortets indstillinger (UI-editor).</div>';
      } else if (!rows.length) {
        body = "";
      } else {
        var p95s = [], p100s = [];
        for (var j = 0; j < rows.length; j++) {
          if (typeof rows[j].v95 === 'number' && rows[j].v95 > 0) p95s.push(rows[j].v95);
          if (rows[j].b.has100 && typeof rows[j].v100 === 'number' && rows[j].v100 > 0) p100s.push(rows[j].v100);
        }
        var min95 = p95s.length ? Math.min.apply(null, p95s) : null;
        var min100 = p100s.length ? Math.min.apply(null, p100s) : null;

        var bestHtml = "";
        if (visAndet) {
          var bestParts = [];
          var fuels = [];
          if (visBenzin) fuels.push({ field: 'v95', label: '95' }, { field: 'v100', label: '100' });
          if (visDiesel) fuels.push({ field: 'diesel', label: 'Diesel' });
          fuels.forEach(function (fuel) {
            var pricedRows = rows.filter(function (row) { return (fuel.field !== 'v100' || row.b.has100) && typeof row[fuel.field] === 'number' && isFinite(row[fuel.field]) && row[fuel.field] > 0; });
            if (!pricedRows.length) return;
            var minimum = Math.min.apply(null, pricedRows.map(function (row) { return row[fuel.field]; }));
            var cheapest = pricedRows.filter(function (row) { return row[fuel.field] === minimum; });
            var names = cheapest.map(function (row) { return row.b.brand; });
            var content = compact ? esc(names.slice(0, 2).join(', ')) + (names.length > 2 ? ' +' + (names.length - 2) : '') : cheapest.map(function (row) { return '<img src="/tiny_refuel/static/logos/' + row.b.img + '" alt="' + esc(row.b.brand) + '" class="trf-inline">'; }).join('');
            bestParts.push('<span title="' + esc(names.join(', ')) + '"><b>Billigst ' + fuel.label + ': ' + this._fmt(minimum) + '</b> · ' + content + '</span>');
          }, this);
          if (bestParts.length) bestHtml = '<div class="trf-best">' + bestParts.join('') + '</div>';
        }

        if (visAndet && !compact && loc) {
          var nearBest = null;
          for (var nb = 0; nb < rows.length; nb++) {
            if (rows[nb].liste || rows[nb].km === null) continue;
            if (!nearBest || rows[nb].km < nearBest.km) nearBest = rows[nb];
          }
          if (nearBest) {
            bestHtml += '<div class="trf-em">Nærmeste lige nu: <b>' + esc(nearBest.b.brand) + "</b> · " +
              esc(nearBest.stName || "") + " — <b>" + this._fmtKm(nearBest.km) +
              " km</b> fra din placering. Tryk på et logo for navigation.</div>";
          }
        }

        var head = '<div class="trf-head trf-fuel-head" data-price-cols="' + priceColumnCount + '" style="--trf-price-cols:' + priceColumnCount + ';grid-template-columns: ' + grid + '"><span></span>';
        if (visBenzin) head += '<span class="trf-p">95</span><span class="trf-p">100</span>';
        if (visDiesel) head += '<span class="trf-p">Diesel</span>';
        head += '<span class="trf-km" title="Afstand fra telefonens placering til nærmeste station">km</span></div>';
        body += bestHtml;
        var fuelHtmlRows = [];

        var fuelVisible = this._stationRowLimit("fuel", rows.length);
        for (var r = 0; r < fuelVisible; r++) {
          var row = rows[r];
          var g95 = visBenzin && min95 !== null && row.v95 !== null && row.v95 === min95;
          var g100 = visBenzin && row.b.has100 && min100 !== null && row.v100 !== null && row.v100 === min100;
          var cls = "trf-row";
          var staleTag = row.stale ? '<span class="trf-stale-tag">Gemt</span>' : '';
          var cells = "";
          if (visBenzin) {
            cells += row.v95 === null
              ? '<div class="trf-pcol" data-label="95"><span class="trf-price trf-na">–</span></div>'
              : '<div class="trf-pcol" data-label="95"><span class="trf-price' + (g95 ? " trf-g95" : "") + '">' + this._fmt(row.v95) + "</span>" + staleTag + row.chg + "</div>";
            cells += (!row.b.has100 || row.v100 === null)
              ? '<div class="trf-pcol" data-label="100"><span class="trf-price trf-na">–</span></div>'
              : '<div class="trf-pcol" data-label="100"><span class="trf-price' + (g100 ? " trf-g100" : "") + '">' + this._fmt(row.v100) + "</span>" + staleTag + "</div>";
          }
          if (visDiesel) {
            cells += row.diesel === null
              ? '<div class="trf-pcol" data-label="Diesel"><span class="trf-price trf-na">–</span></div>'
              : '<div class="trf-pcol" data-label="Diesel"><span class="trf-price">' + this._fmt(row.diesel) + "</span>" + staleTag + "</div>";
          }
          var kmCell, link, title;
          if (row.liste) {
            kmCell = '<span class="trf-km" style="font-weight:400;font-size:11px;">liste</span>';
            link = this._navHref(null, row.b.brand);
            title = row.b.brand + " listepris" + (row.stAgeRaw ? " · " + row.stAgeRaw : "");
          } else if (row.ll) {
            var kmTxt = row.km !== null ? this._fmtKm(row.km) : "–";
            var kmShow = row.km !== null ? kmTxt + " km" : kmTxt;
            var kmCls = row.km !== null && row.km > 15 ? "trf-km trf-far" : "trf-km";
            kmCell = row.stAge
              ? '<span class="' + kmCls + '">' + kmShow + '<span class="trf-age">' + esc(row.stAge) + "</span></span>"
              : '<span class="' + kmCls + '">' + kmShow + "</span>";
            link = this._navHref(row.ll, row.b.brand);
            title = row.b.brand + " — " + (row.km !== null ? kmTxt + " km · " : "") + (row.stName || "") +
              (row.stAgeRaw ? " · prisinfo: " + row.stAgeRaw : "") + this._altTitle(row.alt, visBenzin, visDiesel);
          } else {
            kmCell = '<span class="trf-km">–</span>';
            link = this._navHref(null, [row.b.brand, row.stAddr || row.stName].filter(Boolean).join(" "));
            title = [row.b.brand, row.stAddr || row.stName].filter(Boolean).join(" · ");
          }
          var logo = '<div class="trf-logo"><a class="trf-navlink" data-waze="' + esc(row.b.brand) +
            '" href="' + link + '" rel="noopener" title="' + esc(title) + '"><img src="/tiny_refuel/static/logos/' +
            row.b.img + '" alt="' + esc(row.b.brand) + '"></a></div>';
          var sub = "";
          var benefitEntry = this._benefitEntry(row.b.key);
          var fbtn = (visAndet && benefitEntry)
            ? '<a href="#" class="trf-fordel-btn" data-fordel="' + esc(row.b.key) + '" title="Se udbyderens fordele">★ Fordele</a>'
            : "";
          if (row.liste) {
            sub = '<div class="trf-station"><span class="trf-subtxt"><span class="trf-pill">Listepris</span>' +
              (row.stAgeRaw && this._fmtAge(row.stAgeRaw, true) === null ? " · " + esc(row.stAgeRaw) : "") + "</span>" + fbtn + "</div>";
          } else if (row.stName || row.stAddr) {
            sub = '<div class="trf-station"><span class="trf-subtxt">' + esc(row.stName || "") +
              (row.stName && row.stAddr ? " · " : "") + esc(row.stAddr || "") +
              this._altTitle(row.alt, visBenzin, visDiesel) + "</span>" + fbtn + "</div>";
          } else if (fbtn) {
            sub = '<div class="trf-station"><span class="trf-subtxt"></span>' + fbtn + "</div>";
          }
          if (row.locationNote) {
            sub += '<div class="trf-station"><span class="trf-subtxt">' + esc(row.locationNote) + '</span></div>';
          }
          if (benefitEntry) sub += this._benefitBox(row.b.key, row.b.brand, benefitEntry);
          fuelHtmlRows.push('<div class="' + cls + '" data-price-cols="' + priceColumnCount + '" style="--trf-price-cols:' + priceColumnCount + ';grid-template-columns: ' + grid + '" title="' + esc(title) + '">' +
            logo + cells + kmCell + sub + "</div>");
        }
        body += head + '<div class="trf-fuel-grid">' + fuelHtmlRows.join("") + '</div>' + this._stationRowActions("fuel", fuelVisible, rows.length);
      }

      if (hasData) {
        if (visEl && !visBenzin && !visDiesel && !compact) body += this._nearestEvHtml(loc);
        if (visEl) {
          body += this._evHtml(loc);
        }

        if (visAndet) {
          var _carFuel = null;
          var _carBatt = NaN;
          try {
            var _cc = this._car();
            _carFuel = _cc && _cc.brændstof;
            _carBatt = _cc ? parseFloat(_cc.batteri_kwh) : NaN;
          } catch (e) {}
          if (_carFuel !== "el" && (visBenzin || visDiesel)) {
            var tankFuelField = visBenzin ? "v95" : "diesel", tankFuelLabel = visBenzin ? "95" : "Diesel";
            var tankL = this._tankLiters();
          var priced = [];
          for (var m = 0; m < rows.length; m++) {
            if (!rows[m].liste && typeof rows[m][tankFuelField] === "number" && isFinite(rows[m][tankFuelField]) && rows[m][tankFuelField] > 0) {
              priced.push({ brand: rows[m].b.brand, v: rows[m][tankFuelField] });
            }
          }
          if (priced.length >= 2 && tankL !== null) {
            var cheap = priced[0], dear = priced[0];
            for (var n2 = 1; n2 < priced.length; n2++) {
              if (priced[n2].v < cheap.v) cheap = priced[n2];
              if (priced[n2].v > dear.v) dear = priced[n2];
            }
            infoMetrics += '<div class="trf-tank">Fuld tank (' + String(tankL).replace(".", ",") + ' L' +
              (this._cars().length > 1 && this._car().navn ? " · " + esc(this._car().navn) : "") + ') ' + tankFuelLabel + ': <b>' +
              esc(cheap.brand) + " " + Math.round(cheap.v * tankL) + " kr</b> → " + esc(dear.brand) + " " +
              Math.round(dear.v * tankL) + " kr · spar <b>" + Math.round((dear.v - cheap.v) * tankL) + " kr</b></div>";
          }
          }
          if ((_carFuel === "el" || _carFuel === "plug_in_hybrid") && visEl && isFinite(_carBatt) && _carBatt > 0 && this._data && Array.isArray(this._data.ev)) {
            var kwhs = [];
            for (var me = 0; me < this._data.ev.length; me++) {
              var _ev = this._data.ev[me];
              if (typeof _ev.kwh === "number" && isFinite(_ev.kwh) && _ev.kwh > 0 && _ev.address && showBrand(cfg, this._evBrandKey(_ev.brand))) kwhs.push(_ev.kwh);
            }
            if (kwhs.length >= 2) {
              var kmin = Math.min.apply(null, kwhs), kmax = Math.max.apply(null, kwhs);
              var bkwh = _carBatt;
              infoMetrics += '<div class="trf-tank">Fuld opladning (' + String(bkwh).replace(".", ",") + ' kWh' +
                (this._cars().length > 1 && this._car().navn ? " · " + esc(this._car().navn) : "") + '): <b>' +
                Math.round(kmin * bkwh) + " kr</b> → " + Math.round(kmax * bkwh) +
                " kr · spar <b>" + Math.round((kmax - kmin) * bkwh) + " kr</b></div>";
            }
          }
          var snit = this._data && this._data.snittet;
          var snitKey = visBenzin ? "p95" : (visDiesel ? "diesel" : null);
          var snitLbl = visBenzin ? "95" : "Diesel";
          if (snitKey && snit && snit[snitKey]) {
            var snitTxt = "Landsnit (" + snit[snitKey].n + " stationer): " + snitLbl + " <b>" + this._fmt(snit[snitKey].v) + "</b>";
            var snitMin = visBenzin ? min95 : null;
            if (visBenzin && snitMin === null && rows.length) {
              snitMin = null;
            }
            if (!visBenzin && visDiesel) {
              var dvals = [];
              for (var md = 0; md < rows.length; md++) {
                if (isFinite(rows[md].diesel)) dvals.push(rows[md].diesel);
              }
              snitMin = dvals.length ? Math.min.apply(null, dvals) : null;
            }
            if (snitMin !== null) {
              var sdiff = Math.round((snitMin - snit[snitKey].v) * 100) / 100;
              snitTxt += sdiff <= -0.005
                ? " · billigst nær dig <b>" + Math.abs(sdiff).toFixed(2).replace(".", ",") + " under</b>"
                : (sdiff >= 0.005
                  ? " · billigst nær dig " + sdiff.toFixed(2).replace(".", ",") + " over"
                  : " · billigst nær dig = snit");
            }
            infoMetrics += '<div class="trf-tank">' + snitTxt + "</div>";
          }
        }

      }

      var upd = "–";
      var src = this._data;
      if (src && src.updated) {
        var dt = new Date(src.updated);
        if (!isNaN(dt.getTime()) && window.Intl) {
          upd = new Intl.DateTimeFormat("da-DK", { timeZone: "Europe/Copenhagen", hour: "2-digit", minute: "2-digit", day: "numeric", month: "short" }).format(dt);
        }
      }
      var cars = this._cars();
      var carHtml = "";
      if (Array.isArray(cfg.biler) && cfg.biler.length && (cars.length > 1 || cfgGet(cfg, "vis_bilvaelger", !compact))) {
        var sel = this._carIdx();
        carHtml = '<div class="trf-cars">';
        for (var ci = 0; ci < cars.length; ci++) {
          var plainCarName = [cars[ci].mærke, cars[ci].model].filter(Boolean).join(" ");
          var modelAsset = this._katalog && this._katalog.model_logos && this._katalog.model_logos[cars[ci].mærke] && this._katalog.model_logos[cars[ci].mærke][cars[ci].model];
          var customCarName = !cars[ci].model || (modelAsset && modelAsset.family) || String(cars[ci].navn).toLowerCase() !== plainCarName.toLowerCase();
          carHtml += '<button class="trf-car' + (ci === sel ? " trf-on" : "") + '" data-car="' + ci + '" aria-label="' + esc(cars[ci].navn) + '">' +
            vehicleMakeHtml(this._katalog, cars[ci], "trf-car-logo") +
            vehicleModelHtml(this._katalog, cars[ci]) +
            (customCarName ? '<span>' + esc(cars[ci].navn) + "</span>" : "") + "</button>";
        }
        carHtml += "</div>";
      }

      var legends = [];
      if (visBenzin) legends.push('<b>95</b> = Blyfri 95 (E10) · <b>100</b> = 100-oktan · <b>Premium 95</b> = benzin med additiver · <b>92</b> = Blyfri 92');
      if (visDiesel) legends.push('<b>Diesel</b> = standard diesel · <b>Extra</b> = opgraderet diesel · <b>HVO100</b> = alternativt dieselbrændstof · <b>AdBlue</b> = væske til dieselkøretøjets udstødningsrensning');
      if (visEl) legends.push('<b>EL</b> = opladning i kr/kWh · <b>Se pris</b> = ingen verificeret stationspris; tjek udbyderens app eller kort · <b>*</b> = offentlig selskabstakst, lokal pris kan afvige · <b>fra</b> = udbyderens startpris · <b>km</b> = afstand i luftlinje');
      var legendHtml = legends.length ? '<div class="trf-legend"><b>Energityper:</b> ' + legends.join(' · ') + '</div>' : '';
      if (visBenzin || visDiesel) legendHtml += '<div class="trf-legend"><b>Listepris</b> = kædens vejledende brændstofpris. En listepris er ikke knyttet til en bestemt station; pumpeprisen kan afvige.</div>';
      var infoSections = (visBenzin || visDiesel ? this._fuelDataSummary() : '') +
        (visEl ? this._evDataSummary(this._evEntries()) : '') + this._coordinateSummary() + infoMetrics + legendHtml;
      var infoPanelHtml = infoSections ? '<details class=\"trf-info-panel\" data-card-panel=\"information\"><summary>Information og datagrundlag</summary><div class=\"trf-info-content\">' + infoSections + '</div></details>' : '';
      var selectedFuel = this._car() && this._car().brændstof;
      var cardTitle = selectedFuel === 'plug_in_hybrid' && visBenzin && visEl ? 'Hybrid – benzin og opladning' :
        (selectedFuel === 'hybrid' && visBenzin && !visEl ? 'Hybrid – benzin' :
        (visEl && !visBenzin && !visDiesel ? 'Ladepriser' :
        (visEl ? 'Brændstof og ladepriser' : (visDiesel && !visBenzin ? 'Dieselpriser' : 'Benzinpriser'))));

      var scrapeStatus = this._data && this._data.refreshing && this._data.progress
        ? this._progressText(this._data.progress) : (this._scrapeMessage || "");
      var integrationVersion = this._data && this._data.version;
      var scrapeButton = cfgGet(cfg, "vis_scrape_knap", !compact) ? '<button type="button" class="trf-ev-button" data-scrape' + (this._scraping ? ' disabled' : '') + '>Hent data</button>' : '';
      var dataTools = scrapeButton || scrapeStatus ? '<div class="trf-data-tools">' + scrapeButton + '<span role="status">' + esc(scrapeStatus) + '</span></div>' : '';
      this.innerHTML =
        "<style>" + CSS + "</style>" +
        '<div class="trf' + (compact ? ' trf-compact' : '') + '">' +
        '<div class="trf-titlebar"><div class="trf-title">' + cardTitle + '</div>' +
        '<button class="trf-refresh' + (this._locRefreshing ? " trf-spin" : "") + '" data-refresh title="Hent frisk GPS-position fra telefonen">⟳</button></div>' +
        '<div class="trf-rule"></div>' +
        dataTools + this._dataErrorsHtml() +
        carHtml +
        (visAndet && !compact
          ? '<div class="trf-pos">Position: ' + (this._locRefreshing ? "opdaterer…" : esc(this._posAge() || "ukendt")) + "</div>"
          : "") +
        body +
        infoPanelHtml +
        '<div class="trf-foot"><span>Hentet fra selskabernes egne lister: ' + esc(upd) + '</span><span>Tiny Refuel v' + esc(integrationVersion || "ukendt") + '</span></div>' +
        "</div>" + this._evPopupHtml(loc);
      this.querySelectorAll("details[data-card-panel]").forEach(function (node) {
        node.open = !!openPanels[node.getAttribute("data-card-panel")];
      });
      var popup = this.querySelector && this.querySelector(".trf-ev-dialog");
      if (popup) {
        if (typeof popup.showModal === "function") popup.showModal();
        else popup.setAttribute("open", "");
        var popupList = popup.querySelector(".trf-ev-list");
        if (popupList) popupList.scrollTop = popupScroll;
      }
      this._maybeLoad();
    }

    _brandImg(brand) {
      if (!brand) return null;
      var bl = String(brand).toLowerCase();
      for (var i = 0; i < BRANDS.length; i++) {
        if (BRANDS[i].brand.toLowerCase() === bl) return BRANDS[i].img;
      }
      return null;
    }

    _altTitle(alt, showBenzin, showDiesel) {
      if (!alt) return "";
      if (showBenzin === false && showDiesel === false) return "";
      var parts = [];
      for (var k in alt) {
        if (!isFinite(alt[k])) continue;
        var kl = k.toLowerCase();
        var isDiesel = kl.indexOf("diesel") >= 0 || kl.indexOf("hvo") >= 0 ||
          kl.indexOf("adblue") >= 0 || kl.indexOf("ad-blue") >= 0;
        if (isDiesel && showDiesel === false) continue;
        if (!isDiesel && showBenzin === false) continue;
        parts.push(k + " " + alt[k].toFixed(2).replace(".", ","));
      }
      return parts.length ? " · også: " + parts.join(", ") : "";
    }

    _evBrandKey(brand) {
      for (var i = 0; i < BRANDS.length; i++) {
        if (BRANDS[i].brand.toLowerCase() === String(brand).toLowerCase()) return BRANDS[i].key;
      }
      return null;
    }

    _evEntries() {
      var self = this;
      return this._data && Array.isArray(this._data.ev) ? this._data.ev.filter(function (ev) {
        return ev && ev.brand && self._evBrandKey(ev.brand) && showBrand(self._config, self._evBrandKey(ev.brand));
      }) : [];
    }

    _evPublicTariff(ev) {
      if (!ev || !this._data || !Array.isArray(this._data.ev)) return null;
      var brand = String(ev.brand || '').toLowerCase();
      var entries = this._data.ev.filter((row) => row && String(row.brand || '').toLowerCase() === brand &&
        !this._evHasLocation(row) && typeof row.kwh === 'number' && isFinite(row.kwh) && row.kwh > 0);
      if (!entries.length) return null;
      var kind = String(ev.kind || '').toLowerCase();
      var power = Number(ev.power_kw);
      var category = kind;
      if (brand === 'ok') {
        if (kind === 'normal' || kind === 'hurtig' || kind === 'lyn') category = kind;
        else if (kind === 'ac' || (isFinite(power) && power > 0 && power <= 22)) category = 'normal';
        else if (isFinite(power) && power > 22 && power < 100) category = 'hurtig';
        else if (kind === 'dc' || (isFinite(power) && power >= 100)) category = 'lyn';
        var okItem = entries.find((row) => String(row.name || '').toLowerCase().indexOf(category) === 0);
        return okItem ? { kwh: okItem.kwh, stale: !!okItem.stale, label: 'indicative' } : null;
      }
      if (brand === 'q8') {
        category = kind === 'ac' || kind === 'normal' || (isFinite(power) && power > 0 && power <= 22)
          ? 'normal' : 'lyn';
        var q8Item = entries.find((row) => String(row.name || '').toLowerCase().indexOf(category) >= 0);
        return q8Item ? { kwh: q8Item.kwh, stale: !!q8Item.stale, label: 'indicative' } : null;
      }
      if (brand === 'e.on') {
        category = kind === 'ac' || kind.indexOf('ac') >= 0 ? 'ac' : 'dc';
        var eonItem = entries.find((row) => String(row.name || '').toLowerCase().indexOf(category) === 0);
        return eonItem ? { kwh: eonItem.kwh, stale: !!eonItem.stale, label: 'from' } : null;
      }
      if (brand === 'circle k' && kind === 'dc' && isFinite(power) && power >= 100) {
        var ckItem = entries.find((row) => /lynlader/i.test(String(row.name || '')));
        return ckItem ? { kwh: ckItem.kwh, stale: !!ckItem.stale, label: 'list' } : null;
      }
      if (brand === 'ionity') {
        var ionityItem = entries.find((row) => /direkte betaling/i.test(String(row.name || '')));
        return ionityItem ? { kwh: ionityItem.kwh, stale: !!ionityItem.stale, label: 'from' } : null;
      }
      return null;
    }

    _evCoords(ev) {
      if (ev.lat === null || ev.lat === undefined || ev.lat === '' || ev.lon === null || ev.lon === undefined || ev.lon === '') return null;
      var lat = Number(ev.lat), lon = Number(ev.lon);
      if (!isFinite(lat) || !isFinite(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180 || (lat === 0 && lon === 0)) return null;
      return { lat: lat, lon: lon };
    }

    _evHasLocation(ev) {
      return !!(ev.address || (ev.name && this._evCoords(ev)));
    }

    _benefitEntry(key) {
      var all = this._data && this._data.benefits;
      var item = all && all[key];
      if (item && typeof item.summary === "string" && item.summary.trim()) return item;
      return null;
    }

    _benefitBox(key, brand, item) {
      if (!item) return "";
      var text = typeof item.summary === "string" ? item.summary.trim() : "";
      if (!text) return "";
      var checked = item.fetched_at ? "<br><small>Hentet: " + esc(item.fetched_at.slice(0, 10)) +
        (item.status === "stale" ? " · gemte oplysninger" : "") + "</small>" : "";
      var source = item.source_url ? ' <a href="' + esc(item.source_url) + '" target="_blank" rel="noopener">Officiel kilde</a>' : "";
      return this._openFordel === key ? '<div class="trf-fordel-box"><b>' + esc(brand) + " · fordele, app og abonnement:</b><br>" +
        esc(text) + source + checked + "</div>" : "";
    }

    _nearestEvHtml(loc) {
      if (!loc) return '<div class="trf-em">Nærmeste ladested: position mangler. Vælg en positions-enhed i kortets editor.</div>';
      var entries = this._evEntries(), nearest = null;
      for (var i = 0; i < entries.length; i++) {
        var ev = entries[i], coords = this._evCoords(ev);
        if (!this._evHasLocation(ev) || !coords) continue;
        var km = this._haversineKm(loc.lat, loc.lon, coords.lat, coords.lon);
        if (!nearest || km < nearest.km) nearest = { ev: ev, km: km };
      }
      return nearest ? '<div class="trf-em">Nærmeste lige nu: <b>' + esc(nearest.ev.brand) + '</b> ' +
        esc(nearest.ev.address || nearest.ev.name) + (nearest.ev.stale ? ' (gemte data)' : '') + ' — <b>' + this._fmtKm(nearest.km) +
        ' km</b> fra din placering. Tryk på et logo for navigation.</div>' :
        '<div class="trf-em">Nærmeste ladested kan ikke beregnes: ingen valgte ladesteder med koordinater.</div>';
    }

    _evBenefits(ev, part) {
      if (!this._effVis().andet) return '';
      var brand = this._evBrandKey(ev.brand), item = this._benefitEntry(brand);
      if (!item) return '';
      var stationRef = ev.location_id || ev.id || ev.address || ev.name || "provider";
      var benefitKey = "ev:" + brand + ":" + String(stationRef) + ":" + String(ev.kind || "");
      var button = '<a href="#" class="trf-fordel-btn" data-fordel="' + esc(benefitKey) + '" title="Se ladefordele">★ Fordele</a>';
      if (part === 'button') return button;
      if (part === 'box') return this._benefitBox(benefitKey, ev.brand, item);
      return button + this._benefitBox(benefitKey, ev.brand, item);
    }

    _evRow(ev, loc, count, inPopup, tariffs, companyGroup) {
      var coords = this._evCoords(ev);
      var km = loc && coords ? this._haversineKm(loc.lat, loc.lon, coords.lat, coords.lon) : null;
      var query = ev.brand + ' ' + (ev.address || ev.name || '');
      var link = this._navHref(coords ? coords.lat + ',' + coords.lon : null, query);
      var logo = this._brandImg(ev.brand);
      var logoContent = logo ? '<img src="/tiny_refuel/static/logos/' + esc(logo) + '" alt="' + esc(ev.brand) + '">' : esc(ev.brand);
      var title = query + (km !== null ? ' · ' + this._fmtKm(km) + ' km' : '');
      var localPrice = typeof ev.kwh === 'number' && isFinite(ev.kwh) && ev.kwh > 0;
      var publicTariff = localPrice ? null : this._evPublicTariff(ev);
      var price = localPrice ? this._fmt(ev.kwh) : (publicTariff
        ? (publicTariff.label === 'from' ? 'fra ' : '') + this._fmt(publicTariff.kwh) + (publicTariff.label === 'indicative' || publicTariff.label === 'list' ? '*' : '')
        : 'Se pris');
      var info = [ev.name || ev.brand, ev.address];
      if (publicTariff && publicTariff.stale) info.push('gemt selskabstakst: seneste hentning fejlede');
      if (publicTariff) info.push(publicTariff.label === 'from'
        ? 'offentlig fra-pris; stationsprisen kan være højere'
        : 'offentlig selskabstakst; den lokale pris kan afvige');
      if (!ev.address && coords) info.push('gadeadresse ikke oplyst; navigation til koordinater');
      if (ev.access_note) info.push(ev.access_note);
      if (ev.kind) info.push(ev.kind);
      if (ev.power_kw) info.push(ev.power_kw + ' kW');
      if (Array.isArray(ev.connector_types) && ev.connector_types.length) info.push(ev.connector_types.join('/'));
      if (ev.plugs) info.push(ev.plugs + ' ladepunkter');
      if (ev.stale) info.push('gemte data: seneste hentning fejlede');
      if (ev.source_updated) info.push('hentet ' + new Date(ev.source_updated).toLocaleString('da-DK'));
      if (count > 1) info.push('+' + (count - 1) + (companyGroup ? ' andre ladevalg hos selskabet' : (!localPrice && !publicTariff ? ' andre ladesteder hos selskabet uden stationspris i udtrækket' : ' ladesteder hos samme selskab')));
      var age = this._fmtAge(ev.lu);
      return '<div class="trf-evrow" style="grid-template-columns: minmax(70px,130px) minmax(60px,1fr) 52px" title="' + esc(title) + '">' +
        '<div class="trf-logo"><a class="trf-navlink" data-waze="' + esc(ev.brand) + '" href="' + esc(link) + '" title="' + esc(title) + '">' + logoContent + '</a></div>' +
        '<div class="trf-pcol">' + '<span class="trf-price"><b>' + price + '</b></span>' + '</div>' +
        '<span class="trf-km' + (km !== null && km > 15 ? ' trf-far' : '') + '">' + (km !== null ? this._fmtKm(km) + ' km' : '–') +
        (age ? '<span class="trf-age">' + esc(age) + '</span>' : '') + '</span>' +
        this._evTariffsHtml(tariffs) + '<div class="trf-station"><span class="trf-subtxt">' + info.filter(Boolean).map(esc).join(' · ') + '</span>' +
        (inPopup ? '' : this._evPopupButton(ev.brand)) +
        this._evBenefits(ev, 'button') + '</div>' + this._evBenefits(ev, 'box') + '</div>';
    }

    _evPopupButton(brand) {
      return cfgGet(this._config, "vis_ladeoversigt", true) ? '<button type="button" class="trf-fordel-btn trf-ev-link" data-open-ev="' + esc(brand) + '">Ladesteder</button>' : '';
    }

    _closeEvPopup() {
      var brand = this._openEvBrand;
      this._openEvBrand = null;
      this._render();
      if (this.querySelectorAll) {
        var buttons = this.querySelectorAll("[data-open-ev]");
        for (var i = 0; i < buttons.length; i++) {
          if (buttons[i].getAttribute("data-open-ev") === brand) { buttons[i].focus(); break; }
        }
      }
    }

    _evPopupHtml(loc) {
      if (!this._openEvBrand || !cfgGet(this._config, "vis_ladeoversigt", true) || !this._effVis().el) return '';
      var self = this, brand = this._openEvBrand, kind = this._evPopupKind || 'all';
      var rows = this._evEntries().filter(function (ev) {
        return ev.brand === brand && self._evHasLocation(ev) && (kind === 'all' || ev.kind === kind);
      }).map(function (ev) {
        var coords = self._evCoords(ev);
        return { ev: ev, km: loc && coords ? self._haversineKm(loc.lat, loc.lon, coords.lat, coords.lon) : null };
      });
      rows.sort(function (a, b) { return (a.km === null ? Infinity : a.km) - (b.km === null ? Infinity : b.km); });
      var limit = this._evPopupLimit || 10;
      var html = '<dialog class="trf-ev-dialog" aria-label="' + esc(brand) + ' ladesteder">' +
        '<div class="trf-ev-dialog-head"><h3>' + esc(brand) + ' · Ladesteder</h3><button type="button" class="trf-ev-button" data-close-ev aria-label="Luk ladeoversigt" autofocus>Luk ×</button></div>' +
        '<div class="trf-em">' + (loc ? 'Nærmeste først · afstand i luftlinje fra din valgte position.' : 'Position mangler; afstand kan ikke beregnes.') + ' Tryk på et logo for navigation.</div>' +
        '<div class="trf-ev-filters">';
      var choices = ['all'];
      ['AC', 'DC', 'Normal', 'Hurtig', 'Lyn'].forEach(function (k) {
        if (self._evEntries().some(function (ev) { return ev.brand === brand && self._evHasLocation(ev) && ev.kind === k; })) choices.push(k);
      });
      choices.forEach(function (k) {
        html += '<button type="button" class="trf-ev-button' + (kind === k ? ' trf-on' : '') + '" data-ev-kind="' + k + '" aria-pressed="' + (kind === k) + '">' + (k === 'all' ? 'Alle' : k) + '</button>';
      });
      html += '</div><div class="trf-ev-list">';
      if (rows.length) {
        var popupRows = rows.slice(0, limit).map(function (row) { return self._evRow(row.ev, loc, 1, true); });
        html += popupRows.join("");
      } else {
        html += '<div class="trf-em">Ingen konkrete ladesteder i udtrækket for dette selskab og filter.</div>';
      }
      html += '</div><div class="trf-ev-actions">';
      if (rows.length > limit) html += '<button type="button" class="trf-ev-button" data-more-ev>Vis 10 mere</button>';
      if (limit > 10) html += '<button type="button" class="trf-ev-button" data-fewer-ev>Vis færre</button>';
      html += '<span class="trf-em">Viser ' + Math.min(limit, rows.length) + ' af ' + rows.length + ' ladevalg. Et sted kan have både AC og DC.</span></div></dialog>';
      return html;
    }

    _evTariffsHtml(items) {
      if (!items || !items.length) return '';
      var self = this, seen = new Set();
      var lines = items.filter(function (ev) {
        var key = ev.name + '|' + ev.kwh;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      }).map(function (ev) {
        return '<span class="trf-tariff-line">' + esc(ev.name) + ' <b>' + esc(self._fmt(ev.kwh)) + '</b> kr/kWh' + (ev.stale ? ' · gemt takst (hentning fejlede)' : '') + '</span>';
      }).join('');
      var detail = items.find(function (ev) { return ev.tariff_note; });
      var dated = items.find(function (ev) { return ev.lu; });
      var note = 'Generelle selskabstakster; ikke en bekræftet pris på det enkelte ladested.';
      if (detail) note += ' ' + detail.tariff_note;
      if (dated) {
        var parsedDate = new Date(dated.lu);
        note += ' Pris opdateret ' + (isNaN(parsedDate.getTime()) ? dated.lu : parsedDate.toLocaleDateString('da-DK')) + '.';
      }
      return '<div class="trf-tariffs">' + lines + '<span class="trf-tariff-note">' + esc(note) + '</span></div>';
    }

    _fuelDataSummary() {
      if (!this._effVis().benzin && !this._effVis().diesel) return '';
      var data = this._data, sources = data && data.fuel_sources;
      if (!sources || !Object.keys(sources).length) {
        return data && Array.isArray(data.stations) && data.stations.length
          ? '<div class="trf-em">Brændstofkildernes datastatus vises efter næste hentning.</div>' : '';
      }
      var names = {
        "api.circlek.com": "Circle K og Ingo", "f24.dk": "F24 og Q8", "goon.nu": "Go’on",
        "unoxmobility.dk": "Uno-X", "shellservice.dk": "Shell", "ok.dk": "OK",
        "mobility-prices.ok.dk": "OK brændstofpriser", "oil-fuel-api": "OIL brændstofpriser",
        "oil-tankstationer.dk": "OIL listepriser"
      };
      var keys = Object.keys(sources).sort(function (a, b) { return (names[a] || a).localeCompare(names[b] || b, "da"); });
      var failures = keys.filter(function (key) { return sources[key] && sources[key].status !== "ok"; }).length;
      var summary = failures ? failures + " brændstofkilder kræver opmærksomhed" : keys.length + " brændstofkilder · seneste status";
      var html = '<section class="trf-info-section"><div class="trf-info-count">' + esc(summary) + '</div><div class="trf-info-table-wrap"><table><thead><tr><th>Kilde</th><th>Stationer</th><th>Priser</th><th>Koordinater mangler</th><th>Status · tidspunkt</th></tr></thead><tbody>';
      keys.forEach(function (key) {
        var item = sources[key] || {}, state = item.status === "ok" ? "OK" :
          (item.status === "stale" ? "Gemte data · nyt forsøg fejlede" : "Fejl");
        var stamp = item.status === "ok" ? item.last_success : item.last_attempt;
        var detail = item.error ? ' title="' + esc(item.error) + '"' : '';
        html += '<tr><td>' + esc(names[key] || key) + '</td><td>' + (Number(item.records) || 0) +
          '</td><td>' + (Number(item.priced) || 0) + '</td><td>' + (Number(item.missing_coordinates) || 0) +
          '</td><td' + detail + '>' + esc(state + " · " + this._fmtStamp(stamp)) + '</td></tr>';
      }, this);
      html += '</tbody></table></div>';
      html += '</section>';
      return html;
    }

    _coordinateSummary() {
      var data = this._data;
      if (!data) return '';
      var html = '<section class="trf-info-section">';
      var pending = Number(data.geocode_pending) || 0, geo = data.geocoding;
      if (!geo) {
        html += pending ? '<div>' + pending + ' stationer mangler koordinater. Detaljeret køstatus bliver tilgængelig efter næste hentning.</div>' : '<div>Ingen registrerede stationer mangler koordinater.</div>';
      } else {
        html += '<div><b>Koordinatopslag:</b> ' + (Number(geo.queued) || 0) + ' unikke adresser klar til opslag · ' +
          (Number(geo.not_found) || 0) + ' forsøgt uden resultat · ' + (Number(geo.missing_address) || 0) + ' stationer uden adresse til opslag.</div>';
        var run = geo.run;
        if (run && run.checked_at) {
          html += '<div>Seneste kontrol: ' + esc(this._fmtStamp(run.checked_at)) + '. ' + (Number(run.attempted) || 0) + ' opslag forsøgt: ' +
            (Number(run.found) || 0) + ' fundet, ' + (Number(run.not_found) || 0) + ' uden resultat, ' + (Number(run.failed) || 0) + ' fejl.</div>';
          if (run.error) html += '<div>Opslagene blev stoppet af en fejl: ' + esc(run.error) + '. Se fejloversigten.</div>';
        } else html += '<div>Koordinatopslag blev ikke kørt i denne hentning (fx hvis alle koordinater allerede fandtes).</div>';
        if (geo.queued) html += '<div>Der behandles højst ' + (Number(geo.limit) || 30) + ' adresser ved næste hentning af relevante drivmidler, fordelt mellem selskaberne. En slutdato kan ikke garanteres.</div>';
        if (geo.not_found) html += '<div>Adresser uden søgeresultat prøves tidligst igen efter syv dage. Tidspunktet nedenfor er første mulige genforsøg, ikke en garanti for et resultat.</div>';
        var missing = Array.isArray(geo.pending_addresses) ? geo.pending_addresses : [];
        if (missing.length) html += '<div class="trf-info-table-wrap" style="max-height:240px;overflow:auto"><table><thead><tr><th>Station / adresse</th><th>Årsag</th><th>Tidligste genforsøg</th></tr></thead><tbody>' + missing.map(function (item) {
          return '<tr><td>' + esc([item.brand, item.name, item.address].filter(Boolean).join(' · ')) + '</td><td>' +
            (item.status === 'not_found' ? 'Søgt uden resultat' : 'Klar til opslag') + '</td><td>' +
            (item.retry_after ? esc(this._fmtStamp(item.retry_after)) : 'Næste hentning af relevante drivmidler') + '</td></tr>';
        }, this).join('') + '</tbody></table></div>';
      }
      html += '</section>';
      return html;
    }

    _evDataSummary(entries) {
      var self = this, providers = new Map();
      entries.forEach(function (ev) {
        var p = providers.get(ev.brand);
        if (!p) { p = { sites: new Set(), priced: new Set(), stale: new Set(), missingCoords: 0, tariffs: false }; providers.set(ev.brand, p); }
        if (!self._evHasLocation(ev)) {
          if (typeof ev.kwh === 'number' && isFinite(ev.kwh) && ev.kwh > 0) p.tariffs = true;
          return;
        }
        var coords = self._evCoords(ev);
        if (!coords) p.missingCoords++;
        var key = ev.location_id || (coords ? coords.lat + ',' + coords.lon : String(ev.address).toLowerCase().trim());
        p.sites.add(key);
        if (!ev.app_only && typeof ev.kwh === 'number' && isFinite(ev.kwh) && ev.kwh > 0) p.priced.add(key);
        if (ev.stale) p.stale.add(key);
      });
      var sites = 0, priced = 0, count = 0;
      providers.forEach(function (p) { sites += p.sites.size; priced += p.priced.size; if (p.sites.size || p.tariffs) count++; });
      var html = '<section class="trf-info-section"><div class="trf-info-count">Data fra ' + count + ' selskaber · ' + sites + ' ladesteder · ' + priced + ' med lokal elpris</div><div class="trf-info-table-wrap"><table><thead><tr><th>Selskab</th><th>Steder</th><th>Med lokal pris</th><th>Koordinater mangler</th><th>Datastatus · seneste kontrol</th></tr></thead><tbody>';
      var sourceKeys = { "Clever": "clever", "E.ON": "eon", "IONITY": "ionity", "OK": "ok", "OIL": "oil", "Shell": "shell", "Circle K": "circle_k" };
      providers.forEach(function (p, brand) {
        if (!p.sites.size && !p.tariffs) return;
        var source = self._data && self._data.ev_sources && self._data.ev_sources[sourceKeys[brand]];
        var state = source && source.status;
        var status = state === 'stale' ? 'Seneste forsøg fejlede · gemte data' :
          (state === 'error' ? 'Seneste hentning fejlede' : (p.stale.size ? p.stale.size + ' steder med gemte data' : 'Indlæste data'));
        if (p.tariffs) status += ' · generelle takster';
        var stamp = source && (state === 'ok' ? source.last_success : source.last_attempt);
        if (!source) status += ' · status afventer næste hentning';
        html += '<tr><td>' + esc(brand) + '</td><td>' + p.sites.size + '</td><td>' + p.priced.size + '</td><td>' + p.missingCoords +
          '</td><td title="' + esc(source && source.error || '') + '">' + esc(status + (stamp ? ' · ' + self._fmtStamp(stamp) : '')) + '</td></tr>';
      });
      Object.keys(sourceKeys).forEach(function (brand) {
        var key = sourceKeys[brand], p = providers.get(brand);
        if (!showBrand(self._config, key) || (p && (p.sites.size || p.tariffs))) return;
        var source = self._data && self._data.ev_sources && self._data.ev_sources[key];
        if (!source) return;
        var state = source.status === 'ok' ? 'OK · ingen steder i udtrækket' :
          (source.status === 'stale' ? 'Seneste forsøg fejlede · ingen gemte steder' : 'Seneste hentning fejlede');
        var stamp = source.status === 'ok' ? source.last_success : source.last_attempt;
        html += '<tr><td>' + esc(brand) + '</td><td>0</td><td>0</td><td>–</td><td title="' + esc(source.error || '') + '">' +
          esc(state + (stamp ? ' · ' + self._fmtStamp(stamp) : '')) + '</td></tr>';
      });
      html += '</tbody></table></div><div>Kun valgte selskaber. AC/DC på samme sted tælles én gang pr. selskab. Generelle takster tælles ikke som lokale priser.</div></section>';
      return html;
    }

    _errorGroups() {
      var data = this._data || {}, groups = [];
      if (this._dataApiError) groups.push({ source: "Home Assistant data-API", message: this._dataApiError });
      if (data.last_error) groups.push({ source: "Hentning", message: data.last_error });
      (Array.isArray(data.errors) ? data.errors : []).forEach(function (error) {
        if (!error || typeof error !== "object") { groups.push({ source: "Datakilde", message: String(error) }); return; }
        var source = error.source || Object.keys(error).filter(function (key) { return key !== "stale_reused"; })[0] || "Datakilde";
        groups.push({ source: source, message: error.error || error[source] || "Hentningen fejlede" });
      });
      (Array.isArray(data.benefit_errors) ? data.benefit_errors : []).forEach(function (error) {
        groups.push({ source: "Fordele · " + (error.provider || "Udbyder"), message: error.error || "Hentningen fejlede" });
      });
      return groups;
    }

    _issueUrl() {
      // Allow only error categories and HTTP codes into the public draft.
      // Raw exceptions may contain local paths, URLs, addresses or credentials.
      var lines = this._errorGroups().slice(0, 20).map(function (error) {
        var source = String(error.source || "");
        var known = ["Home Assistant data-API", "Hentning", "Datakilde", "ck_api", "stations_cache", "f24q8", "q8_el", "circlek_el", "eon_el", "ionity_el", "unox", "goon", "shell_pdf", "shell", "ok_fuel_api", "oil_fuel_api", "ok", "ok_el", "oil", "geocode", "clever.dk", "eon.dk", "ionity.eu", "shell.dk", "unox.dk", "ok.dk", "oil-tankstationer.dk", "circlek.dk", "stale_reused"];
        BRANDS.forEach(function (brand) { known.push("Fordele · " + brand.brand); });
        known.push("Fordele · IONITY");
        if (known.indexOf(source) < 0) source = "Datakilde";
        var message = String(error.message || "");
        var http = message.match(/(?:HTTP(?: Error)?|status(?: code)?)[ :]*(\d{3})/i);
        var category = http ? "HTTP " + http[1] : /json|delimiter/i.test(message) ? "Ugyldigt JSON-svar" :
          /timeout|timed out/i.test(message) ? "Timeout" : "Hentningen fejlede (tilføj evt. renset fejltekst)";
        return "- " + source + ": " + category;
      });
      var version = String(this._data && this._data.version || "ukendt").replace(/[^a-zA-Z0-9.+_-]/g, "").slice(0, 32);
      var body = "Tiny Refuel: " + version + "\n\nFejl:\n" + lines.join("\n") +
        "\n\nHvad skete der?\n[Beskriv her]\n\nForventet resultat:\n[Beskriv her]\n\nRapporten indeholder kun fejlkategorier og HTTP-koder. Tilføj gerne relevant logtekst efter at have fjernet personlige oplysninger.";
      return "https://github.com/Salvationdk/tiny-refuel/issues/new?" + new URLSearchParams({ title: "Fejl ved hentning i Tiny Refuel", body: body }).toString();
    }

    _dataErrorsHtml() {
      var groups = this._errorGroups(), html = "";
      if (this._data && this._data.refreshing) html += '<div class="trf-em">Tiny Refuel henter nye data…</div>';
      var hasHttp500 = groups.some(function (error) { return /(?:HTTP(?: Error)?|status(?: code)?)[ :]*500\b/i.test(String(error.message || "")); });
      var hasJsonError = groups.some(function (error) { return /json|delimiter/i.test(String(error.message || "")); });
      var explanation = (hasHttp500 ? '<p>HTTP 500 betyder, at serveren ikke kunne behandle forespørgslen.</p>' : '') +
        (hasJsonError ? '<p>Datakilden leverede et ufuldstændigt eller ugyldigt JSON-svar. Det kan skyldes et afbrudt svar eller en fejl hos datakilden.</p>' : '') +
        '<p>Datakilden står ved fejlen; gemte data kan stadig vises.</p>';
      if (groups.length) html += '<details class="trf-data-counts" data-card-panel="errors"><summary>' + groups.length + ' fejl i seneste hentning</summary>' +
        groups.map(function (error) { return '<div>' + esc(error.source) + ': ' + esc(error.message) + '</div>'; }).join('') +
        explanation +
        '<a class="trf-ev-button" href="' + esc(this._issueUrl()) + '" target="_blank" rel="noopener noreferrer">Rapportér på GitHub</a>' +
        '<div class="trf-em">Åbner et udkast med fejlkategorier og HTTP-koder. Gennemse og indsend selv; GitHub kan bede dig logge ind.</div></details>';
      return html;
    }

    _evHtml(loc) {
      var self = this, entries = this._evEntries();
      var html = '<div class="trf-brand">El (kr/kWh)</div>';
      if (this._effVis().andet) {
        var knownPrices = entries.filter(function (ev) { return typeof ev.kwh === 'number' && isFinite(ev.kwh) && ev.kwh > 0; });
        if (knownPrices.length) {
          var lowest = Math.min.apply(null, knownPrices.map(function (ev) { return ev.kwh; }));
          var names = Array.from(new Set(knownPrices.filter(function (ev) { return ev.kwh === lowest; }).map(function (ev) { return ev.brand; })));
          html += '<div class="trf-best"><span title="Kun oplyste priser. Generelle takster og fra-priser er ikke bekræftede stationspriser.">Laveste oplyste elpris: <b>' + this._fmt(lowest) + ' kr/kWh</b> · ' + esc(names.join(', ')) + '</span></div>';
        }
      }

      var stations = entries.filter(function (ev) { return self._evHasLocation(ev); }).map(function (ev) {
        var coords = self._evCoords(ev);
        return { ev: ev, km: loc && coords ? self._haversineKm(loc.lat, loc.lon, coords.lat, coords.lon) : null };
      });
      stations.sort(function (a, b) { return (a.km === null ? Infinity : a.km) - (b.km === null ? Infinity : b.km); });
      var groups = new Map();
      for (var i = 0; i < stations.length; i++) {
        var item = stations[i], ev = item.ev;
        var companyGroup = self._evBrandKey(ev.brand) === 'q8';
        var key = companyGroup ? ev.brand : ev.brand + '|' + (ev.kind || '') + '|' + (ev.app_only ? 'app' : ev.kwh);
        if (!groups.has(key)) groups.set(key, { ev: ev, count: 0, companyGroup: companyGroup });
        groups.get(key).count++;
      }
      var tariffs = new Map();
      entries.forEach(function (ev) {
        if (!self._evHasLocation(ev) && typeof ev.kwh === 'number' && isFinite(ev.kwh) && ev.kwh > 0) {
          if (!tariffs.has(ev.brand)) tariffs.set(ev.brand, []);
          tariffs.get(ev.brand).push(ev);
        }
      });
      var renderedBrands = new Set();
      var evHtmlRows = [];
      groups.forEach(function (group) {
        var first = !renderedBrands.has(group.ev.brand);
        renderedBrands.add(group.ev.brand);
        evHtmlRows.push(self._evRow(group.ev, loc, group.count, false, first ? tariffs.get(group.ev.brand) : null, group.companyGroup));
      });
      tariffs.forEach(function (items, brand) {
        if (renderedBrands.has(brand)) return;
        var logo = self._brandImg(brand);
        evHtmlRows.push('<div class="trf-evrow" style="grid-template-columns: minmax(70px,130px) minmax(60px,1fr) 52px"><div class="trf-logo">' + (logo ? '<img src="/tiny_refuel/static/logos/' + esc(logo) + '" alt="' + esc(brand) + '">' : esc(brand)) + '</div>' +
          '<div class="trf-pcol"><span class="trf-tariff-note">Generelle takster</span></div><span class="trf-km">–</span>' +
          self._evTariffsHtml(items) + '<div class="trf-station">' + self._evPopupButton(brand) + self._evBenefits(items[0], 'button') + '</div>' + self._evBenefits(items[0], 'box') + '</div>');
      });
      var evVisible = this._stationRowLimit("ev", evHtmlRows.length);
      html += '<div class="trf-ev-grid">' + evHtmlRows.slice(0, evVisible).join("") + '</div>' + this._stationRowActions("ev", evVisible, evHtmlRows.length);
      if (!stations.length && !tariffs.size) html += '<div class="trf-em">Ingen ladesteder eller el-priser for de valgte selskaber.</div>';
      var absent = BRANDS.filter(function (b) {
        return b.electricOnly && showBrand(self._config, b.key) && !entries.some(function (ev) { return self._evBrandKey(ev.brand) === b.key; });
      }).map(function (b) { return b.brand; });
      if (absent.length) html += '<div class="trf-em">Ingen ladedata i udtrækket: ' + absent.map(esc).join(', ') + '.</div>';
      var sources = this._data && this._data.ev_sources;
      var expected = { clever: 'Clever', eon: 'E.ON', ionity: 'Ionity', ok: 'OK', oil: 'OIL', shell: 'Shell', circle_k: 'Circle K' };
      var missingSetup = [], failed = [];
      Object.keys(expected).forEach(function (key) {
        if (!showBrand(self._config, key)) return;
        var status = sources && sources[key];
        if (!status) missingSetup.push(expected[key]);
        else if (status.status === 'error' || status.status === 'stale') failed.push(expected[key]);
      });
      if (missingSetup.length && this._data && this._data.updated) html += '<div class="trf-em">De indlæste stationsdata mangler datakildestatus for ' + missingSetup.map(esc).join(', ') +
        '. Opdatér Tiny Refuel-integrationen, og vælg Hent alle data på integrationens enhed i Home Assistant.</div>';
      if (failed.length) html += '<div class="trf-em">Seneste hentning fejlede hos ' + failed.map(esc).join(', ') + '. Eventuelle gemte steder er ikke bekræftet ved denne hentning.</div>';
      return html;
    }

  }

  customElements.define("tiny-refuel-card", TinyRefuelCard);
  window.TinyRefuelCard = TinyRefuelCard;
  window.customCards = window.customCards || [];
  if (!window.customCards.some(function (card) { return card.type === "tiny-refuel-card"; })) {
    window.customCards.push({ type: "tiny-refuel-card", name: "Tiny Refuel", description: "Benzin, diesel og opladning", preview: true });
  }

  // ---------- Visual editor ----------

  function visForFuel(fuel) {
    if (fuel === "diesel") return { benzin: false, diesel: true, el: false, andet: true };
    if (fuel === "el") return { benzin: false, diesel: false, el: true, andet: true };
    if (fuel === "plug_in_hybrid") return { benzin: true, diesel: false, el: true, andet: true };
    if (fuel === "hybrid") return { benzin: true, diesel: false, el: false, andet: true };
    return { benzin: true, diesel: false, el: false, andet: true };
  }

  function yamlScalar(value) {
    if (typeof value === "string") return JSON.stringify(value);
    if (value === null) return "null";
    return String(value);
  }

  function yamlLines(value, depth) {
    var pad = new Array(depth + 1).join(" "), lines = [];
    if (Array.isArray(value)) {
      value.forEach(function (item) {
        if (item && typeof item === "object") {
          lines.push(pad + "-");
          lines = lines.concat(yamlLines(item, depth + 2));
        } else lines.push(pad + "- " + yamlScalar(item));
      });
    } else if (value && typeof value === "object") {
      Object.keys(value).forEach(function (key) {
        var item = value[key], name = JSON.stringify(key) + ":";
        if (item && typeof item === "object") {
          lines.push(pad + name);
          lines = lines.concat(yamlLines(item, depth + 2));
        } else lines.push(pad + name + " " + yamlScalar(item));
      });
    }
    return lines;
  }

  class TinyRefuelCardEditor extends HTMLElement {
    constructor() {
      super();
      vehicleLogoFailure(this);
      this._config = {};
      var self = this;
      this.addEventListener("input", function (ev) {
        var target = ev.target, key = target && target.dataset && target.dataset.key;
        var match = key && key.match(/^bil:(\d+):(mærke|model|variant)$/);
        if (!match) return;
        var index = Number(match[1]), car = (self._config.biler || [])[index] || {};
        if (match[2] === "mærke") {
          var makes = self.querySelector('[data-make-options="' + index + '"]');
          if (makes) makes.innerHTML = self._makeSuggestions(target.value).html;
          return;
        }
        if (match[2] === "variant") {
          var variants = self.querySelector('[data-variant-options="' + index + '"]');
          if (variants) variants.innerHTML = self._variantOptions(car.mærke, car.model, target.value, car.aargang);
          return;
        }
        var suggestions = self._modelSuggestions(car.mærke, target.value);
        var list = self.querySelector('[data-model-options="' + index + '"]');
        if (list) list.innerHTML = suggestions.html;
        var count = self.querySelector('[data-model-count="' + index + '"]');
        if (count) count.textContent = suggestions.message;
        // Only the option list changes. The live input, caret and config survive.
      });
      this.addEventListener("click", function (ev) {
        var copy = ev.target && ev.target.closest ? ev.target.closest("[data-yaml-copy]") : null;
        if (copy) {
          ev.preventDefault();
          var yaml = self.querySelector("[data-card-yaml]");
          if (yaml && navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(yaml.value).then(function () {
              copy.textContent = "Kopieret";
              setTimeout(function () { copy.textContent = "Kopiér YAML"; }, 1500);
            }).catch(function () { yaml.focus(); yaml.select(); });
          } else if (yaml) { yaml.focus(); yaml.select(); }
          return;
        }
        var carSummary = ev.target && ev.target.closest ? ev.target.closest("[data-car-toggle]") : null;
        if (carSummary) {
          var carCard = carSummary.parentElement;
          self._openCar = carCard && carCard.open ? null : parseInt(carSummary.getAttribute("data-car-toggle"), 10);
          return;
        }
        var t = ev.target && ev.target.closest ? ev.target.closest("[data-bil-add],[data-bil-del]") : null;
        if (!t) return;
        ev.preventDefault();
        var cfg = Object.assign({}, self._config);
        var biler = Array.isArray(cfg.biler) && cfg.biler.length
          ? cfg.biler.map(function (b) { return Object.assign({}, b); })
          : [];
        if (t.hasAttribute && t.hasAttribute("data-bil-add")) {
          self._openCar = biler.length;
          biler.push({});
        } else {
          var idx = parseInt(t.getAttribute("data-bil-del"), 10);
          if (isFinite(idx)) biler.splice(idx, 1);
          self._openCar = null;
        }
        if (!biler.length) delete cfg.biler;
        else cfg.biler = biler;
        self._config = cfg;
        self._render({ resetCars: true });
        self._updateYaml();
        self.dispatchEvent(new CustomEvent("config-changed", { detail: { config: cfg }, bubbles: true, composed: true }));
      });
      this.addEventListener("change", function (ev) {
        var t = ev.target;
        if (!t || !t.dataset || !t.dataset.key) return;
        var key = t.dataset.key;
        var cfg = Object.assign({}, self._config);
        if (key === "tank_liters") {
          var v = parseFloat(t.value);
          if (isFinite(v) && v > 0) cfg.tank_liters = v;
          else delete cfg.tank_liters;
        } else if (key.indexOf("bil:") === 0) {
          var parts = key.split(":");
          var bi = parseInt(parts[1], 10);
          var field = parts.slice(2).join(":");
          if (!isFinite(bi)) return;
          var biler = Array.isArray(cfg.biler) ? cfg.biler.map(function (b) { return Object.assign({}, b); }) : [];
          while (biler.length <= bi) biler.push({});
          var needRender = false;
          var previousCar = biler[bi];
          var previousLabel = [previousCar.mærke, previousCar.model].filter(Boolean).join(" ");
          var autoName = !previousCar.navn || /^(?:Bil|Køretøj) \d+$/.test(previousCar.navn) || catalogKey(previousCar.navn) === catalogKey(previousLabel);
          function clearSelection() {
            ["variant", "aargang", "tank_liters", "batteri_kwh", "brændstof", "vis"].forEach(function (key) { delete biler[bi][key]; });
          }
          if (field === "tank_liters" || field === "batteri_kwh") {
            var bv = parseFloat(t.value);
            if (isFinite(bv) && bv > 0) biler[bi][field] = bv;
            else delete biler[bi][field];
          } else if (field === "mærke") {
            var mk = String(t.value || "").trim();
            var foundMake = catalogIndex(self._katalog);
            var canonical = foundMake && foundMake.makes.get(catalogKey(mk));
            if (canonical) mk = canonical.mærke;
            if (catalogKey(mk) !== catalogKey(biler[bi].mærke)) {
              delete biler[bi].model;
              clearSelection();
              if (autoName) delete biler[bi].navn;
              needRender = true;
            }
            if (mk) biler[bi].mærke = mk;
            else delete biler[bi].mærke;
            t.value = mk;
          } else if (field === "model") {
            var md = String(t.value || "").trim();
            var entry = md ? self._katalogFind(biler[bi].mærke, md) : null;
            if (entry) md = entry.model;
            var oldEntry = self._katalogFind(biler[bi].mærke, biler[bi].model);
            var modelChanged = entry && oldEntry ? entry !== oldEntry : catalogKey(md) !== catalogKey(biler[bi].model);
            if (modelChanged) {
              clearSelection();
              if (autoName) delete biler[bi].navn;
              if (entry) {
                if (entry.tank_l != null) biler[bi].tank_liters = entry.tank_l;
                if (entry.batteri_kwh != null) biler[bi].batteri_kwh = entry.batteri_kwh;
                if (entry.brændstof) {
                  biler[bi].brændstof = entry.brændstof;
                  biler[bi].vis = visForFuel(entry.brændstof);
                }
              }
            }
            if (md) biler[bi].model = md;
            else delete biler[bi].model;
          } else if (field === "aargang") {
            var year = String(t.value || "").trim();
            if (year && !/^\d{4}$/.test(year)) { t.value = biler[bi].aargang || ""; return; }
            if (year !== String(biler[bi].aargang || "")) {
              var previousVariant = biler[bi].variant;
              var modelEntry = self._katalogFind(biler[bi].mærke, biler[bi].model);
              var choices = self._variantsForYear(modelEntry, year);
              // A year may choose a variant only when every variant has year data
              // and exactly one is eligible. Never infer this from a model-wide list.
              var completeYears = modelEntry && modelEntry.variants && modelEntry.variants.length && modelEntry.variants.every(function (v) { return Array.isArray(v.model_years) && v.model_years.length; });
              if (year && completeYears && choices.length === 1) biler[bi].variant = choices[0].name;
              else if (year && completeYears && !choices.some(function (v) { return catalogKey(v.name) === catalogKey(biler[bi].variant); })) delete biler[bi].variant;
              if (previousVariant !== biler[bi].variant) {
                ["tank_liters", "batteri_kwh", "brændstof", "vis"].forEach(function (key) { delete biler[bi][key]; });
              }
            }
            if (year) biler[bi].aargang = year;
            else delete biler[bi].aargang;
          } else if (field === "variant") {
            var variant = String(t.value || "").trim();
            if (variant !== (biler[bi].variant || "")) {
              // A model-wide default is not a verified specification for a new variant.
              delete biler[bi].brændstof;
              delete biler[bi].vis;
              delete biler[bi].tank_liters;
              delete biler[bi].batteri_kwh;
            }
            if (variant) biler[bi].variant = variant;
            else delete biler[bi].variant;
          } else if (field === "brændstof") {
            var fb = String(t.value || "");
            if (fb) {
              biler[bi].brændstof = fb;
              biler[bi].vis = visForFuel(fb);
            } else {
              delete biler[bi].brændstof;
            }
          } else if (field.indexOf("vis_") === 0) {
            var vk = field.slice(4);
            biler[bi].vis = Object.assign({}, biler[bi].vis);
            biler[bi].vis[vk] = !!t.checked;
          } else {
            var bs = String(t.value || "").trim();
            if (bs) biler[bi][field] = bs;
            else delete biler[bi][field];
          }
          cfg.biler = biler;
          self._config = cfg;
          if (needRender) self._render();
          else self._updateCarFields(bi);
          self._updateYaml();
          self.dispatchEvent(new CustomEvent("config-changed", { detail: { config: cfg }, bubbles: true, composed: true }));
          return;
        } else if (key === "antal_stationer") {
          var countValue = String(t.value == null ? "" : t.value).trim();
          var stationCount = Number(countValue);
          if (!countValue) delete cfg.antal_stationer;
          else if (Number.isInteger(stationCount) && stationCount >= 0 && stationCount <= 50) cfg.antal_stationer = stationCount;
          else { t.value = cfg.antal_stationer === undefined ? "" : String(cfg.antal_stationer); return; }
        } else if (key === "scrape_entity" || key === "location_entity" || key === "notify_service" || key === "katalog_url" || key === "navigation") {
          var s = String(t.value || "").trim();
          if (s) cfg[key] = s;
          else delete cfg[key];
          if (key === "katalog_url") {
            self._config = cfg;
            self._loadKatalog();
            self._updateYaml();
            self.dispatchEvent(new CustomEvent("config-changed", { detail: { config: cfg }, bubbles: true, composed: true }));
            return;
          }
        } else if (key.indexOf("kæde:") === 0) {
          var bk = key.slice(5);
          cfg.kaeder = Object.assign({}, cfg.kaeder);
          cfg.kaeder[bk] = !!t.checked;
          var count = BRANDS.filter(function (brand) { return !(cfg.kaeder && cfg.kaeder[brand.key] === false); }).length;
          var countNode = self.querySelector("[data-provider-count]");
          if (countNode) countNode.textContent = count + " af " + BRANDS.length + " valgt";
        } else {
          cfg[key] = !!t.checked;
          if (key === "kompakt") {
            ["vis_bilvaelger", "vis_scrape_knap"].forEach(function (field) {
              var node = self.querySelector('[data-key="' + field + '"]');
              if (node && cfg[field] === undefined) node.checked = !cfg.kompakt;
            });
            var countInput = self.querySelector('[data-key="antal_stationer"]');
            if (countInput) countInput.placeholder = cfg.kompakt ? "3" : "Alle";
          }
        }
        self._config = cfg;
        self._updateYaml();
        self.dispatchEvent(new CustomEvent("config-changed", { detail: { config: cfg }, bubbles: true, composed: true }));
      });
    }

    setConfig(config) {
      var next = config || {};
      function signature(value) {
        return JSON.stringify(value, function (key, item) {
          if (!item || typeof item !== "object" || Array.isArray(item)) return item;
          var sorted = {};
          Object.keys(item).sort().forEach(function (k) { sorted[k] = item[k]; });
          return sorted;
        });
      }
      // Home Assistant echoes config-changed back to setConfig. Keep the live
      // form intact so a blur/change event cannot move the Save button.
      if (this._editorRendered && signature(next) === signature(this._config)) return;
      this._config = next;
      this._render();
    }

    set hass(hass) {
      this._hass = hass;
      vehicleLogoTheme(this, hass);
      if (!this._config) return;
      var keys = [];
      for (var ek in hass.states) {
        if (ek.indexOf("device_tracker.") === 0) keys.push(ek);
      }
      keys.sort();
      var sig = keys.join(",");
      if (sig !== this._lastTrackers) {
        this._lastTrackers = sig;
        this._render();
      }
    }

    _katalogUrl() {
      return vehicleCatalogUrl(this._config);
    }

    _loadKatalog() {
      loadVehicleCatalog(this);
    }

    _katalogBrands() {
      if (this._katalog && Array.isArray(this._katalog.brands)) return this._katalog.brands;
      return [];
    }

    _katalogModels(maerke) {
      var index = catalogIndex(this._katalog);
      var brand = index && index.makes.get(catalogKey(maerke));
      return brand && brand.modeller || [];
    }

    _makeSuggestions(query) {
      var words = catalogKey(query).split(/\s+/).filter(Boolean);
      var matches = this._katalogBrands().filter(function (brand) {
        var name = catalogKey([brand.mærke].concat(brand.source_names || []).join(" "));
        return words.every(function (word) { return name.indexOf(word) !== -1; });
      });
      return { total: matches.length, html: matches.slice(0, 60).map(function (brand) {
        return '<option value="' + esc(brand.mærke) + '"></option>';
      }).join("") };
    }

    _yearOptions(make, model) {
      var entry = this._katalogFind(make, model);
      return ((entry && entry.model_years) || []).filter(function (year) {
        return /^\d{4}$/.test(String(year));
      }).map(function (year) { return '<option value="' + esc(year) + '"></option>'; }).join("");
    }

    _modelSuggestions(make, query) {
      var normalize = function (value) { return String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/æ/g, "ae").replace(/ø/g, "o"); };
      var words = normalize(query).trim().split(/\s+/).filter(Boolean);
      var matches = this._katalogModels(make).filter(function (entry) {
        var name = normalize([entry.model].concat(entry.source_names || []).join(" "));
        return words.every(function (word) { return name.indexOf(word) !== -1; });
      });
      var visible = matches.slice(0, 60);
      return {
        html: visible.map(function (entry) {
          return '<option value="' + esc(entry.model) + '">' + esc(entry.model + " · " + (entry.brændstof || "vælg drivmiddel") +
            (entry.tank_l != null ? " · " + entry.tank_l + " L" : "")) + '</option>';
        }).join(""),
        total: matches.length,
        message: matches.length > visible.length ? "Viser " + visible.length + " af " + matches.length + " match — skriv mere for at indsnævre." :
          (matches.length ? matches.length + " modeller matcher. Du kan også skrive din egen model." : "Ingen katalogmatch. Du kan skrive din egen model."),
      };
    }

    _variantsForYear(entry, year) {
      return ((entry && entry.variants) || []).filter(function (variant) {
        return !year || !Array.isArray(variant.model_years) || !variant.model_years.length || variant.model_years.map(String).indexOf(String(year)) !== -1;
      });
    }

    _variantOptions(make, model, query, year) {
      var entry = this._katalogFind(make, model);
      return this._variantsForYear(entry, year).filter(function (variant) {
        return String(variant.name || "").toLowerCase().indexOf(String(query || "").toLowerCase()) !== -1;
      }).slice(0, 100).map(function (variant) {
        return '<option value="' + esc(variant.name) + '">' + esc((variant.fuel_types || []).join(" / ")) + '</option>';
      }).join("");
    }

    _variantYearNote(car) {
      var entry = this._katalogFind(car.mærke, car.model);
      var variants = entry && entry.variants || [];
      if (car.aargang && variants.length && variants.every(function (v) { return Array.isArray(v.model_years) && v.model_years.length; })) {
        var choices = this._variantsForYear(entry, car.aargang);
        return choices.length ? choices.length + ' varianter passer til modelåret. Kontrollér drivmiddel og kapacitet.' : 'Ingen varianter har bekræftet dette modelår. Kontrollér årstallet eller indtast varianten manuelt.';
      }
      if (!variants.length) return 'Årgang og variant er valgfrie manuelle oplysninger. Kataloget indeholder kapaciteter på modelniveau.';
      return 'Kataloget mangler en sikker kobling mellem årgang og variant. Vælg varianten manuelt; årstallet vælger ikke motor eller kapacitet.';
    }

    _katalogFind(maerke, model) {
      var index = catalogIndex(this._katalog);
      if (!index) return null;
      var makeKey = catalogKey(maerke);
      var sourceModels = this._katalogModels(maerke);
      var cached = index.models.get(makeKey);
      if (!cached || cached.source !== sourceModels || cached.length !== sourceModels.length) {
        var models = new Map();
        sourceModels.forEach(function (entry) {
          models.set(catalogKey(entry.model), entry);
          (entry.source_names || []).forEach(function (name) { models.set(catalogKey(name), entry); });
        });
        index.models.set(makeKey, { source: sourceModels, length: sourceModels.length, entries: models });
      }
      var entry = index.models.get(makeKey).entries.get(catalogKey(model)) || null;
      loadVehicleModelDetails(this, entry);
      return entry;
    }

    _bool(key, def) {
      if (this._config && this._config[key] !== undefined) return !!this._config[key];
      return def;
    }

    _refreshModelDetailFields(entry) {
      var self = this;
      (this._config.biler || []).forEach(function (car, index) {
        if (self._katalogFind(car.mærke, car.model) !== entry) return;
        var variants = self.querySelector('[data-variant-options="' + index + '"]');
        var input = self.querySelector('[data-key="bil:' + index + ':variant"]');
        if (variants) variants.innerHTML = self._variantOptions(car.mærke, car.model, input ? input.value : car.variant, car.aargang);
        var years = self.querySelector('[data-year-options="' + index + '"]');
        if (years) years.innerHTML = self._yearOptions(car.mærke, car.model);
        var note = self.querySelector('[data-model-note="' + index + '"]');
        if (note) note.textContent = vehicleModelNote(entry, car.variant);
        var yearNote = self.querySelector('[data-variant-year-note="' + index + '"]');
        if (yearNote) yearNote.textContent = self._variantYearNote(car);
      });
    }

    _updateCarFields(index) {
      var car = this._config.biler && this._config.biler[index];
      if (!car) return;
      var self = this;
      ["model", "variant", "aargang", "navn", "tank_liters", "batteri_kwh"].forEach(function (field) {
        var node = self.querySelector('[data-key="bil:' + index + ':' + field + '"]');
        if (node && node.value !== (car[field] == null ? "" : String(car[field]))) node.value = car[field] == null ? "" : String(car[field]);
      });
      this.querySelectorAll('[data-key="bil:' + index + ':brændstof"]').forEach(function (node) {
        node.checked = node.value === car.brændstof;
      });
      ["benzin", "diesel", "el", "andet"].forEach(function (fuel) {
        var node = self.querySelector('[data-key="bil:' + index + ':vis_' + fuel + '"]');
        if (node) node.checked = car.vis && car.vis[fuel] !== undefined ? !!car.vis[fuel] : self._bool("vis_" + fuel, fuel !== "diesel");
      });
      var title = this.querySelector('[data-car-card="' + index + '"] .trfe-car-title');
      if (title) title.textContent = car.navn || [car.mærke, car.model].filter(Boolean).join(" ") || "Køretøj " + (index + 1);
      var hint = this.querySelector('[data-car-card="' + index + '"] .trfe-summary-meta');
      if (hint) hint.textContent = { benzin: "Benzin", diesel: "Diesel", el: "El", hybrid: "Hybrid", plug_in_hybrid: "Plug-in-hybrid" }[car.brændstof] || car.brændstof || "Vælg drivmiddel";
      var modelNote = this.querySelector('[data-model-note="' + index + '"]');
      var selectedModel = this._katalogFind(car.mærke, car.model);
      if (modelNote) modelNote.textContent = vehicleModelNote(selectedModel, car.variant);
      var yearNote = this.querySelector('[data-variant-year-note="' + index + '"]');
      if (yearNote) yearNote.textContent = this._variantYearNote(car);
      var variantOptions = this.querySelector('[data-variant-options="' + index + '"]');
      if (variantOptions) variantOptions.innerHTML = this._variantOptions(car.mærke, car.model, "", car.aargang);
      var years = this.querySelector('[data-year-options="' + index + '"]');
      if (years) years.innerHTML = this._yearOptions(car.mærke, car.model);
      var logo = this.querySelector('[data-model-logo="' + index + '"]');
      if (logo) logo.innerHTML = vehicleLogoHtml(this._katalog, car, "trfe-model-logo", true);
    }

    _updateYaml() {
      var textarea = this.querySelector && this.querySelector("[data-card-yaml]");
      if (!textarea) return;
      var config = Object.assign({}, this._config || {}, { type: "custom:tiny-refuel-card" });
      textarea.value = yamlLines(config, 0).join("\n");
    }

    _render(options) {
      options = options || {};
      var detailsState = {};
      this.querySelectorAll("details[data-editor-section], details[data-car-card]").forEach(function (node) {
        var section = node.getAttribute("data-editor-section");
        if (section) detailsState["section:" + section] = node.open;
        else if (!options.resetCars) detailsState["car:" + node.getAttribute("data-car-card")] = node.open;
      });
      var root = this.getRootNode ? this.getRootNode() : this.ownerDocument;
      var active = root && root.activeElement;
      var focus = active && this.contains && this.contains(active) && active.dataset && active.dataset.key ? {
        key: active.dataset.key, value: active.value,
        start: active.selectionStart, end: active.selectionEnd
      } : null;
      var c = this._config || {};
      function cb(key, label, checked, tooltip, icon) {
        var tip = tooltip ? ' title="' + esc(tooltip) + '" aria-label="' + esc(label + ". " + tooltip) + '"' : "";
        var logo = icon ? '<img class="trfe-brand-logo" src="/tiny_refuel/static/logos/' + esc(icon) + '" alt="" loading="lazy">' : "";
        return '<label' + tip + '><input type="checkbox" data-key="' + key + '"' +
          (checked ? " checked" : "") + ">" + logo + "<span>" + esc(label) + "</span></label>";
      }
      var html = '<div class="trfe"><style>' + ECSS + "</style>";
      html += '<h4>Visning <span class="trfe-tip" tabindex="0" title="Vælg hvilke energityper og oplysninger kortet skal vise." aria-label="Hjælp: Vælg hvilke energityper og oplysninger kortet skal vise.">i</span></h4>';
      html += cb("kompakt", "Kompakt kort", this._bool("kompakt", false), "Mindre afstande, færre oversigter og som standard tre rækker pr. prisliste. Køretøjsvælgeren skjules som standard ved ét køretøj. Hent data-knappen skjules som standard i kompakt visning.");
      html += cb("vis_bilvaelger", "Vis køretøjsvælger ved ét køretøj", this._bool("vis_bilvaelger", !c.kompakt), "Ved flere køretøjer vises køretøjsvælgeren altid.");
      html += '<div class="trfe-hint">Antal rækker pr. prisliste (0 = alle, tom = automatisk)</div><input type="number" data-key="antal_stationer" min="0" max="50" step="1" value="' + esc(c.antal_stationer === undefined ? '' : c.antal_stationer) + '" placeholder="' + (c.kompakt ? '3' : 'Alle') + '">';
      html += '<div class="trfe-hint">Brændstof viser en række pr. selskab; el viser grupper af ladevalg. Kompakt visning starter med tre rækker, normal visning med alle. Vis 10 mere åbner flere rækker.</div>';
      html += cb("vis_benzin", "Benzin (95/100-oktan)", this._bool("vis_benzin", true), "Vis benzinpriser fra de valgte selskaber.");
      html += cb("vis_diesel", "Diesel", this._bool("vis_diesel", false), "Vis dieselpriser fra de valgte selskaber.");
      html += cb("vis_el", "El (kr/kWh)", this._bool("vis_el", true), "Vis ladepriser og ladesteder.");
      html += cb("vis_ladeoversigt", "Ladesteder pr. selskab", this._bool("vis_ladeoversigt", true), "Vis en liste over ladesteder for hvert valgt ladeselskab.");
      html += cb("vis_andet", "Prisoversigt og beregninger", this._bool("vis_andet", true), "Vis blandt andet billigste pris og beregning af fuld tank eller opladning.");
      var activeBrands = BRANDS.filter(function (brand) { return !(c.kaeder && c.kaeder[brand.key] === false); }).length;
      html += '<details class="trfe-section" data-editor-section="providers"><summary><span>Stationer og udbydere</span><span class="trfe-summary-meta" data-provider-count>' +
        activeBrands + " af " + BRANDS.length + ' valgt</span></summary><div class="trfe-section-body">' +
        '<div class="trfe-hint">Vælg de selskaber, der skal vises på kortet. Som standard er alle valgt.</div><div class="trfe-brand-grid">';
      for (var i = 0; i < BRANDS.length; i++) {
        var b = BRANDS[i];
        var on = !(c.kaeder && c.kaeder[b.key] === false);
        html += cb("kæde:" + b.key, b.brand, on, "Vis eller skjul " + b.brand + " på dette kort.", b.img);
      }
      html += "</div></div></details>";
      html += cb("brug_faelles_koeretoejer", "Brug integrationens køretøjer, når kortet ikke har egne", c.brug_faelles_koeretoejer !== false, "Fælles køretøjer oprettes under Indstillinger → Enheder og tjenester → Tiny Refuel → Konfigurer. De bruges også af køretøjssensorerne.");
      html += "<h4>Køretøjer <span class=\"trfe-tip\" tabindex=\"0\" title=\"Køretøjer styrer valgt drivmiddel, tank- eller batteristørrelse og eventuel position.\" aria-label=\"Hjælp: Køretøjer styrer valgt drivmiddel, tank- eller batteristørrelse og eventuel position.\">i</span></h4>";
      this._loadKatalog();
      var biler = Array.isArray(c.biler) && c.biler.length ? c.biler : [];
      var trackers = [];
      if (this._hass && this._hass.states) {
        for (var ek in this._hass.states) {
          if (ek.indexOf("device_tracker.") === 0) trackers.push(ek);
        }
        trackers.sort();
      }
      var dl = '<datalist id="trf-trackers">';
      for (var ti = 0; ti < trackers.length; ti++) {
        dl += '<option value="' + esc(trackers[ti]) + '">';
      }
      dl += "</datalist>";
      var katBrands = this._katalogBrands();
      var gB = this._bool("vis_benzin", true), gD = this._bool("vis_diesel", false),
          gE = this._bool("vis_el", true), gA = this._bool("vis_andet", true);
      var fuels = [["benzin", "Benzin"], ["diesel", "Diesel"], ["el", "El"], ["hybrid", "Hybrid (uden stik)"], ["plug_in_hybrid", "Plug-in-hybrid"]];
      if (!biler.length) {
        html += '<div class="trfe-empty-car"><strong>Intet køretøj tilføjet endnu</strong>' +
          'Kortet viser de energityper, du har slået til ovenfor. Uden et køretøj filtreres priserne ikke efter drivmiddel, og manuel hentning tager alle typer. ' +
          'Fuld tank kræver en angivet tankstørrelse eller en gyldig tanksensor.</div>';
      }
      for (var bi2 = 0; bi2 < biler.length; bi2++) {
        var bb = biler[bi2] || {};
        var carTitle = bb.navn || ((bb.mærke || bb.model) ? [bb.mærke, bb.model].filter(Boolean).join(" ") : ("Køretøj " + (bi2 + 1)));
        var carHint = bb.brændstof ? ({ benzin: "Benzin", diesel: "Diesel", el: "El", hybrid: "Hybrid", plug_in_hybrid: "Plug-in-hybrid" }[bb.brændstof] || bb.brændstof) : "Vælg drivmiddel";
        var carLogoHtml = vehicleMakeHtml(this._katalog, bb, "trfe-car-logo") +
          '<span data-model-logo="' + bi2 + '">' + vehicleLogoHtml(this._katalog, bb, "trfe-model-logo", true) + '</span>';
        html += '<details class="trfe-car" data-car-card="' + bi2 + '"' + (this._openCar === bi2 ? " open" : "") + '><summary data-car-toggle="' + bi2 + '">' + carLogoHtml + '<span class="trfe-car-title">' +
          esc(carTitle) + '</span><span class="trfe-summary-meta">' + esc(carHint) + '</span></summary><div class="trfe-car-fields">';
        html += '<div class="trfe-hint">Køretøjstype (valgfrit, vælges manuelt)</div><select data-key="bil:' + bi2 + ':koeretoejstype">';
        [["", "Ikke valgt"], ["personbil", "Personbil"], ["varebil", "Varevogn"], ["lastbil", "Lastbil"], ["bus", "Bus"], ["motorcykel", "Motorcykel"], ["knallert", "Knallert"], ["traktor", "Traktor"], ["andet", "Andet motorkøretøj"]].forEach(function (type) {
          html += '<option value="' + type[0] + '"' + ((bb.koeretoejstype || "") === type[0] ? " selected" : "") + '>' + type[1] + '</option>';
        });
        html += '</select><div class="trfe-hint">Mærke (søg — eller skriv dit eget)</div>' +
          '<input type="text" data-key="bil:' + bi2 + ':mærke" list="trf-makes-' + bi2 + '" value="' + esc(bb.mærke || "") + '" placeholder="Skriv et mærke">' +
          '<datalist id="trf-makes-' + bi2 + '" data-make-options="' + bi2 + '">' + this._makeSuggestions(bb.mærke).html + '</datalist>';
        var katModels = bb.mærke ? this._katalogModels(bb.mærke) : [];
        var dlmId = "trf-models-" + bi2;
        var suggestions = this._modelSuggestions(bb.mærke, bb.model);
        var dlm = '<datalist id="' + dlmId + '" data-model-options="' + bi2 + '">' + suggestions.html + '</datalist>';
        html += '<div class="trfe-hint">Model (søg i fabrikantens modeller — eller skriv selv)</div>' +
          '<input type="text" list="' + dlmId + '" data-key="bil:' + bi2 + ':model" value="' +
          esc(bb.model || "") + '" placeholder="fx up!" ' + (bb.mærke ? "" : 'disabled title="Vælg mærke først"') + ">" + dlm;
        html += '<div class="trfe-hint" data-model-count="' + bi2 + '">' + esc(suggestions.message) + '</div>';
        html += '<details data-editor-section="vehicle-extra-' + bi2 + '"' + (bb.variant || bb.aargang ? ' open' : '') + '><summary>Årgang og variant (valgfrit)</summary><div class="trfe-hint">Variant</div>' +
          '<input type="text" data-key="bil:' + bi2 + ':variant" list="trf-variants-' + bi2 + '" value="' + esc(bb.variant || '') + '" placeholder="fx 1.6 TDI">' +
          '<datalist id="trf-variants-' + bi2 + '" data-variant-options="' + bi2 + '">' + this._variantOptions(bb.mærke, bb.model, "", bb.aargang) + '</datalist>';
        html += '<div class="trfe-hint">Modelår (valgfrit — kontrollér din variant)</div>' +
          '<input type="text" inputmode="numeric" data-key="bil:' + bi2 + ':aargang" list="trf-years-' + bi2 + '" value="' + esc(bb.aargang || '') + '" placeholder="fx 2020">' +
          '<datalist id="trf-years-' + bi2 + '" data-year-options="' + bi2 + '">' + this._yearOptions(bb.mærke, bb.model) + '</datalist>' +
          '<div class="trfe-hint" data-variant-year-note="' + bi2 + '">' + esc(this._variantYearNote(bb)) + '</div></details>';
        var selectedModel = this._katalogFind(bb.mærke, bb.model);
        html += '<div class="trfe-hint" data-model-note="' + bi2 + '">' +
          esc(vehicleModelNote(selectedModel, bb.variant)) + '</div>';
        var bfuel = bb.brændstof || "";
        html += '<div class="trfe-hint">Drivmiddel (vælger hvilke priser der vises)</div><div class="trfe-row">';
        for (var fi = 0; fi < fuels.length; fi++) {
          html += '<label><input type="radio" name="trf-fuel-' + bi2 + '" data-key="bil:' + bi2 + ':brændstof" value="' +
            fuels[fi][0] + '"' + (bfuel === fuels[fi][0] ? " checked" : "") + "><span>" + fuels[fi][1] + "</span></label>";
        }
        html += "</div>";
        html += '<div class="trfe-hint">Navn</div><input type="text" data-key="bil:' + bi2 + ':navn" value="' +
          esc(bb.navn || "") + '" placeholder="Køretøj 1">';
        html += '<div class="trfe-hint">Tank (L — fra katalog, ret ved behov)</div><input type="number" data-key="bil:' + bi2 +
          ':tank_liters" min="0.01" step="any" value="' +
          esc(bb.tank_liters !== undefined && bb.tank_liters !== null ? bb.tank_liters : "") + '" placeholder="Auto">';
        html += '<div class="trfe-hint">Batteri (kWh — fra katalog, ret ved behov)</div><input type="number" data-key="bil:' + bi2 +
          ':batteri_kwh" min="0.01" step="any" value="' +
          esc(bb.batteri_kwh !== undefined && bb.batteri_kwh !== null ? bb.batteri_kwh : "") + '" placeholder="Auto">';
        html += '<div class="trfe-hint">Telefon (GPS-kilde)</div><input type="text" list="trf-trackers" data-key="bil:' +
          bi2 + ':location_entity" value="' + esc(bb.location_entity || "") +
          '" placeholder="device_tracker.din_telefon">';
        var sug = "";
        if (bb.location_entity && bb.location_entity.indexOf("device_tracker.") === 0 && !bb.notify_service) {
          sug = "notify.mobile_app_" + bb.location_entity.slice("device_tracker.".length);
        }
        html += '<div class="trfe-hint">Notifikation til ⟳-knap' + (sug ? " (forslag: " + esc(sug) + ")" : "") +
          '</div><input type="text" data-key="bil:' + bi2 + ':notify_service" value="' +
          esc(bb.notify_service || "") + '" placeholder="' + esc(sug || "notify.mobile_app_...") + '">';
        var cv = (bb.vis && typeof bb.vis === "object") ? bb.vis : {};
        function cbv(k, label, fb2) {
          var on = cv[k] !== undefined ? !!cv[k] : fb2;
          return '<label><input type="checkbox" data-key="bil:' + bi2 + ":vis_" + k + '"' +
            (on ? " checked" : "") + "><span>" + esc(label) + "</span></label>";
        }
        html += '<div class="trfe-hint">Vis for dette køretøj</div>';
        html += cbv("benzin", "Benzin", gB) + cbv("diesel", "Diesel", gD) +
          cbv("el", "El", gE) + cbv("andet", "Andet", gA);
        html += '<div class="trfe-hint"><a href="#" data-bil-del="' + bi2 + '">Fjern køretøjet</a></div>';
        html += "</div></details>";
      }
      html += '<div class="trfe-hint"><a href="#" data-bil-add>' + (biler.length ? "Tilføj endnu et køretøj" : "＋ Tilføj køretøj") + '</a> · tankstørrelser er vejledende — kontroller mod instruktionsbogen</div>' + dl;
      html += "<h4>Køretøjskatalog (mærker/modeller)</h4>";
      if (this._katalogFailed) html += '<div class="trfe-hint" role="alert">Kataloget kunne ikke indlæses. Kontrollér URL og katalogformat. Du kan stadig indtaste køretøjet manuelt.</div>';
      html += '<div class="trfe-hint">Indlæst katalog: ' +
        this._katalogBrands().length + ' mærker · ' + this._katalogBrands().reduce(function (total, brand) { return total + (brand.modeller || []).length; }, 0) + ' modeller</div><div class="trfe-hint">Eget katalog (valgfrit)</div><input type="text" data-key="katalog_url" value="' +
        esc(c.katalog_url || "") + '" placeholder="/tiny_refuel/static/katalog.json">';
      html += '<div class="trfe-hint">Tomt felt bruger integrationens katalog.json. Eget katalog kan ligge under /local/katalog.json (config/www). Kort og editor deler hentningen; genindlæs browseren efter filændringer.</div>';
      html += '<details class="trfe-yaml" data-editor-section="yaml"><summary>Vis hele kortets YAML</summary>';
      html += '<div class="trfe-hint">Kopiér hele konfigurationen til Udseende → Rediger i YAML.</div>';
      html += '<button type="button" data-yaml-copy>Kopiér YAML</button>';
      html += '<textarea data-card-yaml readonly spellcheck="false" rows="14" aria-label="Hele kortets YAML"></textarea></details>';
      html += "<h4>Fælles tankstørrelse (bruges hvis køretøjet ikke har egen)</h4>";
      var tl = (c.tank_liters !== undefined && c.tank_liters !== null) ? c.tank_liters : "";
      html += '<div class="trfe-row"><input type="number" data-key="tank_liters" min="0.01" step="any" value="' +
        esc(tl) + '" placeholder="Auto"></div>';
      html += '<div class="trfe-hint">Tomt felt bruger en angivet tank_entity eller input_number.tankstorrelse, hvis den findes. Uden en kendt størrelse vises ingen fuld-tank-beregning. Køretøjets egen tankstørrelse har førsteprioritet.</div>';
      html += "<h4>Navigation (tryk på logo)</h4>";
      var nv = c.navigation || "waze";
      html += '<label><input type="radio" name="trf-nav" data-key="navigation" value="waze"' +
        (nv === "waze" ? " checked" : "") + "><span>Waze</span></label>";
      html += '<label><input type="radio" name="trf-nav" data-key="navigation" value="google"' +
        (nv === "google" ? " checked" : "") + "><span>Google Maps</span></label>";
      html += '<div class="trfe-hint">Åbner navigation til den nærmeste station ved tryk på logo.</div>';
      html += '<h4>Hent data</h4>';
      html += cb("vis_scrape_knap", "Vis knappen på kortet", this._bool("vis_scrape_knap", !c.kompakt));
      html += cb("scrape_valgt_bil", "Begræns hentning til det valgte køretøj", this._bool("scrape_valgt_bil", true));
      html += '<div class="trfe-hint">Manuel hentning følger køretøjets drivmiddel: benzin henter benzinpriser, diesel dieselpriser, el ladepriser og plug-in-hybrid benzin samt el. Slå valget fra for at hente alle typer. Automatisk intervalhentning henter altid alle typer, så køretøjer du tilføjer senere også får data.</div>';
      html += '<details data-editor-section="advanced"><summary>Avanceret</summary>';
      html += '<div class="trfe-hint">Positions-enhed</div><input type="text" data-key="location_entity" value="' +
        esc(c.location_entity || "") + '" placeholder="device_tracker.din_telefon">';
      html += '<div class="trfe-hint">Notifikations-service til ⟳-knap</div><input type="text" data-key="notify_service" value="' +
        esc(c.notify_service || "") + '" placeholder="notify.mobile_app_din_telefon">';
      html += "</details></div>";
      this.innerHTML = html;
      this._editorRendered = true;
      this.querySelectorAll("details[data-editor-section], details[data-car-card]").forEach(function (node) {
        var section = node.getAttribute("data-editor-section");
        var key = section ? "section:" + section : "car:" + node.getAttribute("data-car-card");
        if (Object.prototype.hasOwnProperty.call(detailsState, key)) node.open = detailsState[key];
      });
      if (focus) {
        var focused = this.querySelector('[data-key="' + focus.key + '"]');
        if (focused) {
          focused.value = focus.value;
          focused.focus({ preventScroll: true });
          if (focus.start !== null && typeof focused.setSelectionRange === "function") focused.setSelectionRange(focus.start, focus.end);
        }
      }
      this._updateYaml();
    }
  }

  customElements.define("tiny-refuel-card-editor", TinyRefuelCardEditor);
  window.TinyRefuelCardEditor = TinyRefuelCardEditor;
}(window);

