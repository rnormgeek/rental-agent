# rental-agent

An event-driven GCP agent that screens SeLoger rental alerts for Annecy, filters low-score listings, requests human approval for good matches, and then sends the contact form automatically.

## What this does

1. Gmail alert emails arrive in your inbox.
2. Gmail push notifications send events to Cloud Pub/Sub.
3. This service receives the Pub/Sub push and fetches new emails from Gmail.
4. An ADK agent scores each listing against your criteria.
5. Listings below the score threshold are dropped silently and logged.
6. Listings at or above the threshold trigger an approval email.
7. On approval, Playwright fills and submits the SeLoger contact form.
8. If a CAPTCHA appears, the app falls back to an email with a copy-pasteable message for manual send.

## Stack

- Python 3.11+
- FastAPI (HTTP API and webhooks)
- Google ADK + Gemini on Vertex AI
- Gmail API + Pub/Sub push notifications
- Firestore (approval state + TTL)
- Playwright (headless Chromium)
- Secret Manager (credentials and private values)
- Cloud Run (deployment target)

## Architecture

Runtime flow:

1. Gmail -> Pub/Sub topic
2. Pub/Sub push -> POST /pubsub/push
3. Service decodes historyId and pulls new Gmail messages
4. Service extracts listing details and runs ADK agent
5. Agent either:
	 - rejects listing (score < MIN_SCORE_TO_NOTIFY), or
	 - drafts message + creates approval request + emails approval links
6. User clicks either:
	 - GET /approve/{token}, or
	 - GET /reject/{token}
7. Approval path runs Playwright:
	 - submit contact form if no CAPTCHA
	 - fallback email if CAPTCHA is detected

## Repository layout

- main.py: FastAPI app, Pub/Sub ingestion, approval endpoints, watch renewal endpoint
- agent/agent.py: ADK LlmAgent definition and workflow instructions
- agent/tools/: tools for rejection logging, message drafting, approval persistence, approval email
- automation/seloger_form.py: SeLoger form automation and CAPTCHA fallback
- utils/gmail.py: Gmail read/send/watch helpers
- utils/secrets.py: Secret Manager helper
- config/settings.py: environment-driven configuration
- config/criteria.txt: your matching criteria
- config/message_template.txt: contact message template (French)
- infra/setup.sh: one-time GCP provisioning helper
- scripts/gmail_oauth.py: one-time OAuth flow to obtain Gmail refresh token

## Requirements

- GCP project with billing enabled
- gcloud CLI installed and authenticated
- Python 3.11+
- Access to Gmail account receiving SeLoger alerts
- Access to Vertex AI in your selected region

## Local setup

1) Create and activate a virtual environment

		python3 -m venv .venv
		source .venv/bin/activate

2) Install dependencies

		pip install -e .

3) Create local env file

		cp .env.example .env

4) Fill required values in .env

- GOOGLE_CLOUD_PROJECT
- SERVICE_BASE_URL

For local testing, SERVICE_BASE_URL can point to your local tunnel URL.

## Configure your criteria and message template

Edit:

- config/criteria.txt
- config/message_template.txt

The criteria text is used by the agent to score listings from 0 to 100.

## One-time GCP bootstrap

Run:

		bash infra/setup.sh

This script enables APIs, creates Pub/Sub topic, creates Firestore (if needed), creates a bucket for screenshots, creates service account bindings, and creates empty Secret Manager secrets.

After that, follow the script output to:

- add secret values,
- deploy Cloud Run,
- create Pub/Sub push subscription,
- create Cloud Scheduler job for Gmail watch renewal,
- enable Firestore TTL on expiresAt for approvals.

## Gmail OAuth (one time)

1. In Google Cloud Console, create an OAuth Client ID of type Desktop app.
2. Save the JSON credentials file to scripts/credentials.json.
3. Run:

		python scripts/gmail_oauth.py

4. Copy the generated secret values into Secret Manager.

Important: never commit scripts/credentials.json.

## Run locally

Start the API:

		uvicorn main:app --host 0.0.0.0 --port 8080 --reload

Health check:

		curl http://localhost:8080/health

Renew Gmail watch manually:

		curl http://localhost:8080/tasks/renew-watch

If you want to test Pub/Sub locally without OIDC verification:

		export PUBSUB_SKIP_AUTH=true

## API endpoints

- POST /pubsub/push
	- Receives Pub/Sub push messages containing Gmail history updates.
	- Returns 204 for most non-fatal processing cases.
- GET /approve/{token}
	- Marks request approved and triggers Playwright form submission.
- GET /reject/{token}
	- Marks request rejected.
- GET /tasks/renew-watch
	- Calls Gmail users.watch to renew push subscription.
- GET /health
	- Basic liveness endpoint.

## Environment variables

See .env.example for the complete list.

Most important values:

- GOOGLE_CLOUD_PROJECT
- GOOGLE_CLOUD_LOCATION
- SERVICE_BASE_URL
- MIN_SCORE_TO_NOTIFY
- APPROVAL_TTL_HOURS
- FIRESTORE_COLLECTION
- PUBSUB_TOPIC
- RENTAL_ALERT_SENDERS
- GCS_BUCKET
- SECRET_GMAIL_REFRESH_TOKEN
- SECRET_GMAIL_CLIENT_ID
- SECRET_GMAIL_CLIENT_SECRET
- SECRET_USER_EMAIL
- SECRET_USER_NAME
- PUBSUB_SKIP_AUTH (local testing only)

## Score filtering behavior

- Listings with score < MIN_SCORE_TO_NOTIFY:
	- no approval email sent
	- no approval record created
	- rejection is logged for audit

- Listings with score >= MIN_SCORE_TO_NOTIFY:
	- draft is generated
	- approval record is created in Firestore
	- approval email is sent

Default threshold is 50.

## CAPTCHA fallback behavior

If a CAPTCHA is detected during form automation:

1. The app does not submit the form.
2. Firestore status is set to captcha_fallback.
3. A fallback email is sent to you with:
	 - listing URL
	 - draft message
	 - manual send instructions
4. Event is logged.

## Deployment

Build/deploy with Cloud Run from source:

		gcloud run deploy rental-agent \
			--source . \
			--region YOUR_REGION \
			--project YOUR_PROJECT \
			--service-account rental-agent-sa@YOUR_PROJECT.iam.gserviceaccount.com \
			--memory 2Gi --cpu 1 --max-instances 5

Set required environment variables at deploy time (or via service configuration).

## Operational notes

- Gmail watch expires and must be renewed regularly (the scheduler endpoint handles this).
- Firestore TTL should be enabled on approvals.expiresAt.
- Cloud Run BackgroundTasks work for simple async execution; for stronger guarantees, migrate approval execution to Cloud Tasks.

## Troubleshooting

- 401 on POST /pubsub/push:
	- verify Pub/Sub push auth and SERVICE_BASE_URL audience.
- No emails processed:
	- check RENTAL_ALERT_SENDERS and Gmail label/watch configuration.
- No approval emails sent:
	- verify score threshold and Secret Manager values.
- Form not sent:
	- inspect Firestore status values: sent, captcha_fallback, form_error.
- Playwright failures:
	- confirm Cloud Run memory is at least 2Gi and Chromium is installed in image.

## Security

- Keep all secrets in Secret Manager.
- Never commit OAuth credentials or refresh tokens.
- Keep PUBSUB_SKIP_AUTH=false in deployed environments.

## License

No license file is included yet. Add one before open-sourcing.
