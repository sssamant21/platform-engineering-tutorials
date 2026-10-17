output "environment" {
  value = var.environment
}
output "database_contract" {
  value = terraform_data.database.output
}
output "audit_contract" {
  value = terraform_data.audit.output
}
