terraform {
  required_version = ">= 1.5.0"
}

variable "environment" {
  type    = string
  default = "lab"
  validation {
    condition     = contains(["lab", "staging"], var.environment)
    error_message = "Only lab and staging are allowed in this exercise."
  }
}

resource "terraform_data" "change" {
  input = {
    environment = var.environment
    ticket      = "CHG-004"
    owner       = "platform-sre"
  }
}

output "change_record" {
  value = terraform_data.change.output
}
