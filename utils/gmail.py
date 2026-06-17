from __future__ import annotations

import base64
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config import settings
from utils.secrets import get_secret

_GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]


def _get_credentials() -> Credentials:
    return Credentials(
        token=None,
        refresh_token=get_secret(settings.SECRET_GMAIL_REFRESH_TOKEN),
        client_id=get_secret(settings.SECRET_GMAIL_CLIENT_ID),
        client_secret=get_secret(settings.SECRET_GMAIL_CLIENT_SECRET),
        token_uri="https://oauth2.googleapis.com/token",
        scopes=_GMAIL_SCOPES,
    )


def get_gmail_service():
    return build("gmail", "v1", credentials=_get_credentials(), cache_discovery=False)


def register_watch() -> dict:
    """Register a Gmail push notification watch. Must be renewed at least every 7 days."""
    service = get_gmail_service()
    return (
        service.users()
        .watch(
            userId="me",
            body={
                "topicName": (
                    f"projects/{settings.GOOGLE_CLOUD_PROJECT}/topics/{settings.PUBSUB_TOPIC}"
                ),
                "labelIds": ["INBOX"],
                "labelFilterBehavior": "INCLUDE",
            },
        )
        .execute()
    )


def list_new_messages(history_id: str) -> list[dict]:
    """Return full message payloads for messages added since history_id."""
    service = get_gmail_service()
    messages = []
    page_token = None
    while True:
        kwargs: dict = {
            "userId": "me",
            "startHistoryId": history_id,
            "historyTypes": ["messageAdded"],
        }
        if page_token:
            kwargs["pageToken"] = page_token
        history = service.users().history().list(**kwargs).execute()
        for record in history.get("history", []):
            for added in record.get("messagesAdded", []):
                msg_id = added["message"]["id"]
                full = (
                    service.users()
                    .messages()
                    .get(userId="me", id=msg_id, format="full")
                    .execute()
                )
                messages.append(full)
        page_token = history.get("nextPageToken")
        if not page_token:
            break
    return messages



def get_sender(message: dict) -> str:
    """Extract the sender email address from a Gmail message."""
    headers = message.get("payload", {}).get("headers", [])
    for h in headers:
        if h["name"].lower() == "from":
            match = re.search(r"<([^>]+)>", h["value"])
            return match.group(1).lower() if match else h["value"].lower()
    return ""


def get_html_body(message: dict) -> str:
    """Recursively extract the HTML body from a Gmail message payload."""

    def _extract(payload: dict) -> str:
        mime_type = payload.get("mimeType", "")
        if mime_type == "text/html":
            data = payload.get("body", {}).get("data", "")
            padded_data = data + "=" * (-len(data) % 4)
            return base64.urlsafe_b64decode(padded_data).decode("utf-8", errors="replace")
        for part in payload.get("parts", []):
            result = _extract(part)
            if result:
                return result
        return ""

    return _extract(message.get("payload", {}))


def send_email(to: str, subject: str, html_body: str) -> None:
    """Send an HTML email from the authenticated Gmail account."""
    service = get_gmail_service()
    message = MIMEMultipart("alternative")
    message["to"] = to
    message["subject"] = subject
    message.attach(MIMEText(html_body, "html"))
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
