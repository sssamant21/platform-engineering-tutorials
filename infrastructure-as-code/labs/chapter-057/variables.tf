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
variable "backend_isolated" {
  type = bool
}

variable "backend_encrypted" {
  type = bool
}

variable "locking_verified" {
  type = bool
}

variable "lineage_recorded" {
  type = bool
}

variable "serial_recorded" {
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

variable "concurrent_writers" {
  type = bool
}

variable "provider_source_pinned" {
  type = bool
}

variable "provider_version_pinned" {
  type = bool
}

variable "lockfile_reviewed" {
  type = bool
}

variable "schema_compatibility_reviewed" {
  type = bool
}

variable "registry_trusted" {
  type = bool
}

variable "auth_short_lived" {
  type = bool
}

variable "unexpected_replacement" {
  type = bool
}

variable "module_sources_pinned" {
  type = bool
}

variable "module_contract_tested" {
  type = bool
}

variable "input_output_reviewed" {
  type = bool
}

variable "address_migrations_reviewed" {
  type = bool
}

variable "transitive_deps_reviewed" {
  type = bool
}

variable "module_rollback_tested" {
  type = bool
}

variable "plan_policy_enabled" {
  type = bool
}

variable "native_plan_adapter_reviewed" {
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
