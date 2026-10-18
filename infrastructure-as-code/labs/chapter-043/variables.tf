variable "environment" {
  type = string
  validation {
    condition = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging or prod"
  }
}
variable "tenant_id" {
  type = string
  validation {
    condition = can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", var.tenant_id))
    error_message = "valid tenant UUID required"
  }
}
variable "subscription_id" {
  type = string
  validation {
    condition = can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", var.subscription_id))
    error_message = "valid subscription UUID required"
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
variable "oidc_federation_enabled" { type = bool }
variable "static_client_secret_used" { type = bool }
variable "rbac_least_privilege_reviewed" { type = bool }
variable "privileged_role_assignment_used" { type = bool }
variable "managed_identity_enabled" { type = bool }
variable "key_vault_rbac_enabled" { type = bool }
variable "key_vault_private" { type = bool }
variable "key_vault_purge_protection" { type = bool }
variable "secret_rotation_enabled" { type = bool }
variable "cmk_recovery_tested" { type = bool }
variable "state_encrypted" { type = bool }
variable "state_private" { type = bool }
variable "audit_logs_enabled" { type = bool }
