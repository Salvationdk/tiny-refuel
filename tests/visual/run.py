"""Real HA + Chromium smoke tests and screenshots, using synthetic source data.

Run from any directory with Python 3.14 and requirements.txt installed.
No real account, source scraper, location or Home Assistant installation is used.
"""
import json
import hashlib
import os
from pathlib import Path
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
import shutil
import subprocess
import sys
import tempfile
import time

import requests
import yaml
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "visual-results"
BASE = "http://127.0.0.1:8123"
CAR = {"navn": "Familiebil", "mærke": "Volkswagen", "model": "up!",
       "brændstof": "benzin", "tank_liters": 35, "location_entity": "device_tracker.visual"}
CONFIG = {"type": "custom:tiny-refuel-card", "biler": [CAR], "vis_el": False}
BRANDS = ["Circle K", "Ingo", "F24", "Q8", "Go'on", "Shell", "Uno-X", "OK", "OIL"]
FIXTURE = {
    "project": "Tiny Refuel", "version": "0.2.2", "scraper_version": "0.2.2",
    "updated": "2026-10-18T12:00:00+00:00", "errors": [],
    "stations": [{"brand": brand, "name": brand + " Teststation", "address": "Eksempelvej " + str(i+1),
                  "lat": 55.67 + i*.005, "lon": 12.56, "p95": 14.19+i*.1,
                  "p100": 16.19+i*.1, "diesel": 13.09+i*.1}
                 for i, brand in enumerate(BRANDS)],
    "ev": [{"brand": brand, "name": brand + " Testlader", "address": "Ladevej " + str(i+1),
            "lat": 55.67+i*.005, "lon": 12.56, "kind": "DC", "kwh": 2.49+i*.2,
            "location_id": "test-" + str(i)}
           for i, brand in enumerate(["OK", "Q8", "Circle K", "Clever", "E.ON", "Ionity"])],
    "fuel_sources": {}, "ev_sources": {}, "benefits": {}, "geocode_pending": 0,
}
FIXTURE["ev_sources"] = {key: {"status": "ok", "last_success": FIXTURE["updated"]}
                         for key in ["clever", "eon", "ionity", "ok", "oil", "shell", "circle_k", "q8"]}
FIXTURE["fuel_sources"] = {key: {"status": "ok", "last_success": FIXTURE["updated"], "records": count, "priced": count, "missing_coordinates": 0}
                           for key, count in [("api.circlek.com", 2), ("f24.dk", 2), ("goon.nu", 1), ("unoxmobility.dk", 1), ("shellservice.dk", 1), ("mobility-prices.ok.dk", 1), ("oil-fuel-api", 1)]}


def prepare(folder):
    storage = folder / ".storage"
    storage.mkdir()
    # Core configuration is supplied below. Skip optional onboarding discovery
    # (weather/radio/translation) so screenshots never need those services.
    (storage / "onboarding").write_text(json.dumps({
        "version": 4, "minor_version": 1, "key": "onboarding",
        "data": {"done": ["core_config", "analytics", "integration"]},
    }))
    custom = folder / "custom_components"
    custom.mkdir()
    shutil.copytree(ROOT / "custom_components/tiny_refuel", custom / "tiny_refuel")
    # Inject fixed source data only into the disposable copy, never the repository.
    manager = custom / "tiny_refuel/manager.py"
    payload = json.dumps(json.dumps(FIXTURE))
    manager.write_text(manager.read_text() + '\n\ndef _visual_refresh(self, fuel_types=None):\n    import json\n    self.data = json.loads(' + payload + ')\n    self._notify()\n\nRefuelManager.start_refresh = _visual_refresh\n')
    # Exercise the real downloader/cache/API against deterministic catalog bytes.
    bundled = json.loads((ROOT / "custom_components/tiny_refuel/frontend/katalog.json").read_text())
    names = {"personbil":"car.json", "varebil":"van.json", "lastbil":"truck.json", "motorcykel":"motorcycle.json", "knallert":"moped.json", "bus":"bus.json", "traktor":"tractor.json", "andet":"other.json"}
    payloads = {}
    index = {"schema_version":1, "version":"visual-fixture", "catalogs":{}}
    for kind, filename in names.items():
        brands = []
        for brand in bundled["brands"]:
            models = [m for m in brand["modeller"] if kind in [("varebil" if t=="varevogn" else t) for t in m.get("vehicle_types",[])]]
            if models: brands.append({**brand,"modeller":models})
        raw = json.dumps({"vehicle_type":kind,"brands":brands},ensure_ascii=False)
        payloads[filename] = raw
        index["catalogs"][kind] = {"file":filename,"size_bytes":len(raw.encode()),"sha256":hashlib.sha256(raw.encode()).hexdigest()}
    payloads["index.json"] = json.dumps(index)
    store = custom / "tiny_refuel/catalog_store.py"
    store.write_text(store.read_text() + "\n_visual_payloads = " + repr(payloads) + "\n" +
        "_original_catalog_init = CatalogStore.__init__\n" +
        "async def _visual_fetch(url, limit):\n    return _visual_payloads[url.rsplit('/',1)[-1]].encode()\n" +
        "def _visual_init(self, directory, fetch_bytes, bundled_catalog, base_url=CATALOG_BASE):\n    _original_catalog_init(self,directory,_visual_fetch,bundled_catalog,base_url)\n" +
        "CatalogStore.__init__ = _visual_init\n")
    (folder / "configuration.yaml").write_text(yaml.safe_dump({
        "homeassistant": {"name": "Tiny Refuel visuel test", "latitude": 55.67,
                          "longitude": 12.56, "elevation": 0, "unit_system": "metric", "time_zone": "Europe/Copenhagen"},
        "http": {"server_host": "127.0.0.1"}, "frontend": {},
        "recorder": {"purge_keep_days": 1, "commit_interval": 1},
        "lovelace": {"mode": "storage"},
    }))
    (storage / "lovelace").write_text(json.dumps({"version": 1, "minor_version": 1, "key": "lovelace",
        "data": {"config": {"title": "Tiny Refuel", "views": [{"title": "Test", "path": "test", "cards": [CONFIG]}, {"title":"Stationskort","path":"stationer","cards":[{"type":"map","title":"Stationer","geo_location_sources":["tiny_refuel"],"default_zoom":11,"auto_fit":True}]}]}}}, ensure_ascii=False))


