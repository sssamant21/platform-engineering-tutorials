terraform {
  required_version = ">= 1.5.0"
}

variable "environment" {
  type    = string
  default = "lab"
  validation {
    condition     = contains(["lab", "staging"], var.environment)
    error_message = "Only lab and staging are allowed."
  }
}

resource "terraform_data" "desired" {
  input = {
    environment = var.environment
    owner       = "sre-platform"
  }
}

output "observed" {
  value = terraform_data.desired.output
}
