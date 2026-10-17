variable "environment" {
  type     = string
  default  = "dev"
  nullable = false
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging or prod"
  }
}
variable "owner" {
  type     = string
  default  = "platform-sre"
  nullable = false
  validation {
    condition     = length(trimspace(var.owner)) > 0
    error_message = "owner required"
  }
}
variable "backend_type" {
  type     = string
  default  = "local"
  nullable = false
  validation {
    condition     = contains(["local", "s3", "azurerm", "gcs", "remote"], var.backend_type)
    error_message = "unsupported backend type"
  }
}
variable "change_ticket" {
  type     = string
  default  = "CHG-DEMO-027"
  nullable = false
  validation {
    condition     = length(trimspace(var.change_ticket)) > 0
    error_message = "change ticket required"
  }
}
