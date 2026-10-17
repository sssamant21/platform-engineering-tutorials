output "network_contract" {
  value = module.network.contract
}
output "database_contract" {
  value = module.database.contract
}
output "application_contract" {
  value = terraform_data.application.output
}
output "monitoring_contract" {
  value = terraform_data.monitoring.output
}
output "audit_contract" {
  value = terraform_data.audit.output
}
