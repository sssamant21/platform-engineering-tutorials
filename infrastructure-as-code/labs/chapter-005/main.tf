terraform {
  required_version = ">= 1.5.0"
}

variable "environment" {
  type    = string
  default = "lab"
  validation {
    condition     = contains(["lab", "staging"], var.environment)
    error_message = "This lab allows lab or staging only."
  }
}

resource "terraform_data" "governance" {
  input = {
    environment = var.environment
    owner       = "platform-sre"
    cost_center = "training"
    managed_by  = "terraform"
  }
}

output "governance_record" {
  value = terraform_data.governance.output
}
