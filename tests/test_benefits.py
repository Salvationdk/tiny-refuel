"""Offline checks for cached provider benefit extracts."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "benefits_scraper", Path(__file__).parents[1] / "custom_components/tiny_refuel/benefits.py")
benefits = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benefits)


class BenefitsTests(unittest.TestCase):
    def test_extracts_relevant_page_text_and_skips_page_chrome(self):
        page = """
        <header><p>Navigation menu with app, price and benefits</p></header>
        <main><h2>Customer benefits</h2>
        <p>Members receive a discount of 20 øre per kWh when they pay using the provider app.</p>
        <p>Information that does not mention a benefit or payment feature.</p></main>
        <footer><p>Footer says free app and discount but is only navigation.</p></footer>
        """
        excerpt = benefits.extract_excerpt(page)
        self.assertEqual(excerpt, "Members receive a discount of 20 øre per kWh when they pay using the provider app.")

    def test_uses_fresh_cache_without_requesting_page(self):
        now = 2_000_000_000
        cache = {key: {"provider": provider, "summary": "Cached benefit",
                       "source_url": "https://example.test", "fetched_ts": now - 20,
                       "fetched_at": "cached", "status": "ok"}
                 for key, (provider, _) in benefits.PROVIDER_PAGES.items()}
        saved = []
        result, failures = benefits.update(
            lambda *a, **k: self.fail("fresh cache should avoid network"),
            lambda path, default: cache, lambda path, data: saved.append(data),
            "cache.json", now=now)
        self.assertEqual(result["circle_k"]["summary"], "Cached benefit")
        self.assertEqual(failures, [])
        self.assertEqual(saved[0], result)

    def test_failed_refresh_retains_stale_provider_record(self):
        now = 2_000_000_000
        old = {"circle_k": {"provider": "Circle K", "summary": "Last good benefit",
                            "source_url": "https://example.test", "fetched_ts": now - benefits.REFRESH_AFTER - 1,
                            "fetched_at": "old", "status": "ok"}}
        result, failures = benefits.update(
            lambda *a, **k: (_ for _ in ()).throw(OSError("offline")),
            lambda path, default: old, lambda *a: None, "cache.json", now=now)
        self.assertEqual(result["circle_k"]["summary"], "Last good benefit")
        self.assertEqual(result["circle_k"]["status"], "stale")
        self.assertEqual(len(failures), len(benefits.PROVIDER_PAGES))

    def test_empty_page_does_not_replace_last_good_excerpt(self):
        now = 2_000_000_000
        old = {key: {"provider": provider, "summary": "Last good benefit",
                     "source_url": url, "fetched_ts": now - benefits.REFRESH_AFTER - 1,
                     "fetched_at": "old", "status": "ok"}
               for key, (provider, url) in benefits.PROVIDER_PAGES.items()}
        result, _ = benefits.update(lambda *a, **k: "<html><body>No matching page text.</body></html>",
                                    lambda path, default: old, lambda *a: None,
                                    "cache.json", now=now)
        self.assertEqual(result["circle_k"]["summary"], "Last good benefit")
        self.assertEqual(result["circle_k"]["status"], "stale")


if __name__ == "__main__":
    unittest.main()
