variable "environment" {
  type    = string
  default = "staging"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging or prod."
  }
}
variable "services" {
  type = map(object({
    owner = string
    tier  = string
  }))
  default = {
    api    = { owner = "platform-sre", tier = "frontend" }
    worker = { owner = "data-sre", tier = "backend" }
  }
  validation {
    condition     = length(var.services) > 0 && alltrue([for k, v in var.services : length(trimspace(k)) > 0 && length(trimspace(v.owner)) > 0])
    error_message = "services must have stable, nonempty keys and owners."
  }
}
