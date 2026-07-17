# nyc housing — listing alerts

A small bot that watches [StreetEasy](https://streeteasy.com) and
[LeaseBreak](https://www.leasebreak.com) for NYC rentals matching your search,
and emails you new listings and price drops.

Your filters (price, beds, baths, neighborhoods) live entirely in the search
URLs, so you build them in your browser and paste the full URL into `.env`.
Scraping runs on [Browserbase](https://www.browserbase.com/) (a remote
browser), so no local Chromium is needed.

## Setup

Uses [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env          # fill in Browserbase + SMTP creds and search URLs
uv pip install -r requirements.txt
```

## Usage

```bash
uv run python run.py            # scrape, diff against state, email the batch
uv run python run.py --dry-run  # print what would alert; send nothing
uv run python run.py --init     # seed state without emailing (first run)
```

State (which listings you've already seen, and their last price) is kept in
`state.json`.

## Running on a schedule

`.github/workflows/check.yml` runs the bot twice a day on GitHub Actions and
commits the updated `state.json` back to the repo. It reads config from repo
**Secrets** (`BROWSERBASE_API_KEY`, `BROWSERBASE_PROJECT_ID`, `SMTP_PASSWORD`)
and **Variables** (`SMTP_USER`, `EMAIL_FROM`, `EMAIL_TO`, `STREETEASY_URL`,
`LEASEBREAK_URL`) — set them under *Settings → Secrets and variables → Actions*.
