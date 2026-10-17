variable "environment" {
  type = string
  nullable = false
  validation {
    condition = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging or prod"
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
variable "network_cidr" {
  type = string
  nullable = false
  validation {
    condition = can(cidrhost(var.network_cidr, 0))
    error_message = "network_cidr must be valid CIDR"
  }
}
variable "database_replicas" {
  type = number
  nullable = false
  validation {
    condition = var.database_replicas >= 1 && floor(var.database_replicas) == var.database_replicas
    error_message = "database_replicas must be a positive integer"
  }
}
variable "backup_enabled" {
  type = bool
  nullable = false
}
variable "encryption_enabled" {
  type = bool
  nullable = false
}
variable "change_ticket" {
  type = string
  nullable = false
  validation {
    condition = length(trimspace(var.change_ticket)) > 0
    error_message = "change ticket required"
  }
}
