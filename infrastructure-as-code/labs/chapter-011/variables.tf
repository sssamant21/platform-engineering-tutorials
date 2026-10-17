variable "environment" {
  type = string
  default = "staging"
  validation {
    condition = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging or prod"
  }
}
variable "service" {
  type = string
  default = "patient-api"
  validation {
    condition = can(regex("^[a-z][a-z0-9-]*$", var.service))
    error_message = "service must be lowercase letters, digits and hyphens"
  }
}
variable "owner" {
  type = string
  default = "platform-sre"
  validation {
    condition = length(trimspace(var.owner)) > 0
    error_message = "owner must not be empty"
  }
}
variable "replicas" {
  type = number
  default = 3
  validation {
    condition = var.replicas >= 0 && var.replicas <= 20 && floor(var.replicas) == var.replicas
    error_message = "replicas must be an integer between 0 and 20"
  }
}
variable "zones" {
  type = list(string)
  default = ["A", "B"]
  validation {
    condition = length(var.zones) > 0 && alltrue([for z in var.zones : length(trimspace(z)) > 0])
    error_message = "zones cannot contain blank values"
  }
}
