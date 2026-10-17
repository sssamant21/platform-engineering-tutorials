output "environment" {
  value = var.environment
}
output "resource_contract" {
  value = {
    network     = terraform_data.network.output
    database    = terraform_data.database.output
    application = terraform_data.application.output
  }
}
