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
variable "owner" { type = string }
variable "change_ticket" { type = string }
variable "mig_regional" { type = bool }
variable "mig_autohealing" { type = bool }
variable "mig_autoscaling" { type = bool }
variable "vm_shielded" { type = bool }
variable "vm_public_ip" { type = bool }
variable "vm_os_login" { type = bool }
variable "gke_private_nodes" { type = bool }
variable "gke_private_endpoint_reviewed" { type = bool }
variable "gke_workload_identity" { type = bool }
variable "gke_network_policy" { type = bool }
variable "gke_release_channel_reviewed" { type = bool }
variable "gke_pdb_reviewed" { type = bool }
variable "gke_autoscaling_reviewed" { type = bool }
variable "static_service_account_keys" { type = bool }
variable "app_ingress_tls" { type = bool }
variable "app_health_checks" { type = bool }
variable "app_image_digest_pinned" { type = bool }
variable "app_secret_payload_in_state" { type = bool }
variable "db_private_connectivity_reviewed" { type = bool }
variable "db_connection_pooling_reviewed" { type = bool }
variable "monitoring_enabled" { type = bool }
variable "audit_logs_enabled" { type = bool }
variable "rollback_tested" { type = bool }
variable "dbre_approved" { type = bool }
variable "security_approved" { type = bool }
