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
variable "provider_pinned" {
  type = bool
}
variable "chart_version_pinned" {
  type = bool
}
variable "repository_verified" {
  type = bool
}
variable "image_digest_pinned" {
  type = bool
}
variable "chart_render_reviewed" {
  type = bool
}
variable "chart_rbac_reviewed" {
  type = bool
}
variable "chart_hooks_reviewed" {
  type = bool
}
variable "crd_staged" {
  type = bool
}
variable "rollout_health_checked" {
  type = bool
}
variable "rollback_tested" {
  type = bool
}
variable "pdb_reviewed" {
  type = bool
}
variable "secrets_excluded_from_state" {
  type = bool
}
variable "unapproved_uninstall" {
  type = bool
}
variable "unapproved_crd_delete" {
  type = bool
}
variable "owner_registry" {
  type = bool
}
variable "single_reconciler" {
  type = bool
}
variable "drift_reviewed" {
  type = bool
}
variable "handoff_documented" {
  type = bool
}
variable "policy_gate_enabled" {
  type = bool
}
variable "competing_reconciler" {
  type = bool
}
variable "audit_logs_enabled" {
  type = bool
}
variable "monitoring_enabled" {
  type = bool
}
variable "backup_tested" {
  type = bool
}
variable "rpo_rto_measured" {
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
