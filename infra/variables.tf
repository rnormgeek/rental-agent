variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "Primary GCP region"
  type        = string
  default     = "europe-west1"
}

variable "service_name" {
  description = "Cloud Run service name"
  type        = string
  default     = "rental-agent"
}

variable "pubsub_topic" {
  description = "Pub/Sub topic receiving Gmail watch notifications"
  type        = string
  default     = "rental-emails-topic"
}

variable "pubsub_subscription" {
  description = "Pub/Sub push subscription name"
  type        = string
  default     = "rental-emails-sub"
}

variable "scheduler_job_name" {
  description = "Cloud Scheduler job name for watch renewal"
  type        = string
  default     = "rental-agent-watch-renewal"
}

variable "scheduler_cron" {
  description = "Cron schedule used to renew Gmail watch"
  type        = string
  default     = "0 9 */6 * *"
}

variable "scheduler_time_zone" {
  description = "Scheduler timezone"
  type        = string
  default     = "Etc/UTC"
}

variable "sa_name" {
  description = "Service account ID used by Cloud Run and push invocations"
  type        = string
  default     = "rental-agent-sa"
}

variable "gcs_bucket_name" {
  description = "Optional override for screenshot bucket name"
  type        = string
  default     = null
  nullable    = true
}

variable "cloud_run_image" {
  description = "Container image for Cloud Run deployment"
  type        = string
}

variable "cloud_run_memory" {
  description = "Cloud Run container memory limit"
  type        = string
  default     = "2Gi"
}

variable "cloud_run_cpu" {
  description = "Cloud Run container CPU limit"
  type        = string
  default     = "1"
}

variable "cloud_run_max_instances" {
  description = "Cloud Run max instance count"
  type        = number
  default     = 5
}

variable "service_base_url" {
  description = "Public base URL used in approval links. If null, integrations use Cloud Run generated URL."
  type        = string
  default     = null
  nullable    = true
}

variable "min_score_to_notify" {
  description = "MIN_SCORE_TO_NOTIFY environment value"
  type        = number
  default     = 50
}

variable "approval_ttl_hours" {
  description = "APPROVAL_TTL_HOURS environment value"
  type        = number
  default     = 48
}

variable "firestore_collection" {
  description = "Firestore collection used for approvals"
  type        = string
  default     = "approvals"
}

variable "rental_alert_senders" {
  description = "Comma-separated list for RENTAL_ALERT_SENDERS"
  type        = string
  default     = "alerte@seloger.com,notifications@seloger.com"
}

variable "secret_ids" {
  description = "Secret Manager secret IDs created as empty containers"
  type        = object({
    gmail_refresh_token = string
    gmail_client_id     = string
    gmail_client_secret = string
    user_email          = string
    user_name           = string
  })
  default = {
    gmail_refresh_token = "gmail-refresh-token"
    gmail_client_id     = "gmail-client-id"
    gmail_client_secret = "gmail-client-secret"
    user_email          = "user-email"
    user_name           = "user-name"
  }
}
