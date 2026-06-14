from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone

from google.cloud import firestore

from config import settings
from utils import gmail
from utils.secrets import get_secret

logger = logging.getLogger(__name__)

_db: firestore.Client | None = None


def _get_db() -> firestore.Client:
    global _db
    if _db is None:
        _db = firestore.Client(project=settings.GOOGLE_CLOUD_PROJECT)
    return _db


def create_approval_request(
    listing_url: str,
    title: str,
    price: str,
    size: str,
    location: str,
    description: str,
    score: int,
    score_reasons: list[str],
    draft_message: str,
) -> str:
    """
    Persist an approval request in Firestore and return the unique approval token.
    The document has a TTL on the expiresAt field and starts with status "pending".

    Args:
        listing_url: URL of the listing.
        title: Listing title.
        price: Monthly rent.
        size: Surface area.
        location: City / neighbourhood.
        description: Short listing description (max ~500 chars).
        score: Criteria match score (0–100).
        score_reasons: List of reasons for the score.
        draft_message: The draft contact message produced by draft_contact_message.

    Returns:
        The approval token string (URL-safe, 32 bytes).
    """
    token = secrets.token_urlsafe(32)
    db = _get_db()
    doc_ref = db.collection(settings.FIRESTORE_COLLECTION).document(token)
    doc_ref.set(
        {
            "token": token,
            "status": "pending",
            "createdAt": datetime.now(tz=timezone.utc),
            "expiresAt": datetime.now(tz=timezone.utc)
            + timedelta(hours=settings.APPROVAL_TTL_HOURS),
            "listing": {
                "url": listing_url,
                "title": title,
                "price": price,
                "size": size,
                "location": location,
                "description": description,
            },
            "score": score,
            "score_reasons": score_reasons,
            "draft_message": draft_message,
        }
    )
    logger.info(
        "Approval request created",
        extra={"json_fields": {"token": token, "listing_url": listing_url, "score": score}},
    )
    return token


def send_approval_email(
    token: str,
    title: str,
    price: str,
    size: str,
    location: str,
    listing_url: str,
    score: int,
    score_reasons: list[str],
    draft_message: str,
) -> dict:
    """
    Send an HTML approval email to the user containing a listing summary, the
    criteria match score with reasons, the draft contact message, and
    Approve / Reject action links.

    Args:
        token: The Firestore approval token returned by create_approval_request.
        title: Listing title.
        price: Monthly rent.
        size: Surface area.
        location: City / neighbourhood.
        listing_url: URL of the listing page.
        score: Criteria match score (0–100).
        score_reasons: List of reasons for the score.
        draft_message: The draft contact message.

    Returns:
        Confirmation dict.
    """
    user_email = get_secret(settings.SECRET_USER_EMAIL)
    approve_url = f"{settings.SERVICE_BASE_URL}/approve/{token}"
    reject_url = f"{settings.SERVICE_BASE_URL}/reject/{token}"
    reasons_html = "".join(f"<li>{r}</li>" for r in score_reasons)

    html_body = f"""
<html>
<body style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:16px;">
  <h2 style="color:#1a237e;">🏠 New Rental Listing — Your Review Required</h2>
  <table style="border-collapse:collapse;width:100%;margin-bottom:16px;">
    <tr><td style="padding:6px 10px;font-weight:bold;background:#f5f5f5;">Title</td>
        <td style="padding:6px 10px;">{title}</td></tr>
    <tr><td style="padding:6px 10px;font-weight:bold;">Price</td>
        <td style="padding:6px 10px;">{price}</td></tr>
    <tr><td style="padding:6px 10px;font-weight:bold;background:#f5f5f5;">Size</td>
        <td style="padding:6px 10px;background:#f5f5f5;">{size}</td></tr>
    <tr><td style="padding:6px 10px;font-weight:bold;">Location</td>
        <td style="padding:6px 10px;">{location}</td></tr>
    <tr><td style="padding:6px 10px;font-weight:bold;background:#f5f5f5;">Match Score</td>
        <td style="padding:6px 10px;background:#f5f5f5;"><strong>{score}/100</strong></td></tr>
  </table>
  <h3 style="margin-bottom:4px;">Why this score?</h3>
  <ul style="margin-top:4px;">{reasons_html}</ul>
  <h3 style="margin-bottom:4px;">Draft Contact Message</h3>
  <pre style="background:#f9f9f9;padding:12px;border-left:3px solid #9e9e9e;white-space:pre-wrap;">{draft_message}</pre>
  <p><a href="{listing_url}" target="_blank" style="color:#1565c0;">View listing on SeLoger →</a></p>
  <p style="margin-top:32px;">
    <a href="{approve_url}"
       style="background:#2e7d32;color:white;padding:12px 28px;text-decoration:none;
              border-radius:4px;margin-right:12px;display:inline-block;">
      ✓ Approve &amp; Send
    </a>
    <a href="{reject_url}"
       style="background:#c62828;color:white;padding:12px 28px;text-decoration:none;
              border-radius:4px;display:inline-block;">
      ✗ Reject
    </a>
  </p>
  <p style="color:#9e9e9e;font-size:12px;margin-top:24px;">
    This request expires in {settings.APPROVAL_TTL_HOURS} hours.
  </p>
</body>
</html>
"""
    gmail.send_email(
        to=user_email,
        subject=f"[Rental Agent] Review: {title} — {price} ({score}/100)",
        html_body=html_body,
    )
    logger.info(
        "Approval email sent",
        extra={"json_fields": {"token": token, "to": user_email, "score": score}},
    )
    return {"status": "email_sent", "token": token}
