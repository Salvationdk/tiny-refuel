!function (window) {
  "use strict";
  if (window.customElements.get("tiny-refuel-card")) return;

  var CSS = `
  .trf { font-family: var(--paper-font-body1_-_font-family, inherit); padding: 14px 16px; color: var(--primary-text-color); }
  .trf-titlebar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 2px; }
  .trf-title { font-weight: 600; font-size: 15px; text-transform: uppercase; letter-spacing: .6px; text-shadow: 0 0 12px rgba(0,229,255,.35); }
  .trf-rule { height: 2px; border-radius: 2px; margin: 6px 0 4px; background: linear-gradient(90deg, var(--primary-color, #00e5ff), var(--accent-color, #b967ff)); opacity: .55; box-shadow: 0 0 8px rgba(0,229,255,.35); }
  .trf-pos { font-size: 11px; color: var(--secondary-text-color); margin-bottom: 8px; opacity: .85; }
  .trf-cars { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px; }
  .trf-car { border: 1px solid rgba(0,229,255,.45); background: linear-gradient(180deg, rgba(0,229,255,.08), rgba(185,103,255,.08)); color: var(--primary-text-color); border-radius: 20px; padding: 5px 14px; font-size: 12px; font-weight: 600; letter-spacing: .8px; text-transform: uppercase; cursor: pointer; box-shadow: 0 0 8px rgba(0,229,255,.25); }
  .trf-car:active { transform: scale(.95); }
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
  .trf-brand { font-weight: 700; font-size: 13px; margin: 12px 6px 4px; }
  .trf-evrow .trf-price { color: var(--primary-color, #00e5ff); text-shadow: 0 0 10px rgba(0,229,255,.75); }
  .trf-evrow .trf-meta { color: var(--secondary-text-color); font-size: 10px; }
  .trf-tariffs { grid-column: 1 / -1; min-width: 0; font-size: clamp(8px, 2.4vw, 10px); line-height: 1.5; }
  .trf-tariff-line { display: block; white-space: nowrap; overflow-x: auto; font-weight: 600; }
  .trf-tariff-note { color: var(--secondary-text-color); font-size: 10px; }
  .trf-data-tools { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 8px 0; font-size: 11px; }
  .trf-data-tools button:disabled { cursor: wait; opacity: .65; }
  .trf-data-counts { margin: 8px 6px; font-size: 11px; color: var(--secondary-text-color); }
  .trf-data-counts summary { cursor: pointer; }
  .trf-data-counts table { width: 100%; margin-top: 5px; border-collapse: collapse; font-size: 10px; }
  .trf-data-counts th, .trf-data-counts td { padding: 3px 5px; text-align: left; }
  .trf-data-counts th { font-weight: 600; }
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
  }`;

  var ECSS = `
  .trfe { font-family: var(--paper-font-body1_-_font-family, inherit); padding: 8px 4px; color: var(--primary-text-color); font-size: 13px; }
  .trfe h4 { margin: 14px 0 6px; font-size: 13px; text-transform: uppercase; letter-spacing: .5px; color: var(--secondary-text-color); }
  .trfe h4:first-child { margin-top: 0; }
  .trfe label { display: flex; align-items: center; gap: 8px; padding: 4px 0; cursor: pointer; }
  .trfe input[type=checkbox] { width: 16px; height: 16px; accent-color: var(--primary-color, #03a9f4); }
  .trfe input[type=number], .trfe input[type=text], .trfe select { background: var(--mdc-text-field-fill-color, rgba(255,255,255,.06)); color: var(--primary-text-color); border: 1px solid var(--divider-color, rgba(255,255,255,.12)); border-radius: 4px; padding: 6px 8px; font-size: 13px; width: 100%; box-sizing: border-box; }
  .trfe .trfe-row { display: flex; gap: 8px; align-items: center; }
  .trfe .trfe-hint { font-size: 11px; color: var(--secondary-text-color); opacity: .8; margin-top: 2px; }
  .trfe details { margin-top: 10px; }
  .trfe summary { cursor: pointer; color: var(--secondary-text-color); font-size: 12px; }
  .trfe .trfe-car { border: 1px solid var(--divider-color, rgba(255,255,255,.12)); border-radius: 8px; padding: 8px 10px; margin-bottom: 8px; }
  .trfe .trfe-car b { font-size: 13px; }
  .trfe a { color: var(--primary-color, #03a9f4); }`;

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (m) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m];
    });
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
    { key: "tesla", brand: "Tesla", img: "logo-tesla.svg", has100: false, electricOnly: true },
    { key: "ionity", brand: "Ionity", img: "logo-ionity.svg", has100: false, electricOnly: true },
  ];

  var FORDELE = {
    circle_k: "extra-app: op til 20 øre/L efter besøgstal",
    ok: "OK-app + Coop-medlemskab: bonus pr. liter",
    q8: "Q8 Smile-point kan veksles til brændstofrabat",
    shell: "Shell App/Card: faste øre-rabatter pr. liter",
    goon: "Go'on App + Klubkort støtter lokal forening",
    uno_x: "Uno-X app + Forbrugsforeningskort: rabat i procent",
    ingo: "Ingen bonusordning — altid lav pris",
    f24: "Lavpriskæde uden bonusprogram",
    oil: "OIL Kundekort til hurtig selvbetjening",
  };

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
          self._closeEvPopup();
        }
      }, true);
      this.addEventListener("click", function (ev) {
        var openEv = ev.target && ev.target.closest ? ev.target.closest("[data-open-ev]") : null;
        if (openEv) {
          ev.preventDefault();
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
        if (ev.target && ev.target.classList && ev.target.classList.contains("trf-ev-dialog")) {
          var rect = ev.target.getBoundingClientRect();
          if (ev.clientX < rect.left || ev.clientX > rect.right || ev.clientY < rect.top || ev.clientY > rect.bottom) {
            self._closeEvPopup();
            return;
          }
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
        var moreEv = ev.target && ev.target.closest ? ev.target.closest("[data-more-ev]") : null;
        if (moreEv) {
          self._evPopupLimit = (self._evPopupLimit || 10) + 10;
          self._render();
          return;
        }
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
      this._config = config || {};
      this._render();
    }

    getCardSize() { return 6; }

    static getStubConfig() {
      return { vis_benzin: true, vis_el: true, vis_andet: true };
    }

    static getConfigElement() {
      return document.createElement("tiny-refuel-card-editor");
    }

    set hass(hass) {
      var prev = this._hass && this._trackerState();
      this._hass = hass;
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

    _tankLiters() {
      var car = this._car();
      var cfgL = parseFloat(car && car.tank_liters !== undefined && car.tank_liters !== null && car.tank_liters !== ""
        ? car.tank_liters : (this._config && this._config.tank_liters));
      if (isFinite(cfgL) && cfgL > 0) return Math.min(200, Math.max(5, cfgL));
      var tankEnt = (car && car.tank_entity) || (this._config && this._config.tank_entity) || "input_number.tankstorrelse";
      var st = this._state(tankEnt);
      var v = st ? parseFloat(st.state) : NaN;
      if (!isFinite(v)) v = 50;
      return Math.min(200, Math.max(5, v));
    }

    _notifyService() {
      var car = this._car();
      if (car && car.notify_service) return car.notify_service;
      return cfgGet(this._config, "notify_service", "");
    }

    _cars() {
      var cfg = this._config || {};
      if (Array.isArray(cfg.biler) && cfg.biler.length) {
        return cfg.biler.map(function (b, i) {
          return {
            navn: (b && b.navn) || ("Bil " + (i + 1)),
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

    _scrapeAll() {
      if (this._scraping) return;
      if (!this._hass || typeof this._hass.callService !== "function") {
        this._scrapeMessage = "Tilføj Tiny Refuel under Enheder og tjenester.";
        this._render();
        return;
      }
      this._scraping = true;
      this._scrapeMessage = "Scraper alle data… Det kan tage flere minutter.";
      this._scrapeBaseline = this._data && this._data.updated;
      this._scrapeStarted = Date.now();
      this._scrapeRun = (this._scrapeRun || 0) + 1;
      var self = this, run = this._scrapeRun;
      this._render();
      try {
        Promise.resolve(this._hass.callService("tiny_refuel", "refresh", {})).catch(function (err) {
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
        var stamp = data && Date.parse(data.updated);
        if (data && data.updated !== self._scrapeBaseline && isFinite(stamp) && stamp >= self._scrapeStarted - 1000) {
          var errors = Array.isArray(data.errors) ? data.errors.length : 0;
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
        self._data = data;
        self._dataFetchedAt = Date.now();
        self._dataLoading = false;
        self._render();
        clearTimeout(self._dataTimer);
        self._dataTimer = setTimeout(function () { self._maybeLoad(); }, data.refreshing || !data.updated ? 5000 : 60000);
        return data;
      }).catch(function () {
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
      var cfg = this._config || {};
      var car = null;
      try { car = this._car(); } catch (e) { car = null; }
      if (car && car.vis && typeof car.vis === "object") {
        return {
          benzin: car.vis.benzin !== false,
          diesel: car.vis.diesel === true,
          el: car.brændstof !== "hybrid" && car.vis.el !== false,
          andet: car.vis.andet !== false,
        };
      }
      return {
        benzin: cfgGet(cfg, "vis_benzin", true),
        diesel: cfgGet(cfg, "vis_diesel", false),
        el: (!car || car.brændstof !== "hybrid") && cfgGet(cfg, "vis_el", true),
        andet: cfgGet(cfg, "vis_andet", true),
      };
    }

    _render() {
      if (!this._config) return;
      var previousList = this.querySelector && this.querySelector(".trf-ev-list");
      var popupScroll = previousList ? previousList.scrollTop : 0;
      var cfg = this._config;
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

      var body = "";
      var rows = this._buildRows(loc);
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
        if (visAndet && min95 !== null) {
          bestHtml = '<div class="trf-best"><span><b class="trf-b95">▎Billigst 95:</b>';
          for (var k = 0; k < rows.length; k++) {
            if (rows[k].v95 === min95) {
              bestHtml += '<img src="/tiny_refuel/static/logos/' + rows[k].b.img + '" alt="" class="trf-inline">';
            }
          }
          bestHtml += "</span>";
          if (min100 !== null) {
            bestHtml += '<span><b class="trf-b100">▎Billigst 100:</b>';
            for (var k2 = 0; k2 < rows.length; k2++) {
              if (rows[k2].b.has100 && rows[k2].v100 === min100) {
                bestHtml += '<img src="/tiny_refuel/static/logos/' + rows[k2].b.img + '" alt="" class="trf-inline">';
              }
            }
            bestHtml += "</span>";
          }
          bestHtml += "</div>";
        }

        if (visAndet && loc) {
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

        var head = '<div class="trf-head" style="grid-template-columns: ' + grid + '"><span></span>';
        if (visBenzin) head += '<span class="trf-p">95</span><span class="trf-p">100</span>';
        if (visDiesel) head += '<span class="trf-p">Diesel</span>';
        head += '<span class="trf-km" title="Afstand fra telefonens placering til nærmeste station">km</span></div>';
        body += bestHtml + head;

        for (var r = 0; r < rows.length; r++) {
          var row = rows[r];
          var g95 = visBenzin && min95 !== null && row.v95 !== null && row.v95 === min95;
          var g100 = visBenzin && row.b.has100 && min100 !== null && row.v100 !== null && row.v100 === min100;
          var cls = "trf-row";
          var cells = "";
          if (visBenzin) {
            cells += row.v95 === null
              ? '<div class="trf-pcol"><span class="trf-price trf-na">–</span></div>'
              : '<div class="trf-pcol"><span class="trf-price' + (g95 ? " trf-g95" : "") + '">' + this._fmt(row.v95) + "</span>" + row.chg + "</div>";
            cells += (!row.b.has100 || row.v100 === null)
              ? '<div class="trf-pcol"><span class="trf-price trf-na">–</span></div>'
              : '<div class="trf-pcol"><span class="trf-price' + (g100 ? " trf-g100" : "") + '">' + this._fmt(row.v100) + "</span></div>";
          }
          if (visDiesel) {
            cells += row.diesel === null
              ? '<div class="trf-pcol"><span class="trf-price trf-na">–</span></div>'
              : '<div class="trf-pcol"><span class="trf-price">' + this._fmt(row.diesel) + "</span></div>";
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
            link = this._navHref(null, row.b.brand);
            title = row.b.brand;
          }
          var logo = '<div class="trf-logo"><a class="trf-navlink" data-waze="' + esc(row.b.brand) +
            '" href="' + link + '" rel="noopener" title="' + esc(title) + '"><img src="/tiny_refuel/static/logos/' +
            row.b.img + '" alt="' + esc(row.b.brand) + '"></a></div>';
          var sub = "";
          var fbtn = (visAndet && FORDELE[row.b.key])
            ? '<a href="#" class="trf-fordel-btn" data-fordel="' + esc(row.b.key) + '" title="Se kundefordele">★ Fordele</a>'
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
          if (this._openFordel === row.b.key && FORDELE[row.b.key]) {
            sub += '<div class="trf-fordel-box"><b>' + esc(row.b.brand) +
              " kundefordele:</b><br>" + esc(FORDELE[row.b.key]) + "</div>";
          }
          body += '<div class="' + cls + '" style="grid-template-columns: ' + grid + '" title="' + esc(title) + '">' +
            logo + cells + kmCell + sub + "</div>";
        }
      }

      if (hasData) {
        if (visEl && !visBenzin && !visDiesel) body += this._nearestEvHtml(loc);
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
          if (_carFuel !== "el" && visBenzin) {
            var tankL = this._tankLiters();
          var priced = [];
          for (var m = 0; m < rows.length; m++) {
            if (!rows[m].liste && isFinite(rows[m].v95)) {
              priced.push({ brand: rows[m].b.brand, v: rows[m].v95 });
            }
          }
          if (priced.length >= 2) {
            var cheap = priced[0], dear = priced[0];
            for (var n2 = 1; n2 < priced.length; n2++) {
              if (priced[n2].v < cheap.v) cheap = priced[n2];
              if (priced[n2].v > dear.v) dear = priced[n2];
            }
            body += '<div class="trf-tank">Fuld tank (' + String(tankL).replace(".", ",") + ' L' +
              (this._cars().length > 1 && this._car().navn ? " · " + esc(this._car().navn) : "") + ') 95: <b>' +
              esc(cheap.brand) + " " + Math.round(cheap.v * tankL) + " kr</b> → " + esc(dear.brand) + " " +
              Math.round(dear.v * tankL) + " kr · spar <b>" + Math.round((dear.v - cheap.v) * tankL) + " kr</b></div>";
          }
          } else if (_carFuel === "el" && visEl && isFinite(_carBatt) && _carBatt > 0 && this._data && Array.isArray(this._data.ev)) {
            var kwhs = [];
            for (var me = 0; me < this._data.ev.length; me++) {
              var _ev = this._data.ev[me];
              if (typeof _ev.kwh === "number" && isFinite(_ev.kwh) && _ev.kwh > 0 && _ev.address && showBrand(cfg, this._evBrandKey(_ev.brand))) kwhs.push(_ev.kwh);
            }
            if (kwhs.length >= 2) {
              var kmin = Math.min.apply(null, kwhs), kmax = Math.max.apply(null, kwhs);
              var bkwh = Math.min(200, Math.max(10, _carBatt));
              body += '<div class="trf-tank">Fuld opladning (' + String(bkwh).replace(".", ",") + ' kWh' +
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
            body += '<div class="trf-tank">' + snitTxt + "</div>";
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
      if (cars.length > 1) {
        var sel = this._carIdx();
        carHtml = '<div class="trf-cars">';
        for (var ci = 0; ci < cars.length; ci++) {
          carHtml += '<button class="trf-car' + (ci === sel ? " trf-on" : "") + '" data-car="' + ci + '">' +
            esc(cars[ci].navn) + "</button>";
        }
        carHtml += "</div>";
      }

      var legends = [];
      if (visBenzin) legends.push('<b>95</b> = Blyfri 95 (E10) · <b>100</b> = 100-oktan · <b>Premium 95</b> = benzin med additiver · <b>92</b> = Blyfri 92');
      if (visDiesel) legends.push('<b>Diesel</b> = standard diesel · <b>Extra</b> = opgraderet diesel · <b>HVO100</b> = alternativt dieselbrændstof · <b>AdBlue</b> = væske til dieselbilens udstødningsrensning');
      if (visEl) legends.push('<b>EL</b> = opladning i kr/kWh · <b>pris i app</b> = prisen findes ikke i udtrækket · <b>km</b> = afstand i luftlinje');
      var legendHtml = legends.length ? '<div class="trf-legend"><b>Energityper:</b> ' + legends.join(' · ') + '</div>' : '';
      if (visBenzin || visDiesel) legendHtml += '<div class="trf-legend"><b>Listepris</b> = kædens vejledende brændstofpris. En listepris er ikke knyttet til en bestemt station; pumpeprisen kan afvige.</div>';
      var selectedFuel = this._car() && this._car().brændstof;
      var cardTitle = selectedFuel === 'plug_in_hybrid' && visBenzin && visEl ? 'Hybrid – benzin og opladning' :
        (selectedFuel === 'hybrid' && visBenzin && !visEl ? 'Hybrid – benzin' :
        (visEl && !visBenzin && !visDiesel ? 'Ladepriser' :
        (visEl ? 'Brændstof og ladepriser' : (visDiesel && !visBenzin ? 'Dieselpriser' : 'Benzinpriser'))));

      this.innerHTML =
        "<style>" + CSS + "</style>" +
        '<div class="trf">' +
        '<div class="trf-titlebar"><div class="trf-title">' + cardTitle + '</div>' +
        '<button class="trf-refresh' + (this._locRefreshing ? " trf-spin" : "") + '" data-refresh title="Hent frisk GPS-position fra telefonen">⟳</button></div>' +
        '<div class="trf-rule"></div>' +
        '<div class="trf-data-tools"><button type="button" class="trf-ev-button" data-scrape' + (this._scraping ? ' disabled' : '') + '>Scrape alle data</button><span role="status">' + esc(this._scrapeMessage || '') + '</span></div>' + this._dataErrorsHtml() +
        carHtml +
        (visAndet
          ? '<div class="trf-pos">Position: ' + (this._locRefreshing ? "opdaterer…" : esc(this._posAge() || "ukendt")) + "</div>"
          : "") +
        body +
        legendHtml +
        '<div class="trf-foot"><span>Hentet fra selskabernes egne lister: ' + esc(upd) + '</span><span>Tiny Refuel v0.1</span></div>' +
        "</div>" + this._evPopupHtml(loc);
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

    _evCoords(ev) {
      if (ev.lat === null || ev.lat === undefined || ev.lat === '' || ev.lon === null || ev.lon === undefined || ev.lon === '') return null;
      var lat = Number(ev.lat), lon = Number(ev.lon);
      if (!isFinite(lat) || !isFinite(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180 || (lat === 0 && lon === 0)) return null;
      return { lat: lat, lon: lon };
    }

    _evHasLocation(ev) {
      return !!(ev.address || (ev.name && this._evCoords(ev)));
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
      var brand = this._evBrandKey(ev.brand), key = 'el_' + brand;
      // Oplysninger kontrolleret 2026-10-08; aktuelle betingelser findes hos selskabet.
      var benefits = {
        circle_k: { text: 'Circle K extra giver medlemsfordele på opladning. Se den aktuelle medlemspris og betingelser hos Circle K.',
          url: 'https://www.circlek.dk/opladning/opladningskort' },
        ok: { text: '10 % rabat på offentlig opladning kræver OK Ladepakke med serviceaftale, OK Kort og betaling via OK-appen.',
          url: 'https://www.ok.dk/privat/produkter/opladning/kampagner/laderabat' },
        uno_x: { text: 'Opladning uden abonnement. Uno-X Privatkort giver automatisk rabat på lynladning; se gældende vilkår hos Uno-X.',
          url: 'https://www.unoxmobility.dk/privat/produkter/opladning/lad-uden-abonnement' }
      };
      var b = benefits[brand];
      if (!b && typeof ev.benefits === 'string' && ev.benefits.trim()) b = { text: ev.benefits };
      if (!b) return '';
      var html = part === 'box' ? '' : '<a href="#" class="trf-fordel-btn" data-fordel="' + esc(key) + '" title="Se ladefordele">★ Fordele</a>';
      if (part === 'button') return html;
      if (this._openFordel === key) html += '<div class="trf-fordel-box"><b>' + esc(ev.brand) + ' ladefordele:</b><br>' + esc(b.text) +
        (b.url ? ' <a href="' + esc(b.url) + '" target="_blank" rel="noopener">Se vilkår</a>' : '') + '</div>';
      return html;
    }

    _evRow(ev, loc, count, inPopup, tariffs, companyGroup) {
      var coords = this._evCoords(ev);
      var km = loc && coords ? this._haversineKm(loc.lat, loc.lon, coords.lat, coords.lon) : null;
      var query = ev.brand + ' ' + (ev.address || ev.name || '');
      var link = this._navHref(coords ? coords.lat + ',' + coords.lon : null, query);
      var logo = this._brandImg(ev.brand);
      var logoContent = logo ? '<img src="/tiny_refuel/static/logos/' + esc(logo) + '" alt="' + esc(ev.brand) + '">' : esc(ev.brand);
      var title = query + (km !== null ? ' · ' + this._fmtKm(km) + ' km' : '');
      var price = typeof ev.kwh === 'number' && isFinite(ev.kwh) && ev.kwh > 0 ? this._fmt(ev.kwh) : 'pris i app';
      var info = [ev.name || ev.brand, ev.address];
      if (!ev.address && coords) info.push('gadeadresse ikke oplyst; navigation til koordinater');
      if (ev.access_note) info.push(ev.access_note);
      if (ev.kind) info.push(ev.kind);
      if (ev.power_kw) info.push(ev.power_kw + ' kW');
      if (Array.isArray(ev.connector_types) && ev.connector_types.length) info.push(ev.connector_types.join('/'));
      if (ev.plugs) info.push(ev.plugs + ' ladepunkter');
      if (ev.stale) info.push('gemte data: seneste hentning fejlede');
      if (ev.source_updated) info.push('hentet ' + new Date(ev.source_updated).toLocaleString('da-DK'));
      if (count > 1) info.push('+' + (count - 1) + (companyGroup ? ' andre ladevalg hos selskabet' : price === 'pris i app' ? ' andre ladesteder hos selskabet med pris i app' : ' ladesteder hos samme selskab til samme pris'));
      var age = this._fmtAge(ev.lu);
      return '<div class="trf-evrow" style="grid-template-columns: minmax(70px,130px) minmax(60px,1fr) 52px" title="' + esc(title) + '">' +
        '<div class="trf-logo"><a class="trf-navlink" data-waze="' + esc(ev.brand) + '" href="' + esc(link) + '" title="' + esc(title) + '">' + logoContent + '</a></div>' +
        '<div class="trf-pcol"><span class="trf-price"><b>' + price + '</b></span></div>' +
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
        rows.slice(0, limit).forEach(function (row) { html += self._evRow(row.ev, loc, 1, true); });
      } else {
        html += '<div class="trf-em">Ingen konkrete ladesteder i udtrækket for dette selskab og filter.</div>';
      }
      html += '</div><div class="trf-ev-actions">';
      if (rows.length > limit) html += '<button type="button" class="trf-ev-button" data-more-ev>Vis 10 mere</button>';
      html += '<span class="trf-em">Viser ' + Math.min(limit, rows.length) + ' af ' + rows.length + ' ladevalg. Et sted kan have både AC og DC.</span></div></dialog>';
      return html;
    }

    _evTariffsHtml(items) {
      if (!items || !items.length) return '';
      var self = this, seen = new Set();
      var text = items.filter(function (ev) {
        var key = ev.name + '|' + ev.kwh;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      }).map(function (ev) { return ev.name + ' ' + self._fmt(ev.kwh); }).join(' · ') + ' kr/kWh';
      return '<div class="trf-tariffs"><span class="trf-tariff-line" title="' + esc(text) + '">' + esc(text) +
        '</span><span class="trf-tariff-note">Generelle selskabstakster; ikke en bekræftet pris på det enkelte ladested.</span></div>';
    }

    _evDataSummary(entries) {
      var self = this, providers = new Map();
      entries.forEach(function (ev) {
        var p = providers.get(ev.brand);
        if (!p) { p = { sites: new Set(), priced: new Set(), stale: new Set(), tariffs: false }; providers.set(ev.brand, p); }
        if (!self._evHasLocation(ev)) {
          if (typeof ev.kwh === 'number' && isFinite(ev.kwh) && ev.kwh > 0) p.tariffs = true;
          return;
        }
        var coords = self._evCoords(ev);
        var key = ev.location_id || (coords ? coords.lat + ',' + coords.lon : String(ev.address).toLowerCase().trim());
        p.sites.add(key);
        if (typeof ev.kwh === 'number' && isFinite(ev.kwh) && ev.kwh > 0 && !ev.app_only) p.priced.add(key);
        if (ev.stale) p.stale.add(key);
      });
      var sites = 0, priced = 0, count = 0;
      providers.forEach(function (p) { sites += p.sites.size; priced += p.priced.size; if (p.sites.size || p.tariffs) count++; });
      var html = '<details class="trf-data-counts"><summary>Data fra ' + count + ' selskaber · ' + sites + ' ladesteder · ' + priced + ' med lokal elpris</summary>' +
        '<table><thead><tr><th>Selskab</th><th>Steder</th><th>Med lokal pris</th><th>Datastatus</th></tr></thead><tbody>';
      providers.forEach(function (p, brand) {
        if (!p.sites.size && !p.tariffs) return;
        var status = p.stale.size ? p.stale.size + ' steder med gemte data' : 'Indlæste data';
        if (p.tariffs) status += ' · generelle takster';
        html += '<tr><td>' + esc(brand) + '</td><td>' + p.sites.size + '</td><td>' + p.priced.size + '</td><td>' + esc(status) + '</td></tr>';
      });
      html += '</tbody></table><div>Kun valgte selskaber. AC/DC på samme sted tælles én gang pr. selskab. Generelle takster tælles ikke som lokale priser.</div></details>';
      return html;
    }

    _dataErrorsHtml() {
      var html = this._data && this._data.last_error ? '<div class="trf-em">Hentningen fejlede: ' + esc(this._data.last_error) + '</div>' : '';
      if (this._data && this._data.refreshing) html += '<div class="trf-em">Tiny Refuel henter nye data…</div>';
      var errors = this._data && this._data.errors;
      if (Array.isArray(errors) && errors.length) html += '<details class="trf-data-counts"><summary>' + errors.length + ' fejl i seneste hentning</summary>' +
        errors.map(function (error) {
          if (!error || typeof error !== 'object') return '<div>' + esc(error) + '</div>';
          var source = error.source || Object.keys(error).filter(function (key) { return key !== 'stale_reused'; })[0] || 'Datakilde';
          var message = error.error || error[source] || 'Hentningen fejlede';
          return '<div>' + esc(source) + ': ' + esc(message) + '</div>';
        }).join('') + '</details>';
      return html;
    }

    _evHtml(loc) {
      var self = this, entries = this._evEntries();
      var html = '<div class="trf-brand">El (kr/kWh)</div>';
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
      groups.forEach(function (group) {
        var first = !renderedBrands.has(group.ev.brand);
        renderedBrands.add(group.ev.brand);
        html += self._evRow(group.ev, loc, group.count, false, first ? tariffs.get(group.ev.brand) : null, group.companyGroup);
      });
      tariffs.forEach(function (items, brand) {
        if (renderedBrands.has(brand)) return;
        var logo = self._brandImg(brand);
        html += '<div class="trf-evrow" style="grid-template-columns: minmax(70px,130px) minmax(60px,1fr) 52px"><div class="trf-logo">' + (logo ? '<img src="/tiny_refuel/static/logos/' + esc(logo) + '" alt="' + esc(brand) + '">' : esc(brand)) + '</div>' +
          '<div class="trf-pcol"><span class="trf-tariff-note">Generelle takster</span></div><span class="trf-km">–</span>' +
          self._evTariffsHtml(items) + '<div class="trf-station">' + self._evPopupButton(brand) + self._evBenefits(items[0], 'button') + '</div>' + self._evBenefits(items[0], 'box') + '</div>';
      });
      html += self._evDataSummary(entries);
      if (!stations.length && !tariffs.size) html += '<div class="trf-em">Ingen ladesteder eller el-priser for de valgte selskaber.</div>';
      var absent = BRANDS.filter(function (b) {
        return b.electricOnly && showBrand(self._config, b.key) && !entries.some(function (ev) { return self._evBrandKey(ev.brand) === b.key; });
      }).map(function (b) { return b.brand; });
      if (absent.length) html += '<div class="trf-em">Ingen ladedata i udtrækket: ' + absent.map(esc).join(', ') + '.</div>';
      var sources = this._data && this._data.ev_sources;
      var expected = { clever: 'Clever', eon: 'E.ON', tesla: 'Tesla', ionity: 'Ionity', ok: 'OK', oil: 'OIL', shell: 'Shell', circle_k: 'Circle K' };
      var missingSetup = [], failed = [];
      Object.keys(expected).forEach(function (key) {
        if (!showBrand(self._config, key)) return;
        var status = sources && sources[key];
        if (!status) missingSetup.push(expected[key]);
        else if (status.status === 'error' || status.status === 'stale') failed.push(expected[key]);
      });
      if (missingSetup.length && this._data && this._data.updated) html += '<div class="trf-em">Den indlæste datafil mangler de nye datakilder for ' + missingSetup.map(esc).join(', ') +
        '. Udskift scraperscriptet fra den nyeste pakke, tryk på Scrape alle data, og tryk derefter på kortets opdateringsknap.</div>';
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

  class TinyRefuelCardEditor extends HTMLElement {
    constructor() {
      super();
      this._config = {};
      var self = this;
      this.addEventListener("click", function (ev) {
        var t = ev.target && ev.target.closest ? ev.target.closest("[data-bil-add],[data-bil-del]") : null;
        if (!t) return;
        ev.preventDefault();
        var cfg = Object.assign({}, self._config);
        var biler = Array.isArray(cfg.biler) && cfg.biler.length
          ? cfg.biler.map(function (b) { return Object.assign({}, b); })
          : [{ navn: "Bil 1" }];
        if (t.hasAttribute && t.hasAttribute("data-bil-add")) {
          biler.push({ navn: "Bil " + (biler.length + 1) });
        } else {
          var idx = parseInt(t.getAttribute("data-bil-del"), 10);
          if (isFinite(idx)) biler.splice(idx, 1);
        }
        if (!biler.length) delete cfg.biler;
        else cfg.biler = biler;
        self._config = cfg;
        self._render();
        self.dispatchEvent(new CustomEvent("config-changed", { detail: { config: cfg } }));
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
          if (field === "tank_liters" || field === "batteri_kwh") {
            var bv = parseFloat(t.value);
            if (isFinite(bv) && bv > 0) biler[bi][field] = bv;
            else delete biler[bi][field];
          } else if (field === "mærke") {
            var mk = String(t.value || "");
            if (mk) biler[bi].mærke = mk;
            else delete biler[bi].mærke;
            delete biler[bi].model;
            needRender = true;
          } else if (field === "model") {
            var md = String(t.value || "");
            if (md) {
              biler[bi].model = md;
              var entry = self._katalogFind(biler[bi].mærke, md);
              if (entry) {
                if (entry.tank_l != null) biler[bi].tank_liters = entry.tank_l;
                else delete biler[bi].tank_liters;
                if (entry.batteri_kwh != null) biler[bi].batteri_kwh = entry.batteri_kwh;
                else delete biler[bi].batteri_kwh;
                if (entry.brændstof) {
                  biler[bi].brændstof = entry.brændstof;
                  biler[bi].vis = visForFuel(entry.brændstof);
                }
                var nm = biler[bi].navn || "";
                if (!nm || /^Bil \d+$/.test(nm)) {
                  biler[bi].navn = biler[bi].mærke + " " + md;
                }
              }
            } else {
              delete biler[bi].model;
            }
            needRender = true;
          } else if (field === "brændstof") {
            var fb = String(t.value || "");
            if (fb) {
              biler[bi].brændstof = fb;
              biler[bi].vis = visForFuel(fb);
            } else {
              delete biler[bi].brændstof;
            }
            needRender = true;
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
          self.dispatchEvent(new CustomEvent("config-changed", { detail: { config: cfg } }));
          return;
        } else if (key === "scrape_entity" || key === "location_entity" || key === "notify_service" || key === "katalog_url" || key === "navigation") {
          var s = String(t.value || "").trim();
          if (s) cfg[key] = s;
          else delete cfg[key];
          if (key === "katalog_url") {
            self._config = cfg;
            self._loadKatalog();
            self.dispatchEvent(new CustomEvent("config-changed", { detail: { config: cfg } }));
            return;
          }
        } else if (key.indexOf("kæde:") === 0) {
          var bk = key.slice(5);
          cfg.kaeder = Object.assign({}, cfg.kaeder);
          cfg.kaeder[bk] = !!t.checked;
        } else {
          cfg[key] = !!t.checked;
        }
        self._config = cfg;
        self.dispatchEvent(new CustomEvent("config-changed", { detail: { config: cfg } }));
      });
    }

    setConfig(config) {
      this._config = config || {};
      this._render();
    }

    set hass(hass) {
      this._hass = hass;
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
      var u = this._config && this._config.katalog_url;
      if (u && String(u).trim() && ["/local/fuelprices/bilkatalog.json", "/local/tiny-gas/data/bilkatalog.json", "/local/tiny-refuel/data/bilkatalog.json"].indexOf(String(u).trim()) === -1) return String(u).trim();
      return "/tiny_refuel/static/bilkatalog.json";
    }

    _loadKatalog() {
      if (typeof fetch !== "function") return;
      var url = this._katalogUrl();
      if (this._katalog && this._katalogUrlUsed === url) return;
      if (this._katalogLoading && this._katalogUrlUsed === url) return;
      this._katalog = null;
      this._katalogUrlUsed = url;
      this._katalogLoading = true;
      var self = this;
      fetch(url, { cache: "no-store" }).then(function (r) {
        if (!r.ok) throw new Error("http " + r.status);
        return r.json();
      }).then(function (data) {
        if (self._katalogUrlUsed !== url) return;
        self._katalog = data;
        self._katalogLoading = false;
        self._render();
      }).catch(function () {
        if (self._katalogUrlUsed !== url) return;
        self._katalogLoading = false;
      });
    }

    _katalogBrands() {
      if (this._katalog && Array.isArray(this._katalog.brands)) return this._katalog.brands;
      return [];
    }

    _katalogModels(maerke) {
      var brands = this._katalogBrands();
      for (var i = 0; i < brands.length; i++) {
        if (brands[i].mærke === maerke) return brands[i].modeller || [];
      }
      return [];
    }

    _katalogFind(maerke, model) {
      var models = this._katalogModels(maerke);
      for (var i = 0; i < models.length; i++) {
        if (models[i].model === model) return models[i];
      }
      return null;
    }

    _bool(key, def) {
      if (this._config && this._config[key] !== undefined) return !!this._config[key];
      return def;
    }

    _render() {
      var c = this._config || {};
      function cb(key, label, checked) {
        return '<label><input type="checkbox" data-key="' + key + '"' +
          (checked ? " checked" : "") + "><span>" + esc(label) + "</span></label>";
      }
      var html = '<div class="trfe"><style>' + ECSS + "</style>";
      html += "<h4>Informationer</h4>";
      html += cb("vis_benzin", "Benzin (95/100-oktan)", this._bool("vis_benzin", true));
      html += cb("vis_diesel", "Diesel", this._bool("vis_diesel", false));
      html += cb("vis_el", "El (kr/kWh)", this._bool("vis_el", true));
      html += cb("vis_ladeoversigt", "Ladesteder (popup pr. selskab)", this._bool("vis_ladeoversigt", true));
      html += cb("vis_andet", "Andet (billigst, fuld tank, position)", this._bool("vis_andet", true));
      html += "<h4>Tank- og ladeselskaber (alle forvalgt)</h4>";
      for (var i = 0; i < BRANDS.length; i++) {
        var b = BRANDS[i];
        var on = !(c.kaeder && c.kaeder[b.key] === false);
        html += cb("kæde:" + b.key, b.brand, on);
      }
      html += "<h4>Biler (katalog, tank, telefon)</h4>";
      this._loadKatalog();
      var biler = Array.isArray(c.biler) && c.biler.length ? c.biler : [{ navn: "Bil 1" }];
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
      for (var bi2 = 0; bi2 < biler.length; bi2++) {
        var bb = biler[bi2] || {};
        html += '<div class="trfe-car"><b>' + esc(bb.navn || ("Bil " + (bi2 + 1))) + "</b>";
        html += '<div class="trfe-hint">Mærke (fra katalog)</div><select data-key="bil:' + bi2 + ':mærke">';
        html += '<option value="">Manuel indtastning…</option>';
        for (var mi = 0; mi < katBrands.length; mi++) {
          html += '<option value="' + esc(katBrands[mi].mærke) + '"' +
            (bb.mærke === katBrands[mi].mærke ? " selected" : "") + ">" + esc(katBrands[mi].mærke) + "</option>";
        }
        html += "</select>";
        var katModels = bb.mærke ? this._katalogModels(bb.mærke) : [];
        var dlmId = "trf-models-" + bi2;
        var dlm = '<datalist id="' + dlmId + '">';
        for (var mj = 0; mj < katModels.length; mj++) {
          var _mm0 = katModels[mj];
          dlm += '<option value="' + esc(_mm0.model) + '">' +
            esc(_mm0.model + " · " + _mm0.brændstof + (_mm0.tank_l != null ? " · " + _mm0.tank_l + " L" : "")) + "</option>";
        }
        dlm += "</datalist>";
        html += '<div class="trfe-hint">Model (forslag fra katalog — eller skriv selv)</div>' +
          '<input type="text" list="' + dlmId + '" data-key="bil:' + bi2 + ':model" value="' +
          esc(bb.model || "") + '" placeholder="fx up!" ' + (katModels.length ? "" : 'disabled title="Vælg mærke først"') + ">" + dlm;
        var bfuel = bb.brændstof || "";
        html += '<div class="trfe-hint">Drivmiddel (sætter fornuftig visning)</div><div class="trfe-row">';
        for (var fi = 0; fi < fuels.length; fi++) {
          html += '<label><input type="radio" name="trf-fuel-' + bi2 + '" data-key="bil:' + bi2 + ':brændstof" value="' +
            fuels[fi][0] + '"' + (bfuel === fuels[fi][0] ? " checked" : "") + "><span>" + fuels[fi][1] + "</span></label>";
        }
        html += "</div>";
        html += '<div class="trfe-hint">Navn</div><input type="text" data-key="bil:' + bi2 + ':navn" value="' +
          esc(bb.navn || "") + '" placeholder="Bil 1">';
        html += '<div class="trfe-hint">Tank (L — fra katalog, ret ved behov)</div><input type="number" data-key="bil:' + bi2 +
          ':tank_liters" min="5" max="200" step="1" value="' +
          esc(bb.tank_liters !== undefined && bb.tank_liters !== null ? bb.tank_liters : "") + '" placeholder="Auto">';
        html += '<div class="trfe-hint">Batteri (kWh — kun elbil, fra katalog)</div><input type="number" data-key="bil:' + bi2 +
          ':batteri_kwh" min="10" max="200" step="1" value="' +
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
        html += '<div class="trfe-hint">Vis for denne bil</div>';
        html += cbv("benzin", "Benzin", gB) + cbv("diesel", "Diesel", gD) +
          cbv("el", "El", gE) + cbv("andet", "Andet", gA);
        if (biler.length > 1 || (c.biler && c.biler.length)) {
          html += '<div class="trfe-hint"><a href="#" data-bil-del="' + bi2 + '">Fjern bilen</a></div>';
        }
        html += "</div>";
      }
      html += '<div class="trfe-hint"><a href="#" data-bil-add>Tilføj bil</a> · tankstørrelser er vejledende — kontroller mod instruktionsbogen</div>' + dl;
      html += "<h4>Bilkatalog (mærker/modeller)</h4>";
      html += '<div class="trfe-hint">Katalogkilde (tom = indbygget: ' +
        this._katalogBrands().length + ' mærker)</div><input type="text" data-key="katalog_url" value="' +
        esc(c.katalog_url || "") + '" placeholder="/tiny_refuel/static/bilkatalog.json">';
      html += '<div class="trfe-hint">Peg på en anden JSON i samme format {brands:[{mærke, modeller:[{model, brændstof, tank_l, batteri_kwh}]}]} for at udvide — fx din egen fil under www/. Indlæses hver gang editoren åbnes.</div>';
      html += "<h4>Fælles tankstørrelse (bruges hvis bilen ikke har egen)</h4>";
      var tl = (c.tank_liters !== undefined && c.tank_liters !== null) ? c.tank_liters : "";
      html += '<div class="trfe-row"><input type="number" data-key="tank_liters" min="5" max="200" step="1" value="' +
        esc(tl) + '" placeholder="Auto"></div>';
      html += '<div class="trfe-hint">Tom = bruger Tankstørrelse-helperen (' +
        "pt. " + esc(String((this._hass && this._hass.states["input_number.tankstorrelse"] || {}).state || "?")) +
        " L). Bruges til fuld-tank-beregningen.</div>";
      html += "<h4>Navigation (tryk på logo)</h4>";
      var nv = c.navigation || "waze";
      html += '<label><input type="radio" name="trf-nav" data-key="navigation" value="waze"' +
        (nv === "waze" ? " checked" : "") + "><span>Waze</span></label>";
      html += '<label><input type="radio" name="trf-nav" data-key="navigation" value="google"' +
        (nv === "google" ? " checked" : "") + "><span>Google Maps</span></label>";
      html += '<div class="trfe-hint">Åbner navigation til den nærmeste station ved tryk på logo.</div>';
      html += '<h4>Scrape alle data</h4><div class="trfe-hint">Tiny Refuel-integrationen opdaterer alle selskaber med én handling. Automatisk interval vælges, når integrationen tilføjes under Enheder og tjenester.</div>';
      html += "<details><summary>Avanceret</summary>";
      html += '<div class="trfe-hint">Positions-enhed</div><input type="text" data-key="location_entity" value="' +
        esc(c.location_entity || "") + '" placeholder="device_tracker.din_telefon">';
      html += '<div class="trfe-hint">Notifikations-service til ⟳-knap</div><input type="text" data-key="notify_service" value="' +
        esc(c.notify_service || "") + '" placeholder="notify.mobile_app_din_telefon">';
      html += "</details></div>";
      this.innerHTML = html;
    }
  }

  customElements.define("tiny-refuel-card-editor", TinyRefuelCardEditor);
  window.TinyRefuelCardEditor = TinyRefuelCardEditor;
}(window);
