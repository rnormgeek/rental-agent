from __future__ import annotations

import base64

from utils import gmail


def test_get_sender_extracts_address_from_header_with_angle_brackets() -> None:
    message = {
        "payload": {
            "headers": [
                {"name": "From", "value": "SeLoger Alerts <alerte@seloger.com>"},
            ]
        }
    }

    assert gmail.get_sender(message) == "alerte@seloger.com"


def test_get_sender_returns_lowercase_plain_header_when_no_brackets() -> None:
    message = {
        "payload": {
            "headers": [
                {"name": "From", "value": "ALERTE@SELOGER.COM"},
            ]
        }
    }

    assert gmail.get_sender(message) == "alerte@seloger.com"


def test_get_html_body_extracts_nested_html_part() -> None:
    html = "<html><body><p>Bonjour Annecy</p></body></html>"
    encoded = base64.urlsafe_b64encode(html.encode("utf-8")).decode("utf-8")

    message = {
        "payload": {
            "mimeType": "multipart/alternative",
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {
                        "data": base64.urlsafe_b64encode(b"plain").decode("utf-8")
                    },
                },
                {"mimeType": "text/html", "body": {"data": encoded}},
            ],
        }
    }

    assert gmail.get_html_body(message) == html
