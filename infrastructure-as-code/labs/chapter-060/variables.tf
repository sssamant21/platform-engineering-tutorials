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

variable "terraform_baseline_recorded" {
  type = bool
}

variable "provider_versions_pinned" {
  type = bool
}

variable "module_revisions_pinned" {
  type = bool
}

variable "schema_compatibility_reviewed" {
  type = bool
}

variable "migration_rehearsed" {
  type = bool
}

variable "rollback_documented" {
  type = bool
}

variable "backend_keys_unique" {
  type = bool
}

variable "backend_encrypted" {
  type = bool
}

variable "backend_lock_verified" {
  type = bool
}

variable "lineage_serial_recorded" {
  type = bool
}

variable "state_backup_verified" {
  type = bool
}

variable "isolated_restore_tested" {
  type = bool
}

variable "exclusive_writer" {
  type = bool
}

variable "concurrent_writers" {
  type = bool
}

variable "dag_acyclic" {
  type = bool
}

variable "dependency_outputs_reviewed" {
  type = bool
}

variable "prod_mock_outputs_disabled" {
  type = bool
}

variable "bounded_parallelism" {
  type = bool
}

variable "partial_failure_runbook" {
  type = bool
}

variable "gitops_single_writer" {
  type = bool
}

variable "competing_orchestrators" {
  type = bool
}

variable "oidc_short_lived" {
  type = bool
}

variable "native_plan_adapter_reviewed" {
  type = bool
}

variable "plan_policy_enabled" {
  type = bool
}

variable "immutable_artifacts" {
  type = bool
}

variable "environment_approvals" {
  type = bool
}

variable "untrusted_pr_prod_access" {
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

variable "pitr_verified" {
  type = bool
}

variable "rpo_rto_measured" {
  type = bool
}

variable "slo_monitored" {
  type = bool
}

variable "incident_game_day" {
  type = bool
}

variable "unapproved_destroy" {
  type = bool
}
