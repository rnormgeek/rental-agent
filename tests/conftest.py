from __future__ import annotations

import os
import sys
from pathlib import Path
from collections.abc import Callable

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Ensure required config vars exist before application modules import `config.settings`.
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "test-project")
os.environ.setdefault("SERVICE_BASE_URL", "https://example.test")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "europe-west1")
os.environ.setdefault("FIRESTORE_COLLECTION", "approvals")
os.environ.setdefault("APPROVAL_TTL_HOURS", "48")
os.environ.setdefault("MIN_SCORE_TO_NOTIFY", "50")
os.environ.setdefault("PUBSUB_TOPIC", "rental-emails-topic")


class FakeDocumentSnapshot:
    def __init__(self, data: dict | None = None, exists: bool = True):
        self._data = data or {}
        self.exists = exists

    def to_dict(self) -> dict:
        return self._data


class FakeDocumentRef:
    def __init__(self):
        self.data: dict = {}
        self.exists = False

    def set(self, payload: dict) -> None:
        self.data = payload
        self.exists = True

    def update(self, payload: dict) -> None:
        self.data.update(payload)
        self.exists = True

    def get(self) -> FakeDocumentSnapshot:
        return FakeDocumentSnapshot(data=self.data, exists=self.exists)


class FakeCollection:
    def __init__(self):
        self.documents: dict[str, FakeDocumentRef] = {}

    def document(self, token: str) -> FakeDocumentRef:
        if token not in self.documents:
            self.documents[token] = FakeDocumentRef()
        return self.documents[token]


class FakeFirestoreClient:
    def __init__(self):
        self.collections: dict[str, FakeCollection] = {}

    def collection(self, name: str) -> FakeCollection:
        if name not in self.collections:
            self.collections[name] = FakeCollection()
        return self.collections[name]


@pytest.fixture
def sample_listing() -> dict:
    return {
        "listing_url": "https://www.seloger.com/annonces/location/appartement/annecy-74/123456789.htm",
        "title": "T2 lumineux centre Annecy",
        "price": "1 050 €/mois",
        "size": "49 m²",
        "location": "Annecy",
        "description": "Appartement calme avec balcon proche du lac.",
        "score": 82,
        "score_reasons": [
            "Budget within range",
            "Good surface for a T2",
            "Location matches target area",
        ],
        "draft_message": "Bonjour, je suis intéressé(e) par votre annonce.",
    }


@pytest.fixture
def fake_firestore() -> FakeFirestoreClient:
    return FakeFirestoreClient()


@pytest.fixture
def secret_lookup() -> Callable[[str], str]:
    values = {
        "user-email": "user@example.test",
        "user-name": "Jane Doe",
        "gmail-refresh-token": "refresh-token",
        "gmail-client-id": "client-id",
        "gmail-client-secret": "client-secret",
    }

    def _lookup(secret_id: str) -> str:
        return values[secret_id]

    return _lookup
