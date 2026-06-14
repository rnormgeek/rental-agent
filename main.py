from __future__ import annotations

import base64
import json
import logging
import os
import re
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

# Load .env before config (which reads env vars at import time)
from dotenv import load_dotenv

load_dotenv(override=False)

import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.cloud import firestore
from google.genai import types as genai_types

from agent.agent import create_agent
from automation.seloger_form import fill_seloger_form
from config import settings
from utils import gmail

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── ADK runtime ───────────────────────────────────────────────────────────────
_session_service = InMemorySessionService()
_runner: Runner | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _runner
    agent = create_agent()
    _runner = Runner(
        agent=agent,
        app_name="rental-agent",
        session_service=_session_service,
    )
    yield


app = FastAPI(title="rental-agent", lifespan=lifespan)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _verify_pubsub_token(authorization: str | None) -> bool:
    """Verify the OIDC bearer token sent by Cloud Pub/Sub on push deliveries."""
    if not authorization or not authorization.startswith("Bearer "):
        return False
    # Allow skipping verification during local development
    if os.getenv("PUBSUB_SKIP_AUTH") == "true":
        return True
    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token

        token = authorization[len("Bearer "):]
        audience = f"{settings.SERVICE_BASE_URL}/pubsub/push"
        id_token.verify_oauth2_token(token, google_requests.Request(), audience=audience)
        return True
    except Exception:
        return False


def _get_db() -> firestore.Client:
    return firestore.Client(project=settings.GOOGLE_CLOUD_PROJECT)


