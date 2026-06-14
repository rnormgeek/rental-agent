#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# infra/setup.sh — one-time GCP infrastructure provisioning for rental-agent
# Usage:
#   export GOOGLE_CLOUD_PROJECT=my-project-id
#   export GOOGLE_CLOUD_LOCATION=europe-west1   # optional, defaults to us-central1
#   bash infra/setup.sh
# ---------------------------------------------------------------------------
set -euo pipefail

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
SERVICE_NAME="rental-agent"
TOPIC="rental-emails-topic"
SA_NAME="rental-agent-sa"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
GCS_BUCKET="${PROJECT_ID}-rental-agent-screenshots"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Project  : $PROJECT_ID"
echo "  Region   : $REGION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. Enable APIs ────────────────────────────────────────────────────────────
echo ""
echo "==> Enabling required APIs…"
gcloud services enable \
  gmail.googleapis.com \
  pubsub.googleapis.com \
  run.googleapis.com \
  firestore.googleapis.com \
  aiplatform.googleapis.com \
  secretmanager.googleapis.com \
  cloudscheduler.googleapis.com \
  storage.googleapis.com \
  --project "$PROJECT_ID"

# ── 2. Pub/Sub topic ──────────────────────────────────────────────────────────
echo ""
echo "==> Creating Pub/Sub topic '$TOPIC'…"
gcloud pubsub topics create "$TOPIC" --project "$PROJECT_ID" 2>/dev/null || \
  echo "   (topic already exists)"

echo "==> Granting gmail-api-push publisher role on topic…"
gcloud pubsub topics add-iam-policy-binding "$TOPIC" \
  --member="serviceAccount:gmail-api-push@system.gserviceaccount.com" \
  --role="roles/pubsub.publisher" \
  --project "$PROJECT_ID"

# ── 3. Firestore ──────────────────────────────────────────────────────────────
echo ""
echo "==> Creating Firestore database (native mode)…"
gcloud firestore databases create \
  --location="$REGION" \
  --type=firestore-native \
  --project "$PROJECT_ID" 2>/dev/null || \
  echo "   (Firestore database already exists)"

echo "==> NOTE: Enable TTL on the 'approvals' collection manually:"
echo "    gcloud firestore fields ttls update expiresAt \\"
echo "      --collection-group=approvals --project $PROJECT_ID --enable-ttl"

# ── 4. GCS bucket (screenshots) ───────────────────────────────────────────────
echo ""
echo "==> Creating GCS bucket '$GCS_BUCKET'…"
gcloud storage buckets create "gs://$GCS_BUCKET" \
  --location="$REGION" \
  --project "$PROJECT_ID" 2>/dev/null || \
  echo "   (bucket already exists)"

# ── 5. Service account ────────────────────────────────────────────────────────
echo ""
echo "==> Creating service account '$SA_NAME'…"
gcloud iam service-accounts create "$SA_NAME" \
  --display-name="Rental Agent Service Account" \
  --project "$PROJECT_ID" 2>/dev/null || \
  echo "   (service account already exists)"

echo "==> Granting IAM roles…"
for ROLE in \
  roles/aiplatform.user \
  roles/datastore.user \
  roles/secretmanager.secretAccessor \
  roles/pubsub.subscriber \
  roles/storage.objectAdmin \
  roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="$ROLE" \
    --quiet
  echo "   ✓ $ROLE"
done

# ── 6. Secret Manager secrets ─────────────────────────────────────────────────
echo ""
echo "==> Creating Secret Manager secrets (empty — populate manually)…"
for SECRET in gmail-refresh-token gmail-client-id gmail-client-secret user-email user-name; do
  gcloud secrets create "$SECRET" \
    --replication-policy="automatic" \
    --project "$PROJECT_ID" 2>/dev/null || \
    echo "   (secret '$SECRET' already exists)"
done

# ── Summary ───────────────────────────────────────────────────────────────────
cat <<EOF

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Infrastructure ready. Next steps:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Run the OAuth flow to get Gmail credentials:
     python scripts/gmail_oauth.py
   Then store tokens in Secret Manager as shown by that script.

2. Store your name and email:
     echo -n 'your@email.com' | gcloud secrets versions add user-email --data-file=-
     echo -n 'Your Name'      | gcloud secrets versions add user-name  --data-file=-

3. Build and deploy to Cloud Run:
     gcloud run deploy $SERVICE_NAME \\
       --source . \\
       --region $REGION \\
       --project $PROJECT_ID \\
       --service-account $SA_EMAIL \\
       --memory 2Gi --cpu 1 --max-instances 5 \\
       --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID \\
       --set-env-vars GOOGLE_CLOUD_LOCATION=$REGION \\
       --set-env-vars GOOGLE_GENAI_USE_VERTEXAI=TRUE \\
       --set-env-vars GCS_BUCKET=$GCS_BUCKET \\
       --set-env-vars SERVICE_BASE_URL=https://<YOUR_CLOUD_RUN_URL>

4. Register Gmail watch:
     curl -X GET https://<YOUR_CLOUD_RUN_URL>/tasks/renew-watch

5. Create a Cloud Scheduler job to renew the watch every 6 days:
     gcloud scheduler jobs create http rental-agent-watch-renewal \\
       --schedule='0 9 */6 * *' \\
       --uri=https://<YOUR_CLOUD_RUN_URL>/tasks/renew-watch \\
       --http-method=GET \\
       --location=$REGION

6. Create a Pub/Sub push subscription pointing to your Cloud Run endpoint:
     gcloud pubsub subscriptions create rental-emails-sub \\
       --topic=$TOPIC \\
       --push-endpoint=https://<YOUR_CLOUD_RUN_URL>/pubsub/push \\
       --push-auth-service-account=$SA_EMAIL \\
       --project=$PROJECT_ID

7. Enable Firestore TTL on the approvals collection:
     gcloud firestore fields ttls update expiresAt \\
       --collection-group=approvals --project $PROJECT_ID --enable-ttl

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
