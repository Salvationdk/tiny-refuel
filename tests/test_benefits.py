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

    def test_ignores_customer_comments_even_when_they_match_benefit_keywords(self):
        page = """
        <main><p>Get 15 øre discount per kWh with the provider's own charging app.</p>
        <div class="reviews"><article><p>Customer says the app gives a great discount and cheap price.</p></article></div>
        <section aria-label="Kundeanmeldelser"><p>Users receive a discount and free charging, says a customer.</p></section>
        <p class="customer-comment">I got a discount, says one reviewer of the app.</p>
        <div data-testid="feedback-carousel"><p>We love the price and app benefits, writes a member.</p></div>
        </main>
        """
        self.assertEqual(benefits.extract_excerpt(page),
                         "Get 15 øre discount per kWh with the provider's own charging app.")

    def test_ignores_unmarked_first_person_customer_comments(self):
        page = """
        <main>
        <p>Jeg fik 15 øre i rabat med appen og synes prisen er fantastisk.</p>
        <p>Super app og gode rabatter, skriver en kunde.</p>
        <p>Med udbyderens app får medlemmer 15 øre i rabat pr. kWh.</p>
        </main>
        """
        self.assertEqual(benefits.extract_excerpt(page),
                         "Med udbyderens app får medlemmer 15 øre i rabat pr. kWh.")

    def test_ignores_review_widgets_with_generic_data_attributes(self):
        page = """
        <main>
        <p>Udbyderen giver 10 øre i rabat pr. kWh ved betaling med app.</p>
        <div data-widget-type="customer-quote-slider">
          <p>Appen er fantastisk, jeg fik en god rabat, skriver en kunde.</p>
        </div>
        </main>
        """
        self.assertEqual(benefits.extract_excerpt(page),
                         "Udbyderen giver 10 øre i rabat pr. kWh ved betaling med app.")

    def test_ignores_unattributed_opinion_from_a_reviewer(self):
        page = """
        <main>
        <p>Great app and discount, writes one user.</p>
        <p>Get 20 øre off per kWh with the provider app.</p>
        </main>
        """
        self.assertEqual(benefits.extract_excerpt(page),
                         "Get 20 øre off per kWh with the provider app.")

    def test_uses_fresh_cache_without_requesting_page(self):
        now = 2_000_000_000
        cache = {key: {"provider": provider, "summary": "Cached benefit",
                       "source_url": "https://example.test", "fetched_ts": now - 20,
                       "fetched_at": "cached", "extractor_version": benefits.EXTRACTOR_VERSION, "status": "ok"}
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
                            "fetched_at": "old", "extractor_version": benefits.EXTRACTOR_VERSION, "status": "ok"}}
        result, failures = benefits.update(
            lambda *a, **k: (_ for _ in ()).throw(OSError("offline")),
            lambda path, default: old, lambda *a: None, "cache.json", now=now)
        self.assertEqual(result["circle_k"]["summary"], "Last good benefit")
        self.assertEqual(result["circle_k"]["status"], "stale")
        self.assertEqual(len(failures), len(benefits.PROVIDER_PAGES))

    def test_legacy_extract_is_refreshed_and_not_shown_if_refresh_fails(self):
        now = 2_000_000_000
        old = {"circle_k": {"provider": "Circle K", "summary": "Customer review with a discount",
                            "source_url": "https://example.test", "fetched_ts": now - 10,
                            "fetched_at": "old", "status": "ok"}}
        result, _ = benefits.update(
            lambda *a, **k: (_ for _ in ()).throw(OSError("offline")),
            lambda path, default: old, lambda *a: None, "cache.json", now=now)
        self.assertIsNone(result["circle_k"]["summary"])
        self.assertEqual(result["circle_k"]["status"], "unavailable")

    def test_empty_page_does_not_replace_last_good_excerpt(self):
        now = 2_000_000_000
        old = {key: {"provider": provider, "summary": "Last good benefit",
                     "source_url": url, "fetched_ts": now - benefits.REFRESH_AFTER - 1,
                     "fetched_at": "old", "extractor_version": benefits.EXTRACTOR_VERSION, "status": "ok"}
               for key, (provider, url) in benefits.PROVIDER_PAGES.items()}
        result, _ = benefits.update(lambda *a, **k: "<html><body>No matching page text.</body></html>",
                                    lambda path, default: old, lambda *a: None,
                                    "cache.json", now=now)
        self.assertEqual(result["circle_k"]["summary"], "Last good benefit")
        self.assertEqual(result["circle_k"]["status"], "stale")


if __name__ == "__main__":
    unittest.main()
