import smtplib
from datetime import datetime
from email.message import EmailMessage
from html import escape

import config


# Palette + type, matched to the site.
# Web fonts don't load reliably in email, so the display face degrades to
# Georgia and the utility face to Courier — both keep the site's character.
BG = "#FCFBF7"       # warm paper
TEXT = "#0B0B0B"     # ink
MUTED = "#8A8A82"    # warm gray
RULE = "#0B0B0B"
MARKER = "#D8FE51"   # highlighter accent (the signature, used sparingly)
FONT = "'IBM Plex Mono', 'Courier New', Courier, 'SFMono-Regular', Menlo, Consolas, monospace"
SERIF = "'Instrument Serif', Georgia, 'Times New Roman', serif"


def _mark(text: str) -> str:
    """Solid highlighter swipe — the email-robust version of the site's .mark."""
    return (
        f'<span style="background:{MARKER};padding:1px 5px;'
        f'box-decoration-break:clone;-webkit-box-decoration-break:clone;">{text}</span>'
    )


def _fmt_price(price: int | None) -> str:
    return f"${price:,}" if price else "$?"


def _beds_baths(listing: dict) -> str:
    beds, baths = listing.get("beds"), listing.get("baths")
    bd = "studio" if beds == 0 else (f"{int(beds)}br" if beds is not None else "?br")
    return f"{bd} / {baths}ba".lower() if baths is not None else bd


def _location(listing: dict) -> str:
    return listing.get("address") or "unknown"


# --- group events by bathroom count ---

_BATH_ORDER = ["1 bath", "2 bath", "other baths"]


def _bath_label(listing: dict) -> str:
    b = listing.get("baths")
    if b == 1:
        return "1 bath"
    if b == 2:
        return "2 bath"
    return "other baths"


def _group_by_bath(events: list[dict]) -> list[tuple[str, list[dict]]]:
    """Bucket events by bathroom count. Within each bucket, new listings
    come before price drops. Returns non-empty buckets in a fixed order."""
    new_evts = [e for e in events if e["type"] == "new"]
    drop_evts = [e for e in events if e["type"] == "price_drop"]
    groups: dict[str, list[dict]] = {}
    for e in new_evts + drop_evts:
        groups.setdefault(_bath_label(e["listing"]), []).append(e)
    return [(label, groups[label]) for label in _BATH_ORDER if label in groups]


# --- plain-text body (fallback) ---

def _new_text(l: dict) -> str:
    nb = f"  {l['neighborhood']}\n" if l.get("neighborhood") else ""
    return (
        f"{_location(l)}\n"
        f"{nb}"
        f"  {_fmt_price(l.get('price'))}/mo  ·  {_beds_baths(l)}  ·  {l.get('source')}\n"
        f"  {l.get('url', '')}\n"
    )


def _drop_text(l: dict, old_price: int) -> str:
    nb = f"  {l['neighborhood']}\n" if l.get("neighborhood") else ""
    return (
        f"{_location(l)}\n"
        f"{nb}"
        f"  {_fmt_price(old_price)} -> {_fmt_price(l.get('price'))}/mo  ·  {_beds_baths(l)}  ·  {l.get('source')}\n"
        f"  {l.get('url', '')}\n"
    )


def _event_text(e: dict) -> str:
    if e["type"] == "price_drop":
        return _drop_text(e["listing"], e["old_price"])
    return _new_text(e["listing"])


def _build_text(events: list[dict]) -> str:
    parts = []
    for label, evts in _group_by_bath(events):
        parts.append(f"{label.upper()} ({len(evts)})\n")
        parts.extend(_event_text(e) for e in evts)
        parts.append("")
    return "\n".join(parts)


# --- HTML body ---

def _row(label: str, value: str) -> str:
    return (
        f'<div style="display:flex;justify-content:space-between;'
        f'border-bottom:1px solid {TEXT};padding:10px 0;font-size:13px;">'
        f'<span style="color:{MUTED};">{escape(label)}</span>'
        f'<span style="color:{TEXT};text-align:right;">{value}</span>'
        f"</div>"
    )


