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
variable "database_tier" {
  type     = string
  default  = "standard"
  nullable = false
  validation {
    condition     = contains(["standard", "premium"], var.database_tier)
    error_message = "database_tier must be standard or premium"
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
    error_message = "replicas must be a positive integer"
  }
}
