variable "environment" {
  type = string
  validation {
    condition = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging or prod"
  }
}
variable "subscription_id" {
  type = string
  validation {
    condition = can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", var.subscription_id))
    error_message = "valid Azure subscription UUID required"
  }
}
variable "location" {
  type = string
  validation {
    condition = contains(["eastus", "eastus2", "centralus", "westus2"], var.location)
    error_message = "approved location required"
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
variable "postgresql_private" { type = bool }
variable "postgresql_tls" { type = bool }
variable "postgresql_ha" { type = bool }
variable "sql_private" { type = bool }
variable "storage_private" { type = bool }
variable "storage_versioning" { type = bool }
variable "encryption_enabled" { type = bool }
variable "key_vault_purge_protection" { type = bool }
variable "backup_enabled" { type = bool }
variable "pitr_enabled" { type = bool }
variable "restore_drill_tested" { type = bool }
variable "rpo_minutes" {
  type = number
  validation {
    condition = var.rpo_minutes >= 0 && var.rpo_minutes <= 1440
    error_message = "RPO must be between 0 and 1440 minutes"
  }
}
variable "rto_minutes" {
  type = number
  validation {
    condition = var.rto_minutes > 0 && var.rto_minutes <= 1440
    error_message = "RTO must be between 1 and 1440 minutes"
  }
}
variable "diagnostics_enabled" { type = bool }
variable "dbre_approved" { type = bool }
variable "security_approved" { type = bool }
