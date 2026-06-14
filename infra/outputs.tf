output "service_account_email" {
  description = "Service account email used by Cloud Run and push invocations"
  value       = google_service_account.app.email
}

output "pubsub_topic_name" {
  description = "Pub/Sub topic name for Gmail push"
  value       = google_pubsub_topic.rental_emails.name
}

output "pubsub_subscription_name" {
  description = "Pub/Sub push subscription name"
  value       = google_pubsub_subscription.rental_emails_push.name
}

output "scheduler_job_name" {
  description = "Cloud Scheduler renew-watch job name"
  value       = google_cloud_scheduler_job.renew_watch.name
}

output "gcs_bucket_name" {
  description = "GCS bucket name for screenshots"
  value       = google_storage_bucket.screenshots.name
}

output "cloud_run_url" {
  description = "Cloud Run generated service URL"
  value       = google_cloud_run_v2_service.app.uri
}

output "integration_service_url" {
  description = "URL used by Scheduler and Pub/Sub push integrations"
  value       = local.integration_service_url
}
