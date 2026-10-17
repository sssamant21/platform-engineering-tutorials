terraform {
  required_version = ">= 1.5.0"
}

variable "environment" {
  description = "Isolated lab environment"
  type        = string
  default     = "lab"
  validation {
    condition     = contains(["lab", "staging", "prod"], var.environment)
    error_message = "environment must be lab, staging, or prod."
  }
}

variable "team" {
  type    = string
  default = "platform-sre"
}

locals {
  metadata = {
    environment = var.environment
    team        = var.team
    managed_by  = "terraform"
  }
}

resource "terraform_data" "inventory" {
  input = local.metadata
}

output "inventory" {
  value = terraform_data.inventory.output
}
