variable "environment" {
  type = string
  nullable = false
  validation {
    condition = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging or prod"
  }
}
variable "tenant_id" {
  type = string
  nullable = false
  validation {
    condition = can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", var.tenant_id))
    error_message = "valid tenant UUID required"
  }
}
variable "subscription_id" {
  type = string
  nullable = false
  validation {
    condition = can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", var.subscription_id))
    error_message = "valid subscription UUID required"
  }
}
variable "location" {
  type = string
  nullable = false
  validation {
    condition = contains(["eastus", "eastus2", "centralus", "westus2"], var.location)
    error_message = "approved Azure region required"
  }
}
variable "owner" {
  type = string
  nullable = false
  validation {
    condition = length(trimspace(var.owner)) > 0
    error_message = "owner required"
  }
}
variable "change_ticket" {
  type = string
  nullable = false
  validation {
    condition = length(trimspace(var.change_ticket)) > 0
    error_message = "change ticket required"
  }
}
variable "oidc_federation_enabled" { type = bool }
variable "static_client_secret_used" { type = bool }
variable "rbac_least_privilege_reviewed" { type = bool }
variable "azure_policy_enabled" { type = bool }
variable "state_encrypted" { type = bool }
variable "state_private" { type = bool }
variable "state_locking_enabled" { type = bool }
variable "activity_logs_enabled" { type = bool }
