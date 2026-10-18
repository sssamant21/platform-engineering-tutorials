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
    condition = can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", var.subscription_id))
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
variable "node_vm_size" { type = string }
variable "node_count" {
  type = number
  validation {
    condition = var.node_count >= 1 && var.node_count <= 20 && floor(var.node_count) == var.node_count
    error_message = "node_count must be an integer between 1 and 20"
  }
}
variable "availability_zones" { type = list(string) }
variable "aks_private_cluster" { type = bool }
variable "workload_identity_enabled" { type = bool }
variable "oidc_issuer_enabled" { type = bool }
variable "acr_private" { type = bool }
variable "image_digest_pinned" { type = bool }
variable "pdb_enabled" { type = bool }
variable "autoscaling_enabled" { type = bool }
variable "private_database_access" { type = bool }
variable "diagnostics_enabled" { type = bool }
variable "upgrade_reviewed" { type = bool }
