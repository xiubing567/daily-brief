"""
send_email.py – Send the daily brief via Gmail SMTP.

Required environment variables:
  GMAIL_USERNAME    – your Gmail address (e.g. you@gmail.com)
  GMAIL_APP_PASSWORD – Gmail App Password (not your regular password)

Optional:
  SUBSCRIBERS_PATH  – path to subscribers JSON (default: config/subscribers.json)
"""

from __future__ import annotations

import json
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

log = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465  # SSL


def _normalise_subscribers(value: object) -> list[str]:
    if isinstance(value, dict):
        value = value.get("subscribers", [])
    if not isinstance(value, list):
        raise ValueError("subscriber data must be a list or an object with a subscribers list")

    subscribers = []
    seen = set()
    for item in value:
        email = str(item).strip()
        if email and email not in seen:
            subscribers.append(email)
            seen.add(email)
    return subscribers


def load_subscribers(path: str = "config/subscribers.json") -> list[str]:
    """Return list of subscriber email addresses."""
    subscribers_json = os.environ.get("SUBSCRIBERS_JSON", "").strip()
    if subscribers_json:
        return _normalise_subscribers(json.loads(subscribers_json))

    subscribers_csv = os.environ.get("SUBSCRIBERS_CSV", "").strip()
    if subscribers_csv:
        return _normalise_subscribers(subscribers_csv.split(","))

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return _normalise_subscribers(data)
    except FileNotFoundError:
        log.warning("Subscribers file not found at %s; defaulting to empty list", path)
        return []


def send(
    html_content: str,
    subject: str,
    subscribers: list[str] | None = None,
    sender: str | None = None,
    app_password: str | None = None,
    subscribers_path: str = "config/subscribers.json",
) -> None:
    """
    Send HTML email to all subscribers via Gmail SMTP SSL.

    :param html_content:    Full HTML string for the email body.
    :param subject:         Email subject line.
    :param subscribers:     Override subscriber list (if None, read from file).
    :param sender:          Gmail address (defaults to GMAIL_USERNAME env var).
    :param app_password:    App password (defaults to GMAIL_APP_PASSWORD env var).
    :param subscribers_path: Path to subscribers JSON file.
    """
    sender = sender or os.environ.get("GMAIL_USERNAME", "")
    app_password = app_password or os.environ.get("GMAIL_APP_PASSWORD", "")

    if not sender or not app_password:
        raise EnvironmentError(
            "GMAIL_USERNAME and GMAIL_APP_PASSWORD must be set as environment variables."
        )

    if subscribers is None:
        subscribers = load_subscribers(subscribers_path)

    if not subscribers:
        raise RuntimeError(
            "No email subscribers configured. Set SUBSCRIBERS_JSON, SUBSCRIBERS_CSV, "
            "or provide a non-empty subscribers file."
        )

    log.info("Sending '%s' to %d subscriber(s)…", subject, len(subscribers))

    # Build message
    msg = MIMEMultipart("alternative")
    msg["From"] = sender
    msg["Subject"] = subject
    # BCC-style: send individually so each recipient doesn't see others
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    # Connect once and send to all recipients
    failures = 0
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(sender, app_password)
        for recipient in subscribers:
            try:
                # Rebuild To header each time so each recipient doesn't see others' addresses
                if "To" in msg:
                    msg.replace_header("To", recipient)
                else:
                    msg["To"] = recipient
                server.sendmail(sender, recipient, msg.as_string())
                log.info("  ✓ Sent to one subscriber")
            except Exception as exc:
                failures += 1
                log.error("  ✗ Failed to send to one subscriber: %s", exc)

    if failures:
        raise RuntimeError(f"Failed to send daily brief to {failures} subscriber(s).")

    log.info("Email delivery complete.")


if __name__ == "__main__":
    # Quick smoke-test: requires env vars to be set
    import sys

    html = "<h1>Test email from daily-brief</h1>"
    send(html_content=html, subject="[Test] daily-brief smoke test")
    sys.exit(0)
