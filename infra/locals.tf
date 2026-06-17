locals {
  required_services = toset([
    "gmail.googleapis.com",
    "pubsub.googleapis.com",
    "run.googleapis.com",
    "firestore.googleapis.com",
    "aiplatform.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudscheduler.googleapis.com",
    "storage.googleapis.com",
    "cloudtrace.googleapis.com",
  ])

  sa_roles = toset([
    "roles/aiplatform.user",
    "roles/datastore.user",
    "roles/secretmanager.secretAccessor",
    "roles/pubsub.subscriber",
    "roles/storage.objectAdmin",
    "roles/logging.logWriter",
    "roles/cloudtrace.agent",
  ])

  secrets = {
    "gmail-refresh-token" = var.secret_ids.gmail_refresh_token
    "gmail-client-id"     = var.secret_ids.gmail_client_id
    "gmail-client-secret" = var.secret_ids.gmail_client_secret
    "user-email"          = var.secret_ids.user_email
    "user-name"           = var.secret_ids.user_name
  }

  screenshot_bucket_name    = coalesce(var.gcs_bucket_name, "${var.project_id}-rental-agent-screenshots")
  integration_service_url   = coalesce(var.service_base_url, google_cloud_run_v2_service.app.uri)
  app_service_base_url_env  = coalesce(var.service_base_url, "https://placeholder.invalid")
}
