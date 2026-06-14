from __future__ import annotations

from pathlib import Path

from config import settings
from utils.secrets import get_secret

_TEMPLATE_PATH = Path(__file__).parent.parent.parent / "config" / "message_template.txt"


def draft_contact_message(
    title: str,
    price: str,
    size: str,
    location: str,
    listing_url: str,
) -> str:
    """
    Produce a personalised contact message for a rental listing by filling the
    message template with listing details. The message is in French.

    Args:
        title: Listing title or address.
        price: Monthly rent (e.g. "850 €/mois").
        size: Surface area (e.g. "48 m²").
        location: City or neighbourhood.
        listing_url: URL of the listing page.

    Returns:
        The ready-to-send contact message string.
    """
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    user_name = get_secret(settings.SECRET_USER_NAME)
    return (
        template.replace("{title}", title)
        .replace("{price}", price)
        .replace("{size}", size)
        .replace("{location}", location)
        .replace("{listing_url}", listing_url)
        .replace("{user_name}", user_name)
    )
