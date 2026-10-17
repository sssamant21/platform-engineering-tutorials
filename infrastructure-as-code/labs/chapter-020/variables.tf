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
  default = "CHG-DEMO-020"
  nullable = false
  validation {
    condition = length(trimspace(var.change_ticket)) > 0
    error_message = "change_ticket is required"
  }
}
variable "zones" {
  type = list(string)
  default = ["a", "b"]
  nullable = false
  validation {
    condition = length(var.zones) > 0 && length(var.zones) <= 3 && length(distinct(var.zones)) == length(var.zones) && alltrue([for z in var.zones : contains(["a", "b", "c"], z)])
    error_message = "zones must be unique values from a, b, c"
  }
}
variable "services" {
  type = map(object({ replicas = number, enabled = bool, tier = string }))
  default = {
    api = { replicas = 2, enabled = true, tier = "frontend" }
    worker = { replicas = 2, enabled = true, tier = "backend" }
  }
  nullable = false
  validation {
    condition = length(var.services) > 0 && length(var.services) <= 10 && alltrue([for name, svc in var.services : can(regex("^[a-z][a-z0-9-]*$", name)) && svc.replicas >= 1 && svc.replicas <= 12 && floor(svc.replicas) == svc.replicas && length(trimspace(svc.tier)) > 0])
    error_message = "services need stable lowercase keys, nonempty tier and integer replicas 1–12"
  }
}
variable "database_backup_enabled" { type = bool, default = true, nullable = false }
variable "database_encrypted" { type = bool, default = true, nullable = false }
variable "database_deletion_protection" { type = bool, default = true, nullable = false }
variable "database_replicas" {
  type = number
  default = 2
  nullable = false
  validation {
    condition = var.database_replicas >= 0 && floor(var.database_replicas) == var.database_replicas
    error_message = "database_replicas must be a nonnegative integer"
  }
}
variable "tags" { type = map(string), default = { managed_by = "terraform" } }
