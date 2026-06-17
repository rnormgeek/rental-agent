from __future__ import annotations

import os

# ── Scoring ───────────────────────────────────────────────────────────────────
MIN_SCORE_TO_NOTIFY: int = int(os.getenv("MIN_SCORE_TO_NOTIFY", "50"))

# ── GCP ───────────────────────────────────────────────────────────────────────
GOOGLE_CLOUD_PROJECT: str = os.environ["GOOGLE_CLOUD_PROJECT"]
GOOGLE_CLOUD_LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION", "europe-west1")

# ── Firestore ─────────────────────────────────────────────────────────────────
FIRESTORE_COLLECTION: str = os.getenv("FIRESTORE_COLLECTION", "approvals")
APPROVAL_TTL_HOURS: int = int(os.getenv("APPROVAL_TTL_HOURS", "48"))

# ── Service ───────────────────────────────────────────────────────────────────
# Full Cloud Run URL, e.g. https://rental-agent-xyz-ew.a.run.app
SERVICE_BASE_URL: str = os.environ["SERVICE_BASE_URL"]

# ── Gmail / Pub/Sub ───────────────────────────────────────────────────────────
PUBSUB_TOPIC: str = os.getenv("PUBSUB_TOPIC", "rental-emails-topic")
RENTAL_ALERT_SENDERS: list[str] = os.getenv(
    "RENTAL_ALERT_SENDERS",
    "alerte@seloger.com,notifications@seloger.com",
).split(",")

# ── Secret Manager — secret IDs (not the values themselves) ──────────────────
SECRET_GMAIL_REFRESH_TOKEN: str = os.getenv(
    "SECRET_GMAIL_REFRESH_TOKEN", "gmail-refresh-token"
)
SECRET_GMAIL_CLIENT_ID: str = os.getenv("SECRET_GMAIL_CLIENT_ID", "gmail-client-id")
SECRET_GMAIL_CLIENT_SECRET: str = os.getenv(
    "SECRET_GMAIL_CLIENT_SECRET", "gmail-client-secret"
)
SECRET_USER_EMAIL: str = os.getenv("SECRET_USER_EMAIL", "user-email")
SECRET_USER_NAME: str = os.getenv("SECRET_USER_NAME", "user-name")

# ── GCS (screenshots) ─────────────────────────────────────────────────────────
GCS_BUCKET: str = os.getenv("GCS_BUCKET", "rental-agent-screenshots")
