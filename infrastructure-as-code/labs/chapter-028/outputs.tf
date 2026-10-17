output "environment" {
  value = var.environment
}
output "database_contract" {
  value = terraform_data.database.output
}
output "application_contract" {
  value = terraform_data.application.output
}
