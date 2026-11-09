"""Marketplace packaging and native post-install manifest checks."""
import json
from importlib.metadata import version as package_version
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "tiny_refuel"
SOURCE = ROOT / "custom_components" / DOMAIN


class MarketplacePackageTests(unittest.TestCase):
    def test_catalog_metadata_and_release_identity(self):
        config = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))
        manifest = json.loads((SOURCE / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["domain"], DOMAIN)
        self.assertEqual(manifest["version"], "0.2.9")
        self.assertEqual(config["country"], "DK")
        self.assertTrue(manifest["config_flow"])
        self.assertTrue(manifest["issue_tracker"].startswith("https://"))
        self.assertTrue((SOURCE / "config_flow.py").is_file())
        self.assertTrue((SOURCE / "brand" / "icon.png").is_file())
        self.assertEqual(manifest["categories"], ["energy.energy_prices", "energy.ev_charging"])

    def test_native_marketplace_manifest_on_install_and_upgrade(self):
        ha = tuple(map(int, package_version("homeassistant").split(".")[:2]))
        if ha < (2026, 11):
            self.skipTest("Native Marketplace starts with Home Assistant 2026.11")
        from homeassistant.components.marketplace.repositories.integration import _check_loadable_manifest
        with tempfile.TemporaryDirectory() as tmp:
            installed = Path(tmp) / "custom_components" / DOMAIN
            shutil.copytree(SOURCE, installed)
            manifest_file = installed / "manifest.json"
            current = json.loads(manifest_file.read_text(encoding="utf-8"))
            for version in ("0.2.8", "0.2.9"):
                current["version"] = version
                manifest_file.write_text(json.dumps(current), encoding="utf-8")
                _check_loadable_manifest(installed, DOMAIN)


if __name__ == "__main__":
    unittest.main()
