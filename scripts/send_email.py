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


def load_subscribers(path: str = "config/subscribers.json") -> list[str]:
    """Return list of subscriber email addresses."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        subscribers = data.get("subscribers", [])
        # Support plain list or list of strings
        return [str(s).strip() for s in subscribers if s]
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
        log.warning("No subscribers found; skipping email send.")
        return

    log.info("Sending '%s' to %d subscriber(s)…", subject, len(subscribers))

    # Build message
    msg = MIMEMultipart("alternative")
    msg["From"] = sender
    msg["Subject"] = subject
    # BCC-style: send individually so each recipient doesn't see others
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    # Connect once and send to all recipients
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(sender, app_password)
        for recipient in subscribers:
            try:
                # Rebuild To header each time
                msg.replace_header("To", recipient) if "To" in msg else msg.__setitem__(
                    "To", recipient
                )
                server.sendmail(sender, recipient, msg.as_string())
                log.info("  ✓ Sent to %s", recipient)
            except Exception as exc:
                log.error("  ✗ Failed to send to %s: %s", recipient, exc)

    log.info("Email delivery complete.")


if __name__ == "__main__":
    # Quick smoke-test: requires env vars to be set
    import sys

    html = "<h1>Test email from daily-brief</h1>"
    send(html_content=html, subject="[Test] daily-brief smoke test")
    sys.exit(0)
