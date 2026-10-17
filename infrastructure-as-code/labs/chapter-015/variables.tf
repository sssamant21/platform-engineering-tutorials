variable "environment" {
  type = string
  default = "staging"
  validation {
    condition = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging or prod"
  }
}
variable "replicas" {
  type = number
  default = 2
  validation {
    condition = var.replicas >= 1 && var.replicas <= 10 && floor(var.replicas) == var.replicas
    error_message = "replicas must be an integer from 1 to 10"
  }
}
