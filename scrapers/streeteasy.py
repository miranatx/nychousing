"""StreetEasy rental listing scraper."""

import random
import re
import time

from scrapers._browser import browser_page

import config


def _build_url(page: int = 1) -> str:
    sep = "&" if "?" in config.STREETEASY_URL else "?"
    return config.STREETEASY_URL if page == 1 else f"{config.STREETEASY_URL}{sep}page={page}"


def _parse_first_dollar_amount(text: str) -> int | None:
    """Take the first $X,XXX in the text — avoids concatenating multiple prices on a card."""
    m = re.search(r"\$\s*([\d,]+)", text)
    if not m:
        return None
    digits = m.group(1).replace(",", "")
    return int(digits) if digits else None


def _parse_beds(text: str) -> float | None:
    text = text.lower()
    if "studio" in text:
        return 0
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:bed|br\b)", text)
    return float(m.group(1)) if m else None


def _parse_baths(text: str) -> float | None:
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:bath|ba\b)", text.lower())
    return float(m.group(1)) if m else None


def _extract_cards(page) -> list[dict]:
    """Single page.evaluate() to avoid round-trip session closures."""
    raw = page.evaluate("""
        () => Array.from(document.querySelectorAll('[data-testid="listing-card"]')).map(card => {
            const addrLink = card.querySelector('a[href*="/building/"]');
            const titleEl = card.querySelector('[class*="ListingDescription-module__title"], [class*="Title"]');
            const priceEl = card.querySelector('[class*="PriceInfo-module__price"]');
            return {
                href: addrLink ? addrLink.getAttribute('href') : null,
                addressText: addrLink ? addrLink.innerText.trim() : '',
                titleText: titleEl ? titleEl.innerText.trim() : '',
                priceText: priceEl ? priceEl.innerText.trim() : '',
                fullText: card.innerText,
            };
        })
    """)

    listings = []
    for r in raw:
        href = r.get("href") or ""
        if not href:
            continue
        m = re.search(r"/building/([^/?#]+)(?:/([^/?#]+))?", href)
        listing_id = f"se_{m.group(1)}_{m.group(2) or ''}" if m else f"se_{abs(hash(href))}"

        title = r.get("titleText", "")
        nb_match = re.search(r"\bin\s+(.+)$", title)
        neighborhood = nb_match.group(1).strip() if nb_match else ""

        listings.append({
            "id": listing_id,
            "source": "streeteasy",
            "address": r.get("addressText", ""),
            "neighborhood": neighborhood,
            "price": _parse_first_dollar_amount(r.get("priceText", "")),
            "beds": _parse_beds(r.get("fullText", "")),
            "baths": _parse_baths(r.get("fullText", "")),
            "url": href,
        })
    return listings


def _scrape_one_page(page, url: str) -> list[dict]:
    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(int(random.uniform(2500, 4500)))
    return _extract_cards(page)


def scrape(max_pages: int = 3, retries: int = 1) -> list[dict]:
    """Scrape paginated rentals. Retries page 1 with fresh sessions to ride out bot blocks."""
    if not config.STREETEASY_URL:
        print("  [streeteasy] STREETEASY_URL not set; skipping")
        return []
    results = []
    for attempt in range(1, retries + 1):
        try:
            with browser_page() as page:
                for page_num in range(1, max_pages + 1):
                    url = _build_url(page_num)
                    print(f"  [streeteasy] scraping page {page_num}: {url}")
                    listings = _scrape_one_page(page, url)
                    if not listings:
                        if page_num == 1 and attempt < retries:
                            print(f"  [streeteasy] page 1 empty (likely blocked); retry {attempt}/{retries}")
                            results = []
                            break  # break inner; outer loop retries with fresh session
                        return _done(results)
                    results.extend(listings)
                    time.sleep(random.uniform(1, 3))
                else:
                    return _done(results)
        except Exception as e:
            print(f"  [streeteasy] attempt {attempt} failed: {e}")
            if attempt == retries:
                raise
    return _done(results)


def _done(results: list[dict]) -> list[dict]:
    print(f"  [streeteasy] found {len(results)} listings")
    return results
