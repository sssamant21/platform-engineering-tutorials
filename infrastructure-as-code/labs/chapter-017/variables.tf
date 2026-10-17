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
    error_message = "owner is required"
  }
}
variable "services" {
  type = map(object({ replicas = number, enabled = bool, tier = string }))
  default = {
    api = { replicas = 2, enabled = true, tier = "frontend" }
    worker = { replicas = 2, enabled = true, tier = "backend" }
  }
  validation {
    condition = length(var.services) > 0 && alltrue([for k, v in var.services : can(regex("^[a-z][a-z0-9-]*$", k)) && v.replicas >= 1 && v.replicas <= 12 && floor(v.replicas) == v.replicas])
    error_message = "services require stable lowercase keys and integer replicas 1–12"
  }
}
variable "tags" {
  type = map(string)
  default = { managed_by = "terraform" }
}
