resource "google_pubsub_subscription" "rental_emails_push" {
  name    = var.pubsub_subscription
  project = var.project_id
  topic   = google_pubsub_topic.rental_emails.id

  ack_deadline_seconds       = 30
  message_retention_duration = "604800s"

  push_config {
    push_endpoint = "${local.integration_service_url}/pubsub/push"

    oidc_token {
      service_account_email = google_service_account.app.email
      audience              = local.integration_service_url
    }
  }

  depends_on = [google_cloud_run_v2_service_iam_member.invoker_sa]
}

resource "google_cloud_scheduler_job" "renew_watch" {
  name      = var.scheduler_job_name
  project   = var.project_id
  region    = var.region
  schedule  = var.scheduler_cron
  time_zone = var.scheduler_time_zone

  http_target {
    http_method = "GET"
    uri         = "${local.integration_service_url}/tasks/renew-watch"

    oidc_token {
      service_account_email = google_service_account.app.email
      audience              = local.integration_service_url
    }
  }

  depends_on = [google_cloud_run_v2_service_iam_member.invoker_sa]
}
