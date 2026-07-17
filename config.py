import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise RuntimeError(f"Missing required env var: {key}")
    return val


BROWSERBASE_API_KEY = _require("BROWSERBASE_API_KEY")
BROWSERBASE_PROJECT_ID = _require("BROWSERBASE_PROJECT_ID")

# SMTP creds — only required at send time; dry-run / init mode work without them.
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM") or os.getenv("SMTP_USER")
EMAIL_TO = os.getenv("EMAIL_TO")

# Search URLs encode all filtering (price, beds, baths, neighborhoods).
STREETEASY_URL = os.getenv("STREETEASY_URL", "").strip()
LEASEBREAK_URL = os.getenv("LEASEBREAK_URL", "").strip()