def api(session, path, data):
    response = session.post(BASE + path, json=data, timeout=45)
    response.raise_for_status()
    return response.json()


def websocket_messages(payload):
    """HA may coalesce multiple response messages into one WebSocket frame."""
    try:
        decoded = json.loads(payload)
    except (ValueError, TypeError):
        return []
    return [item for item in (decoded if isinstance(decoded, list) else [decoded]) if isinstance(item, dict)]


def onboard(folder):
    session = requests.Session()
    for _ in range(240):
        try:
            response = session.get(BASE + "/api/onboarding", timeout=2)
            if response.ok:
                break
        except requests.RequestException:
            pass
        time.sleep(1)
    else:
        raise RuntimeError("Home Assistant did not start within four minutes")
    code = api(session, "/api/onboarding/users", {
        "name": "Visual test", "username": "visual", "password": secrets.token_urlsafe(32),
        "client_id": BASE + "/", "language": "da",
    })["auth_code"]
    response = session.post(BASE + "/auth/token", data={
        "grant_type": "authorization_code", "code": code, "client_id": BASE + "/",
    }, timeout=30)
    response.raise_for_status()
    tokens = response.json()
    tokens.update({"hassUrl": BASE, "clientId": BASE + "/", "expires": time.time()*1000 + tokens["expires_in"]*1000})
    session.headers["Authorization"] = "Bearer " + tokens["access_token"]
    for _ in range(90):
        response = session.get(BASE + "/api/config", timeout=10)
        if response.ok and {"frontend", "recorder"}.issubset(response.json().get("components", [])):
            break
        time.sleep(1)
    else:
        raise RuntimeError(f"Home Assistant frontend did not finish setup: {response.status_code} {response.text[:2000]}")
    flow = api(session, "/api/config/config_entries/flow", {"handler": "tiny_refuel", "show_advanced_options": False})
    result = api(session, "/api/config/config_entries/flow/" + flow["flow_id"], {"scan_hours": 6})
    assert result["type"] == "create_entry", result
    for _ in range(60):
        response = session.get(BASE + "/api/tiny_refuel/data", timeout=10)
        if response.ok and response.json().get("stations"):
            break
        time.sleep(1)
    else:
        raise RuntimeError(f"Tiny Refuel config entry/API failed to load: {response.status_code} {response.text[:2000]}")
    api(session, "/api/states/device_tracker.visual", {"state": "home", "attributes": {"friendly_name": "Testposition", "latitude": 55.67, "longitude": 12.56}})
    asset = session.get(BASE + "/tiny_refuel/static/tiny-refuel-card.js", timeout=20)
    asset.raise_for_status()
    assert asset.content == (ROOT / "custom_components/tiny_refuel/frontend/tiny-refuel-card.js").read_bytes(), "HA served a different card module"
    # Exercise the actual integration options API and reload with shared vehicles.
    options = api(session, "/api/config/config_entries/options/flow", {"handler": result["result"]["entry_id"]})
    options = api(session, "/api/config/config_entries/options/flow/" + options["flow_id"], {"next_step_id": "catalog_vehicle"})
    for expected_step, values in [("catalog_vehicle",{"koeretoejstype":"personbil"}),
                                  ("catalog_make",{"mærke":"Volkswagen"}),
                                  ("catalog_model",{"model":"up!"})]:
        assert options["step_id"] == expected_step, options
        options = api(session, "/api/config/config_entries/options/flow/" + options["flow_id"], values)
    assert options["step_id"] == "vehicle", options
    defaults = {field["name"]:field.get("default") for field in options["data_schema"]}
    assert defaults.get("tank_liters") == 35, defaults
    options = api(session, "/api/config/config_entries/options/flow/" + options["flow_id"], {
        "navn": "Fælles testbil", "mærke": "Volkswagen", "model": "up!", "brændstof": "benzin",
        "tank_liters": 35, "koeretoejstype":"personbil", "location_entity": "device_tracker.visual"})
    assert options["type"] == "create_entry", options
    for _ in range(60):
        data = session.get(BASE + "/api/tiny_refuel/data", timeout=10)
        if data.ok and data.json().get("vehicles"):
            break
        time.sleep(1)
    else:
        raise RuntimeError("Shared vehicle options did not reload")
    for _ in range(60):
        states = session.get(BASE + "/api/states", timeout=10).json()
        if any("Fælles testbil" in row.get("attributes", {}).get("friendly_name", "") and row.get("state") not in ("unknown", "unavailable") for row in states):
            break
        time.sleep(1)
    else:
        raise RuntimeError("No shared vehicle entity produced a usable state")
    status = next(row for row in states if row.get("attributes",{}).get("friendly_name","").endswith("Katalogstatus"))
    assert status["state"] == "ready", status
    assert status["attributes"]["catalogs"]["personbil"]["source"] == "github", status
    assert status["attributes"]["catalogs"]["personbil"]["models"] > 0, status
    stations = session.get(BASE + "/api/tiny_refuel/stations", timeout=10)
    stations.raise_for_status()
    rows = stations.json()["stations"]
    assert len(rows) == len(FIXTURE["stations"])+len(FIXTURE["ev"]), rows
    tokens["testStationId"] = next(row["id"] for row in rows if row["brand"]=="Q8" and row["kind"]=="fuel")
    # Seed fixed history only in the disposable HA directory. Recorder contracts
    # are exercised separately; this checks the real authenticated read API/chart.
    with sqlite3.connect(folder / ".storage/tiny_refuel/price-history.sqlite3") as db:
        db.execute("CREATE TABLE IF NOT EXISTS prices (station TEXT NOT NULL,field TEXT NOT NULL,at TEXT NOT NULL,value REAL NOT NULL,PRIMARY KEY(station,field,at))")
        now=datetime.now(timezone.utc)
        for days, value in [(3,14.79),(2,14.59),(1,14.49)]:
            db.execute("INSERT INTO prices VALUES (?,?,?,?)",(tokens["testStationId"],"p95",(now-timedelta(days=days)).isoformat(),value))
    history=session.get(BASE + "/api/tiny_refuel/history/"+tokens["testStationId"]+"?field=p95&days=7",timeout=10)
    history.raise_for_status()
    assert len(history.json()["points"])==3,history.text
    options=api(session,"/api/config/config_entries/options/flow",{"handler":result["result"]["entry_id"]})
    options=api(session,"/api/config/config_entries/options/flow/"+options["flow_id"],{"next_step_id":"map"})
    options=api(session,"/api/config/config_entries/options/flow/"+options["flow_id"],{
        "map_enabled":True,"map_radius_km":25,"map_limit":5,"map_brands":[],
        "map_selected_only":False,"map_location_entity":"device_tracker.visual"})
    assert options["type"]=="create_entry",options
    for _ in range(60):
        states=session.get(BASE+"/api/states",timeout=10).json()
        markers=[row for row in states if row['entity_id'].startswith('geo_location.') and row.get('attributes',{}).get('source')=='tiny_refuel']
        if len(markers)==5:break
        time.sleep(1)
    else:raise RuntimeError("Native map entities were not created")
    summary=session.get(BASE+"/api/tiny_refuel/dashboard",timeout=10);summary.raise_for_status()
    assert summary.json()['map']['count']==5,summary.text
    assert summary.json()['vehicles'][0]['navn']=='Fælles testbil',summary.text
    # Exercise response actions through the real authenticated HA service API.
    def query_action(name, data):
        response=session.post(BASE+"/api/services/tiny_refuel/"+name+"?return_response",
                              json=data,timeout=30)
        response.raise_for_status()
        return response.json()["service_response"]
    metadata=query_action("get_data",{})
    assert "stations" in metadata["sections"],metadata
    selected=query_action("get_stations",{"fuel":"p95","sort":"price","limit":1})
    assert len(selected["items"])==1 and selected["items"][0]["current"],selected
    assert query_action("get_vehicles",{})["items"][0]["tank_liters"]==35
    assert query_action("get_status",{})["map"]["count"]==5
    assert len(query_action("get_history",{"station_id":tokens["testStationId"],"fuel":"p95","days":7})["points"])==3
    catalog=query_action("get_catalog",{"vehicle_type":"personbil","make":"Volkswagen","search":"up!"})
    assert any(item["model"]["model"]=="up!" for item in catalog["items"]),catalog
    options=api(session,"/api/config/config_entries/options/flow",{"handler":result["result"]["entry_id"]})
    options=api(session,"/api/config/config_entries/options/flow/"+options["flow_id"],{"next_step_id":"station_sensors"})
    assert options["type"]=="form",options
    options=api(session,"/api/config/config_entries/options/flow/"+options["flow_id"],
                {"station_sensor_ids":[tokens["testStationId"]]})
    assert options["type"]=="create_entry",options
    for _ in range(60):
        states=session.get(BASE+"/api/states",timeout=10).json()
        prices=[state for state in states if state.get("attributes",{}).get("station_id")==tokens["testStationId"]
                and state.get("attributes",{}).get("fuel")=="p95"]
        if prices and prices[0]["state"] not in ("unknown","unavailable"):
            tokens["testPriceEntity"]=prices[0]["entity_id"]
            break
        time.sleep(1)
    else:raise RuntimeError("Selected station price entity did not become usable")
    assert float(prices[0]["state"])>0
    tokens["testEntryId"] = result["result"]["entry_id"]
    return tokens


