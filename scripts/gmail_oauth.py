#!/usr/bin/env python3
"""
scripts/gmail_oauth.py — One-time Gmail OAuth2 authorisation flow.

Run this script locally to obtain a refresh token for the Gmail API.
Afterwards, store the credentials in GCP Secret Manager as shown below.

Prerequisites:
  1. In Google Cloud Console → APIs & Services → Credentials, create an
     OAuth 2.0 Client ID of type "Desktop app".
  2. Download the JSON file and save it as credentials.json in this directory.
  3. Run: python scripts/gmail_oauth.py

Usage:
  pip install google-auth-oauthlib
  python scripts/gmail_oauth.py
"""

from __future__ import annotations

from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

CREDENTIALS_FILE = Path(__file__).parent / "credentials.json"


def main() -> None:
    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"OAuth credentials file not found: {CREDENTIALS_FILE}\n"
            "Download it from Google Cloud Console → APIs & Services → Credentials."
        )

    flow = InstalledAppFlow.from_client_secrets_file(
        str(CREDENTIALS_FILE), scopes=SCOPES
    )
    creds = flow.run_local_server(port=0)

    print("\n" + "=" * 60)
    print("  OAuth flow complete. Store these in Secret Manager:")
    print("=" * 60)
    print(f"\nRefresh Token : {creds.refresh_token}")
    print(f"Client ID     : {creds.client_id}")
    print(f"Client Secret : {creds.client_secret}")
    print("\n--- Copy-paste commands: ---")
    print(
        f"echo -n '{creds.refresh_token}' | "
        "gcloud secrets versions add gmail-refresh-token --data-file=-"
    )
    print(
        f"echo -n '{creds.client_id}' | "
        "gcloud secrets versions add gmail-client-id --data-file=-"
    )
    print(
        f"echo -n '{creds.client_secret}' | "
        "gcloud secrets versions add gmail-client-secret --data-file=-"
    )
    print("\nDo NOT commit credentials.json to version control.\n")


if __name__ == "__main__":
    main()
