variable "environment" {
  type        = string
  default     = "dev"
  nullable    = false
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging or prod"
  }
}
variable "service" {
  type     = string
  default  = "patient-api"
  nullable = false
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]*$", var.service))
    error_message = "service must use lowercase letters, digits and hyphens"
  }
}
variable "owner" {
  type     = string
  default  = "platform-sre"
  nullable = false
  validation {
    condition     = length(trimspace(var.owner)) > 0
    error_message = "owner must not be blank"
  }
}
variable "replicas" {
  type     = number
  default  = 2
  nullable = false
  validation {
    condition     = var.replicas >= 1 && var.replicas <= 12 && floor(var.replicas) == var.replicas
    error_message = "replicas must be an integer from 1 to 12"
  }
}
variable "zones" {
  type     = list(string)
  default  = ["a", "b"]
  nullable = false
  validation {
    condition     = length(var.zones) > 0 && alltrue([for z in var.zones : length(trimspace(z)) > 0])
    error_message = "zones must be nonempty and cannot contain blanks"
  }
}
variable "tags" {
  type = map(string)
  default = {
    cost_center = "demo"
    managed_by  = "terraform"
  }
}
variable "database" {
  type = object({
    encrypted       = bool
    backup_enabled  = bool
    replica_count   = number
    engine          = optional(string, "postgres")
  })
  default = {
    encrypted      = true
    backup_enabled = true
    replica_count  = 2
  }
  validation {
    condition     = var.database.replica_count >= 0 && floor(var.database.replica_count) == var.database.replica_count
    error_message = "database replica_count must be a nonnegative integer"
  }
}
