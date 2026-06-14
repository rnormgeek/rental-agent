from __future__ import annotations

import functools

from google.cloud import secretmanager

from config import settings


@functools.lru_cache(maxsize=None)
def get_secret(secret_id: str) -> str:
    """Fetch the latest version of a Secret Manager secret (cached per process)."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{settings.GOOGLE_CLOUD_PROJECT}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("utf-8").strip()
