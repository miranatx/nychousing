"""LeaseBreak sublet listing scraper."""

import random
import re
import time

from scrapers._browser import browser_page

import config


def _parse_int_dollars(text: str) -> int | None:
    # Handle ranges like "$3,400 – $3,800" by taking the lower bound
    nums = re.findall(r"\$?\s*([\d,]+)", text)
    if not nums:
        return None
    try:
        return int(nums[0].replace(",", ""))
    except ValueError:
        return None


def _parse_beds(text: str) -> float | None:
    t = text.lower()
    if "studio" in t:
        return 0
    # LeaseBreak labels them as "BEDROOMS:\n\n4"
    m = re.search(r"bedrooms?:\s*(\d+(?:\.\d+)?)", t)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:bed|br\b)", t)
    return float(m.group(1)) if m else None


def _parse_baths(text: str) -> float | None:
    t = text.lower()
    m = re.search(r"bathrooms?:\s*(\d+(?:\.\d+)?)", t)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:bath|ba\b)", t)
    return float(m.group(1)) if m else None


def _extract_cards(page) -> list[dict]:
    """Pull every card's data in one evaluate call to avoid round-trip session timeouts."""
    raw = page.evaluate("""
        () => Array.from(document.querySelectorAll('.search-item')).map(card => {
            const link = card.querySelector('a[href*="-details/"]');
            const priceEl = card.querySelector('.detail-right-price');
            // Address: pick first details-link whose innerText is a non-empty, non-button string
            let addressText = '';
            for (const a of card.querySelectorAll('a[href*="-details/"]')) {
                const t = (a.innerText || '').trim();
                if (t && !/^view/i.test(t)) { addressText = t; break; }
            }
            return {
                href: link ? link.getAttribute('href') : null,
                dataId: link ? link.getAttribute('data-id') : null,
                priceText: priceEl ? priceEl.innerText : '',
                addressText,
                fullText: card.innerText,
            };
        })
    """)
    listings = []
    for r in raw:
        href = r.get("href") or ""
        if not href:
            continue
        listing_url = f"https://leasebreak.com{href}" if href.startswith("/") else href
        listing_id = f"lb_{r['dataId']}" if r.get("dataId") else f"lb_{href.rstrip('/').split('/')[-2:]}"

        # LeaseBreak cards include a "<Neighborhood>, <Borough>" line in their text
        neighborhood = ""
        m = re.search(
            r"^(.+?),\s*(?:Manhattan|Brooklyn|Queens|Bronx|Staten Island)\s*$",
            r.get("fullText", ""),
            re.MULTILINE,
        )
        if m:
            neighborhood = m.group(1).strip()

        listings.append({
            "id": listing_id,
            "source": "leasebreak",
            "address": r.get("addressText", ""),
            "neighborhood": neighborhood,
            "price": _parse_int_dollars(r.get("priceText", "")),
            "beds": _parse_beds(r.get("fullText", "")),
            "baths": _parse_baths(r.get("fullText", "")),
            "url": listing_url,
        })
    return listings


def scrape(max_pages: int = 3) -> list[dict]:
    if not config.LEASEBREAK_URL:
        print("  [leasebreak] LEASEBREAK_URL not set; skipping")
        return []
    base = config.LEASEBREAK_URL
    sep = "&" if "?" in base else "?"
    results = []
    with browser_page() as page:
        for page_num in range(1, max_pages + 1):
            url = base if page_num == 1 else f"{base}{sep}page={page_num}"
            print(f"  [leasebreak] scraping page {page_num}: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(int(random.uniform(3000, 5000)))
            page_results = _extract_cards(page)
            if not page_results:
                break
            results.extend(page_results)
            time.sleep(random.uniform(1, 3))

    print(f"  [leasebreak] found {len(results)} listings")
    return results
