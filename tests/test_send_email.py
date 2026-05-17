import json
import os
import smtplib
import tempfile
import unittest
from unittest.mock import patch

from scripts import send_email


class FakeSMTP:
    sent_recipients = []
    fail_recipients = set()

    def __init__(self, host, port):
        self.host = host
        self.port = port

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def login(self, sender, password):
        self.sender = sender
        self.password = password

    def sendmail(self, sender, recipient, message):
        if recipient in self.fail_recipients:
            raise smtplib.SMTPException("delivery failed")
        self.sent_recipients.append(recipient)


class SendEmailTests(unittest.TestCase):
    def setUp(self):
        FakeSMTP.sent_recipients = []
        FakeSMTP.fail_recipients = set()
        self.env_patch = patch.dict(os.environ, {}, clear=True)
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()

    def test_load_subscribers_prefers_secret_json_from_environment(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as f:
            json.dump({"subscribers": ["public@example.com"]}, f)
            file_path = f.name

        try:
            os.environ["SUBSCRIBERS_JSON"] = json.dumps(
                {"subscribers": ["secret1@example.com", "secret2@example.com"]}
            )

            self.assertEqual(
                send_email.load_subscribers(file_path),
                ["secret1@example.com", "secret2@example.com"],
            )
        finally:
            os.unlink(file_path)

    def test_send_raises_when_any_recipient_delivery_fails(self):
        os.environ["GMAIL_USERNAME"] = "sender@example.com"
        os.environ["GMAIL_APP_PASSWORD"] = "app-password"
        FakeSMTP.fail_recipients = {"bad@example.com"}

        with patch.object(send_email.smtplib, "SMTP_SSL", FakeSMTP):
            with self.assertRaises(RuntimeError):
                send_email.send(
                    html_content="<p>Hello</p>",
                    subject="Daily",
                    subscribers=["ok@example.com", "bad@example.com"],
                )

        self.assertEqual(FakeSMTP.sent_recipients, ["ok@example.com"])

    def test_send_raises_when_no_subscribers_are_configured(self):
        os.environ["GMAIL_USERNAME"] = "sender@example.com"
        os.environ["GMAIL_APP_PASSWORD"] = "app-password"

        with self.assertRaises(RuntimeError):
            send_email.send(
                html_content="<p>Hello</p>",
                subject="Daily",
                subscribers=[],
            )


if __name__ == "__main__":
    unittest.main()
