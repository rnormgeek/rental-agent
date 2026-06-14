from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def log_rejection(listing_url: str, score: int, reasons: list[str]) -> dict:
    """
    Log a rejected listing to Cloud Logging. Call this when a listing scores
    below the minimum score threshold. Do NOT proceed with any further tools
    after calling this function.

    Args:
        listing_url: The URL of the rejected listing.
        score: The match score (0–100).
        reasons: List of concise reasons why the listing was rejected.

    Returns:
        Confirmation dict so the agent knows the action completed.
    """
    logger.info(
        "Listing rejected — below score threshold",
        extra={
            "json_fields": {
                "event": "listing_rejected",
                "listing_url": listing_url,
                "score": score,
                "reasons": reasons,
            }
        },
    )
    return {"status": "rejected", "listing_url": listing_url, "score": score}
