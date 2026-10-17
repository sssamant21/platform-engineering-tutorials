variable "environment" {
  type = string
  default = "dev"
  nullable = false
  validation {
    condition = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging or prod"
  }
}
variable "service" {
  type = string
  default = "patient-api"
  nullable = false
  validation {
    condition = can(regex("^[a-z][a-z0-9-]*$", var.service))
    error_message = "service must use lowercase letters, digits and hyphens"
  }
}
variable "owner" {
  type = string
  default = "platform-sre"
  nullable = false
  validation {
    condition = length(trimspace(var.owner)) > 0
    error_message = "owner cannot be blank"
  }
}
variable "change_ticket" {
  type = string
  default = "CHG-DEMO-019"
  nullable = false
  validation {
    condition = length(trimspace(var.change_ticket)) > 0
    error_message = "change_ticket cannot be blank"
  }
}
variable "replicas" {
  type = number
  default = 2
  nullable = false
  validation {
    condition = var.replicas >= 1 && var.replicas <= 12 && floor(var.replicas) == var.replicas
    error_message = "replicas must be an integer between 1 and 12"
  }
}
variable "display_name" {
  type = string
  default = null
}
variable "backup_enabled" {
  type = bool
  default = true
  nullable = false
}
variable "encryption_enabled" {
  type = bool
  default = true
  nullable = false
}
variable "deletion_protection" {
  type = bool
  default = true
  nullable = false
}
variable "database" {
  type = object({
    engine = optional(string, "postgres")
    backup_enabled = optional(bool)
    replicas = optional(number)
  })
  default = {}
}
