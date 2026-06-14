resource "google_cloud_run_v2_service" "app" {
  name     = var.service_name
  location = var.region
  project  = var.project_id
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.app.email

    scaling {
      max_instance_count = var.cloud_run_max_instances
    }

    containers {
      image = var.cloud_run_image

      resources {
        limits = {
          cpu    = var.cloud_run_cpu
          memory = var.cloud_run_memory
        }
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }

      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.region
      }

      env {
        name  = "GOOGLE_GENAI_USE_VERTEXAI"
        value = "TRUE"
      }

      env {
        name  = "GCS_BUCKET"
        value = google_storage_bucket.screenshots.name
      }

      env {
        name  = "SERVICE_BASE_URL"
        value = local.app_service_base_url_env
      }

      env {
        name  = "PUBSUB_TOPIC"
        value = google_pubsub_topic.rental_emails.name
      }

      env {
        name  = "MIN_SCORE_TO_NOTIFY"
        value = tostring(var.min_score_to_notify)
      }

      env {
        name  = "APPROVAL_TTL_HOURS"
        value = tostring(var.approval_ttl_hours)
      }

      env {
        name  = "FIRESTORE_COLLECTION"
        value = var.firestore_collection
      }

      env {
        name  = "RENTAL_ALERT_SENDERS"
        value = var.rental_alert_senders
      }

      env {
        name  = "SECRET_GMAIL_REFRESH_TOKEN"
        value = var.secret_ids.gmail_refresh_token
      }

      env {
        name  = "SECRET_GMAIL_CLIENT_ID"
        value = var.secret_ids.gmail_client_id
      }

      env {
        name  = "SECRET_GMAIL_CLIENT_SECRET"
        value = var.secret_ids.gmail_client_secret
      }

      env {
        name  = "SECRET_USER_EMAIL"
        value = var.secret_ids.user_email
      }

      env {
        name  = "SECRET_USER_NAME"
        value = var.secret_ids.user_name
      }
    }
  }

  depends_on = [
    google_project_service.required,
    google_project_iam_member.app_roles,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "invoker_sa" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.app.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.app.email}"
}
