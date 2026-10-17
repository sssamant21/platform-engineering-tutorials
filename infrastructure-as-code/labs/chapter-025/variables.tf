variable "environment" {
  type     = string
  default  = "dev"
  nullable = false
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging or prod"
  }
}
variable "owner" {
  type     = string
  default  = "platform-sre"
  nullable = false
  validation {
    condition     = length(trimspace(var.owner)) > 0
    error_message = "owner required"
  }
}
variable "change_ticket" {
  type     = string
  default  = "CHG-DEMO-025"
  nullable = false
  validation {
    condition     = length(trimspace(var.change_ticket)) > 0
    error_message = "change ticket required"
  }
}
variable "subnet_ids" {
  type     = map(string)
  default  = { primary = "subnet-lab-a", secondary = "subnet-lab-b" }
  nullable = false
  validation {
    condition     = contains(keys(var.subnet_ids), "primary") && contains(keys(var.subnet_ids), "secondary") && alltrue([for id in values(var.subnet_ids) : length(trimspace(id)) > 0])
    error_message = "primary and secondary subnet IDs required"
  }
}
variable "replicas" {
  type     = number
  default  = 2
  nullable = false
  validation {
    condition     = var.replicas >= 1 && floor(var.replicas) == var.replicas
    error_message = "replicas must be a positive integer"
  }
}
variable "backup_enabled" {
  type     = bool
  default  = true
  nullable = false
}
variable "encryption_enabled" {
  type     = bool
  default  = true
  nullable = false
}
variable "deletion_protection" {
  type     = bool
  default  = true
  nullable = false
}
variable "release" {
  type     = string
  default  = "v1"
  nullable = false
  validation {
    condition     = can(regex("^v[0-9]+$", var.release))
    error_message = "release must be v1, v2, etc"
  }
}
