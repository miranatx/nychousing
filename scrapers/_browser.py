"""Shared Browserbase + Playwright session helper."""

from contextlib import contextmanager

from browserbase import Browserbase
from playwright.sync_api import sync_playwright

import config


# Resource types we don't need for DOM scraping. Blocking these saves
# significant proxy bandwidth (images and media are usually 80%+ of page weight).
_BLOCKED_RESOURCE_TYPES = {"image", "media", "font", "stylesheet"}


def _block_heavy_resources(route, request):
    if request.resource_type in _BLOCKED_RESOURCE_TYPES:
        route.abort()
    else:
        route.continue_()


@contextmanager
def browser_page():
    """Yield a Playwright Page connected to a fresh Browserbase session."""
    bb = Browserbase(api_key=config.BROWSERBASE_API_KEY)
    session = bb.sessions.create(
        project_id=config.BROWSERBASE_PROJECT_ID,
        proxies=True,
        browser_settings={"solve_captchas": True, "block_ads": True},
    )
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(session.connect_url)
        try:
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else context.new_page()
            page.route("**/*", _block_heavy_resources)
            yield page
        finally:
            browser.close()
