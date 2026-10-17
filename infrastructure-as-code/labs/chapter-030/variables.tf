variable "environment" {
  type = string
  default = "dev"
  nullable = false
  validation {
    condition = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging or prod"
  }
}
variable "owner" {
  type = string
  default = "platform-sre"
  nullable = false
  validation {
    condition = length(trimspace(var.owner)) > 0
    error_message = "owner must be nonempty"
  }
}
variable "replicas" {
  type = number
  default = 2
  nullable = false
  validation {
    condition = var.replicas >= 1 && floor(var.replicas) == var.replicas
    error_message = "replicas must be a positive integer"
  }
}
variable "backup_enabled" {
  type = bool
  default = true
  nullable = false
}
variable "change_ticket" {
  type = string
  default = "CHG-DEMO-030"
  nullable = false
  validation {
    condition = length(trimspace(var.change_ticket)) > 0
    error_message = "change_ticket is required"
  }
}
