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
variable "terragrunt_version_pinned" {
  type = bool
}

variable "tofu_version_pinned" {
  type = bool
}

variable "include_paths_reviewed" {
  type = bool
}

variable "parent_local_scope_reviewed" {
  type = bool
}

variable "environment_inputs_explicit" {
  type = bool
}

variable "module_source_pinned" {
  type = bool
}

variable "effective_config_reviewed" {
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

variable "state_backup_verified" {
  type = bool
}

variable "restore_tested" {
  type = bool
}

variable "account_region_isolated" {
  type = bool
}

variable "concurrent_writers" {
  type = bool
}

variable "graph_acyclic" {
  type = bool
}

variable "dependency_outputs_reviewed" {
  type = bool
}

variable "mock_outputs_disabled_prod" {
  type = bool
}

variable "bounded_parallelism" {
  type = bool
}

variable "partial_failure_runbook" {
  type = bool
}

variable "promotions_approved" {
  type = bool
}

variable "competing_orchestrators" {
  type = bool
}

variable "oidc_short_lived" {
  type = bool
}

variable "policy_gate_enabled" {
  type = bool
}

variable "drift_reviewed" {
  type = bool
}

variable "slo_monitored" {
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

variable "unapproved_destroy" {
  type = bool
}
