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
variable "least_privilege" { type = bool }
variable "primitive_roles_used" { type = bool }
variable "iam_deny_reviewed" { type = bool }
variable "org_policy_reviewed" { type = bool }
variable "wif_enabled" { type = bool }
variable "static_service_account_keys" { type = bool }
variable "oidc_trust_reviewed" { type = bool }
variable "impersonation_scoped" { type = bool }
variable "kms_enabled" { type = bool }
variable "kms_rotation_reviewed" { type = bool }
variable "kms_recovery_tested" { type = bool }
variable "secret_metadata_only" { type = bool }
variable "secret_payload_in_state" { type = bool }
variable "gcs_state_private" { type = bool }
variable "gcs_state_versioned" { type = bool }
variable "audit_logs_enabled" { type = bool }
variable "security_approved" { type = bool }
variable "dbre_approved" { type = bool }