def browsers(tokens):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        context = browser.new_context(locale="da-DK", timezone_id="Europe/Copenhagen", reduced_motion="reduce")
        context.add_init_script("localStorage.setItem('hassTokens', " + json.dumps(json.dumps(tokens)) + ");localStorage.setItem('selectedLanguage','\"da\"');")
        context.add_init_script("window.addEventListener('unhandledrejection',e=>{let r=e.reason;window.visualReportRejection(typeof r==='object'?JSON.stringify(r,Object.getOwnPropertyNames(r)):String(r)).catch(()=>{});});")
        page = context.new_page()
        errors = []
        rejections = []
        failed_requests = []
        page.on("response", lambda response: failed_requests.append({"status": response.status, "url": response.url}) if response.status >= 400 else None)
        websocket_errors = []
        def watch_socket(socket):
            commands = {}
            def sent(payload):
                for message in websocket_messages(payload):
                    if "id" in message:
                        commands[message["id"]] = message.get("type")
            def received(payload):
                for message in websocket_messages(payload):
                    if message.get("success") is False:
                        websocket_errors.append({"command": commands.get(message.get("id")), "error": message.get("error")})
            socket.on("framesent", sent)
            socket.on("framereceived", received)
        page.on("websocket", watch_socket)
        page.expose_function("visualReportRejection", lambda message: rejections.append(message))
        page.on("pageerror", lambda error: errors.append({"message": str(error), "stack": error.stack}))
        page.goto(BASE + "/lovelace/test")
        # HA 2026.10 asks the test owner to confirm the localhost HTTP binding.
        # Resolve that real setup dialog before taking pictures or clicking cards.
        pending = page.locator("dialog-http-pending-config")
        confirm = pending.locator('ha-button[slot="primaryAction"]')
        expect(confirm).to_be_visible(timeout=30000)
        confirm.click()
        expect(confirm).not_to_be_visible(timeout=15000)
        page.reload()
        card = page.locator("tiny-refuel-card").first
        try:
            page.wait_for_function("customElements.get('tiny-refuel-card') !== undefined", timeout=30000)
            expect(card.locator(".trf-row").first).to_be_visible(timeout=90000)
        except Exception:
            diagnostics = {"errors": errors, "rejections": rejections, "websocket_errors": websocket_errors,
                           "card_errors": page.locator("hui-error-card").all_text_contents(), "failed_requests": failed_requests}
            (OUT / "browser-diagnostics.json").write_text(json.dumps(diagnostics, indent=2))
            print(diagnostics, flush=True)
            page.screenshot(path=str(OUT / "startup-failure.png"), full_page=True)
            raise
        page.wait_for_function("customElements.get('tiny-refuel-card-editor') !== undefined")
        def set_theme(dark):
            # Change HA's real default theme as well as the browser preference.
            page.evaluate("dark => document.querySelector('home-assistant').dispatchEvent(new CustomEvent('settheme', {detail:{theme:'default',dark},bubbles:true,composed:true}))", dark)
            page.emulate_media(color_scheme="dark" if dark else "light")
            page.wait_for_function("dark => document.querySelector('home-assistant').hass.themes.darkMode === dark", arg=dark)
            page.wait_for_timeout(300)

        def paired_page_shots(name, full_page=False):
            for dark in [False, True]:
                set_theme(dark)
                theme = "dark" if dark else "light"
                filename = "desktop-" + theme + "-" + name
                page.screenshot(path=str(OUT / (filename + ".png")), full_page=full_page, animations="disabled")
                results.append(filename)
            set_theme(False)

        set_theme(False)
        # Native Lovelace entry, save, reload and reopen; no manually added resource.
        page.set_viewport_size({"width": 1280, "height": 1000})
        page.goto(BASE + "/lovelace/test?edit=1")
        options = page.locator("hui-card-options").first
        expect(options).to_be_visible(timeout=30000)
        options.locator("ha-button").first.click()
        dialog = page.locator("hui-dialog-edit-card")
        native_editor = dialog.locator("tiny-refuel-card-editor")
        expect(native_editor).to_be_visible(timeout=30000)
        vehicle = native_editor.locator('[data-car-card="0"]')
        if not vehicle.evaluate("el => el.open"):
            vehicle.locator("summary").first.click()
        tank = native_editor.locator('[data-key="bil:0:tank_liters"]')
        tank.fill("36")
        tank.dispatch_event("change")
        paired_page_shots("native-editor-save")
        dialog.locator('ha-button[slot="primaryAction"]').click()
        expect(native_editor).not_to_be_visible(timeout=15000)
        page.goto(BASE + "/lovelace/test?edit=1")
        page.locator("hui-card-options").first.locator("ha-button").first.click()
        expect(native_editor).to_be_visible(timeout=30000)
        vehicle = native_editor.locator('[data-car-card="0"]')
        if not vehicle.evaluate("el => el.open"):
            vehicle.locator("summary").first.click()
        expect(native_editor.locator('[data-key="bil:0:tank_liters"]')).to_have_value("36")
        native_editor.locator('[data-key="bil:0:tank_liters"]').fill("35")
        native_editor.locator('[data-key="bil:0:tank_liters"]').dispatch_event("change")
        dialog.locator('ha-button[slot="primaryAction"]').click()
        expect(native_editor).not_to_be_visible(timeout=15000)
        page.goto(BASE + "/lovelace/test")
        expect(card.locator(".trf")).to_be_visible(timeout=30000)
        # Retain the real HA object and card for deterministic scenario changes.
        card.evaluate("el => {window.visualCard = el; window.visualHass = el._hass;}")

        def set_config(config):
            page.evaluate("config => window.visualCard.setConfig(config)", config)
            expect(card.locator(".trf")).to_be_visible()

        def shot(name, target=card):
            target.scroll_into_view_if_needed()
            page.evaluate("document.fonts.ready")
            target.screenshot(path=str(OUT / (name + ".png")), animations="disabled",
                              style="app-header, app-toolbar, ha-toast { visibility: hidden !important; }")
            results.append(name)

        for width, label in [(1280, "desktop"), (390, "mobile")]:
            page.set_viewport_size({"width": width, "height": 2400})
            for dark in [False, True]:
                theme = "dark" if dark else "light"
                set_theme(dark)
                prefix = label + "-" + theme
                set_config(CONFIG)
                expect(card).to_contain_text("Billigst")
                shot(prefix + "-fuel")
                set_config({**CONFIG, "kompakt": True})
                expect(card.locator(".trf-row")).to_have_count(3)
                expect(card).to_contain_text("Billigst 95")
                shot(prefix + "-compact")
                card.locator('[data-more-stations="fuel"]').click()
                expect(card.locator(".trf-row")).to_have_count(9)
                card.locator('[data-fewer-stations="fuel"]').click()
                expect(card.locator(".trf-row")).to_have_count(3)
                diesel = {**CAR, "navn": "Dieselvarevogn", "model": "Transporter", "brændstof": "diesel", "tank_liters": 70, "koeretoejstype": "varevogn"}
                set_config({**CONFIG, "vis_benzin": False, "vis_diesel": True, "biler": [diesel]})
                expect(card).to_contain_text("Billigst Diesel")
                shot(prefix + "-diesel")
                electric = {**CAR, "navn": "Elbil", "mærke": "Aiways", "model": "U5", "brændstof": "el", "batteri_kwh": 63}
                set_config({**CONFIG, "biler": [electric], "vis_benzin": False, "vis_el": True})
                expect(card.locator(".trf-evrow").first).to_be_visible()
                if dark:
                    for logo in [card.locator(".trf-car-logo").first, card.locator('.trf-logo img[alt="Clever"]').first, card.locator('.trf-logo img[alt="Ionity"]').first]:
                        assert "brightness(0) invert(1)" in logo.evaluate("el => getComputedStyle(el).filter"), "dark logo lacks a readable white rendering"
                shot(prefix + "-charging")
                card.locator('[data-open-ev]').first.click()
                expect(card.locator("dialog[open]")).to_be_visible()
                shot(prefix + "-charging-locations", card.locator("dialog[open]"))
                card.locator('[data-close-ev]').first.click()
                hybrid = {**CAR, "navn": "Plug-in-hybrid", "model": "Golf", "tank_liters": 40, "brændstof": "plug_in_hybrid", "batteri_kwh": 13}
                set_config({**CONFIG, "vis_el": True, "biler": [hybrid, electric]})
                shot(prefix + "-hybrid")
                set_config(CONFIG)
                info = card.locator('details[data-card-panel]').filter(has_text="Information og datagrundlag").first
                info.locator("summary").click()
                shot(prefix + "-information")
                # A failed supplier must remain visible alongside retained data.
                page.evaluate("data => {window.visualCard._data = data; window.visualCard._render();}", {
                    **FIXTURE, "errors": [{"source": "clever.dk", "error": "HTTP Error 500"}],
                    "ev": [{**row, "stale": True} if row["brand"] == "Clever" else row for row in FIXTURE["ev"]],
                    "ev_sources": {**FIXTURE["ev_sources"], "clever": {"status": "stale", "last_success": FIXTURE["updated"]}},
                })
                expect(card).to_contain_text("clever.dk")
                card.locator('[data-card-panel="errors"] > summary').click()
                shot(prefix + "-source-error")
                page.evaluate("data => {window.visualCard._data = data; window.visualCard._render();}", FIXTURE)

                # Render the production editor using real HA state/theme; echo its config
                # events exactly as Lovelace does. This avoids relying on HA menu wording.
                page.evaluate("""config => {
                    let host = document.createElement('div'); host.id='visual-editor-host';
                    host.style.cssText='position:absolute;z-index:9999;top:0;left:0;width:min(100%,600px);background:var(--card-background-color);color:var(--primary-text-color);font-family:Roboto,Arial,sans-serif';
                    let editor=document.createElement('tiny-refuel-card-editor');
                    editor.hass=window.visualCard._hass; editor.setConfig(config);
                    editor.addEventListener('config-changed', e=>editor.setConfig(e.detail.config));
                    host.append(editor); document.body.append(host); window.visualEditor=editor;
                }""", CONFIG)
                editor = page.locator("tiny-refuel-card-editor")
                expect(editor).to_contain_text("913", timeout=30000)
                shot(prefix + "-editor-overview", editor)
                editor.locator('[data-editor-section="providers"] > summary').click()
                shot(prefix + "-editor-providers", editor)
                editor.locator('[data-editor-section="providers"] > summary').click()
                vehicle = editor.locator('[data-car-card="0"]')
                if not vehicle.evaluate("el => el.open"):
                    vehicle.locator("summary").first.click()
                shot(prefix + "-editor-vehicle", editor)
                make = editor.locator('[data-key="bil:0:mærke"]')
                make.fill("Citroën")
                make.dispatch_event("change")
                expect(editor.locator('[data-key="bil:0:model"]')).to_have_value("")
                expect(editor.locator('[data-key="bil:0:tank_liters"]')).to_have_value("")
                model = editor.locator('[data-key="bil:0:model"]')
                model.fill("C3")
                model.dispatch_event("change")
                expect(editor.locator('[data-key="bil:0:tank_liters"]')).not_to_have_value("")
                extra = editor.locator('[data-editor-section="vehicle-extra-0"]')
                extra.locator("summary").click()
                shot(prefix + "-editor-details", editor)
                def wait_catalog(kind):
                    page.wait_for_function("kind => window.visualEditor._katalogUrlUsed === 'types:' + kind && window.visualEditor._katalogLoading === false", arg=kind)
                type_select = editor.locator('[data-key="bil:0:koeretoejstype"]')
                type_select.select_option("varebil")
                wait_catalog("varebil")
                expect(editor.locator('[data-key="bil:0:model"]')).to_have_value("")
                expect(editor.locator('[data-key="bil:0:tank_liters"]')).to_have_value("")
                model_values = editor.locator('[data-model-options="0"] option').evaluate_all("els => els.map(el => el.value)")
                assert "Jumper" in model_values and "C3" not in model_values
                shot(prefix + "-editor-vehicle-type", editor)
                type_select.select_option("lastbil")
                wait_catalog("lastbil")
                expect(editor.locator('[data-key="bil:0:mærke"]')).to_have_value("")
                expect(editor.locator('[data-make-options="0"] option')).to_have_count(3)
                assert 'Citroën' not in editor.locator('[data-make-options="0"] option').evaluate_all('els => els.map(el => el.value)')
                for category, brand, name, field, capacity in [
                    ("lastbil", "Volvo", "FH Electric (540 kWh-konfiguration)", "batteri_kwh", "460"),
                    ("bus", "Mercedes", "eCitaro G NMC3 (7 batteripakker)", "batteri_kwh", "686"),
                    ("motorcykel", "Honda", "CB500 Hornet", "tank_liters", "17.1"),
                    ("knallert", "Piaggio", "Zip 50 i-get Special Edition", "tank_liters", "6.6"),
                    ("traktor", "John Deere", "6M 150 (205 L-konfiguration)", "tank_liters", "205"),
                    ("andet", "Polaris", "Ranger 1000 (2025, terrænmodel)", "tank_liters", "43"),
                ]:
                    type_select.select_option(category)
                    wait_catalog(category)
                    make = editor.locator('[data-key="bil:0:mærke"]')
                    make.fill(brand)
                    make.dispatch_event("change")
                    model = editor.locator('[data-key="bil:0:model"]')
                    model.fill(name)
                    model.dispatch_event("change")
                    expect(editor.locator('[data-key="bil:0:' + field + '"]')).to_have_value(capacity)
                shot(prefix + "-editor-expanded-catalog", editor)
                type_select.select_option("personbil")
                wait_catalog("personbil")
                make = editor.locator('[data-key="bil:0:mærke"]')
                make.fill("Volkswagen")
                make.dispatch_event("change")
                model_values = editor.locator('[data-model-options="0"] option').evaluate_all("els => els.map(el => el.value)")
                assert "up!" in model_values and "Caddy Cargo" not in model_values
                page.locator("#visual-editor-host").evaluate("el => el.remove()")
                # Optional station cards keep the existing vehicle card intact.
                page.wait_for_function("customElements.get('tiny-refuel-prices-card') !== undefined")
                page.evaluate("""id => {
                    const host=document.createElement('div'); host.id='station-card-test';
                    host.style.cssText='position:absolute;z-index:9999;top:0;left:0;width:min(100%,600px);background:var(--card-background-color);font-family:Roboto,Arial,sans-serif';
                    document.querySelector('home-assistant').shadowRoot.append(host);window.stationTestHost=host;
                    window.stationTestConfig={type:'custom:tiny-refuel-prices-card',fuel:'p95',limit:4};
                    window.stationTestCard=document.createElement('tiny-refuel-prices-card');
                    window.stationTestCard.setConfig(window.stationTestConfig);window.stationTestCard.hass=window.visualCard._hass;
                    host.append(window.stationTestCard);
                }""",tokens["testStationId"])
                price_card=page.locator('tiny-refuel-prices-card')
                expect(price_card.locator('.ts-station')).to_have_count(4)
                price_card.locator('[data-search]').fill('Q8')
                expect(price_card.locator('.ts-station')).to_have_count(1)
                shot(prefix+'-station-prices',price_card)
                price_card.locator('[data-fuel]').select_option('kwh')
                expect(price_card.locator('.ts-price small')).to_contain_text('kWh')
                page.evaluate("""id=>{
                    const host=window.stationTestHost;host.replaceChildren();
                    const card=document.createElement('tiny-refuel-station-card');
                    card.setConfig({type:'custom:tiny-refuel-station-card',station_id:id,fuel:'all'});
                    card.hass=window.visualCard._hass;host.append(card);
                }""",tokens["testStationId"])
                single=page.locator('tiny-refuel-station-card')
                expect(single.locator('.ts-station')).to_have_count(1)
                single.locator('.ts-history > summary').click()
                expect(single.locator('.ts-history svg')).to_be_visible()
                expect(single.locator('.ts-history tbody tr')).to_have_count(3)
                shot(prefix+'-station-history',single)
                page.evaluate("""id=>{
                    const host=window.stationTestHost;host.replaceChildren();
                    const card=document.createElement('tiny-refuel-favorites-card');
                    card.setConfig({type:'custom:tiny-refuel-favorites-card',favorites:[id],fuel:'all'});
                    card.hass=window.visualCard._hass;host.append(card);
                }""",tokens["testStationId"])
                favorites=page.locator('tiny-refuel-favorites-card')
                expect(favorites.locator('.ts-station')).to_have_count(1)
                shot(prefix+'-station-favorites',favorites)
                page.evaluate("""id=>{
                    const host=window.stationTestHost;host.replaceChildren();
                    const editor=document.createElement('tiny-refuel-stations-editor');
                    editor.setConfig({type:'custom:tiny-refuel-favorites-card',favorites:[id],fuel:'all'});
                    editor.hass=window.visualCard._hass;
                    editor.addEventListener('config-changed',e=>window.stationSavedConfig=e.detail.config);
                    host.append(editor);
                }""",tokens["testStationId"])
                station_editor=page.locator('tiny-refuel-stations-editor')
                expect(station_editor.locator('[data-favorite]')).to_have_count(15)
                station_editor.locator('[data-filter]').fill('Q8')
                expect(station_editor.locator('[data-favorite]')).to_have_count(2)
                station_editor.locator('[data-favorite]').first.set_checked(True)
                station_editor.locator('[data-key="title"]').fill('Mine lokale priser')
                station_editor.locator('[data-key="title"]').dispatch_event('change')
                assert page.evaluate("window.stationSavedConfig.title")=='Mine lokale priser'
                shot(prefix+'-station-editor',station_editor)
                page.locator('#station-card-test').evaluate('el=>el.remove()')
                page.wait_for_function("customElements.get('tiny-refuel-vehicles-card') !== undefined")
                for type_, marker in [('vehicles','.td-car'),('comparison','.td-table'),('vehicle-details','.td-kv'),('status','[data-collect]'),('charging','.ts-station')]:
                    page.evaluate("""type=>{
                        const host=document.createElement('div');host.id='dashboard-card-test';
                        host.style.cssText='position:absolute;z-index:9999;top:0;left:0;width:min(100%,600px);background:var(--card-background-color);font-family:Roboto,Arial,sans-serif';
                        document.querySelector('home-assistant').shadowRoot.append(host);
                        const card=document.createElement('tiny-refuel-'+type+'-card');
                        card.setConfig({type:'custom:tiny-refuel-'+type+'-card',limit:4,sort:'price'});
                        card.hass=window.visualCard._hass;host.append(card);window.extraTestCard=card;
                    }""",type_)
                    extra_card=page.locator('tiny-refuel-'+type_+'-card')
                    expect(extra_card.locator(marker).first).to_be_visible(timeout=30000)
                    if type_=='comparison':
                        expect(extra_card).to_contain_text('496,65')
                    if type_=='charging':
                        extra_card.evaluate("el=>{el._data={...el._data,tariffs:[{brand:'OK',name:'Generel normal',kwh:3.49,current:true}]};el._render();}")
                        expect(extra_card).to_contain_text('Generelle selskabstakster')
                        expect(extra_card.locator('[data-fuel]')).to_have_value('kwh')
                    assert extra_card.evaluate('el=>el.scrollWidth<=el.clientWidth+1')
                    shot(prefix+'-dashboard-'+type_,extra_card)
                    page.locator('#dashboard-card-test').evaluate('el=>el.remove()')
                page.evaluate("""async entity=>{
                    const host=document.createElement('div');host.id='native-price-card-test';
                    host.style.cssText='position:absolute;z-index:9999;top:0;left:0;width:min(100%,600px);background:var(--card-background-color)';
                    document.querySelector('home-assistant').shadowRoot.append(host);
                    const helpers=await window.loadCardHelpers();
                    const card=helpers.createCardElement({type:'entities',title:'Tiny Refuel · Egne kort',entities:[entity]});
                    card.hass=window.visualCard._hass;host.append(card);
                }""",tokens["testPriceEntity"])
                native_card=page.locator('#native-price-card-test')
                expect(native_card.locator('hui-entities-card')).to_contain_text('Tiny Refuel · Egne kort')
                shot(prefix+'-native-entities-prices',native_card)
                native_card.evaluate('el=>el.remove()')
                for kind in ['comparison','charging']:
                    page.evaluate("""kind=>{
                        const host=document.createElement('div');host.id='dashboard-editor-test';
                        host.style.cssText='position:absolute;z-index:9999;top:0;left:0;width:min(100%,600px);background:var(--card-background-color);font-family:Roboto,Arial,sans-serif';
                        document.querySelector('home-assistant').shadowRoot.append(host);
                        const editor=document.createElement(kind==='charging'?'tiny-refuel-charging-editor':'tiny-refuel-dashboard-editor');
                        editor.setConfig({type:'custom:tiny-refuel-'+kind+'-card'});editor.hass=window.visualCard._hass;
                        editor.addEventListener('config-changed',e=>{window.extraSavedConfig=e.detail.config;editor.setConfig(e.detail.config);});
                        host.append(editor);
                    }""",kind)
                    extra_editor=page.locator('tiny-refuel-charging-editor' if kind=='charging' else 'tiny-refuel-dashboard-editor')
                    if kind=='comparison':
                        expect(extra_editor.locator('[data-key="vehicle_id"] option')).to_have_count(2)
                    extra_editor.locator('[data-key="title"]').fill('Mit ekstra kort')
                    extra_editor.locator('[data-key="title"]').dispatch_event('change')
                    assert page.evaluate('window.extraSavedConfig.title')=='Mit ekstra kort'
                    shot(prefix+'-dashboard-'+kind+'-editor',extra_editor)
                    page.locator('#dashboard-editor-test').evaluate('el=>el.remove()')
                assert card.evaluate("el => el.scrollWidth <= el.clientWidth + 1"), prefix + " horizontal overflow"
        # Empty shared list: use the real Lovelace websocket to discover the old card.
        page.evaluate("""()=>{
            const original=window.visualCard._hass;
            const hass=new Proxy(original,{get(target,key){
                if(key==='connection')return window.legacyVehicleConnection||(window.legacyVehicleConnection={});
                if(key==='callApi')return async(method,path,...args)=>{
                    const data=await target.callApi(method,path,...args);
                    return path==='tiny_refuel/dashboard'?{...data,vehicles:[]}:data;
                };
                const value=target[key];return typeof value==='function'?value.bind(target):value;
            }});
            const host=document.createElement('div');host.id='legacy-vehicles-test';
            document.querySelector('home-assistant').shadowRoot.append(host);
            const config={type:'custom:tiny-refuel-vehicle-details-card'};
            const card=document.createElement('tiny-refuel-vehicle-details-card');
            card.setConfig(config);card.hass=hass;host.append(card);
            const editor=document.createElement('tiny-refuel-dashboard-editor');
            editor.setConfig(config);editor.hass=hass;host.append(editor);
        }""")
        legacy=page.locator('#legacy-vehicles-test')
        expect(legacy.locator('tiny-refuel-vehicle-details-card .td-car')).to_contain_text('Familiebil')
        expect(legacy.locator('tiny-refuel-dashboard-editor [data-key="vehicle_id"] option')).to_have_count(2)
        assert legacy.locator('tiny-refuel-vehicle-details-card').evaluate('el=>el._selected()[0].tank_liters')==35
        legacy.evaluate('el=>el.remove()')
        page.goto(BASE + "/lovelace/stationer")
        native_map=page.locator('hui-map-card')
        expect(native_map.locator('ha-map')).to_be_visible(timeout=30000)
        assert native_map.evaluate('el=>el._filteredMapEntities.length')==5
        for width,label in [(1280,'desktop'),(390,'mobile')]:
            page.set_viewport_size({'width':width,'height':1000})
            for dark in [False,True]:
                set_theme(dark)
                shot(label+('-dark-' if dark else '-light-')+'native-station-map',native_map)
        page.set_viewport_size({"width": 1280, "height": 1000})
        page.goto(BASE + "/config/integrations/integration/tiny_refuel")
        expect(page.get_by_text("Tiny Refuel", exact=True).first).to_be_visible(timeout=30000)
        paired_page_shots("integration-settings", full_page=True)
        page.goto(BASE + "/config/entities?config_entry=" + tokens["testEntryId"])
        expect(page.locator("ha-data-table")).to_be_visible(timeout=30000)
        paired_page_shots("integration-entities", full_page=True)
        diagnostics = {"errors": errors, "rejections": rejections, "websocket_errors": websocket_errors}
        (OUT / "browser-diagnostics.json").write_text(json.dumps(diagnostics, indent=2))
        assert not errors, diagnostics
        # Every successful gallery screenshot must have its opposite-theme twin.
        assert len(results) == len(set(results)), "Duplicate screenshot names"
        names = set(results)
        for name in results:
            assert "-light-" in name or "-dark-" in name, "Missing theme: " + name
            twin = name.replace("-light-", "-dark-") if "-light-" in name else name.replace("-dark-", "-light-")
            assert twin in names, "Missing theme pair: " + twin
            assert (OUT / (twin + ".png")).is_file(), "Missing screenshot: " + twin
        browser.close()
    return sorted(results, key=lambda name: name.replace("-light-", "-theme-").replace("-dark-", "-theme-"))


