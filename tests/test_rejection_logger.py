from __future__ import annotations

from agent.tools.rejection_logger import log_rejection


def test_log_rejection_returns_rejected_status() -> None:
    result = log_rejection(
        listing_url="https://example.test/listing",
        score=22,
        reasons=["Budget too high", "Ground floor"],
    )

    assert result == {
        "status": "rejected",
        "listing_url": "https://example.test/listing",
        "score": 22,
    }
