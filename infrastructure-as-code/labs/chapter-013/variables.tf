variable "environment" {
  type = string
  default = "lab"
  validation {
    condition = contains(["lab", "dev", "staging", "prod"], var.environment)
    error_message = "Use lab, dev, staging or prod."
  }
}
variable "replicas" {
  type = number
  default = 2
  validation {
    condition = var.replicas >= 1 && var.replicas <= 10 && floor(var.replicas) == var.replicas
    error_message = "replicas must be an integer from 1 through 10."
  }
}
