# nyc housing — listing alerts

A small bot that watches [StreetEasy](https://streeteasy.com) and
[LeaseBreak](https://www.leasebreak.com) for NYC rentals matching your search,
and texts new listings and price drops to your chosen phone numbers through
[Sendblue](https://sendblue.com/).

Your filters (price, beds, baths, neighborhoods) live entirely in the search
URLs, so you build them in your browser and paste the full URL into `.env`.
Scraping runs on [Browserbase](https://www.browserbase.com/) (a remote
browser), so no local Chromium is needed.

Browserbase proxies are disabled by default because they require a paid
Browserbase plan. If your project has proxy access and you want to use it, set
`BROWSERBASE_PROXIES=true`.

## Setup

Uses [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env          # fill in Browserbase + Sendblue creds and search URLs
uv pip install -r requirements.txt
```

## Usage

```bash
uv run python run.py            # scrape, diff against state, text the batch
uv run python run.py --dry-run  # print what would alert; send nothing
uv run python run.py --init     # seed state without sending alerts
```

State (which listings you've already seen, and their last price) is kept in
`state.json`.

## Running on a schedule

`.github/workflows/check.yml` runs the bot twice a day on GitHub Actions and
commits the updated `state.json` back to the repo. It reads config from repo
**Secrets** (`BROWSERBASE_API_KEY`, `BROWSERBASE_PROJECT_ID`,
`SENDBLUE_API_KEY`, `SENDBLUE_API_SECRET`) and **Variables**
(`SENDBLUE_FROM_NUMBER`, `ALERT_PHONE_NUMBERS`, `STREETEASY_URL`,
`LEASEBREAK_URL`) — set them under *Settings → Secrets and variables → Actions*.
Set `ALERT_PHONE_NUMBERS` to comma-separated E.164 numbers, for example
`+12125550001,+12125550002`; every alert is sent to both recipients.

Each listing is delivered separately. Sendblue first sends the listing details,
then sends the listing URL as its own message so iMessage can render a link
preview when the listing site provides compatible preview metadata.
