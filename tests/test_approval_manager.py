from __future__ import annotations

from datetime import timedelta

from agent.tools import approval_manager
from config import settings


def test_create_approval_request_persists_expected_document(
    sample_listing: dict,
    fake_firestore,
    monkeypatch,
) -> None:
    monkeypatch.setattr(approval_manager, "_db", fake_firestore)
    monkeypatch.setattr(approval_manager.secrets, "token_urlsafe", lambda _n: "token-123")

    token = approval_manager.create_approval_request(
        listing_url=sample_listing["listing_url"],
        title=sample_listing["title"],
        price=sample_listing["price"],
        size=sample_listing["size"],
        location=sample_listing["location"],
        description=sample_listing["description"],
        score=sample_listing["score"],
        score_reasons=sample_listing["score_reasons"],
        draft_message=sample_listing["draft_message"],
    )

    assert token == "token-123"

    doc = (
        fake_firestore.collection(settings.FIRESTORE_COLLECTION)
        .document("token-123")
        .get()
        .to_dict()
    )

    assert doc["token"] == "token-123"
    assert doc["status"] == "pending"
    assert doc["score"] == sample_listing["score"]
    assert doc["listing"]["url"] == sample_listing["listing_url"]
    assert doc["draft_message"] == sample_listing["draft_message"]

    ttl = doc["expiresAt"] - doc["createdAt"]
    assert timedelta(hours=settings.APPROVAL_TTL_HOURS - 1) < ttl < timedelta(
        hours=settings.APPROVAL_TTL_HOURS + 1
    )


def test_send_approval_email_contains_action_links(
    sample_listing: dict,
    secret_lookup,
    monkeypatch,
) -> None:
    sent_payload: dict = {}

    def _capture_send_email(*, to: str, subject: str, html_body: str) -> None:
        sent_payload["to"] = to
        sent_payload["subject"] = subject
        sent_payload["html_body"] = html_body

    monkeypatch.setattr(approval_manager, "get_secret", secret_lookup)
    monkeypatch.setattr(approval_manager.gmail, "send_email", _capture_send_email)

    result = approval_manager.send_approval_email(
        token="token-abc",
        title=sample_listing["title"],
        price=sample_listing["price"],
        size=sample_listing["size"],
        location=sample_listing["location"],
        listing_url=sample_listing["listing_url"],
        score=sample_listing["score"],
        score_reasons=sample_listing["score_reasons"],
        draft_message=sample_listing["draft_message"],
    )

    assert result == {"status": "email_sent", "token": "token-abc"}
    assert sent_payload["to"] == "user@example.test"
    assert "[Rental Agent] Review:" in sent_payload["subject"]
    assert f"{settings.SERVICE_BASE_URL}/approve/token-abc" in sent_payload["html_body"]
    assert f"{settings.SERVICE_BASE_URL}/reject/token-abc" in sent_payload["html_body"]
    assert sample_listing["draft_message"] in sent_payload["html_body"]