def _listing_block(l: dict, *, drop_from: int | None = None) -> str:
    address = escape(_location(l))
    source = (l.get("source") or "").lower()
    url = escape(l.get("url") or "#")
    bb = _beds_baths(l)

    if drop_from is not None:
        new_p = l.get("price") or 0
        pct = round((1 - new_p / drop_from) * 100) if drop_from else 0
        price_html = (
            f'<span style="text-decoration:line-through;color:{MUTED};">{escape(_fmt_price(drop_from))}</span> '
            f'→ {_mark(escape(_fmt_price(l.get("price"))) + "/mo")} '
            f'<span style="color:{MUTED};">({-pct:+d}%)</span>' if pct else
            f'<span style="text-decoration:line-through;color:{MUTED};">{escape(_fmt_price(drop_from))}</span> '
            f'<span style="color:{TEXT};">→ {escape(_fmt_price(l.get("price")))}/mo</span>'
        )
    else:
        price_html = _mark(f'{escape(_fmt_price(l.get("price")))}/mo')

    nb = (l.get("neighborhood") or "")
    return f"""
    <div style="border-top:1px solid {TEXT};padding:28px 0;">
      <div style="font-size:17px;font-weight:700;color:{TEXT};line-height:1.4;
                  letter-spacing:0.01em;">
        {address}
      </div>
      {f'<div style="font-size:14px;color:{MUTED};margin-top:4px;letter-spacing:0.02em;">{escape(nb)}</div>' if nb else ''}
      <div style="margin-top:18px;font-size:14px;line-height:2;letter-spacing:0.02em;
                  color:{TEXT};font-weight:700;">
        <div><span style="display:inline-block;width:64px;color:{MUTED};font-weight:600;">price</span>{price_html}</div>
        <div><span style="display:inline-block;width:64px;color:{MUTED};font-weight:600;">unit</span>{escape(bb)}</div>
        <div><span style="display:inline-block;width:64px;color:{MUTED};font-weight:600;">via</span>{escape(source)}</div>
      </div>
      <div style="margin-top:20px;font-size:13px;letter-spacing:0.06em;font-weight:700;">
        <a href="{url}" style="color:{TEXT};text-decoration:underline;text-underline-offset:3px;">
          → open listing
        </a>
      </div>
    </div>
    """


def _section(label: str, count: int) -> str:
    return f"""
    <div style="margin:56px 0 8px;font-size:12px;letter-spacing:0.22em;
                text-transform:uppercase;color:{TEXT};font-weight:700;">
      [ {escape(label)} {count:02d} ]
    </div>
    """


def _build_html(events: list[dict]) -> str:
    new_evts = [e for e in events if e["type"] == "new"]
    drop_evts = [e for e in events if e["type"] == "price_drop"]

    summary_bits = []
    if new_evts:
        summary_bits.append(f"{len(new_evts)} new")
    if drop_evts:
        summary_bits.append(f"{len(drop_evts)} drop{'s' if len(drop_evts) != 1 else ''}")
    summary = " / ".join(summary_bits)
    today = datetime.now().strftime("%a %b %d %Y").lower()

    blocks = []
    for label, evts in _group_by_bath(events):
        blocks.append(_section(label, len(evts)))
        for e in evts:
            if e["type"] == "price_drop":
                blocks.append(_listing_block(e["listing"], drop_from=e["old_price"]))
            else:
                blocks.append(_listing_block(e["listing"]))

    return f"""<!doctype html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=Instrument+Serif&display=swap" rel="stylesheet"></head>
<body style="margin:0;padding:0;background:{BG};font-family:{FONT};
             color:{TEXT};-webkit-font-smoothing:antialiased;">
  <div style="max-width:560px;margin:0 auto;padding:56px 28px 72px;">

    <div style="font-size:12px;letter-spacing:0.28em;color:{TEXT};margin-bottom:36px;
                font-weight:700;">
      [ nyc housing ]
    </div>

    <div style="font-family:{SERIF};font-size:52px;font-weight:400;letter-spacing:-0.01em;
                line-height:1.0;color:{TEXT};text-transform:lowercase;">
      {escape(summary)}
    </div>
    <div style="font-size:13px;letter-spacing:0.18em;color:{MUTED};margin-top:14px;
                text-transform:lowercase;font-weight:700;">
      {escape(today)}
    </div>

    <div style="border-top:2px solid {TEXT};margin-top:40px;"></div>

    {''.join(blocks)}

    <div style="border-top:2px solid {TEXT};margin-top:48px;padding-top:20px;
                font-size:10px;letter-spacing:0.25em;color:{MUTED};
                text-transform:uppercase;text-align:center;font-weight:700;line-height:2;">
      streeteasy &nbsp;/&nbsp; leasebreak
    </div>

  </div>
</body>
</html>"""


# --- send ---

def _send_email(subject: str, text_body: str, html_body: str) -> None:
    for key in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "EMAIL_FROM", "EMAIL_TO"):
        if not getattr(config, key):
            raise RuntimeError(f"Cannot send email: {key} is not set in .env")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config.EMAIL_FROM
    msg["To"] = config.EMAIL_TO
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as s:
        s.starttls()
        s.login(config.SMTP_USER, config.SMTP_PASSWORD)
        s.send_message(msg)


def _build_subject(events: list[dict]) -> str:
    new_n = sum(1 for e in events if e["type"] == "new")
    drop_n = sum(1 for e in events if e["type"] == "price_drop")
    parts = []
    if new_n:
        parts.append(f"{new_n} new")
    if drop_n:
        parts.append(f"{drop_n} drop{'s' if drop_n != 1 else ''}")
    return f"[nyc housing] {' / '.join(parts)}"


def send_batch(events: list[dict]) -> None:
    if not events:
        return
    subject = _build_subject(events)
    _send_email(subject, _build_text(events), _build_html(events))
    print(f"  [alert] email sent: {subject}")


def _send(subject: str, body: str) -> None:
    _send_email(subject, body, f"<pre>{escape(body)}</pre>")
