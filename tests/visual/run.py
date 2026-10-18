"""Real HA + Chromium smoke tests and screenshots, using synthetic source data.

Run from any directory with Python 3.14 and requirements.txt installed.
No real account, source scraper, location or Home Assistant installation is used.
"""
import json
import os
from pathlib import Path
import secrets
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
    manager.write_text(manager.read_text() + '\n\ndef _visual_refresh(self, fuel_types=None):\n    import json\n    self.data = json.loads((Path(__file__).parent / "visual-data.json").read_text())\n    self._notify()\n\nRefuelManager.start_refresh = _visual_refresh\n')
    (custom / "tiny_refuel/visual-data.json").write_text(json.dumps(FIXTURE))
    (folder / "configuration.yaml").write_text(yaml.safe_dump({
        "homeassistant": {"name": "Tiny Refuel visuel test", "latitude": 55.67,
                          "longitude": 12.56, "elevation": 0, "unit_system": "metric", "time_zone": "Europe/Copenhagen"},
        "http": {"server_host": "127.0.0.1"}, "frontend": {},
        "lovelace": {"mode": "yaml"},
    }))
    (folder / "ui-lovelace.yaml").write_text(yaml.safe_dump({
        "title": "Tiny Refuel", "views": [{"title": "Test", "path": "test", "cards": [CONFIG]}],
    }, allow_unicode=True))


def api(session, path, data):
    response = session.post(BASE + path, json=data, timeout=45)
    response.raise_for_status()
    return response.json()


def onboard():
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
        if response.ok and "frontend" in response.json().get("components", []):
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
    return tokens


def browsers(tokens):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        context = browser.new_context(locale="da-DK", timezone_id="Europe/Copenhagen", reduced_motion="reduce")
        context.add_init_script("localStorage.setItem('hassTokens', " + json.dumps(json.dumps(tokens)) + ");localStorage.setItem('selectedLanguage','\"da\"');")
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(BASE + "/lovelace/test")
        card = page.locator("tiny-refuel-card").first
        try:
            expect(card.locator(".trf-row").first).to_be_visible(timeout=90000)
        except Exception:
            page.screenshot(path=str(OUT / "startup-failure.png"), full_page=True)
            raise
        # HA 2026.10 asks the test owner to confirm the localhost HTTP binding.
        # Resolve that real setup dialog before taking pictures or clicking cards.
        pending = page.locator("dialog-http-pending-config")
        expect(pending).to_be_visible(timeout=30000)
        pending.locator('ha-button[slot="primaryAction"]').click()
        expect(pending).not_to_be_visible(timeout=15000)
        page.wait_for_function("customElements.get('tiny-refuel-card-editor') !== undefined")
        # Retain the real HA object and card for deterministic scenario changes.
        card.evaluate("el => {window.visualCard = el; window.visualHass = el._hass;}")

        def set_config(config):
            page.evaluate("config => window.visualCard.setConfig(config)", config)
            expect(card.locator(".trf")).to_be_visible()

        def shot(name, target=card):
            target.scroll_into_view_if_needed()
            page.evaluate("document.fonts.ready")
            target.screenshot(path=str(OUT / (name + ".png")), animations="disabled")
            results.append(name)

        for width, label in [(1280, "desktop"), (390, "mobile")]:
            page.set_viewport_size({"width": width, "height": 1000})
            for dark in [False, True]:
                theme = "dark" if dark else "light"
                # Set actual HA theme, inherited by the card/editor.
                page.evaluate("dark => document.querySelector('home-assistant').dispatchEvent(new CustomEvent('settheme', {detail:{theme:'default',dark},bubbles:true,composed:true}))", dark)
                page.emulate_media(color_scheme=theme)
                page.wait_for_timeout(300)
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
                    editor.hass=window.visualHass; editor.setConfig(config);
                    editor.addEventListener('config-changed', e=>editor.setConfig(e.detail.config));
                    host.append(editor); document.body.append(host); window.visualEditor=editor;
                }""", CONFIG)
                editor = page.locator("tiny-refuel-card-editor")
                expect(editor).to_contain_text("895", timeout=30000)
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
                page.locator("#visual-editor-host").evaluate("el => el.remove()")
                assert card.evaluate("el => el.scrollWidth <= el.clientWidth + 1"), prefix + " horizontal overflow"
        page.set_viewport_size({"width": 1280, "height": 1000})
        page.goto(BASE + "/config/integrations/integration/tiny_refuel")
        expect(page.get_by_text("Tiny Refuel", exact=True).first).to_be_visible(timeout=30000)
        page.screenshot(path=str(OUT / "integration-settings.png"), full_page=True, animations="disabled")
        results.append("integration-settings")
        assert not errors, errors
        browser.close()
    return results


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
                tokens = onboard()
                screenshots = browsers(tokens)
                (OUT / "report.json").write_text(json.dumps({"status": "passed", "home_assistant": "2026.10.0", "screenshots": screenshots,
                    "data": "Synthetic station prices and position; production integration, catalog and editor", "browser": "Chromium"}, indent=2))
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
