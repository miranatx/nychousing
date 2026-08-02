import json
import os
import unittest
from unittest.mock import patch
from urllib.error import URLError

os.environ.setdefault("BROWSERBASE_API_KEY", "test-browserbase-key")
os.environ.setdefault("BROWSERBASE_PROJECT_ID", "test-project")

import alerts
import config


class _Response:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class SendblueAlertsTest(unittest.TestCase):
    def setUp(self):
        self.original = {
            "SENDBLUE_API_KEY": config.SENDBLUE_API_KEY,
            "SENDBLUE_API_SECRET": config.SENDBLUE_API_SECRET,
            "SENDBLUE_FROM_NUMBER": config.SENDBLUE_FROM_NUMBER,
            "ALERT_PHONE_NUMBERS": config.ALERT_PHONE_NUMBERS,
        }
        config.SENDBLUE_API_KEY = "api-key"
        config.SENDBLUE_API_SECRET = "api-secret"
        config.SENDBLUE_FROM_NUMBER = "+12125550000"
        config.ALERT_PHONE_NUMBERS = ["+12125550001", "+12125550002"]

    def tearDown(self):
        for key, value in self.original.items():
            setattr(config, key, value)

    @patch("alerts.urlopen", side_effect=[_Response(), _Response()])
    def test_sends_every_alert_to_both_numbers(self, mocked_urlopen):
        alerts._send_message("subject", "body")

        self.assertEqual(mocked_urlopen.call_count, 2)
        requests = [call.args[0] for call in mocked_urlopen.call_args_list]
        payloads = [json.loads(request.data) for request in requests]
        self.assertEqual(
            [payload["number"] for payload in payloads],
            ["+12125550001", "+12125550002"],
        )
        self.assertTrue(all(payload["from_number"] == "+12125550000" for payload in payloads))
        self.assertTrue(all(payload["content"] == "subject\n\nbody" for payload in payloads))
        self.assertTrue(all(request.full_url == alerts.SENDBLUE_SEND_URL for request in requests))
        self.assertTrue(all(request.get_method() == "POST" for request in requests))

    @patch("alerts.urlopen", return_value=_Response())
    def test_requires_recipients(self, mocked_urlopen):
        config.ALERT_PHONE_NUMBERS = []

        with self.assertRaisesRegex(RuntimeError, "ALERT_PHONE_NUMBERS"):
            alerts._send_message("subject", "body")
        mocked_urlopen.assert_not_called()

    @patch("alerts.urlopen", side_effect=[URLError("first failed"), _Response()])
    def test_attempts_both_numbers_when_one_fails(self, mocked_urlopen):
        with self.assertRaisesRegex(RuntimeError, r"\+12125550001: first failed"):
            alerts._send_message("subject", "body")

        self.assertEqual(mocked_urlopen.call_count, 2)

    @patch("alerts.urlopen", side_effect=[_Response()] * 4)
    def test_sends_listing_details_then_url_only_to_both_numbers(self, mocked_urlopen):
        event = {
            "type": "new",
            "listing": {
                "address": "123 Example St #4A",
                "neighborhood": "Chelsea",
                "price": 5000,
                "beds": 2,
                "baths": 2,
                "source": "leasebreak",
                "url": "https://leasebreak.com/example-details/123/",
            },
        }

        alerts.send_batch([event])

        self.assertEqual(mocked_urlopen.call_count, 4)
        payloads = [
            json.loads(call.args[0].data)
            for call in mocked_urlopen.call_args_list
        ]
        self.assertEqual(
            [payload["number"] for payload in payloads],
            ["+12125550001", "+12125550002", "+12125550001", "+12125550002"],
        )
        self.assertTrue(all("123 Example St" in payload["content"] for payload in payloads[:2]))
        self.assertEqual(
            [payload["content"] for payload in payloads[2:]],
            [
                "https://leasebreak.com/example-details/123/",
                "https://leasebreak.com/example-details/123/",
            ],
        )


if __name__ == "__main__":
    unittest.main()
