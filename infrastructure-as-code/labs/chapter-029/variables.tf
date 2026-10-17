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
variable "backup_enabled" {
  type     = bool
  default  = true
  nullable = false
}
variable "replicas" {
  type     = number
  default  = 2
  nullable = false
  validation {
    condition     = var.replicas >= 1 && floor(var.replicas) == var.replicas
    error_message = "replicas must be positive integer"
  }
}
variable "change_ticket" {
  type     = string
  default  = "CHG-DEMO-029"
  nullable = false
  validation {
    condition     = length(trimspace(var.change_ticket)) > 0
    error_message = "change ticket required"
  }
}
