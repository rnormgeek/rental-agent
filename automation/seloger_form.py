from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from google.cloud import firestore, storage
from playwright.async_api import async_playwright

from config import settings
from utils import gmail
from utils.secrets import get_secret

logger = logging.getLogger(__name__)

# Selectors that indicate a CAPTCHA widget is present on the page
_CAPTCHA_SELECTORS = [
    "iframe[src*='captcha']",
    "iframe[src*='recaptcha']",
    ".g-recaptcha",
    "[data-hcaptcha-widget-id]",
    "iframe[src*='hcaptcha']",
    "[class*='captcha'][class*='container']",
]

# Candidate selectors for the "contact" button that opens the form
_CONTACT_BUTTON_SELECTORS = [
    "button:has-text('Contacter')",
    "button:has-text('Envoyer un message')",
    "a:has-text('Contacter le propriétaire')",
    "[data-testid='contact-button']",
    "[data-testid='send-message-button']",
]

# Candidate submit button selectors
_SUBMIT_SELECTORS = [
    "button[type='submit']",
    "button:has-text('Envoyer')",
    "button:has-text('Envoyer ma demande')",
    "input[type='submit']",
]


async def _upload_screenshot(screenshot: bytes, token: str) -> str:
    """Upload a PNG screenshot to GCS and return its gs:// URI."""
    client = storage.Client(project=settings.GOOGLE_CLOUD_PROJECT)
    bucket = client.bucket(settings.GCS_BUCKET)
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    blob_name = f"screenshots/{token}/{ts}.png"
    blob = bucket.blob(blob_name)
    await asyncio.to_thread(blob.upload_from_string, screenshot, content_type="image/png")
    return f"gs://{settings.GCS_BUCKET}/{blob_name}"


def _send_captcha_fallback_email(listing_url: str, draft_message: str, token: str) -> None:
    """Email the user the draft message when a CAPTCHA blocks automatic submission."""
    user_email = get_secret(settings.SECRET_USER_EMAIL)
    html_body = f"""
<html>
<body style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:16px;">
  <h2 style="color:#e65100;">⚠️ Action Required — CAPTCHA Detected</h2>
  <p>The rental agent could not automatically send your message because a CAPTCHA
  was encountered on the SeLoger contact form.</p>
  <p><strong>Please send the message manually in 3 steps:</strong></p>
  <ol>
    <li><a href="{listing_url}" style="color:#1565c0;">Open the listing on SeLoger</a></li>
    <li>Click <em>"Contacter"</em> and fill in your details</li>
    <li>Copy and paste the message below into the message field</li>
  </ol>
  <h3 style="margin-bottom:4px;">Your Draft Message</h3>
  <pre style="background:#fff8e1;padding:12px;border-left:3px solid #f9a825;
              white-space:pre-wrap;">{draft_message}</pre>
  <p style="color:#9e9e9e;font-size:12px;">Approval token: {token}</p>
</body>
</html>
"""
    gmail.send_email(
        to=user_email,
        subject="[Rental Agent] Manual Action Required — CAPTCHA on SeLoger",
        html_body=html_body,
    )


async def _fill_field(page, selectors: list[str], value: str) -> None:
    """Try each selector in order and fill the first visible field."""
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if await locator.is_visible(timeout=2_000):
                await locator.fill(value)
                return
        except Exception:
            continue
    logger.warning("Could not fill field — tried selectors: %s", selectors)


async def _click_submit(page) -> None:
    """Click the first visible submit button."""
    for selector in _SUBMIT_SELECTORS:
        try:
            btn = page.locator(selector).first
            if await btn.is_visible(timeout=2_000):
                await btn.click()
                return
        except Exception:
            continue
    raise RuntimeError("Could not find a submit button on the contact form")


async def fill_seloger_form(
    listing_url: str,
    draft_message: str,
    token: str,
) -> None:
    """
    Navigate to the SeLoger listing, open the contact form, fill it in, and
    submit. Detects CAPTCHAs and falls back to a manual-send email if one is
    found. Updates the Firestore document status in all outcomes.

    Args:
        listing_url: Full URL of the SeLoger listing.
        draft_message: The contact message to send.
        token: Firestore approval document ID (used for status updates + screenshots).
    """
    db = firestore.Client(project=settings.GOOGLE_CLOUD_PROJECT)
    doc_ref = db.collection(settings.FIRESTORE_COLLECTION).document(token)

    user_name = get_secret(settings.SECRET_USER_NAME)
    user_email = get_secret(settings.SECRET_USER_EMAIL)
    name_parts = user_name.strip().split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="fr-FR",
        )
        page = await context.new_page()

        try:
            await page.goto(listing_url, wait_until="domcontentloaded", timeout=30_000)

            # Open the contact form
            form_opened = False
            for selector in _CONTACT_BUTTON_SELECTORS:
                try:
                    btn = page.locator(selector).first
                    if await btn.is_visible(timeout=3_000):
                        await btn.click()
                        form_opened = True
                        break
                except Exception:
                    continue

            if not form_opened:
                raise RuntimeError("Could not find the contact button on the listing page")

            await page.wait_for_load_state("networkidle", timeout=10_000)

            # ── CAPTCHA detection ─────────────────────────────────────────────
            for selector in _CAPTCHA_SELECTORS:
                if await page.locator(selector).count() > 0:
                    logger.warning(
                        "CAPTCHA detected on SeLoger form",
                        extra={
                            "json_fields": {
                                "event": "captcha_detected",
                                "token": token,
                                "listing_url": listing_url,
                            }
                        },
                    )
                    screenshot = await page.screenshot(full_page=False)
                    await _upload_screenshot(screenshot, token)
                    await asyncio.to_thread(doc_ref.update, {"status": "captcha_fallback"})
                    await asyncio.to_thread(
                        _send_captcha_fallback_email, listing_url, draft_message, token
                    )
                    return

            # ── Fill the form ─────────────────────────────────────────────────
            await _fill_field(
                page,
                ["[name='firstName']", "[placeholder*='prénom' i]", "#firstName"],
                first_name,
            )
            await _fill_field(
                page,
                ["[name='lastName']", "[placeholder*='nom' i]", "#lastName"],
                last_name,
            )
            await _fill_field(
                page,
                ["[name='email']", "[type='email']", "#email"],
                user_email,
            )
            await _fill_field(
                page,
                ["[name='message']", "textarea", "#message"],
                draft_message,
            )

            # Screenshot before submitting (audit trail)
            screenshot = await page.screenshot(full_page=False)
            gcs_uri = await _upload_screenshot(screenshot, token)
            logger.info(
                "Pre-submit screenshot saved",
                extra={"json_fields": {"gcs_uri": gcs_uri, "token": token}},
            )

            await _click_submit(page)
            await page.wait_for_load_state("networkidle", timeout=10_000)

            await asyncio.to_thread(
                doc_ref.update, {"status": "sent", "screenshotUri": gcs_uri}
            )
            logger.info(
                "Contact form submitted",
                extra={
                    "json_fields": {
                        "event": "form_submitted",
                        "token": token,
                        "listing_url": listing_url,
                    }
                },
            )

        except Exception as exc:
            logger.exception(
                "Error filling SeLoger form",
                extra={
                    "json_fields": {
                        "event": "form_error",
                        "token": token,
                        "error": str(exc),
                    }
                },
            )
            await asyncio.to_thread(
                doc_ref.update, {"status": "form_error", "error": str(exc)}
            )
            raise

        finally:
            await browser.close()
