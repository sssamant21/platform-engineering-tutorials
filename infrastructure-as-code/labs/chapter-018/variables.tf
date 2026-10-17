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
    error_message = "owner cannot be blank"
  }
}
variable "zones" {
  type = list(string)
  default = ["a", "b"]
  nullable = false
  validation {
    condition = length(var.zones) > 0 && length(var.zones) <= 3 && length(distinct(var.zones)) == length(var.zones) && alltrue([for z in var.zones : contains(["a", "b", "c"], z)])
    error_message = "zones must be unique values from a, b, c (1–3 zones)"
  }
}
variable "services" {
  type = map(object({
    replicas = number
    enabled  = bool
    tier     = string
  }))
  default = {
    api    = { replicas = 2, enabled = true, tier = "frontend" }
    worker = { replicas = 2, enabled = true, tier = "backend" }
  }
  nullable = false
  validation {
    condition = length(var.services) > 0 && length(var.services) <= 10 && alltrue([for k, v in var.services : can(regex("^[a-z][a-z0-9-]*$", k)) && v.replicas >= 1 && v.replicas <= 12 && floor(v.replicas) == v.replicas && length(trimspace(v.tier)) > 0])
    error_message = "services must have stable lowercase keys, valid tier and integer replicas 1–12"
  }
}
variable "tags" {
  type = map(string)
  default = { managed_by = "terraform" }
}
