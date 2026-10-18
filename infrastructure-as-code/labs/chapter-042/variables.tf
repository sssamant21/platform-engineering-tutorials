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
    error_message = "approved Azure location required"
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
variable "vnet_cidr" {
  type = string
  validation {
    condition = can(cidrhost(var.vnet_cidr, 0))
    error_message = "valid VNet CIDR required"
  }
}
variable "aks_subnet_cidr" {
  type = string
  validation {
    condition = can(cidrhost(var.aks_subnet_cidr, 0))
    error_message = "valid AKS subnet CIDR required"
  }
}
variable "app_subnet_cidr" {
  type = string
  validation {
    condition = can(cidrhost(var.app_subnet_cidr, 0))
    error_message = "valid app subnet CIDR required"
  }
}
variable "endpoint_subnet_cidr" {
  type = string
  validation {
    condition = can(cidrhost(var.endpoint_subnet_cidr, 0))
    error_message = "valid private endpoint subnet CIDR required"
  }
}
variable "database_subnet_cidr" {
  type = string
  validation {
    condition = can(cidrhost(var.database_subnet_cidr, 0))
    error_message = "valid database subnet CIDR required"
  }
}
variable "nsg_reviewed" { type = bool }
variable "udr_reviewed" { type = bool }
variable "private_endpoint_enabled" { type = bool }
variable "private_dns_linked" { type = bool }
variable "database_subnet_delegated" { type = bool }
variable "public_database_access_disabled" { type = bool }
variable "flow_logs_enabled" { type = bool }