def _extract_listing_from_email(html_body: str) -> dict:
    """
    Best-effort extraction of listing fields from a SeLoger alert email.
    The ADK agent receives this structured dict as its input.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_body, "lxml")
    text = soup.get_text(separator="\n", strip=True)

    # Extract the first SeLoger listing URL from anchor tags
    url = ""
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "seloger.com" in href and "/annonces/" in href:
            url = href
            break

    price_match = re.search(r"(\d[\d\s]*\s*[€$](?:\s*/\s*mois)?)", text, re.IGNORECASE)
    size_match = re.search(r"(\d+)\s*m²", text)
    title = soup.title.string.strip() if soup.title and soup.title.string else ""

    return {
        "title": title,
        "url": url,
        "price": price_match.group(1).strip() if price_match else "",
        "size": f"{size_match.group(1)} m²" if size_match else "",
        "location": "Annecy",
        "description": text[:2000],
    }


def _build_agent_prompt(listing: dict) -> str:
    return (
        "Please screen the following rental listing:\n\n"
        f"Title: {listing.get('title', 'N/A')}\n"
        f"URL: {listing.get('url', 'N/A')}\n"
        f"Price: {listing.get('price', 'N/A')}\n"
        f"Size: {listing.get('size', 'N/A')}\n"
        f"Location: {listing.get('location', 'N/A')}\n"
        f"Description:\n{listing.get('description', 'N/A')}"
    )


def _html_page(message: str, color: str = "#333") -> Response:
    html = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<title>Rental Agent</title></head>"
        "<body style='font-family:Arial,sans-serif;display:flex;align-items:center;"
        "justify-content:center;height:100vh;margin:0;'>"
        f"<div style='text-align:center;color:{color};font-size:1.4rem;'>{message}</div>"
        "</body></html>"
    )
    return Response(content=html, media_type="text/html")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.post("/pubsub/push")
async def receive_pubsub_push(request: Request) -> Response:
    """
    Receive Gmail push notifications from Cloud Pub/Sub.
    Decodes the historyId, fetches new messages, and runs the ADK agent
    for each rental alert email.
    Always returns 2xx so Pub/Sub does not retry on application errors.
    """
    auth = request.headers.get("Authorization")
    if not _verify_pubsub_token(auth):
        raise HTTPException(status_code=401, detail="Unauthorized")

    body = await request.json()
    encoded = body.get("message", {}).get("data", "")
    if not encoded:
        return Response(status_code=204)

    try:
        payload = json.loads(
            base64.urlsafe_b64decode(encoded + "==").decode("utf-8")
        )
    except Exception:
        logger.warning("Could not decode Pub/Sub message data")
        return Response(status_code=204)

    history_id = payload.get("historyId")
    if not history_id:
        return Response(status_code=204)

    try:
        messages = gmail.list_new_messages(str(history_id))
    except Exception:
        logger.exception("Failed to fetch Gmail history")
        return Response(status_code=204)

    for message in messages:
        sender = gmail.get_sender(message)
        if not any(s in sender for s in settings.RENTAL_ALERT_SENDERS):
            continue

        html_body = gmail.get_html_body(message)
        if not html_body:
            continue

        listing = _extract_listing_from_email(html_body)
        prompt = _build_agent_prompt(listing)
        session_id = str(uuid.uuid4())

        try:
            await _session_service.create_session(
                app_name="rental-agent", user_id="system", session_id=session_id
            )
            content = genai_types.Content(
                role="user", parts=[genai_types.Part(text=prompt)]
            )
            async for event in _runner.run_async(
                user_id="system",
                session_id=session_id,
                new_message=content,
            ):
                if event.is_final_response():
                    logger.info(
                        "Agent finished for listing",
                        extra={"json_fields": {"url": listing.get("url")}},
                    )
        except Exception:
            logger.exception(
                "Agent error for listing",
                extra={"json_fields": {"url": listing.get("url")}},
            )

    return Response(status_code=204)


@app.get("/approve/{token}")
async def approve(token: str, background_tasks: BackgroundTasks) -> Response:
    """Human approval webhook — triggers Playwright to fill the SeLoger form."""
    db = _get_db()
    doc_ref = db.collection(settings.FIRESTORE_COLLECTION).document(token)
    doc = doc_ref.get()

    if not doc.exists:
        raise HTTPException(status_code=404, detail="Approval request not found")

    data = doc.to_dict()

    if data["status"] != "pending":
        return _html_page(f"This request has already been <strong>{data['status']}</strong>.")

    if data["expiresAt"] < datetime.now(tz=timezone.utc):
        raise HTTPException(status_code=410, detail="Approval request has expired")

    doc_ref.update({"status": "approved", "approvedAt": datetime.now(tz=timezone.utc)})

    listing = data["listing"]
    # NOTE: for higher reliability on long Playwright runs consider replacing
    # BackgroundTasks with a Cloud Tasks HTTP target pointing at a /tasks/fill route.
    background_tasks.add_task(
        fill_seloger_form,
        listing_url=listing["url"],
        draft_message=data["draft_message"],
        token=token,
    )

    return _html_page(
        "✓ Approved! Sending your message to the landlord now…",
        color="#2e7d32",
    )


@app.get("/reject/{token}")
async def reject(token: str) -> Response:
    """Human rejection webhook — marks the request as rejected."""
    db = _get_db()
    doc_ref = db.collection(settings.FIRESTORE_COLLECTION).document(token)
    doc = doc_ref.get()

    if not doc.exists:
        raise HTTPException(status_code=404, detail="Approval request not found")

    data = doc.to_dict()
    if data["status"] != "pending":
        return _html_page(f"This request has already been <strong>{data['status']}</strong>.")

    doc_ref.update({"status": "rejected", "rejectedAt": datetime.now(tz=timezone.utc)})
    return _html_page("✗ Listing rejected.", color="#c62828")


@app.get("/tasks/renew-watch")
async def renew_gmail_watch() -> dict:
    """Called by Cloud Scheduler every 6 days to renew the Gmail push watch."""
    result = gmail.register_watch()
    logger.info("Gmail watch renewed", extra={"json_fields": result})
    return {"status": "ok", "expiration": result.get("expiration")}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)

