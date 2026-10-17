terraform {
  required_version = ">= 1.5.0"
}

variable "environment" {
  type    = string
  default = "lab"
  validation {
    condition     = contains(["lab", "staging"], var.environment)
    error_message = "Only lab or staging is allowed in this exercise."
  }
}

resource "terraform_data" "tool_selection" {
  input = {
    environment = var.environment
    tool_family = "declarative-provisioning"
    owner       = "sre-platform"
  }
}

output "selection" {
  value = terraform_data.tool_selection.output
}
