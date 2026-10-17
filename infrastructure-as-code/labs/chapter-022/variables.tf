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
    error_message = "owner is required"
  }
}
variable "change_ticket" {
  type = string
  default = "CHG-DEMO-022"
  nullable = false
  validation {
    condition = length(trimspace(var.change_ticket)) > 0
    error_message = "change_ticket is required"
  }
}
