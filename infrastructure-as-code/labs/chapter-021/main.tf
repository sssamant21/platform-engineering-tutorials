locals {
  identity_contract = {
    environment = var.environment
    owner = var.owner
    identity_reference = var.identity_reference
    provider_source = "terraform.io/builtin/terraform"
    external_cloud_credentials_required = false
  }
}
resource "terraform_data" "identity_contract" {
  input = local.identity_contract
}
resource "terraform_data" "audit" {
  input = {
    environment = var.environment
    owner = var.owner
    identity_record = terraform_data.identity_contract.output.identity_reference
  }
}
