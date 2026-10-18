variable "environment" {
  type = string
}
variable "cluster_name" {
  type = string
}
variable "namespace" {
  type = string
}
variable "owner" {
  type = string
}
variable "change_ticket" {
  type = string
}
variable "immutable_image" {
  type = bool
}
variable "readiness_probe" {
  type = bool
}
variable "liveness_probe" {
  type = bool
}
variable "startup_probe" {
  type = bool
}
variable "resource_requests" {
  type = bool
}
variable "pdb_reviewed" {
  type = bool
}
variable "hpa_pool_capacity_reviewed" {
  type = bool
}
variable "graceful_shutdown" {
  type = bool
}
variable "stateful_operator_reviewed" {
  type = bool
}
variable "pvc_reclaim_reviewed" {
  type = bool
}
variable "csi_topology_reviewed" {
  type = bool
}
variable "snapshot_policy_reviewed" {
  type = bool
}
variable "backup_tested" {
  type = bool
}
variable "restore_tested" {
  type = bool
}
variable "rpo_rto_measured" {
  type = bool
}
variable "provider_pinned" {
  type = bool
}
variable "chart_version_pinned" {
  type = bool
}
variable "image_digest_pinned" {
  type = bool
}
variable "crd_staged" {
  type = bool
}
variable "chart_rbac_reviewed" {
  type = bool
}
variable "gitops_ownership_defined" {
  type = bool
}
variable "secrets_excluded_from_state" {
  type = bool
}
variable "unapproved_uninstall" {
  type = bool
}
variable "audit_logs_enabled" {
  type = bool
}
variable "monitoring_enabled" {
  type = bool
}
variable "rollback_tested" {
  type = bool
}
variable "dr_runbook_tested" {
  type = bool
}
variable "security_approved" {
  type = bool
}
variable "dbre_approved" {
  type = bool
}
variable "change_approved" {
  type = bool
}
variable "unapproved_destroy" {
  type = bool
}
