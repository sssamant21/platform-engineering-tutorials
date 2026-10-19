terraform {
  required_version = ">= 1.6.0"
}
variable "environment" {
  type    = string
  default = "lab"
  validation {
    condition     = contains(["lab", "dev"], var.environment)
    error_message = "Only lab/dev allowed."
  }
}
resource "terraform_data" "metadata" {
  input = { environment = var.environment, owner = "sre-dbre" }
}
output "environment" {
  value = terraform_data.metadata.output.environment
}
