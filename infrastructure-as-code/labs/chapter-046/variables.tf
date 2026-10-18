variable "environment" {
  type = string
  validation {
    condition = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging or prod"
  }
}
variable "project_id" {
  type = string
  validation {
    condition = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "valid GCP project ID required"
  }
}
variable "project_number" {
  type = string
  validation {
    condition = can(regex("^[0-9]{6,15}$", var.project_number))
    error_message = "valid numeric GCP project number required"
  }
}
variable "region" {
  type = string
  validation {
    condition = contains(["us-central1", "us-east1", "us-east4", "us-west1"], var.region)
    error_message = "approved region required"
  }
}
variable "owner" {
  type = string
  validation {
    condition = length(trimspace(var.owner)) > 0
    error_message = "owner required"
  }
}
variable "change_ticket" {
  type = string
  validation {
    condition = length(trimspace(var.change_ticket)) > 0
    error_message = "change ticket required"
  }
}
variable "billing_reviewed" { type = bool }
variable "org_policy_reviewed" { type = bool }
variable "service_apis_reviewed" { type = bool }
variable "quota_reviewed" { type = bool }
variable "wif_enabled" { type = bool }
variable "static_service_account_key_used" { type = bool }
variable "least_privilege_reviewed" { type = bool }
variable "gcs_state_private" { type = bool }
variable "gcs_state_versioning" { type = bool }
variable "gcs_state_encrypted" { type = bool }
variable "gcs_state_locking" { type = bool }
variable "audit_logs_enabled" { type = bool }
variable "budget_alerts_enabled" { type = bool }
variable "security_approved" { type = bool }
