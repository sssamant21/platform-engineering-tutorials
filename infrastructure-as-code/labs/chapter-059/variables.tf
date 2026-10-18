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
variable "graph_acyclic" {
  type = bool
}

variable "output_contracts_reviewed" {
  type = bool
}

variable "upstream_state_verified" {
  type = bool
}

variable "mock_outputs_disabled_prod" {
  type = bool
}

variable "failure_domains_separated" {
  type = bool
}

variable "bounded_parallelism" {
  type = bool
}

variable "graph_reviewed" {
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

variable "toolchain_pinned" {
  type = bool
}

variable "module_revisions_pinned" {
  type = bool
}

variable "oidc_short_lived" {
  type = bool
}

variable "plan_artifact_reviewed" {
  type = bool
}

variable "native_plan_adapter_reviewed" {
  type = bool
}

variable "environment_approval_required" {
  type = bool
}

variable "untrusted_pr_prod_access" {
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
