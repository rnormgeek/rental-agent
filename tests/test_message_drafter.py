from __future__ import annotations

from pathlib import Path

from agent.tools import message_drafter


def test_draft_contact_message_renders_all_placeholders(
    tmp_path: Path,
    monkeypatch,
) -> None:
    template = (
        "Titre: {title}\n"
        "Prix: {price}\n"
        "Surface: {size}\n"
        "Lieu: {location}\n"
        "Lien: {listing_url}\n"
        "Nom: {user_name}\n"
    )
    template_path = tmp_path / "template.txt"
    template_path.write_text(template, encoding="utf-8")

    monkeypatch.setattr(message_drafter, "_TEMPLATE_PATH", template_path)
    monkeypatch.setattr(message_drafter, "get_secret", lambda *_args, **_kwargs: "Jane Doe")

    rendered = message_drafter.draft_contact_message(
        title="T2 Annecy",
        price="1000 €/mois",
        size="48 m²",
        location="Annecy",
        listing_url="https://example.test/ad",
    )

    assert "{title}" not in rendered
    assert "T2 Annecy" in rendered
    assert "1000 €/mois" in rendered
    assert "48 m²" in rendered
    assert "https://example.test/ad" in rendered
    assert "Jane Doe" in rendered
