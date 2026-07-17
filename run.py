#!/usr/bin/env python3
"""
NYC Housing Alert Bot

Scrapes StreetEasy and LeaseBreak (filters encoded in the search URLs),
detects new listings and price drops, and emails the batch.

Flags:
  --dry-run     Print what would alert; don't send email or write state.
  --init        Populate state without sending alerts (use on first run or after a long gap).
  --test-email  Send a test email and exit without scraping or writing state.
"""

import argparse
import sys

import alerts
import state
from scrapers import leasebreak, streeteasy


def _scrape_all() -> list[dict]:
    listings = []
    for name, scraper in [("streeteasy", streeteasy), ("leasebreak", leasebreak)]:
        try:
            listings += scraper.scrape()
        except Exception as e:
            print(f"  [{name}] ERROR: {e}", file=sys.stderr)
    # Dedupe by id (a listing can appear across pages or sources)
    seen, unique = set(), []
    for l in listings:
        if l["id"] not in seen:
            seen.add(l["id"])
            unique.append(l)
    return unique


def run(dry_run: bool = False, init: bool = False, test_email: bool = False) -> None:
    print("=== NYC Housing Bot ===")
    if test_email:
        print("(test-email mode - sending SMTP smoke test only)")
        alerts.send_test()
        print("\nDone. Test email sent.")
        return

    if dry_run:
        print("(dry run — no email will be sent, state will not be updated)")
    if init:
        print("(init mode — populating state without alerting)")

    print("\n[1/3] Scraping listings...")
    listings = _scrape_all()
    print(f"  total scraped (deduped): {len(listings)}")

    print("\n[2/3] Checking for new listings and price drops...")
    current_state = state.load()
    is_first_run = not current_state

    if is_first_run and not init:
        print("  state is empty — treating as first run (auto-init, no alerts)")
        init = True

    events = state.diff(listings, current_state)
    new_n = sum(1 for e in events if e["type"] == "new")
    drop_n = sum(1 for e in events if e["type"] == "price_drop")
    print(f"  events: {len(events)} ({new_n} new, {drop_n} price drops)")

    print("\n[3/3] Sending alerts...")
    if dry_run:
        for event in events:
            l = event["listing"]
            tag = "NEW" if event["type"] == "new" else "PRICE DROP"
            price = l.get("price")
            price_str = f"${price:,}/mo" if price else "$?/mo"
            nb = f" ({l.get('neighborhood')})" if l.get("neighborhood") else ""
            print(f"  [dry] {tag}: {l.get('address') or '(no address)'}{nb} — {price_str} "
                  f"({l.get('beds')}BR/{l.get('baths')}BA) [{l.get('source')}]")
            print(f"        {l.get('url')}")
    elif init:
        print("  skipping alerts (init mode)")
    elif events:
        alerts.send_batch(events)
    else:
        alerts.send_no_changes(len(listings))

    if dry_run:
        print("\nDone (dry run — state not saved).")
        return

    updated = state.update(listings, current_state)
    state.save(updated)
    print(f"\nDone. State saved ({len(updated)} listings tracked).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NYC Housing Alert Bot")
    parser.add_argument("--dry-run", action="store_true", help="Don't send SMS or save state")
    parser.add_argument("--init", action="store_true", help="Populate state without alerting")
    parser.add_argument("--test-email", action="store_true", help="Send a test email and exit")
    args = parser.parse_args()
    run(dry_run=args.dry_run, init=args.init, test_email=args.test_email)
