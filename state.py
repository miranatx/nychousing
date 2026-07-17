"""
Tracks seen listings across runs using a local JSON file.

State is kept minimal: {listing_id: {price, last_seen}}. Entries older
than TTL_DAYS are pruned on save so the file stays bounded.

Diff detects:
- new: listing ID not previously seen
- price_drop: listing already seen but price decreased
"""

import json
import os
import time

STATE_FILE = os.path.join(os.path.dirname(__file__), "state.json")
TTL_DAYS = 30
TTL_SECONDS = TTL_DAYS * 24 * 3600


def load() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE) as f:
        return json.load(f)


def save(state: dict) -> None:
    cutoff = time.time() - TTL_SECONDS
    pruned = {lid: entry for lid, entry in state.items() if entry.get("last_seen", 0) >= cutoff}
    with open(STATE_FILE, "w") as f:
        json.dump(pruned, f, indent=2)


Event = dict  # {"type": "new"|"price_drop", "listing": dict, "old_price": int|None}


def diff(listings: list[dict], state: dict) -> list[Event]:
    events: list[Event] = []
    for listing in listings:
        lid = listing["id"]
        if lid not in state:
            events.append({"type": "new", "listing": listing, "old_price": None})
        else:
            old_price = state[lid].get("price")
            new_price = listing.get("price")
            if old_price is not None and new_price is not None and new_price < old_price:
                events.append({"type": "price_drop", "listing": listing, "old_price": old_price})
    return events


def update(listings: list[dict], state: dict) -> dict:
    now = time.time()
    for listing in listings:
        state[listing["id"]] = {
            "price": listing.get("price"),
            "last_seen": now,
        }
    return state
