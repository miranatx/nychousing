import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise RuntimeError(f"Missing required env var: {key}")
    return val


def _bool_env(key: str, default: bool = False) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


BROWSERBASE_API_KEY = _require("BROWSERBASE_API_KEY")
BROWSERBASE_PROJECT_ID = _require("BROWSERBASE_PROJECT_ID")
BROWSERBASE_PROXIES = _bool_env("BROWSERBASE_PROXIES", False)

# Sendblue creds — only required at send time; dry-run / init mode work without them.
SENDBLUE_API_KEY = os.getenv("SENDBLUE_API_KEY")
SENDBLUE_API_SECRET = os.getenv("SENDBLUE_API_SECRET")
SENDBLUE_FROM_NUMBER = os.getenv("SENDBLUE_FROM_NUMBER")
ALERT_PHONE_NUMBERS = [
    number.strip()
    for number in os.getenv("ALERT_PHONE_NUMBERS", "").split(",")
    if number.strip()
]

# Search URLs encode all filtering (price, beds, baths, neighborhoods).
STREETEASY_URL = os.getenv("STREETEASY_URL", "").strip()
LEASEBREAK_URL = os.getenv("LEASEBREAK_URL", "").strip()
