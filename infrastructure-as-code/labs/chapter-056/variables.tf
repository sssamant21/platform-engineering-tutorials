variable "environment" {
  type = string
}
variable "root_name" {
  type = string
}
variable "backend_key" {
  type = string
}
variable "owner" {
  type = string
}
variable "change_ticket" {
  type = string
}
variable "tofu_version_pinned" {
  type = bool
}
variable "terraform_version_inventoried" {
  type = bool
}
variable "provider_versions_pinned" {
  type = bool
}
variable "module_sources_reviewed" {
  type = bool
}
variable "state_format_reviewed" {
  type = bool
}
variable "backend_compatibility_reviewed" {
  type = bool
}
variable "plan_parity_reviewed" {
  type = bool
}
variable "state_backup_verified" {
  type = bool
}
variable "restore_tested" {
  type = bool
}
variable "exclusive_writer" {
  type = bool
}
variable "lock_owner_verified" {
  type = bool
}
variable "lineage_serial_recorded" {
  type = bool
}
variable "backend_encrypted" {
  type = bool
}
variable "rollback_documented" {
  type = bool
}
variable "concurrent_writers" {
  type = bool
}
variable "oidc_short_lived" {
  type = bool
}
variable "ci_executor_pinned" {
  type = bool
}
variable "policy_gate_enabled" {
  type = bool
}
variable "drift_reviewed" {
  type = bool
}
variable "secret_state_prohibited" {
  type = bool
}
variable "environment_isolated" {
  type = bool
}
variable "destructive_plan_approved" {
  type = bool
}
variable "dbre_approved" {
  type = bool
}
variable "security_approved" {
  type = bool
}
variable "change_approved" {
  type = bool
}
variable "slo_baseline_recorded" {
  type = bool
}
variable "incident_drill_completed" {
  type = bool
}
variable "monitoring_enabled" {
  type = bool
}
variable "unapproved_destroy" {
  type = bool
}
