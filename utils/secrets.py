from __future__ import annotations

import functools

from google.cloud import secretmanager

from config import settings

secret_manager_service = secretmanager.SecretManagerServiceClient()

@functools.lru_cache(maxsize=None)
def get_secret(client: secretmanager.SecretManagerServiceClient, secret_id: str) -> str:
    """Fetch the latest version of a Secret Manager secret (cached per process)."""
    name = f"projects/{settings.GOOGLE_CLOUD_PROJECT}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("utf-8").strip()