def main():
    OUT.mkdir(exist_ok=True)
    # Never save HA storage, credentials or browser traces as artifacts.
    with tempfile.TemporaryDirectory(prefix="tiny-refuel-ha-") as temp:
        folder = Path(temp)
        prepare(folder)
        with (OUT / "home-assistant.log").open("w") as log:
            # Keep the checkout out of Python's custom_components namespace.
            environment = {**os.environ, "VIRTUAL_ENV": sys.prefix}
            process = subprocess.Popen([sys.executable, "-m", "homeassistant", "--config", str(folder)], cwd=folder, env=environment, stdout=log, stderr=subprocess.STDOUT)
            try:
                tokens = onboard(folder)
                screenshots = browsers(tokens)
                (OUT / "report.json").write_text(json.dumps({"status": "passed", "home_assistant": "2026.10.0", "screenshots": screenshots,
                    "data": "Synthetic station prices and position; production integration, catalog and editor", "browser": "Chromium", "native_editor_save_reopen": True, "automatic_module_loading": True, "shared_vehicle_options": True, "themes": ["light", "dark"], "theme_pairs": len(screenshots) // 2}, indent=2))
                gallery = ''.join(f'<figure><a href="{name}.png"><img src="{name}.png" loading="lazy"></a><figcaption>{name}</figcaption></figure>' for name in screenshots)
                (OUT / "index.html").write_text('<!doctype html><html lang="da"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Tiny Refuel screenshots</title><style>body{font:16px system-ui;margin:24px;background:#eee;color:#222}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px}figure{margin:0;padding:12px;background:white;border-radius:12px}img{max-width:100%;max-height:600px;object-fit:contain;object-position:top}figcaption{margin-top:8px}</style><h1>Tiny Refuel · Home Assistant 2026.10</h1><p>Fiktive priser og position. Klik på et billede for fuld størrelse.</p><main>' + gallery + '</main></html>')
                print(f"PASS: {len(screenshots)} screenshots; real Home Assistant, desktop/mobile, light/dark")
            except Exception:
                (OUT / "report.json").write_text(json.dumps({"status": "failed", "home_assistant": "2026.10.0"}))
                print((OUT / "home-assistant.log").read_text()[-16000:])
                raise
            finally:
                process.terminate()
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


if __name__ == "__main__":
    main()

