variable "environment" { type = string }
variable "owner" { type = string }
variable "service" { type = string }

resource "terraform_data" "metadata" {
  input = {
    environment = var.environment
    owner       = var.owner
    service     = var.service
    managed_by  = "iac"
  }
}

output "record" {
  value = terraform_data.metadata.output
}
